import random
import atexit

from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
from def_utilities import local_file, read_json, make_token, hash_password, test_password
from def_stores import DataStore, UserStore

# Map config stuff into constants for clarity
config = read_json(local_file("config.json"))
PORT = config.get("PORT")
USER_STORE = config.get("USER_STORE")
DATA_STORE = config.get("DATA_STORE")

# Initialize the flask webserver
app = Flask(__name__)
# Initialize the websocket server
socketio = SocketIO(app, cors_allowed_origins="*") 
# Initialize the user store - handles users and tokens
users = UserStore(USER_STORE) 
# Initialize the data store - handles supporting data
support_data = DataStore(DATA_STORE)
# Initialize the online-users store - nonpersistent store of users
online_users = {}

print("Datastores have been connected")

def close():
    # Disconnect from datastores when server disconnects
    users.close()
    support_data.close()
    print("Datastores have been closed")

def emit_error(event, error):
    message = { "success":False, "error":error, "color":"red", "username":"System" }
    return emit(event, message, broadcast=False)

# Define the logout route for the webserver 
@app.route("/logout", methods=["POST"])
def logout():
    token = str(request.form["token"])
    users.clear_token(token)
    return jsonify({"status": "success"})
        
# Define the login route for the webserver 
@app.route("/login", methods=["POST"])
def login():
    # Parse the user ID and password from the login data 
    user_id = request.form.get("user_id")
    password = request.form.get("password") 

    # Lookup the user ID requested
    user = users.get(user_id)
    if user is None:
        return jsonify({"status": "failed"}), 401

    if not test_password(password, user.get("password")):
        return jsonify({"status": "failed"}), 401

    token = make_token()
    users.set_token(token, user_id)
    return jsonify({"status": "success", "role": user.get("role"), "token":token, "username":user.get("username") })


# Define the routine to run when a user connects to the server
@socketio.on("connect")
def handle_connect():
    # Note: Client will validate when connected - event will add or update the online user information there
    donothing = True
    # print("Client connected")

# Define the routine to run when a user disconnects from the server
@socketio.on("disconnect")
def handle_disconnect():
    # User has disconnected, delete online user info
    if online_users.get(request.sid) is None:
        return
    user = online_users.pop(request.sid)
    print("Client disconnected [ "+user.get("name")+" ]")
    emit("online_users_list", list(online_users.values()), broadcast=True)

# Define the routine to validate the user session
@socketio.on("validate")
def handle_validate(data):
    user = users.get_user_from_token(data.get("token"))
    if user is None:
        return emit("reauthenticate", {}, broadcast=False)

    if online_users.get(request.sid) is None:
        print("Client connected [ "+user.get("username")+" ]")

    # User has connected and validated, set online user info
    online_users[request.sid] = { 
        "user_id":user.get('id'),
        "role":user.get('role'),
        "name":user.get('username'), 
        "icon":user.get('icon'),
        "color":user.get('color'),
    }
    emit("online_users_list", list(online_users.values()), broadcast=True)


# Define the routine to run when a "send_alert" request is sent by user
# NOTE: This is where the data sent by admin gets re-broadcast out to all the connected users
@socketio.on("send_alert")
def handle_send_alert(data):
    user = users.get_user_from_token(data.get("token"))
    if user is None:
        return emit("reauthenticate", {}, broadcast=False)

    if user.get("role") > 3:
        return emit_error("alert_sent","You do not have permission to broadcast alerts")

    # User was found and has permission to broadcast
    message = {
        "text":data["text"],
        "color":data["color"],
        "username":user.get("username")
    }
    emit("receive_alert", message, broadcast=True)
    print("Broadcasting alert from "+user.get("username"))

@socketio.on("get_online_users")
def handle_get_online_users(data):
    user = users.get_user_from_token(data.get("token"))
    if user is None:
        return emit("reauthenticate", {}, broadcast=False)

    emit("online_users_list", list(online_users.values()), broadcast=False)
    # print("Sending online users to " + user.get("username"))

@socketio.on("change_password")
def handle_change_password(data):
    user = users.get_user_from_token(data.get("token"))
    if user is None:
        return emit("reauthenticate", {}, broadcast=False)

    old_password = data.get("old_password")
    
    # Old password must pass
    if not test_password(old_password, user.get("password")):
        return emit_error("password_changed","Your old password does not match the current password")
        
    new_password = data.get("new_password")

    if new_password is None:
        return emit_error("password_changed","You must supply a new password")

    if len(new_password) < 8:
        return emit_error("password_changed","Your password must be at least 8 characters")

    hashed_password = hash_password(new_password)
    users.edit(user.get("id"), { "password":hashed_password })
    message = {
        "success":True,
        "error":None,
        "color":"green",
        "username":"System"
    }
    return emit("password_changed", message, broadcast=False)

