import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QSlider
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPalette
from time import sleep
import requests
import socketio

# Initialize the server URL to connect
# TODO: Move this to a config file
SERVER_URL = "http://localhost:5000/"

# Define the alert display app class
class AlertDisplay(QWidget):
    def init(self):
        self.token = None
        self.role = None
        self.username = None
        self.init_ui()

    def init_ui(self):
        # Set some Alert window properties
        self.setWindowTitle('Alert App')
        self.setAutoFillBackground(True)
        # Add an opacity slider to the Alert window
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.valueChanged.connect(self.change_opacity)
        # Add a label to the Alert window
        self.alert_label = QLabel('Hello world')
        self.alert_label.setAlignment(Qt.AlignCenter)
        self.alert_label.setWordWrap(True)

        layout = QVBoxLayout()
        layout.addWidget(self.opacity_slider)
        layout.addWidget(self.alert_label)
        self.setLayout(layout)
        self.show()

        if self.token is None:
            self.init_ui_login()
        else:
            self.init_ui_user(self.user_id, self.role, self.token)

    def init_ui_user(self, data):
        # Set properties
        self.role = data["role"]
        self.token = data["token"]
        self.username = data["username"]
        self.display_alert("Logged in as "+self.username+"\nConecting...","blue")
        self.connect_socketio()

    def init_ui_login(self):
        self.display_alert("Please Login","yellow")
        # TODO: add user and pass textbox
        # TODO: add button to trigger login routine


    def change_opacity(self, value):
        # Change the opacity of the Alert window
        opacity = value / 100
        # Never set to zero
        if opacity < 0.1: 
            opacity = 0.1
        self.setWindowOpacity(opacity)

    def display_alert(self, text, color):
        # Display an alert in the label
        self.alert_label.setText(text)
        # Change window color
        palette = self.palette()
        palette.setColor(QPalette.Background, QColor(color))
        self.setPalette(palette)

    def send_alert(self, text, color):
        # If token is allowed, message will be broadcast
        data = {  
            "token": self.token,
            "text": text,
            "color": color
        }
        # Send data t server
        if self.token and self.sio:
            self.sio.emit("send_alert", data)

    def connect_login(self, user_id, password):
        self.display_alert("Logging in...","green")
        # TODO: Return a token
        response = requests.post(f"{SERVER_URL}/login", data={"user_id": user_id, "password": password})
        if response.status_code == 200:
            data = response.json()
            self.init_ui_user(data)
        else:
            self.init_ui_login()
            self.display_alert("Invalid credentials","orange")
            print("Invalid user credentials")

    def connect_socketio(self):
        # Initialize a websocket client
        self.sio = socketio.Client()

        @self.sio.event
        def connect():
            # Handle connect event
            print("Connected to server")
            self.display_alert("Connected!", "grey")

        @self.sio.event
        def disconnect():
            # Handle disconnect event
            print("Disconnected from server")
            self.display_alert("Disconnected!", "grey")

        @self.sio.event
        def receive_alert(data):
            # Handle "receive_alert" event
            # Note: This is the event fired when server sends message to client
            # Parse the text and color from message
            text = data['text']
            color = data['color']
            username = data['username']
            message = username + ": " + text
            # Show the alert message and change window color
            self.display_alert(message, color)

        @self.sio.event
        def reauthenticate(data):
            self.init_ui_login()

        # Connect to server when AlertDisplay initialized
        self.sio.connect(SERVER_URL)

def main():
    # Initialize the app
    app = QApplication(sys.argv)
    alert_display = AlertDisplay()
    alert_display.init()

    # DEMO: Request login
    #alert_display.connect_login("user1", "password1") #admin
    alert_display.connect_login("user2", "password2") #user
    #alert_display.connect_login("user3", "password4") #!!bad password
    #alert_display.connect_login("user4", "password4") #!!bad user

    # DEMO: Send message
    alert_display.send_alert("I'm alive", "red")

    # ?? I don't know what this is        
    sys.exit(app.exec())
        
        
# Run "main" function on start
if __name__ == '__main__':
    main()
