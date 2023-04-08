from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit

name = "main"
app = Flask(name)
socketio = SocketIO(app, cors_allowed_origins="*")

# Sample users with roles (1-3: send/receive, 4-8: receive only)
users = {
    "user1": {"user_id":0, "password": "password1", "role": 2},
    "user2": {"user_id":1, "password": "password2", "role": 4},
}

@app.route("/login", methods=["POST"])
def login():
    user_id = request.form["user_id"]
    password = request.form["password"]

    user = users.get(user_id)
    if user and user["password"] == password:
        return jsonify({"status": "success", "role": user["role"]})
    return jsonify({"status": "failed"}), 401

@socketio.on("connect")
def handle_connect():
    print("Client connected")

@socketio.on("disconnect")
def handle_disconnect():
    print("Client disconnected")

@socketio.on("send_alert")
def handle_send_alert(data):
    user_id = data["user_id"]
    user = users.get(user_id)
    print(user)
    if user and user["role"] <= 3:
        emit("receive_alert", data, broadcast=True)
    else:
        print("User does not have permission to send alerts")

if name == "main":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
