#!/usr/bin/env python3
"""
Test script for the /api/process_media endpoint
"""
import requests
import json

def test_process_media_endpoint(base_url="http://localhost:5000"):
    """
    Test the /api/process_media endpoint
    """
    endpoint = f"{base_url}/api/process_media"

    # Sample payload matching your vclip_timeline structure
    payload = {
        "bucket_name": "your-media-bucket",
        "source_path": "videos/raw",  # Optional path in bucket
        "file_names": [
            "IMG_0153.mov",
            "IMG_0154.mov",
            "Golden Cocktail Hour demo.mp3"
        ],
        "vclip_timeline": [
            {
                "url": "IMG_0153.mov",
                "name": "IMG_0153.mov",
                "start_time": 0,
                "duration": 5.2
            },
            {
                "url": "IMG_0154.mov",
                "name": "IMG_0154.mov",
                "start_time": 5.2,
                "duration": 3.8
            },
            {
                "url": "IMG_0153.mov",
                "name": "IMG_0153.mov",
                "start_time": 9.0,
                "duration": 4.1
            }
        ]
    }

    print(f"Testing endpoint: {endpoint}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print("-" * 50)

    try:
        response = requests.post(
            endpoint,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )

        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 200:
            print("✅ SUCCESS: Media processing request completed")
        else:
            print("❌ ERROR: Request failed")

    except requests.exceptions.RequestException as e:
        print(f"❌ REQUEST ERROR: {e}")
    except json.JSONDecodeError as e:
        print(f"❌ JSON DECODE ERROR: {e}")
        print(f"Raw response: {response.text}")

def test_health_endpoint(base_url="http://localhost:5000"):
    """Test the health endpoint"""
    try:
        response = requests.get(f"{base_url}/health")
        print(f"Health check: {response.json()}")
    except Exception as e:
        print(f"Health check failed: {e}")

if __name__ == "__main__":
    import sys

    # Default to localhost, but allow override
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000"

    print(f"Testing Flask app at: {base_url}")
    print("=" * 60)

    # Test health first
    test_health_endpoint(base_url)
    print()

    # Test the main endpoint
    test_process_media_endpoint(base_url)
