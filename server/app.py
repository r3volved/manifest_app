import sys
import os
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
from pypref import Preferences
import random
import re
import json

if getattr(sys, 'frozen', False):
    # If the application is run as a bundle, the PyInstaller bootloader
    # extends the sys module by a flag frozen=True and sets the app 
    # path into variable _MEIPASS'.
    application_path = sys._MEIPASS
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

# Return filename prefixed with client path
def local_file(filename):
    # return re.sub("app\.py$", filename, __file__)
    return os.path.join(application_path, filename)

# Open and parse the config json
with open(local_file("config.json"), 'r') as f:
    config = json.load(f)

# Map config stuff into constants for clarity
PORT = config["PORT"]
USER_STORE = config["USER_STORE"]
DATA_STORE = config["DATA_STORE"]
TOKEN_STORE = config["TOKEN_STORE"]

# Initialize the flask webserver
app = Flask(__name__)

# Initialize the websocket server
socketio = SocketIO(app, cors_allowed_origins="*")
 
# Simple data store model
# Scale this with more appropriate data storage
class DataStore():
    def init(self, store):
        # TODO: connect to database
        self.source = store["source"]
        self.isjson = re.search("\.json$", self.source)
        if self.isjson:
            # Open and parse the config json
            with open(local_file(self.source), 'r') as f:
                self.data = json.load(f)
        else:
            # Open preferences
            self.data = Preferences(filename=self.source)

    def reset(self):
        # DON'T CLEAR JSON FOR NOW SINCE ITS JUST USERS
        if self.isjson:
            # json_object = json.dumps({}, indent=0)
            # with open(local_file(self.source), "w") as f:
            #     f.write(json_object)
            return 
        else:
            self.data.set_preferences({})

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value):
        if self.isjson:
            self.data[key] = value
            json_object = json.dumps(self.data, indent=0)
            with open(local_file(self.source), "w") as f:
                f.write(json_object)
        else:
            update = {}
            update[key] = value
            self.data.update_preferences(update)
        return value
    
    def rem(self, key):
        value = self.data.get(key)
        if self.isjson:
            self.data.pop(key,None)
            json_object = json.dumps(self.data, indent=0)
            with open(local_file(self.source), "w") as f:
                f.write(json_object)
        else:
            update = {}
            update[key] = None
            self.data.update_preferences(update)
        return value

    def edit(self, key, newData):
        data = self.data.get(key)
        if self.isjson:
            data.update(newData)
            self.data[key] = data
            json_object = json.dumps(self.data, indent=0)
            with open(local_file(self.source), "w") as f:
                f.write(json_object)
        else:
            update = {}
            update[key] = newData
            self.data.update_preferences(update)
        return data


# User store - user details, password, role etc
users = DataStore()
users.init(USER_STORE)

# Token store - used for maintaining and authenticating sessions
tokens = DataStore()
tokens.init(TOKEN_STORE)
# tokens.reset()

# Supporting data store - alerts
support_data = DataStore()
support_data.init(DATA_STORE)

# Online users - nonpersistent dict of users
online_users = {}


def get_user(token):
    user_id = tokens.get(token)
    if user_id is None:
        return None
    
    user = users.get(user_id)
    if user is None or user["token"] != token:
        return None
    
    return user

# Define the logout route for the webserver 
@app.route("/logout", methods=["POST"])
def logout():
    token = str(request.form["token"])
    user_id = tokens.get(token)
    if user_id:
        tokens.rem(token)
        users.edit(user_id, {"token":None})
        return jsonify({"status": "success"})
    # Otherwise fail
    return jsonify({"status": "failed"}), 401
        

# Define the login route for the webserver 
@app.route("/login", methods=["POST"])
def login():
    # Parse the user ID and password from the login data 
    user_id = request.form["user_id"]
    password = request.form["password"]
    # Lookup the user ID requested
    user = users.get(user_id)
    if user and user["password"] == password:
        tokens.rem(user["token"])
        token = str(random.getrandbits(128))
        users.edit(user_id, {"token":token})
        tokens.set(token, user_id)
        return jsonify({"status": "success", "role": user["role"], "token":token, "username":user["username"] })
    # Otherwise fail the login
    return jsonify({"status": "failed"}), 401


# Define the routine to run when a user connects to the server
@socketio.on("connect")
def handle_connect():
    # Note: Client will validate when connected - event will add or update the online user information there
    print("Client connected")

# Define the routine to run when a user disconnects from the server
@socketio.on("disconnect")
def handle_disconnect():
    print("Client disconnected")
    # User has disconnected, delete online user info
    user = online_users.pop(request.sid)
    emit("online_users_list", list(online_users.values()), broadcast=True)

@socketio.on("validate")
def handle_validate(data):
    token = str(data["token"])
    user = get_user(token)
    if user is None:
        return emit("reauthenticate", {}, broadcast=False)
    else:
        # User has connected and validated, set online user info
        online_users[request.sid] = { 
            "name":user.get('username'), 
            "icon":user.get('icon'),
            "color":user.get('color'),
        }
        emit("online_users_list", list(online_users.values()), broadcast=True)

# Define the routine to run when a "send_alert" request is sent by user
# NOTE: This is where the data sent by admin gets re-broadcast out to all the connected users
@socketio.on("send_alert")
def handle_send_alert(data):
    token = str(data["token"])
    user = get_user(token)
    if user is None:
        return emit("reauthenticate", {}, broadcast=False)

    if user["role"] <= 3:
        # User was found and has permission to broadcast
        message = {
            "text":data["text"],
            "color":data["color"],
            "username":user["username"]
        }
        emit("receive_alert", message, broadcast=True)
        print("Broadcasting alert from "+user["username"])
    else:
        # User was found but does not have permission to broadcast
        message = {
            "text":"You do not have permission to broadcast alerts",
            "color":"orange",
            "username":"System"
        }
        emit("receive_alert", message, broadcast=False)
        print("User does not have permission to send alerts")

@socketio.on("get_alerts")
def handle_get_alerts(data):
    token = str(data["token"])
    user = get_user(token)
    if user is None:
        return emit("reauthenticate", {}, broadcast=False)

    emit("alert_list", support_data.get("alerts"), broadcast=False)
    print("Sending alerts to "+user["username"])

@socketio.on("get_online_users")
def handle_get_online_users(data):
    token = str(data["token"])
    user = get_user(token)
    if user is None:
        return emit("reauthenticate", {}, broadcast=False)

    emit("online_users_list", list(online_users.values()), broadcast=False)
    print("Sending online users to " + user["username"])
    
# Start server on port 5000 
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=PORT, debug=False)
