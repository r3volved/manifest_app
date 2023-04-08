from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit

# Initialize the flask webserver
app = Flask(__name__)

# Initialize the websocket server
socketio = SocketIO(app, cors_allowed_origins="*")

# Sample users with roles (1-3: send/receive, 4-8: receive only)
# TODO: Replace this with a datastore for users
users = {
    "user1": {"token":"abc", "password": "password1", "role": 2, "username":"TESTADMIN"},
    "user2": {"token":"xyz", "password": "password2", "role": 4, "username":"TESTUSER"},
}

# Define the login route for the webserver 
@app.route("/login", methods=["POST"])
def login():
    # Parse the user ID and password from the login data 
    user_id = request.form["user_id"]
    password = request.form["password"]
    # Lookup the user ID requested
    user = users.get(user_id)
    # If user was found and the password matches, return success and the user role
    # TODO: Return a token and leverage token for access restriction instead of role
    if user and user["password"] == password:
        return jsonify({"status": "success", "role": user["role"], "token":user["token"], "username":user["username"] })
    # Otherwise fail the login
    return jsonify({"status": "failed"}), 401

# Define the routine to run when a user connects to the server
@socketio.on("connect")
def handle_connect():
    print("Client connected")

# Define the routine to run when a user disconnects from the server
@socketio.on("disconnect")
def handle_disconnect():
    print("Client disconnected")

# Define the routine to run when a "send_alert" request is sent by user
# NOTE: This is where the data sent by admin gets re-broadcast out to all the connected users
@socketio.on("send_alert")
def handle_send_alert(data):
    # Parse the user ID from request
    user_id = data["user_id"]
    token = data["token"]
    # Lookup the user ID requested
    user = users.get(user_id)
    # If user was found and their role is less than 3, rebroadcast data
    if user and user["token"] == token and user["role"] <= 3:
        message = {
            "text":data["text"],
            "color":data["color"],
            "username":data["username"]
        }
        emit("receive_alert", message, broadcast=True)
    else:
        message = {
            "text":"You do not have permission to broadcast alerts",
            "color":"orange",
            "username":"System"
        }
        emit("receive_alert", message, broadcast=False)
        print("User does not have permission to send alerts")

# Start server on port 5000
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