@socketio.on("get_user_profile")
def hande_get_user_profile(data):
    user = users.get_user_from_token(data.get("token"))
    if user is None:
        return emit("reauthenticate", {}, broadcast=False)

    if data.get('user_id') is None:
        profile = users.get_profile(user.get("id"))
    else:
        if user.get("role") > 3 and data.get('user_id') != user.get("id"):
            return emit_error("user_profile", "You do not have permission to access this profile")
        profile = users.get_profile(data.get("user_id"))

    emit('user_profile', profile, broadcast=False)

# Get data from a support_data table
@socketio.on("get_data")
def handle_get_data(data):
    user = users.get_user_from_token(data.get("token"))
    if user is None:
        return emit("reauthenticate", {}, broadcast=False)

    if data.get("table") is not None:
        table_name = data.get("table")
        results = support_data.get_all(table_name)
        return emit(table_name+"_list", results, broadcast=False)

    if data.get("func") is not None:
        func_name = data.get("func") ## Function name from support_data
        if func_name != "__init__" and func_name != "close" and hasattr(support_data, func_name) and callable(getattr(support_data, func_name)):
            data_func = getattr(support_data, func_name)
            ## Arguments for the funtion { "arg1":"val1" }
            #  keys should match the variable names for that function
            #  values should be the type expected
            data_args = data.get("args") 
            if data_args is None:
                data_args = {}
            results = data_func(**data_args)
            return emit(func_name+"_list", results, broadcast=False)


#
# Admin controls
#

# Manage users
@socketio.on("get_all_users")
def hande_get_all_users(data):
    user = users.get_user_from_token(data.get("token"))
    if user is None:
        return emit("reauthenticate", {}, broadcast=False)

    if user.get("role") > 3:
        return emit_error("all_users", "You do not have permission to access user list")

    user_list = users.get_all()
    for record in user_list:
        # Initialize the 'online_status' field as False
        record['online_status'] = False
        # Iterate over all online users
        for online_user in online_users.values():
            # If the 'user_id' of the online user matches the 'id' of the record,
            # set the 'online_status' field to True
            if online_user.get('user_id') == record.get('id'):
                record['online_status'] = True
                # Once we've found a match, there's no need to check the other online users
                break

    emit("all_users", user_list, broadcast=False)

@socketio.on("create_user")
def handle_creat_user(data):
    user = users.get_user_from_token(data.get("token"))
    if user is None:
        return emit("reauthenticate", {}, broadcast=False)

    if user.get("role") > 3:
        return emit_error("user_created", "You do not have permission to create users")

    new_user = data.get("user")

    # Required user object
    if new_user is None:
        return emit_error("user_created", "No user data was passed")

    # Required user["id"] Field
    if new_user.get("id") is None:
        return emit_error("user_created", "New user requires an ID (used for login)")

    # Required user["password"] Field
    if new_user.get("password") is None:
        return emit_error("user_created", "New user requires a password (used for login)")

    # If user["username"], set username as id
    # NOTE: This field is required for a user but defaulted if not set
    if new_user.get("username") is None:
        new_user["username"] = new_user.get("id")

    # If user["role"] is not set, default to 10 (lowest)
    # NOTE: This field is required for a user but defaulted if not set
    if new_user.get("role") is None:
        new_user["role"] = 10

    # If user["role"] is less than or equal to admin role, set to admin role + 1
    # NOTE: This stops a user from creating another user with higher permissions
    if new_user.get("role") <= user.get("role"):
        new_user["role"] = user.get("role") + 1

    # Hash the password
    new_user["password"] = hash_password(new_user["password"])

    # Set new user in database
    users.set(data.get("user"))

    message = {
        "success":True,
        "error":None,
        "color":"green",
        "username":"System"
    }
    return emit("user_created", message, broadcast=False)

@socketio.on("edit_user")
def handle_edit_user(data):
    user = users.get_user_from_token(data.get("token"))
    if user is None:
        return emit("reauthenticate", {}, broadcast=False)

    if user.get("role") > 3:
        return emit_error("user_edited", "You do not have permission to edit users")

    edit_user = data.get("user")

    # Required user object
    if edit_user is None:
        return emit_error("user_edited", "No user data was passed")

    # Required user["id"] Field
    if edit_user.get("id") is None:
        return emit_error("user_edited", "User id is required")

    # If user["role"] is less than or equal to admin role, set to admin role + 1
    # NOTE: This stops a user from creating another user with higher permissions
    if edit_user.get("role") is not None and edit_user.get("role") <= user.get("role"):
        edit_user["role"] = user.get("role") + 1

    # If has password, hash it first
    if edit_user.get("password") is not None:
        edit_user["password"] = hash_password(edit_user["password"])

    # Edit user in database
    users.edit(data.get("user"))

    message = {
        "success":True,
        "error":None,
        "color":"green",
        "username":"System"
    }
    return emit("user_edited", message, broadcast=False)

# Manage data


atexit.register(close)

# Start server on port 5000 
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=PORT, debug=True)
