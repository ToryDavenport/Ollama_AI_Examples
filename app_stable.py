import httpx
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import json
import io
import contextlib

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'  # Fake Secret
socketio = SocketIO(app, cors_allowed_origins="*")

OLLAMA_SERVER_URL = "http://192.168.18.169:5001/api/chat" # Fake IP and port
response_stream = None

@app.route('/')
def index():
    return render_template('index3.html')

@socketio.on('message')
def handle_message(msg):
    global response_stream
    print(f"Message: {msg}")
    
    system_message = {
        "role": "system",
        "content": "You are a helpful assistant. Please format all responses in HTML, including tables and code blocks."
    }
    user_message = {"role": "user", "content": msg}
    messages = [system_message, user_message]

    payload = {
        "model": "llama3.1",
        "messages": messages,
        "stream": True
    }

    headers = {
        "Content-Type": "application/json"
    }

    try:
        response_stream = httpx.Client(timeout=None)
        with response_stream.stream("POST", OLLAMA_SERVER_URL, json=payload, headers=headers) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line:
                    chunk = json.loads(line)
                    print(f"Chunk received: {chunk}")  # Debug print
                    if 'message' in chunk and 'content' in chunk['message']:
                        emit('response', {'content': chunk['message']['content']}, broadcast=True)
    except httpx.HTTPStatusError as e:
        print(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
        emit('response', {"content": "An error occurred. Please try again."}, broadcast=True)
    except Exception as e:
        print(f"An error occurred: {e}")
        emit('response', {"content": "An error occurred. Please try again."}, broadcast=True)

@socketio.on('stop')
def handle_stop():
    global response_stream
    if response_stream:
        response_stream.close()
        response_stream = None
        emit('response', {'content': "<em>Response stopped by user.</em>"}, broadcast=True)

@socketio.on('execute_code')
def handle_execute_code(code):
    print(f"Code to execute: {code}")
    try:
        code_output = io.StringIO()
        with contextlib.redirect_stdout(code_output):
            exec(code)
        output = code_output.getvalue()
        print(f"Code output: {output}")
        emit('response', {'content': f"<pre>{output}</pre>"}, broadcast=True)
    except Exception as e:
        error_message = f"Error: {str(e)}"
        print(error_message)
        emit('response', {'content': f"<pre>{error_message}</pre>"}, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True)
