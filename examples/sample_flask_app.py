"""
Sample Flask Application for GKE Deployment
"""
from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route('/')
def hello():
    return jsonify({
        'message': 'Hello from GKE!',
        'service': 'media-generator-api',
        'version': '1.0.0'
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

@app.route('/api/media')
def media_endpoint():
    return jsonify({
        'message': 'Media processing endpoint',
        'available_formats': ['mp4', 'avi', 'mov'],
        'status': 'ready'
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
