import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QSlider
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPalette
import requests
import socketio

# Initialize the server URL to connect
# TODO: Move this to a config file
SERVER_URL = "http://localhost:5000/"

# Define the alert display app class
class AlertDisplay(QWidget):
    def init(self, user_id, role):
        #super().init()
        # Note: this is commented out cause it errored - created by gpt

        # Set properties
        self.user_id = user_id
        self.role = role

        # Initialize the UI and connect to server
        self.init_ui()
        self.connect_socketio()

    def init_ui(self):
        # Set some Alert window properties
        self.setWindowTitle('Alert App')
        self.setAutoFillBackground(True)

        # Set an initial color
        palette = self.palette()
        palette.setColor(QPalette.Background, QColor('green'))
        self.setPalette(palette)

        # Add a label to the Alert window
        self.alert_label = QLabel('No alert')
        self.alert_label.setAlignment(Qt.AlignCenter)
        self.alert_label.setWordWrap(True)

        # Add an opacity slider to the Alert window
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.valueChanged.connect(self.change_opacity)

        layout = QVBoxLayout()
        layout.addWidget(self.alert_label)
        layout.addWidget(self.opacity_slider)

        self.setLayout(layout)

    def change_opacity(self, value):
        # Change the opacity of the Alert window
        opacity = value / 100
        self.setWindowOpacity(opacity)

    def display_alert(self, text, color):
        # Display an alert in the label
        self.alert_label.setText(text)
        # Change window color
        palette = self.palette()
        palette.setColor(QPalette.Background, QColor(color))
        self.setPalette(palette)

    def send_alert(self, text, color):
        # If role is allowed, send a message to broadcast
        # TODO: Leverage a token system and cross reference token with user on server side
        if self.role <= 3:  
            data = {  
                "user_id": self.user_id,
                "text": text,
                "color": color
            }
            # Send data t server
            self.sio.emit("send_alert", data)
        else:
            print("User does not have permission to send alerts")

    def connect_socketio(self):
        # Initialize a websocket client
        self.sio = socketio.Client()

        @self.sio.event
        def connect():
            # Handle connect event
            print("Connected to server")

        @self.sio.event
        def disconnect():
            # Handle disconnect event
            print("Disconnected from server")

        @self.sio.event
        def receive_alert(data):
            # Handle "receive_alert" event
            # Note: This is the event fired when server sends message to client
            # Parse the text and color from message
            text = data['text']
            color = data['color']
            # Show the alert message and change window color
            self.display_alert(text, color)

        # Connect to server when AlertDisplay initialized
        self.sio.connect(SERVER_URL)

def main():
    # Initialize the app
    app = QApplication(sys.argv)

    # Replace these values with valid user_id and password
    # TODO: Generate and leverage a login page in client
    user_id = "user1"
    password = "password1"
    
    # Request login
    response = requests.post(f"{SERVER_URL}/login", data={"user_id": user_id, "password": password})
        
    if response.status_code == 200:
        data = response.json()
        role = data["role"]
	# Initialize the Alerts
        alert_display = AlertDisplay()
        alert_display.init(user_id, role)
        alert_display.show()
        # Send a test message to broadcast
        alert_display.send_alert("wowiwow","red")        
        # ?? I don't know what this is        
        sys.exit(app.exec())
    else:
        print("Invalid user credentials")

# Run "main" function on start
if __name__ == '__main__':
    main()
