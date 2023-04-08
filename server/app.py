from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
import random

# Initialize the flask webserver
app = Flask(__name__)

# Initialize the websocket server
socketio = SocketIO(app, cors_allowed_origins="*")

# Simple data store model
# Scale this with more appropriate data storage
class DataStore():
    def init(self, config):
        # TODO: connect to database
        self.data = config

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value):
        self.data[key] = value
        return value
    
    def rem(self, key):
        return self.data.pop(key,None)

    def edit(self, key, newData):
        data = self.data.get(key)
        data.update(newData)
        self.data[key] = data
        return data


# Sample users with roles (1-3: send/receive, 4-8: receive only)
# User store - user details, password, role etc
users = DataStore()
users.init({
    "user1": {"token":None, "password": "password1", "role": 2, "username":"TESTADMIN"},
    "user2": {"token":None, "password": "password2", "role": 4, "username":"TESTUSER2"},
    "user3": {"token":None, "password": "password3", "role": 4, "username":"TESTUSER3"},
})


# Token store - used for maintaining and authenticating sessions
tokens = DataStore()
tokens.init({})


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
        tokens.rem(user["token"])
        token = random.getrandbits(128)
        users.edit(user_id, {"token":token})
        tokens.set(token, user_id)
        debug = "Set new token ("+str(token)+") for user ("+user["username"]+")"
        print(debug)

        return jsonify({"status": "success", "role": user["role"], "token":token, "username":user["username"] })
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
    token = data["token"]
    user_id = tokens.get(token)
    if user_id:
        # Token is valid, get user 
        user = users.get(user_id)
        if user and user["role"] <= 3:
            # User was found and has permission to broadcast
            message = {
                "text":data["text"],
                "color":data["color"],
                "username":user["username"]
            }
            emit("receive_alert", message, broadcast=True)
        else:
            # User was found but does not have permission to broadcast
            message = {
                "text":"You do not have permission to broadcast alerts",
                "color":"orange",
                "username":"System"
            }
            emit("receive_alert", message, broadcast=False)
            print("User does not have permission to send alerts")
    else:
        # Token is invalid - not found
        emit("rauthenticate", {}, broadcast=False)
        print("User was not found with this token was not found")


# Start server on port 5000
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
