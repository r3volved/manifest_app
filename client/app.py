import sys
from PyQt5.QtWidgets import QApplication, QDesktopWidget, QFrame, QRadioButton, QHBoxLayout, QTextEdit, QFormLayout, QLineEdit, QPushButton, QWidget, QLabel, QVBoxLayout, QSlider
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
        self.exit_button = QPushButton()
        self.exit_button.setText('Exit')
        self.exit_button.clicked.connect(self.parent.exit)
        self.login_form.addRow(self.exit_button)
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


class UserWindow(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Please login")
        self.setAutoFillBackground(True)
        self.setWindowModality(Qt.ApplicationModal)
        self.setFixedWidth(300)
        self.user_form = QFormLayout()

        # Add opacity slider
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setValue(100)
        self.opacity_slider.setMinimum(1)
        self.opacity_slider.setMaximum(100)
        self.opacity_slider.setTracking(True)
        self.opacity_slider.valueChanged.connect(self.change_opacity)
        self.user_form.addRow(self.opacity_slider)

        # Add message textbox
        self.message_text = QTextEdit()
        self.message_text.setPlaceholderText("Enter an alert message...")
        self.message_text.hide()
        self.user_form.addRow(self.message_text)

        # Add message broadcast button
        self.message_send = QPushButton()
        self.message_send.setText('Broadcast')
        self.message_send.clicked.connect(self.broadcast)
        self.message_send.hide()
        self.user_form.addRow(self.message_send)

        # Add color options
        self.message_color = QFrame()
        self.admin_layout = QHBoxLayout()
        ## Green        
        self.message_send_green = QRadioButton("Green")
        self.message_send_green.setChecked(True)
        self.message_send_green.setStyleSheet("QRadioButton{padding:1em;}QRadioButton:checked{background-color:lightgreen;}")
        self.admin_layout.addWidget(self.message_send_green)
        ## Yellow
        self.message_send_yellow = QRadioButton("Yellow")
        self.message_send_yellow.setStyleSheet("QRadioButton{padding:1em;}QRadioButton:checked{background-color:yellow;}")
        self.admin_layout.addWidget(self.message_send_yellow)
        ## Red
        self.message_send_red = QRadioButton("Red")
        self.message_send_red.setStyleSheet("QRadioButton{padding:1em;}QRadioButton:checked{background-color:red;}")
        self.admin_layout.addWidget(self.message_send_red)

        self.message_color.setLayout(self.admin_layout)
        self.user_form.addRow(self.message_color)
        self.message_color.hide()

        # Add logout button
        self.logout_button = QPushButton()
        self.logout_button.setText('Logout')
        self.logout_button.clicked.connect(self.parent.logout)
        self.user_form.addRow(self.logout_button)

        # Add exit application button
        self.exit_button = QPushButton()
        self.exit_button.setText('Exit')
        self.exit_button.clicked.connect(self.parent.exit)
        self.user_form.addRow(self.exit_button)
        self.setLayout(self.user_form)

    def init_user(self):
        if self.parent.username is not None:
            self.setWindowTitle(self.parent.username)
        else:
            self.setWindowTitle("Please login")

        if self.parent.role is not None and self.parent.role <= 3:
            self.message_text.show()
            self.message_send.show()
            self.message_color.show()
        else:
            self.message_text.hide()
            self.message_send.hide()
            self.message_color.hide()
            
    def broadcast(self):
        # Get text and color
        text = self.message_text.toPlainText()
        color = "green"
        if self.message_send_red.isChecked():
            color = "red"
        elif self.message_send_yellow.isChecked():
            color = "yellow"
        # Call parent send_alert
        self.parent.send_alert(text, color)        
        self.message_text.clear()

    def change_opacity(self):
        # Get opacity percent (1-100)
        value = self.opacity_slider.value()
        # Call parent change_opacity
        self.parent.change_opacity(value)


class AlertWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.sio = None
        self.token = None
        self.role = None
        self.username = None
        self.init_ui()
        self.user_display = UserWindow(self)
        self.login_display = LoginWindow(self)

    def init_ui(self):
        self.title = "Alert App"
        self.setWindowTitle(self.title)
        self.setAutoFillBackground(True)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.layout = QFormLayout()
        self.control_username = QPushButton()
        self.control_username.setText("Login")
        self.control_username.clicked.connect(self.user_menu)
        self.alert_label = QLabel()
        self.alert_label.setWordWrap(True)
        self.alert_label.setText("Welcome")
        self.layout.addRow(self.control_username, self.alert_label)
        self.setLayout(self.layout)        
        sizeObject = QDesktopWidget().screenGeometry(-1)
        self.setGeometry(0, 0, sizeObject.width(), 30)

    def update_ui(self):
        if self.username:
            self.control_username.setText(self.username)
            self.connect_socketio()
        else:
            self.control_username.setText("Login")                

    def user_menu(self):
        if self.token is None:
            self.login_display.show()
        else:
            self.user_display.init_user()
            self.user_display.show()

    def logout(self):
        if self.sio:
            self.sio.disconnect()
            self.sio = None
        self.login_display.logout()
        self.login_display.hide()
        self.user_display.hide()
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
            "token": self.token,
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

    def exit(self):
        self.logout()
        quit()


def main():
    # Initialize the app
    app = QApplication(sys.argv)
    alert_display = AlertWindow()
    alert_display.show()
    app.exec()

# Run "main" function on start
if __name__ == '__main__':
    main()
