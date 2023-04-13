import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QFrame, QTextEdit, QFormLayout, QLineEdit, QPushButton, QWidget, QLabel, QVBoxLayout, QSlider
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPalette
from time import sleep
import requests
import socketio

# Initialize the server URL to connect
# TODO: Move this to a config file
SERVER_URL = "http://localhost:5000/"

# Define the login window
class LoginWindow(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('Please login')
        self.setAutoFillBackground(True)
        self.setWindowModality(Qt.ApplicationModal)
        self.setFixedWidth(300)
        self.login_form = QFormLayout()
        self.login_user = QLineEdit()
        self.login_user.returnPressed.connect(self.login)
        self.login_form.addRow("Username", self.login_user)
        self.login_password = QLineEdit()
        self.login_password.returnPressed.connect(self.login)
        self.login_password.setEchoMode(QLineEdit.Password)
        self.login_form.addRow("Password", self.login_password)
        self.login_button = QPushButton()
        self.login_button.setText('Login')
        self.login_button.clicked.connect(self.login)
        self.login_form.addRow(self.login_button)
        self.setLayout(self.login_form)        

    def login(self):
        user_id = self.login_user.text()
        password = self.login_password.text()
        if user_id and password:
            response = requests.post(f"{SERVER_URL}/login", data={"user_id": user_id, "password": password})
            if response.status_code == 200:
                data = response.json()
                self.parent.token = data["token"]
                self.parent.role = data["role"]
                self.parent.username = data["username"]
                self.parent.display_alert("Welcome "+self.parent.username,"grey")
                self.parent.update_ui()
                self.hide()
            else:
                self.parent.display_alert("Invalid credentials","orange")
                print("Invalid user credentials")

    def logout(self):
        if self.parent.token is not None:
            requests.post(f"{SERVER_URL}/logout", data={"token": self.parent.token})
        self.parent.token = None
        self.parent.role = None
        self.parent.username = None

class AlertWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.sio = None
        self.token = None
        self.role = None
        self.username = None
        self.init_ui()
        self.user_window = None
        self.login_display = LoginWindow(self)

    def init_ui(self):
        self.setWindowTitle('Alert window')
        self.setFixedWidth(800)
        self.setFixedHeight(50)
        self.setAutoFillBackground(True)
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.layout = QFormLayout()
        self.control_username = QPushButton()
        self.control_username.setText("Login")
        self.control_username.clicked.connect(self.user_menu)
        self.alert_label = QLabel()
        self.alert_label.setWordWrap(True)
        self.alert_label.setText("Welcome")
        self.layout.addRow(self.control_username, self.alert_label)
        self.setLayout(self.layout)        

    def update_ui(self):
        if self.username:
            self.control_username.setText(self.username)
            self.connect_socketio()
        else:
            self.control_username.setTExt("Login")                

    def user_menu(self):
        if self.token is None:
            self.login_display.show()
        # else:
        #     self.user_window.show()

    def logout(self):
        if self.sio:
            self.sio.disconnect()
            self.sio = None
        self.login_display.logout()
        self.update_ui()

    def change_opacity(self, value):
        # Change the opacity of the Alert window
        opacity = value / 100
        # Never set to zero
        if opacity < 0.1: 
            opacity = 0.1
        self.setWindowOpacity(opacity)

    def send_alert(self, text, color):
        # If token is allowed, message will be broadcast
        data = {  
            "token": self.app.token,
            "text": text,
            "color": color
        }
        # Send data t server
        if self.token and self.sio:
            self.sio.emit("send_alert", data)

    def display_alert(self, text, color):
        # Display an alert in the label
        self.alert_label.setText(text)
        # Change window color
        palette = self.palette()
        palette.setColor(QPalette.Background, QColor(color))
        self.setPalette(palette)

    def connect_socketio(self):
        if self.sio is None:
            # Initialize a websocket client
            self.sio = socketio.Client()

            @self.sio.event
            def connect():
                self.display_alert("Connected!", "grey")
                # print("Connected to server")

            @self.sio.event
            def disconnect():
                self.display_alert("Disconnected!", "grey")
                # print("Disconnected from server")

            @self.sio.event
            def receive_alert(data):
                text = data['text']
                color = data['color']
                username = data['username']
                message = username + ": " + text
                self.display_alert(message, color)

            @self.sio.event
            def reauthenticate(data):
                self.logout()
                self.display_alert("Please login again", "grey")
                # print("Reauthenticate with server")

        # Connect to server when AlertDisplay initialized
        self.sio.connect(SERVER_URL)



# Define the alert display app class
class AlertDisplay(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.app.token = None
        self.app.role = None
        self.app.username = None

        # Set some Alert window properties
        self.resize(400,80)
        self.setWindowTitle('Alert App')
        self.setAutoFillBackground(True)
        self.layout = QVBoxLayout()

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
        self.message_send.setText('Broadcast')
        # self.message_send.clicked.connect(self.send_message)
        self.message_form.addRow(self.message_send)
        self.message_frame.setLayout(self.message_form)
        self.layout.addWidget(self.message_frame)
        

        self.logout_frame = QFrame()
        self.logout_form = None
        self.layout.addWidget(self.logout_frame)
        self.setLayout(self.layout)


    def init_user(self, data):
        self.app.role = data["role"]
        self.app.token = data["token"]
        self.app.username = data["username"]
        self.display_alert("Wecome "+self.app.username+"!",'grey')
        self.connect_socketio()
        if self.app.role <= 3:
            self.message_frame.show()

    def send_message(self):
        # DEMO: Send message
        message = self.message_text.toPlainText()
        self.message_text.clear()
        self.send_alert(message, "red")

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
            "token": self.app.token,
            "text": text,
            "color": color
        }
        # Send data t server
        if self.app.token and self.sio:
            self.sio.emit("send_alert", data)

    def connect_logout(self):
        self.sio.disconnect()
        self.app.login_display.logout()

    def connect_socketio(self):
        # Initialize a websocket client
        self.sio = socketio.Client()

        @self.sio.event
        def connect():
            # Handle connect event
            self.display_alert("Connected!", "grey")
            print("Connected to server")

        @self.sio.event
        def disconnect():
            # Handle disconnect event
            self.display_alert("Disconnected!", "grey")
            print("Disconnected from server")

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
    alert_display = AlertWindow()
    alert_display.show()
    app.exec()

# Run "main" function on start
if __name__ == '__main__':
    main()
