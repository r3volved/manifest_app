import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QMenu, QToolBar, QSizePolicy, QToolButton, QAction, QDesktopWidget, QFrame, QTabWidget, QRadioButton, QHBoxLayout, QTextEdit, QFormLayout, QLineEdit, QPushButton, QWidget, QLabel, QVBoxLayout, QSlider
from PyQt5.QtCore import Qt, QObject, pyqtSignal
from PyQt5.QtGui import QColor, QPalette, QIcon, QPixmap, QPainter
from PyQt5.QtSvg import QSvgRenderer
from pypref import Preferences
from functools import partial
import requests
import socketio
import re
import json

# Return filename prefixed with client path
def local_file(filename):
    return re.sub("app\.py$", filename, __file__)

# Open and parse the config json
with open(local_file("config.json"), 'r') as f:
    config = json.load(f)

# Map config stuff into constants for clarity
SERVER_URL = config["SERVER_URL"]

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
                newuser = { "token":data["token"], "role":data["role"], "username":data["username"] }
                self.parent.user.update_preferences(newuser)
                self.parent.update_ui()
                self.hide()
            else:
                self.parent.display_alert("Invalid credentials","orange")

# Define the user profile window
class UserWindow(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.init_ui()

    def init_ui(self):
        self.setAutoFillBackground(True)
        self.setWindowModality(Qt.ApplicationModal)
        self.setFixedWidth(500)
        self.user_form = QFormLayout()

        # Add opacity slider
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setValue(100)
        self.opacity_slider.setMinimum(1)
        self.opacity_slider.setMaximum(100)
        self.opacity_slider.setTracking(True)
        self.opacity_slider.valueChanged.connect(self.change_opacity)
        self.user_form.addRow("Alert opacity: ", self.opacity_slider)

        # Add admin frame
        self.admin_frame = QFrame()
        self.admin_layout = QFormLayout()
        self.admin_frame.setStyleSheet("padding:0.25em;")
        self.admin_frame.setLayout(self.admin_layout)
        
        # Add color options
        self.color_frame = QFrame()
        self.color_layout = QHBoxLayout()
        self.color_frame.setStyleSheet("padding:0; margin:0; border:1px inset grey;")
        self.color_frame.setLayout(self.color_layout)
        self.admin_layout.addRow(self.color_frame)
        ## Green        
        self.message_send_green = QRadioButton("Green")
        self.message_send_green.setChecked(True)
        self.message_send_green.setStyleSheet("QRadioButton { padding:0.5em 1em; margin:0; } QRadioButton:checked { background-color:lightgreen; font-weight:bold; }")
        self.color_layout.addWidget(self.message_send_green)
        ## Yellow
        self.message_send_yellow = QRadioButton("Yellow")
        self.message_send_yellow.setStyleSheet("QRadioButton { padding:0.5em 1em; margin:0; } QRadioButton:checked { background-color:yellow; font-weight:bold; }")
        self.color_layout.addWidget(self.message_send_yellow)
        ## Red
        self.message_send_red = QRadioButton("Red")
        self.message_send_red.setStyleSheet("QRadioButton { padding:0.5em 1em; margin:0; } QRadioButton:checked { background-color:red; font-weight:bold; }")
        self.color_layout.addWidget(self.message_send_red)
        # Add message textbox
        self.message_text = QTextEdit()
        self.message_text.setFixedHeight(80)
        self.message_text.setPlaceholderText("Enter an alert message...")
        self.message_text.setStyleSheet("QTextEdit { padding:0; height:5em; }")
        self.admin_layout.addRow(self.message_text)
        # Add message broadcast button
        self.message_send = QPushButton('Broadcast')
        self.message_send.clicked.connect(self.broadcast)
        self.message_send.setStyleSheet("QPushButton { padding:0.5em; font-size:2em; font-weight:bold; }")
        self.admin_layout.addRow(self.message_send)
        self.admin_frame.hide()

        self.user_form.addRow(self.admin_frame)

        # Add logout button
        self.logout_button = QPushButton('Logout')
        self.logout_button.clicked.connect(self.parent.logout)
        # self.user_form.addRow(self.logout_button)

        # Add exit application button
        self.exit_button = QPushButton('Exit the application')
        self.exit_button.clicked.connect(self.parent.exit)
        self.user_form.addRow(self.logout_button, self.exit_button)
        self.setLayout(self.user_form)

    def init_user(self):
        if self.parent.user.get("username") is not None:
            self.setWindowTitle(self.parent.user.get("username"))
        else:
            self.setWindowTitle("Please login")

        if self.parent.user.get("role") is not None and self.parent.user.get("role") <= 3:
            self.admin_frame.show()
        else:
            self.admin_frame.hide()
        
    def broadcast(self):
        # Get text and color
        text = self.message_text.toPlainText()
        color = "lightgreen"
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

class WebSocket(QObject):
    load_alerts = pyqtSignal(list)
    display_alert = pyqtSignal(str, str)
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.sio = socketio.Client()

        @self.sio.event
        def connect():
            self.display_alert.emit("Connected!", "lightgrey")
            if self.parent.user.get("role") <= 3 and self.parent.alerts is None:
                self.sio.emit("get_alerts", { "token":self.parent.user.get("token") })
            else:
                self.sio.emit("validate", { "token":self.parent.user.get("token") })

        @self.sio.event
        def disconnect():
            self.display_alert.emit("Disconnected!", "orange")

        @self.sio.event
        def receive_alert(data):
            text = data['text']
            color = data['color']
            username = data['username']
            message = str(username) + ": " + str(text)
            self.display_alert.emit(message, color)

        @self.sio.event
        def reauthenticate(data):
            self.logout()
            self.display_alert.emit("Please reauthentiate", "orange")

        @self.sio.event
        def validate(data):
            self.sio.emit("validate", { "token":self.parent.user.get("token") })

        @self.sio.event
        def alert_list(data):
            if self.parent.user.get("role") is None or self.parent.user.get("role") > 3:
                return
            self.load_alerts.emit(data)

    def send_alert(self, data):
        self.sio.emit("send_alert", data)

    def connect(self):
        # Connect to server when AlertDisplay initialized
        self.sio.connect(SERVER_URL)

    def disconnect(self):
        self.sio.disconnect()


# Define the main alert bar
class AlertWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.user = Preferences(filename="manifest_cache.py")
        self.alerts = None
        self.sio = WebSocket(self)
        self.sio.load_alerts.connect(self.populate_alerts)
        self.sio.display_alert.connect(self.display_alert)
        self.user_display = UserWindow(self)
        self.login_display = LoginWindow(self)
        self.init_ui()
        self.update_ui()

    def init_ui(self):
        self.title = "Alert App"
        self.setWindowTitle(self.title)
        self.setAutoFillBackground(False)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        # Enable transparency for the QMainWindow
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("background:transparent;")

        sizeObject = QDesktopWidget().screenGeometry(-1)
        fullWidth = sizeObject.width()
        fullHeight = sizeObject.height()
        self.setGeometry(0, 0, fullWidth, fullHeight)

        self.toolbar = self.addToolBar("Alerts")
        self.toolbar.setStyleSheet("background:white;")
        self.toolbar.setGeometry(0, 0, fullWidth, 30)
        self.toolbar.setAllowedAreas(Qt.TopToolBarArea | Qt.BottomToolBarArea)

        self.control_username = QToolButton(self)
        self.control_username.setText("Login")
        self.control_username.setStyleSheet("padding:0.5em;")
        self.control_username.clicked.connect(self.user_menu)
        self.toolbar.addWidget(self.control_username)

        self.toolbar.addSeparator()
        self.alert_label = QLabel()
        self.alert_label.setWordWrap(True)
        self.alert_label.setText("Welcome")
        self.alert_label.setFixedWidth(int(fullWidth*0.9))
        self.alert_label.setStyleSheet("padding:0.5em 1em;")
        self.alert_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.toolbar.addWidget(self.alert_label)

        self.control_exit = QToolButton(self)
        self.control_exit.setText("Exit")
        self.control_exit.setStyleSheet("padding:0.5em; float:right;")
        self.control_exit.clicked.connect(self.exit)
        self.toolbar.addWidget(self.control_exit)


    def update_ui(self):
        if self.user.get("username"):
            self.control_username.setText(self.user.get("username"))
            # self.connect_socketio()
            self.sio.connect()
        else:
            self.control_username.setText("Login")               

    # Open the login window if no session, otherwise open user window
    def user_menu(self):
        if self.user.get("token") is None:
            self.login_display.show()
        else:
            self.user_display.init_user()
            self.user_display.show()

    # Only disconnect from websocket - user session persists 
    def disconnect(self):
        self.sio.disconnect()

    # Disconnect from websocket and then flush user from client and server
    def logout(self):
        self.disconnect()
        if self.user.get("token") is not None:
            requests.post(f"{SERVER_URL}/logout", data={"token": self.user.get("token")})
        reset = { "token":None, "role":None, "username":None }
        self.user.update_preferences(reset)
        self.update_ui()
        self.login_display.hide()
        self.user_display.hide()

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
            "token": self.user.get("token"),
            "text": text,
            "color": color
        }
        # Send data t server
        if self.user.get("token") and self.sio:
            self.sio.send_alert(data)

    def populate_alerts(self, alerts):
        if self.alerts is not None:
            return
        
        def sort_index(e):
            return e["index"]
        
        self.alerts = alerts
        self.alerts.sort(key=sort_index)
        menu = QMenu()
        for alert in self.alerts:
            text = alert["text"]
            color = alert["color"]
            circle = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="50" fill="'+color+'" /></svg>'
            pixmap = svg_to_pixmap(circle, 24)
            action = QAction(QIcon(pixmap), text, menu)
            if alert["shortcut"]:
                action.setShortcut(alert["shortcut"])  
            action.triggered.connect(lambda checked, t=text, c=color: self.send_alert(t,c))
            menu.addAction(action)

        self.control_alerts = QToolButton(self)
        self.control_alerts.setText('Alerts')
        self.control_alerts.setStyleSheet("QToolButton { padding:0.5em; }")
        self.control_alerts.setMenu(menu)
        self.control_alerts.setPopupMode(QToolButton.InstantPopup)
        self.toolbar.insertWidget(self.toolbar.actions()[1], self.control_alerts)

    def display_alert(self, text, color):
        self.alert_label.setText(text)
        self.toolbar.setStyleSheet("background:"+color+";")

    def connect_socketio(self):
        if self.sio is None:
            # Initialize a websocket client
            self.sio = socketio.Client()

            @self.sio.event
            def connect():
                self.display_alert("Connected!", "lightgrey")
                if self.user.get("role") <= 3 and self.alerts is None:
                    self.sio.emit("get_alerts", { "token":self.user.get("token") })
                else:
                    self.sio.emit("validate", { "token":self.user.get("token") })

            @self.sio.event
            def disconnect():
                self.display_alert("Disconnected!", "orange")

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
                self.display_alert("Please reauthentiate", "orange")

            @self.sio.event
            def validate(data):
                self.sio.emit("validate", { "token":self.user.get("token") })

            @self.sio.event
            def alert_list(data):
                if self.user.get("role") is None or self.user.get("role") > 3:
                    return
                
                def sort_index(e):
                    return e["index"]
                
                self.alerts = data
                self.alerts.sort(key=sort_index)
                self.load_alerts.emit()

        # Connect to server when AlertDisplay initialized
        self.sio.connect(SERVER_URL)

    def closeEvent(self, event):
        self.exit()
        event.accept()

    # Disconnect and exit application - user session persists
    def exit(self):
        self.disconnect()
        quit()

def svg_to_pixmap(svg_data, size):
    renderer = QSvgRenderer()
    renderer.load(svg_data.encode())

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()

    return pixmap

# Initialize the app
def main():
    app = QApplication(sys.argv)
    alert_display = AlertWindow()
    alert_display.show()
    app.exec()

# Run "main" function on start
if __name__ == '__main__':
    main()
