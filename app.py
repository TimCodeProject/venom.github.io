import os
import json
from flask import Flask, render_template, session, request, jsonify
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv
import random
import string
from datetime import datetime, timedelta

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key')
socketio = SocketIO(app, cors_allowed_origins="*")

# Agora конфигурация
AGORA_APP_ID = os.getenv('AGORA_APP_ID')
AGORA_APP_CERTIFICATE = os.getenv('AGORA_APP_CERTIFICATE')

# Хранение данных сессий
active_sessions = {}

def generate_channel_name():
    """Генерация уникального имени канала"""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))

def generate_rtc_token(channel_name, uid, role=1):
    """Генерация токена для Agora RTC"""
    try:
        from agora_access_token import AccessToken
        
        if not AGORA_APP_ID or not AGORA_APP_CERTIFICATE:
            return None
            
        expiration_time = 3600  # 1 час
        current_time = datetime.utcnow()
        privilege_expired_ts = (current_time + timedelta(seconds=expiration_time)).timestamp()
        
        token = AccessToken(AGORA_APP_ID, AGORA_APP_CERTIFICATE, channel_name, uid)
        token.add_privilege(AccessToken.Privileges.kJoinChannel, privilege_expired_ts)
        
        if role == 1:  # Publisher
            token.add_privilege(AccessToken.Privileges.kPublishAudioStream, privilege_expired_ts)
            token.add_privilege(AccessToken.Privileges.kPublishVideoStream, privilege_expired_ts)
            token.add_privilege(AccessToken.Privileges.kPublishDataStream, privilege_expired_ts)
        
        return token.build()
    except:
        # Fallback для случаев когда agora_access_token не установлен
        return "dummy_token_for_dev"

@app.route('/')
def index():
    """Главная страница"""
    if 'user_id' not in session:
        session['user_id'] = random.randint(100000, 999999)
    if 'username' not in session:
        session['username'] = f'User_{random.randint(1000, 9999)}'
    
    channel_name = request.args.get('channel')
    if not channel_name:
        channel_name = generate_channel_name()
        return render_template('index.html', 
                             channel_name=channel_name,
                             agora_app_id=AGORA_APP_ID,
                             user_id=session['user_id'],
                             username=session['username'])
    
    return render_template('index.html',
                         channel_name=channel_name,
                         agora_app_id=AGORA_APP_ID,
                         user_id=session['user_id'],
                         username=session['username'])

@app.route('/set_username', methods=['POST'])
def set_username():
    """Установка имени пользователя"""
    username = request.json.get('username')
    if username:
        session['username'] = username
        return jsonify({'success': True, 'username': username})
    return jsonify({'success': False})

@app.route('/token', methods=['POST'])
def generate_token():
    """Генерация токена для клиента"""
    try:
        data = request.json
        channel_name = data['channel']
        user_id = data['uid']
        
        token = generate_rtc_token(channel_name, user_id)
        
        if token:
            return jsonify({
                'token': token,
                'appId': AGORA_APP_ID,
                'channel': channel_name,
                'uid': user_id
            })
        else:
            return jsonify({'error': 'Failed to generate token'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@socketio.on('connect')
def handle_connect():
    """Обработчик подключения WebSocket"""
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    """Обработчик отключения WebSocket"""
    print('Client disconnected')

@socketio.on('join_chat')
def handle_join_chat(data):
    """Пользователь присоединяется к чату"""
    session['room'] = data['channel']
    session['username'] = data['username']
    emit('user_joined', {
        'username': data['username'],
        'message': 'присоединился к чату',
        'timestamp': datetime.now().isoformat()
    }, room=data['channel'], broadcast=True)

@socketio.on('send_message')
def handle_send_message(data):
    """Отправка сообщения в чат"""
    emit('new_message', {
        'username': session['username'],
        'message': data['message'],
        'timestamp': datetime.now().isoformat(),
        'userId': session['user_id']
    }, room=session['room'], broadcast=True)

@socketio.on('send_reaction')
def handle_send_reaction(data):
    """Отправка реакции"""
    emit('new_reaction', {
        'username': session['username'],
        'reaction': data['reaction'],
        'timestamp': datetime.now().isoformat()
    }, room=session['room'], broadcast=True)

@socketio.on('user_activity')
def handle_user_activity(data):
    """Обработка активности пользователя"""
    emit('user_activity_update', {
        'userId': session['user_id'],
        'username': session['username'],
        'activity': data['activity'],
        'timestamp': datetime.now().isoformat()
    }, room=session['room'], broadcast=True)

@app.route('/health')
def health_check():
    """Health check для Render"""
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
