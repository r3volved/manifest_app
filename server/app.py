import sys
import os
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
from pypref import Preferences
import random
import re
import json
import sqlite3
import atexit


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
ONLINE_USER_STORE = config["ONLINE_USER_STORE"]

# Initialize the flask webserver
app = Flask(__name__)

# Initialize the websocket server
socketio = SocketIO(app, cors_allowed_origins="*")
 
# Simple data store model
# Scale this with more appropriate data storage
class DataStore():
    def __init__(self, store):
        # TODO: connect to database
        self.source = store["source"]
        self.type = store["type"]
        self.conn = None
        if self.type == "dict":
            if self.source:
                self.data = self.source #dict
            else:
                self.data = {}
        elif self.type == "py":
            self.data = Preferences(filename=self.source)
        elif self.type == "json":
            with open(local_file(self.source), 'r') as f:
                self.data = json.load(f)
        elif self.type == "sqlite":
            self.conn = sqlite3.connect(local_file(self.source))
            cursor = self.conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    password TEXT NOT NULL,
                    role INTEGER NOT NULL,
                    username TEXT NOT NULL,
                    icon TEXT,
                    color TEXT,
                    token TEXT,
                    last_login TIMESTAMP,
                    last_connect TIMESTAMP,
                    last_disconnect TIMESTAMP
                )
            ''')
            self.conn.commit()

    def connected(self):
        if self.type == "sqlite":
            return self.conn is not None
        return True
            
    def reset(self):
        # No reset for json files
        # No reset for sqlite
        if self.type == "dict":
            self.data = {}
        elif self.type == "py":
            self.data.set_preferences({})

    def get(self, key):
        if self.type == "dict":
            return self.data[key]
        elif self.type == "py":
            return self.data.get(key)
        elif self.type == "json":
            return self.data.get(key)
        elif self.type == "sqlite":
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id=?", (key,))
            result = cursor.fetchone()
            return result[0] if result else None

    def set(self, key, value):
        if self.type == "dict":
            self.data[key] = value
        elif self.type == "py":
            update = {}
            update[key] = value
            self.data.update_preferences(update)
        elif self.type == "json":
            self.data[key] = value
            json_object = json.dumps(self.data, indent=0)
            with open(local_file(self.source), "w") as f:
                f.write(json_object)
        elif self.type == "sqlite":
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO users (
                    id, password, role, username, icon, color, token,
                    last_login, last_connect, last_disconnect
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                value["id"], value["password"], value["role"], value["username"],
                value["icon"], value["color"], value["token"],
                value["last_login"], value["last_connect"], value["last_disconnect"]
            ))
            self.conn.commit()
    
    def rem(self, key):
        if self.type == "dict":
            del self.data[key]
        elif self.type == "py":
            update = {}
            update[key] = None
            self.data.update_preferences(update)
        elif self.type == "json":
            self.data.pop(key,None)
            json_object = json.dumps(self.data, indent=0)
            with open(local_file(self.source), "w") as f:
                f.write(json_object)
        elif self.type == "sqlite":
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM users WHERE id=?", (key,))
            self.conn.commit()

    def edit(self, key, new_data):
        if self.type == "dict":
            self.data[key] = new_data
        elif self.type == "py":
            update = {}
            update[key] = new_data
            self.data.update_preferences(update)
        elif self.type == "json":
            data = self.data.get(key)
            data.update(new_data)
            self.data[key] = data
            json_object = json.dumps(self.data, indent=0)
            with open(local_file(self.source), "w") as f:
                f.write(json_object)
        elif self.type == "sqlite":
            cursor = self.conn.cursor()
            cursor.execute("UPDATE users SET value=? WHERE id=?", (new_data, key))
            self.conn.commit()

    def close(self):
        if self.type == "sqlite":
            self.conn.close()
            self.conn = None


# User store - user details, password, role etc
# Token store - used for maintaining and authenticating sessions
# Supporting data store - alerts
# Online users - nonpersistent store of users
users = DataStore(USER_STORE) 
tokens = DataStore(TOKEN_STORE)
support_data = DataStore(DATA_STORE)
# online_users = DataStore(ONLINE_USER_STORE)
online_users = {}
print("Datastores have been connected")

def close():
    # Disconnect from datastores when server disconnects
    users.close()
    tokens.close()
    support_data.close()
    # online_users.close()
    print("Datastores have been closed")

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


atexit.register(close)

# Start server on port 5000 
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=PORT, debug=False)
