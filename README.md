# manifest_app

## install python 3.7+

### version(cmd):
python --version

### on windows 10(cmd):
python.exe
(it will prompt to install python)


## install libraries

### Server
pip install flask flask-socketio requests simple-websocket pypref sqlite3 atexit

### Client
pip install PyQt5 websocket-client pypref pygame gtts


## run py scripts
unzip this to a folder
open in the following order with python (windows double click file)

1. server/app.py
(server will start and listen for conenctions)
[in the wild this will be run on some host somewhere like aws or digital ocean, etc]

2. client/app.py
(enable the normal/non admin user to start a session and login to the server - will launch a cmd prompt AND a little window thing)
[in the wild this will be run by user and would be the same client app as alert_gui but merged - separate for the purpose of proof of concept]

3. client/app.py
(enable the super user to start a session, login, and send a red alert - will launch a cmd prompt AND a little window thing - both user session window things should go red)


## TODO
server data
- add a database, connect and store user data there instead of in-code

rich messages
- extend communications protocol to send images or links or files or whatever 

TESTING
