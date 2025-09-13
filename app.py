from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
from agora_token_builder import RtcTokenBuilder
import os
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configuration from environment variables
AGORA_APP_ID = 'c770c1ce64ed4cf78810a212b0634c0c'
AGORA_APP_CERTIFICATE = '1b1220744ac644ce898114a2541ad45b'

# Validate configuration
if not AGORA_APP_ID or not AGORA_APP_CERTIFICATE:
    logger.warning("Agora App ID or Certificate not set. Please set AGORA_APP_ID and AGORA_APP_CERTIFICATE environment variables.")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    return '', 204  # No content for favicon

@app.route('/api/health')
def health_check():
    return jsonify({'status': 'healthy', 'agora_configured': bool(AGORA_APP_ID and AGORA_APP_CERTIFICATE)})

@app.route('/api/generate-token', methods=['POST'])
def generate_token():
    try:
        if not AGORA_APP_ID or not AGORA_APP_CERTIFICATE:
            return jsonify({'error': 'Server not configured properly'}), 500

        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        channel_name = data.get('channelName')
        uid = data.get('uid', 0)

        if not channel_name:
            return jsonify({'error': 'Channel name is required'}), 400

        # Validate channel name (basic sanitization)
        if not isinstance(channel_name, str) or len(channel_name) > 64:
            return jsonify({'error': 'Invalid channel name'}), 400

        # Calculate expiration time (1 hour from now)
        expiration_time = 3600
        current_timestamp = int(datetime.now().timestamp())
        expire_timestamp = current_timestamp + expiration_time

        # Build token
        token = RtcTokenBuilder.buildTokenWithUid(
            AGORA_APP_ID,
            AGORA_APP_CERTIFICATE,
            channel_name,
            uid,
            role=1,  # Publisher role
            privilege_expire_ts=expire_timestamp
        )

        logger.info(f"Token generated for channel: {channel_name}, uid: {uid}")

        return jsonify({
            'token': token,
            'appId': AGORA_APP_ID,
            'channel': channel_name,
            'uid': uid,
            'expires': expire_timestamp
        })

    except Exception as e:
        logger.error(f"Error generating token: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(404)
def not_found(e):
    # For SPA routing, return index.html for all undefined routes
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Not found'}), 404
    return render_template('index.html')

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal server error: {str(e)}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting server on port {port}")
    logger.info(f"Agora configured: {bool(AGORA_APP_ID and AGORA_APP_CERTIFICATE)}")
    
    app.run(debug=debug, host='0.0.0.0', port=port)
