"""
Flask Application for GKE Deployment - Media Generator API
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import json
import datetime
from google.cloud import storage
from google.oauth2 import service_account
import tempfile
import logging
import shutil
import subprocess
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configure CORS to allow requests from Angular development server
CORS(app, origins=['http://localhost:4200', 'http://127.0.0.1:4200'])

def get_gcs_client():
    """
    Initialize and return a Google Cloud Storage client with proper authentication.

    Returns:
        storage.Client: Authenticated GCS client

    Raises:
        Exception: If authentication fails
    """
    service_account_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')

    if service_account_path and os.path.exists(service_account_path):
        # Use service account file if available
        credentials = service_account.Credentials.from_service_account_file(service_account_path)
        client = storage.Client(credentials=credentials)
    else:
        # Try default credentials (for development, you'll need to run: gcloud auth application-default login)
        logger.warning(f"Service account file not found at: {service_account_path}. Trying default credentials instead.")
        client = storage.Client()

    return client

def download_files_from_gcs(bucket_name, file_paths, local_dir):
    """
    Download files from Google Cloud Storage

    Args:
        bucket_name: Name of the GCS bucket
        file_paths: List of GCS file paths (e.g., ['videos/test_user/file1.mp4', 'audio/test_user/track.mp3'])
        local_dir: Local directory to download files to

    Returns:
        List of local file paths
    """
    client = get_gcs_client()
    bucket = client.bucket(bucket_name)

    downloaded_files = []

    for file_path in file_paths:
        # Create the blob object using the full GCS path
        blob = bucket.blob(file_path)

        # Check if blob exists
        if not blob.exists():
            raise FileNotFoundError(f'File does not exist in GCS: {file_path}')

        # Create local filename preserving the original filename
        local_filename = os.path.basename(file_path)
        local_file_path = os.path.join(local_dir, local_filename)

        # Download the file
        blob.download_to_filename(local_file_path)

        downloaded_files.append(local_file_path)
        logger.info(f"Successfully downloaded {file_path} to {local_file_path}")

    return downloaded_files


def get_video_dimensions(video_path):
    """
    Get video dimensions using ffprobe

    Args:
        video_path: Path to video file

    Returns:
        tuple: (width, height) or (0, 0) if error
    """
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_streams',
            '-select_streams', 'v:0', video_path
        ]
        logger.info(f"Executing ffprobe command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)
            if 'streams' in data and len(data['streams']) > 0:
                stream = data['streams'][0]
                width = int(stream.get('width', 0))
                height = int(stream.get('height', 0))
                return width, height

        return 0, 0
    except Exception as e:
        logger.error(f"Error getting video dimensions for {video_path}: {e}")
        return 0, 0


def combine_videos_with_ffmpeg(vclip_timeline, downloaded_videos, downloaded_audio_file, temp_dir):
    """
    Combine video clips using FFmpeg according to timeline specifications

    Args:
        vclip_timeline: List of video clips with timing information
        downloaded_videos: List of local video file paths
        downloaded_audio_file: Local path to audio file (optional)
        temp_dir: Temporary directory for processing

    Returns:
        dict: Video creation results with success status, filename, size, and duration
    """
    output_filename = f"combined_video_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    output_path = os.path.join(temp_dir, output_filename)

    # Build FFmpeg command for video concatenation with performance optimizations
    ffmpeg_cmd = [
        'ffmpeg',
        '-y',                       # Overwrite output file
        '-hide_banner',             # Hide FFmpeg banner (cleaner output)
        '-loglevel', 'error',       # Only show errors (reduces overhead)
        '-hwaccel', 'auto'          # Use hardware acceleration if available
    ]

    # First pass: collect unique video files and find maximum dimensions
    unique_videos = {}  # filename -> {path, width, height, needs_scaling}
    max_width = 0
    max_height = 0

    for clip in vclip_timeline:
        # Find matching downloaded video file
        local_path = None
        clip_filename = os.path.basename(clip['gcs_path'])
        for video_path in downloaded_videos:
            if os.path.basename(video_path) == clip_filename:
                local_path = video_path
                break

        if not local_path:
            raise Exception(f"No downloaded video file found for timeline clip: {clip_filename} (gcs_path: {clip['gcs_path']})")

        # Only process dimensions for unique video files
        if clip_filename not in unique_videos:
            width, height = get_video_dimensions(local_path)
            if width > 0 and height > 0:
                max_width = max(max_width, width)
                max_height = max(max_height, height)
                unique_videos[clip_filename] = {
                    'path': local_path,
                    'width': width,
                    'height': height
                }
            else:
                raise Exception(f"Could not determine dimensions for video: {local_path}")

    # Determine which videos need scaling
    for filename, video_info in unique_videos.items():
        video_info['needs_scaling'] = (video_info['width'] < max_width or video_info['height'] < max_height)
        if video_info['needs_scaling']:
            logger.info(f"Video {filename} will be scaled from {video_info['width']}x{video_info['height']} to {max_width}x{max_height}")

    logger.info(f"Maximum video dimensions found: {max_width}x{max_height}")
    logger.info(f"Unique video files: {len(unique_videos)}, Total clips: {len(vclip_timeline)}")

    # Second pass: add inputs and create filters (only unique files as inputs)
    video_input_map = {}  # filename -> input_index
    input_index = 0

    # Add unique video files as inputs
    for filename, video_info in unique_videos.items():
        ffmpeg_cmd.extend(['-i', video_info['path']])
        video_input_map[filename] = input_index
        input_index += 1

    # Third pass: create timeline filters referencing the unique inputs
    video_filter_parts = []
    timeline_index = 0

    for clip in vclip_timeline:
        clip_filename = os.path.basename(clip['gcs_path'])
        input_idx = video_input_map[clip_filename]
        video_info = unique_videos[clip_filename]

        # Create filter chain: trim -> scale (if needed) -> setpts
        filter_chain = f"[{input_idx}:v]trim=duration={clip['duration']}"

        # Add scaling if this unique video needs it
        if video_info['needs_scaling']:
            filter_chain += f",scale={max_width}:{max_height}:force_original_aspect_ratio=decrease,pad={max_width}:{max_height}:(ow-iw)/2:(oh-ih)/2"

        filter_chain += f",setpts=PTS+{clip['start_time']}/TB[v{timeline_index}]"
        video_filter_parts.append(filter_chain)
        timeline_index += 1

    valid_video_count = len(vclip_timeline)  # Number of clips in timeline    # Add audio input if provided
    audio_input_index = len(unique_videos)  # Audio comes after unique video inputs
    if downloaded_audio_file:
        ffmpeg_cmd.extend(['-i', downloaded_audio_file])

    # Calculate total video duration
    total_duration = max(clip['start_time'] + clip['duration'] for clip in vclip_timeline)

    # Build complex filter
    if valid_video_count == 0:
        raise Exception("No valid video clips found")
    elif valid_video_count == 1:
        # Single video - just use the processed video directly
        filter_complex = video_filter_parts[0]
        ffmpeg_cmd.extend(['-filter_complex', filter_complex])
        ffmpeg_cmd.extend(['-map', '[v0]'])
    else:
        # Multiple videos - build overlay chain
        filter_complex = ';'.join(video_filter_parts)

        # Build overlay chain
        overlay_parts = []
        for i in range(1, valid_video_count):
            if i == 1:
                overlay_parts.append(f"[v0][v{i}]overlay[tmp{i}]")
            else:
                overlay_parts.append(f"[tmp{i-1}][v{i}]overlay[tmp{i}]")

        filter_complex += ';' + ';'.join(overlay_parts)
        final_video_label = f"tmp{valid_video_count-1}"

        ffmpeg_cmd.extend(['-filter_complex', filter_complex])
        ffmpeg_cmd.extend(['-map', f'[{final_video_label}]'])

    # Add audio mapping if audio track exists
    if downloaded_audio_file:
        ffmpeg_cmd.extend(['-map', f'{audio_input_index}:a', '-t', str(total_duration)])

    # Output settings - optimized for speed
    ffmpeg_cmd.extend([
        '-c:v', 'libx264',           # Video codec
        '-preset', 'ultrafast',      # Fastest encoding preset
        '-crf', '23',               # Constant rate factor (good quality/speed balance)
        '-threads', '0',            # Use all available CPU cores
        '-c:a', 'aac',              # Audio codec
        '-b:a', '128k',             # Audio bitrate
        '-shortest',                # Stop when shortest input ends
        output_path
    ])

    # Execute FFmpeg command with timing
    logger.info(f"Executing FFmpeg command: {' '.join(ffmpeg_cmd)}")


    start_time = time.time()
    result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
    end_time = time.time()

    execution_time = end_time - start_time
    logger.info(f"FFmpeg execution completed in {execution_time:.2f} seconds")

    if result.returncode == 0:
        logger.info(f"Successfully created combined video: {output_path}")
        video_created = True
        output_file_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
    else:
        logger.error(f"FFmpeg failed: {result.stderr}")
        video_created = False
        output_file_size = 0

    return {
        'success': video_created,
        'output_file': output_filename if video_created else None,
        'output_path': output_path if video_created else None,
        'output_size': output_file_size,
        'total_duration': total_duration,
        'execution_time': execution_time,
        'ffmpeg_error': result.stderr if not video_created else None
    }


@app.route('/')
def hello():
    return jsonify({
        'message': 'Hello from GKE!',
        'service': 'media-generator-api',
        'version': '2.0.0'
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

@app.route('/api/media')
def media_endpoint():
    return jsonify({
        'message': 'Media Generator API',
        'available_endpoints': ['/api/process_media'],
        'supported_formats': ['mp4', 'avi', 'mov', 'mp3', 'wav'],
        'status': 'ready'
    })

@app.route('/api/combine_videos', methods=['POST'])
def combine_videos():
    """
    Combine multiple video files and audio into a single video file.

    Expected JSON payload:
    {
        "vclip_timeline": [
            {"url": "file1.mp4", "start_time": 0, "duration": 5, "gcs_path": "videos/test_user/file1.mp4", "name": "file1.mp4"},
            {"url": "file2.mp4", "start_time": 5, "duration": 3, "gcs_path": "videos/test_user/file2.mp4", "name": "file2.mp4"}
        ],
        "demo_track_gcs_path": "audio/test_user/track.mp3"
    }
    """
    try:
        # Validate request
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON'}), 400

        data = request.get_json()
        logger.info(f"Received combine_videos payload: {data}")

        # Validate required fields
        required_fields = ['vclip_timeline']
        missing_fields = [field for field in required_fields if field not in data]

        if missing_fields:
            return jsonify({
                'error': 'Missing required fields',
                'missing_fields': missing_fields
            }), 400

        vclip_timeline = data['vclip_timeline']
        demo_track_gcs_path = data.get('demo_track_gcs_path')  # Optional audio track

        # Validate vclip_timeline is a list and has required fields
        if not isinstance(vclip_timeline, list):
            return jsonify({'error': 'vclip_timeline must be a list'}), 400

        if len(vclip_timeline) == 0:
            return jsonify({'error': 'vclip_timeline cannot be empty'}), 400

        # Extract unique GCS file paths from the timeline
        file_paths = set()

        # Add video file paths from vclip_timeline
        for clip in vclip_timeline:
            if clip.get('gcs_path', "") == "":
                return jsonify({
                    'error': 'Each clip in vclip_timeline must have a gcs_path field',
                    'clip': clip
                }), 400
            file_paths.add(clip['gcs_path'])

        # Convert to list for download function
        file_paths_list = list(file_paths)

        # Create temporary directory for downloads
        temp_dir = tempfile.mkdtemp(prefix='media_processing_')
        logger.info(f"Created temporary directory: {temp_dir}")

        # Download files from GCS using the GCS paths
        bucket_name = os.environ.get('GCS_BUCKET')
        if not bucket_name:
            return jsonify({
                'status': 'error',
                'message': 'GCS_BUCKET environment variable not set'
            }), 500

        # Download video files
        try:
            downloaded_videos = download_files_from_gcs(
                bucket_name=bucket_name,
                file_paths=file_paths_list,
                local_dir=temp_dir
            )
        except Exception as e:
            logger.error(f"Error downloading video files from GCS: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': 'Failed to download video files from GCS',
                'error': str(e)
            }), 500

        # Download audio file separately if provided
        downloaded_audio_file = None
        if demo_track_gcs_path:
            try:
                audio_files = download_files_from_gcs(
                    bucket_name=bucket_name,
                    file_paths=[demo_track_gcs_path],
                    local_dir=temp_dir
                )
                downloaded_audio_file = audio_files[0]
                logger.info(f"Downloaded audio file: {downloaded_audio_file}")
            except Exception as e:
                logger.error(f"Error downloading audio file from GCS: {str(e)}")
                return jsonify({
                    'status': 'error',
                    'message': 'Failed to download audio file from GCS',
                    'error': str(e)
                }), 500

        # Process the timeline information
        timeline_info = {
            'total_clips': len(vclip_timeline),
            'total_duration': sum(clip.get('duration', 0) for clip in vclip_timeline),
            'clips_processed': len([clip for clip in vclip_timeline if 'gcs_path' in clip]),
            'unique_files': len(file_paths_list),
            'has_audio_track': demo_track_gcs_path is not None
        }

        # VIDEO COMBINING LOGIC
        try:
            video_result = combine_videos_with_ffmpeg(
                vclip_timeline=vclip_timeline,
                downloaded_videos=downloaded_videos,
                downloaded_audio_file=downloaded_audio_file,
                temp_dir=temp_dir
            )
        except Exception as e:
            logger.error(f"Error during video combination: {str(e)}")
            # Cleanup temp directory before returning error
            try:
                shutil.rmtree(temp_dir)
                logger.info(f"Cleaned up temporary directory: {temp_dir}")
            except Exception as cleanup_error:
                logger.error(f"Failed to cleanup directory {temp_dir}: {cleanup_error}")

            return jsonify({
                'status': 'error',
                'message': 'Failed to combine videos',
                'error': str(e)
            }), 400

        response = {
            'status': 'success',
            'message': 'Video combination request processed successfully',
            'downloaded_video_files': downloaded_videos,
            'downloaded_audio_file': downloaded_audio_file,
            'timeline_info': timeline_info,
            'video_creation': video_result,
            'temp_directory': temp_dir,
            'files_downloaded': file_paths_list,
            'processed_at': str(os.environ.get('HOSTNAME', 'unknown-pod'))
        }

        # CLEANUP - copy output file to /tmp/ before cleaning up
        try:
            # Copy output file to /tmp/ if it exists
            if video_result.get('success') and video_result.get('output_path') and os.path.exists(video_result['output_path']):
                output_filename = video_result['output_file']
                tmp_output_path = os.path.join('/tmp', output_filename)
                shutil.copy2(video_result['output_path'], tmp_output_path)
                logger.info(f"Copied output file to: {tmp_output_path}")

                # Update response to include /tmp/ path
                response['video_creation']['tmp_output_path'] = tmp_output_path

            # Clean up temporary directory
            shutil.rmtree(temp_dir)
            logger.info(f"Cleaned up temporary directory: {temp_dir}")
        except Exception as e:
            logger.error(f"Failed to cleanup directory {temp_dir}: {e}")

        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Error in combine_videos: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error during video combination',
            'error': str(e)
        }), 500


@app.route('/api/gcs/get_signed_url', methods=['POST'])
def get_gcs_signed_url():
    """
    Generate a signed URL for direct upload to Google Cloud Storage

    Expected JSON payload:
    {
        "file_name": "file.mp4",
        "file_type": "video/mp4",
        "expiration": 3600
    }
    """
    try:
        # Validate request
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON'}), 400

        data = request.get_json()

        # Validate required fields
        required_fields = ['file_name', 'file_type']
        missing_fields = [field for field in required_fields if field not in data]

        if missing_fields:
            return jsonify({
                'error': 'Missing required fields',
                'missing_fields': missing_fields
            }), 400

        # Use your predefined GCS configuration
        bucket_name = os.environ.get('GCS_BUCKET')
        file_name = data['file_name']
        content_type = data['file_type']
        expiration = data.get('expiration', 3600)  # Default 1 hour

        # Initialize GCS client with proper credentials
        client = get_gcs_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(file_name)

        # Generate signed URL for upload
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(seconds=expiration),
            method="PUT",
            content_type=content_type
        )

        logger.info(f"Generated signed URL for {file_name} in bucket {bucket_name}")

        response = {
            'status': 'success',
            'signed_url': signed_url,
            'bucket_name': bucket_name,
            'file_path': file_name,
            'content_type': content_type,
            'expiration_seconds': expiration,
            'upload_method': 'PUT'
        }

        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Error generating signed URL: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to generate signed URL',
            'error': str(e)
        }), 500

@app.route('/api/example')
def example_endpoint():
    return jsonify({
        'message': 'Flask template example endpoint',
        'available_formats': ['mp4', 'avi', 'mov'],
        'status': 'ready'
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=False)
