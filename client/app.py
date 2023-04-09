import sys
from PyQt5.QtWidgets import QApplication, QFrame, QTextEdit, QFormLayout, QLineEdit, QPushButton, QWidget, QLabel, QVBoxLayout, QSlider
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
    def __init__(self):
        super().__init__()
        self.token = None
        self.role = None
        self.username = None
        # Set some Alert window properties
        self.resize(400,80)
        self.setWindowTitle('Alert App')
        self.setAutoFillBackground(True)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Add an opacity slider to the Alert window
        # self.opacity_slider = QSlider(Qt.Horizontal)
        # self.opacity_slider.valueChanged.connect(self.change_opacity)
        # self.layout.addWidget(self.opacity_slider)

        # Add a label to the Alert window
        self.alert_label = QLabel(self)
        self.alert_label.setAlignment(Qt.AlignCenter)
        self.alert_label.setWordWrap(True)
        self.layout.addWidget(self.alert_label)

        self.message_frame = QFrame()
        self.message_form = QFormLayout()
        self.message_text = QTextEdit()
        self.message_text.setPlaceholderText("Enter an alert message...")
        self.message_form.addRow(self.message_text)
        self.message_send = QPushButton()
        self.message_send.setText('Send')
        self.message_send.clicked.connect(self.test_message)
        self.message_form.addRow(self.message_send)
        self.message_frame.setLayout(self.message_form)
        self.layout.addWidget(self.message_frame)

        self.login_frame = QFrame()
        self.login_form = QFormLayout()
        self.login_user = QLineEdit()
        self.login_user.returnPressed.connect(self.test_login)
        self.login_form.addRow("Username", self.login_user)
        self.login_password = QLineEdit()
        self.login_password.returnPressed.connect(self.test_login)
        self.login_password.setEchoMode(QLineEdit.Password)
        self.login_form.addRow("Password", self.login_password)
        self.login_button = QPushButton()
        self.login_button.setText('Login')
        self.login_button.clicked.connect(self.test_login)
        self.login_form.addRow(self.login_button)
        self.login_frame.setLayout(self.login_form)
        self.layout.addWidget(self.login_frame)

        self.logout_frame = QFrame()
        self.logout_form = QFormLayout()
        self.logout_button = QPushButton()
        self.logout_button.setText('Logout')
        self.logout_button.clicked.connect(self.connect_logout)
        self.logout_form.addRow(self.logout_button)
        self.logout_frame.setLayout(self.logout_form)
        self.layout.addWidget(self.logout_frame)

        self.init_ui_login()

    def init_ui_user(self):
        self.display_alert("Wecome "+self.username+"!",'grey')
        self.login_frame.hide()
        self.logout_frame.show()
        if self.role <= 3:
            self.message_frame.show()
        
    def init_ui_login(self):
        self.display_alert('Please Login','grey')
        self.message_frame.hide()
        self.logout_frame.hide()
        self.login_frame.show()

    def test_message(self):
        # DEMO: Send message
        message = self.message_text.toPlainText()
        self.message_text.clear()
        self.send_alert(message, "red")

    def test_login(self):
        user_id = self.login_user.text()
        password = self.login_password.text()
        if user_id and password:
            self.connect_login(user_id, password)
        # DEMO: Request login
        #self.connect_login("user1", "password1") #admin
        #self.connect_login("user2", "password2") #user
        #self.connect_login("user3", "password4") #!!bad password
        #self.connect_login("user4", "password4") #!!bad user

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
            self.role = data["role"]
            self.token = data["token"]
            self.username = data["username"]
            self.connect_socketio()
            self.init_ui_user()
        else:
            self.init_ui_login()
            self.display_alert("Invalid credentials","orange")
            print("Invalid user credentials")

    def connect_logout(self):
        if self.token is not None:
            requests.post(f"{SERVER_URL}/logout", data={"token": self.token})
        self.token = None
        self.role = None
        self.username = None
        self.init_ui_login()

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
            self.connect_logout()

        # Connect to server when AlertDisplay initialized
        self.sio.connect(SERVER_URL)


def main():
    # Initialize the app
    app = QApplication(sys.argv)
    alert_display = AlertDisplay()
    alert_display.show() 
    sys.exit(app.exec())    
        
# Run "main" function on start
if __name__ == '__main__':
    main()
