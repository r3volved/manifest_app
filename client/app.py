import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QDialog, QMenu, QToolBar, QSizePolicy, QToolButton, QAction, QDesktopWidget, QFrame, QTabWidget, QRadioButton, QHBoxLayout, QTextEdit, QFormLayout, QLineEdit, QPushButton, QWidget, QLabel, QVBoxLayout, QSlider
from PyQt5.QtCore import Qt, QObject, pyqtSignal, QCoreApplication, QTimeLine
from PyQt5.QtGui import QColor, QPalette, QIcon, QPixmap, QPainter, QFontMetrics
from PyQt5.QtSvg import QSvgRenderer
from pypref import Preferences
from functools import partial
import requests
import socketio
import re
import json

from gtts import gTTS
#from playsound import playsound
import pygame
import time
import io

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
SERVER_URL = config["SERVER_URL"]

pygame.mixer.init()

# Define the login window
class LoginWindow(QDialog):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('Please login')
        self.setAutoFillBackground(True)
        self.setWindowModality(Qt.WindowModal)
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

    def focusOutEvent(self, event):
        # Close the window when it loses focus
        self.close()

    def login(self):
        user_id = self.login_user.text()
        password = self.login_password.text()
        if user_id and password:
            self.parent.display_alert("Logging in ...","lightgrey")
            self.hide()
            QCoreApplication.processEvents()

            response = requests.post(f"{SERVER_URL}/login", data={"user_id": user_id, "password": password})
            if response.status_code == 200:
                data = response.json()
                newuser = { "token":data["token"], "role":data["role"], "username":data["username"] }
                self.parent.user.update_preferences(newuser)
                self.parent.update_ui()
            else:
                self.parent.display_alert("Invalid credentials","orange")

# Define the user profile window
class UserWindow(QDialog):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.init_ui()

    def init_ui(self):
        self.setAutoFillBackground(True)
        self.setWindowModality(Qt.WindowModal)
        self.setFixedWidth(500)
        self.user_form = QFormLayout()

        # Add opacity slider
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setValue(100)
        self.opacity_slider.setMinimum(1)
        self.opacity_slider.setMaximum(100)
        self.opacity_slider.setTracking(True)
        self.opacity_slider.valueChanged.connect(self.change_opacity)
        self.user_form.addRow("Alert Opacity: ", self.opacity_slider)
        
        # Add volume slider
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setValue(100)
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setTracking(True)
        self.volume_slider.valueChanged.connect(self.change_opacity)
        self.user_form.addRow("Alert Volume: ", self.volume_slider)
        
        # Add dark/light mode checkbox
        # self.textcolor_checkbox = QCheckBox(Qt.Unchecked)
        # self.volume_slider.valueChanged.connect(self.change_opacity)
        # self.user_form.addRow("Alert Volume: ", self.volume_slider)

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
        ## Purple
        self.message_send_purple = QRadioButton("Purple")
        self.message_send_purple.setStyleSheet("QRadioButton { padding:0.5em 1em; margin:0; } QRadioButton:checked { background-color:purple; font-weight:bold; }")
        self.color_layout.addWidget(self.message_send_purple)
        ## Blue
        self.message_send_blue = QRadioButton("Blue")
        self.message_send_blue.setStyleSheet("QRadioButton { padding:0.5em 1em; margin:0; } QRadioButton:checked { background-color:blue; font-weight:bold; }")
        self.color_layout.addWidget(self.message_send_blue)
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
        color = "lightgrey"
        if self.message_send_green.isChecked():
            color = "lightgreen"
        if self.message_send_red.isChecked():
            color = "red"
        if self.message_send_blue.isChecked():
            color = "blue"
        if self.message_send_purple.isChecked():
            color = "purple"
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
        
    def change_volume(self):
        # Get volume percent (0-100)
        value = self.volume_slider.value()
        # Call parent change_volume
        self.parent.change_volume(value)

class WebSocket(QObject):
    load_users = pyqtSignal(list)
    load_alerts = pyqtSignal(list)
    audio_alert = pyqtSignal(str, str)
    display_alert = pyqtSignal(str, str)
    logout = pyqtSignal()
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.sio = socketio.Client()

        @self.sio.event
        def connect():
            self.connected.emit()
            self.sio.emit("validate", { "token":self.parent.user.get("token") })
            if self.parent.user.get("role") <= 3 and self.parent.alerts is None:
                self.sio.emit("get_alerts", { "token":self.parent.user.get("token") })

        @self.sio.event
        def disconnect():
            self.disconnected.emit()

        @self.sio.event
        def receive_alert(data):
            text = data['text']
            color = data['color']
            username = data['username']
            message = str(username) + ": " + str(text)
            self.display_alert.emit(message, color)
            self.audio_alert.emit(username, text)
                        
        @self.sio.event
        def reauthenticate(data):
            self.logout.emit()
            self.display_alert.emit("Please reauthentiate", "orange")

        @self.sio.event
        def validate(data):
            self.sio.emit("validate", { "token":self.parent.user.get("token") })

        @self.sio.event
        def alert_list(data):
            if self.parent.user.get("role") is None or self.parent.user.get("role") > 3:
                return
            self.load_alerts.emit(data)

        @self.sio.event
        def online_users_list(data):
            self.load_users.emit(data)

    def send_alert(self, data):
        self.sio.emit("send_alert", data)

    def isConnected(self):
        return self.sio.connected

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
        self.init_ui()
        QCoreApplication.processEvents()

        self.ws = WebSocket(self)
        self.ws.load_users.connect(self.populate_users)
        self.ws.load_alerts.connect(self.populate_alerts)
        self.ws.audio_alert.connect(self.audio_alert)
        self.ws.display_alert.connect(self.display_alert)
        self.ws.disconnected.connect(self.websocket_disconnected)
        self.ws.connected.connect(self.websocket_connected)
        self.ws.logout.connect(self.logout)
        self.user_display = UserWindow(self)
        self.login_display = LoginWindow(self)

    def init_ui(self):
        self.title = "Alert App"
        self.setWindowTitle(self.title)
        self.setAutoFillBackground(False)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        screen_geometry = QApplication.desktop().screenGeometry()
        # self.setGeometry(screen_geometry)
        self.setGeometry(0, 0, screen_geometry.width(), 30)
        self.setStyleSheet("background:transparent;")

        self.toolbar = QToolBar(self)
        self.toolbar.setStyleSheet("background:white;")
        self.toolbar.setAllowedAreas(Qt.TopToolBarArea | Qt.BottomToolBarArea)
        # self.toolbar.setGeometry(0, 0, screen_geometry.width(), 30)
        self.toolbar.setMovable(True)
        self.addToolBar(self.toolbar)

        self.toolbar_container = QWidget(self.toolbar)
        self.toolbar_layout = QHBoxLayout(self.toolbar_container)
        self.toolbar_layout.setContentsMargins(0,0,0,0)

        self.control_username = QToolButton(self.toolbar_container)
        self.control_username.setText("Login")
        self.control_username.setStyleSheet("padding:0.5em;")
        self.control_username.clicked.connect(self.user_menu)
        self.toolbar_layout.addWidget(self.control_username)

        self.control_users = QToolButton(self.toolbar_container)
        self.control_users.setText('Users')
        self.control_users.setStyleSheet("QToolButton { padding:0.5em; } QToolButton::menu-indicator { width:0; height:0; }")
        self.control_users.setPopupMode(QToolButton.InstantPopup)
        self.toolbar_layout.addWidget(self.control_users)

        self.control_alerts = QToolButton(self.toolbar_container)
        self.control_alerts.setText('Alerts')
        self.control_alerts.setStyleSheet("QToolButton { padding:0.5em; } QToolButton::menu-indicator { width:0; height:0; }")
        self.control_alerts.setPopupMode(QToolButton.InstantPopup)
        self.toolbar_layout.addWidget(self.control_alerts)

        self.alert_label = QLabel("Welcome", self.toolbar_container)
        self.alert_label.setWordWrap(True)
        self.alert_label.setStyleSheet("padding:0.5em 1em;")
        self.alert_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.toolbar_layout.addWidget(self.alert_label)

        # self.toggle_websocket = QToolButton(self)
        # self.toggle_websocket.setText("WS")
        # self.toggle_websocket.setStyleSheet("padding:0.5em;")
        # self.toggle_websocket.clicked.connect(self.websocket_toggler)
        # self.toolbar_layout.addWidget(self.toggle_websocket)

        self.control_exit = QToolButton(self)
        self.control_exit.setText("X")
        self.control_exit.setStyleSheet("padding:0.5em;")
        self.control_exit.clicked.connect(self.exit)
        self.toolbar_layout.addWidget(self.control_exit)

        self.toolbar.addWidget(self.toolbar_container)

    def update_ui(self):
        self.control_users.hide()
        self.control_alerts.hide()
        if self.user.get("username"):
            self.control_username.setText(self.user.get("username"))
            self.display_alert("Connecting to mothership ...","lightgrey")
            self.ws.connect()
        else:
            self.display_alert("Please login ...","lightgrey")
            self.control_username.setText("Login")               
            self.ws.disconnect()

    def websocket_connected(self):
        self.display_alert("Connected!", "lightgrey")
        self.control_users.show()
        if self.alerts is not None:
            self.control_alerts.show()

    def websocket_disconnected(self):
        self.display_alert("Disconnected!", "orange")
        self.control_users.hide()
        self.control_alerts.hide()

    def websocket_toggler(self):
        if self.ws.isConnected():
            self.ws.disconnect()
        else:
            self.ws.connect()


    # Open the login window if no session, otherwise open user window
    def user_menu(self):
        if self.user.get("token") is None:
            self.login_display.show()
        else:
            self.user_display.init_user()
            self.user_display.show()

    # Only disconnect from websocket - user session persists 
    def disconnect(self):
        if self.ws.isConnected():
            self.ws.disconnect()

    # Disconnect from websocket and then flush user from client and server
    def logout(self):
        self.login_display.hide()
        self.user_display.hide()
        QCoreApplication.processEvents()

        self.disconnect()
        if self.user.get("token") is not None:
            requests.post(f"{SERVER_URL}/logout", data={"token": self.user.get("token")})
        reset = { "token":None, "role":None, "username":None }
        self.user.update_preferences(reset)
        self.update_ui()

    def change_opacity(self, value):
        # Change the opacity of the Alert window
        opacity = value / 100
        # Never set to zero
        if opacity < 0.1: 
            opacity = 0.1
        self.setWindowOpacity(opacity)
        
    def change_volume(self, value):
        # Change the opacity of the Alert window
        self.volume = value / 100

    def send_alert(self, text, color):
        # If token is allowed, message will be broadcast
        data = {  
            "token": self.user.get("token"),
            "text": text,
            "color": color
        }
        # Send data t server
        if self.user.get("token") and self.ws.isConnected():
            self.ws.send_alert(data)

    def populate_users(self, users):
        menu = QMenu()
        for user in users:
            name = user['name']
            color = 'lightgreen'
            if 'color' in user and user['color']:
                color = user['color']

            icon = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="50" fill="'+color+'" /></svg>'
            if 'icon' in user and user["icon"]:
                icon = user["icon"]
    
            pixmap = svg_to_pixmap(icon, 24)
            action = QAction(QIcon(pixmap), name, menu)
            menu.addAction(action)
        self.control_users.setText('Users ('+str(len(users))+')')
        self.control_users.setMenu(menu)

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

        self.control_alerts.setMenu(menu)
    
    #
    # Not sure what this ticker feed thing is supposed to do 
    # but I fixed the runtime errors that were causing client to crash
    #
    # Ticker text functions
    def feed(self, text):
        fm = QFontMetrics(self.alert_label.font())             ###self.parent.fontMetrics()
        self.nl = int(self.alert_label.width()/fm.averageCharWidth())     # shown stringlength
        news = []
        for e in text:
            news.append(e)
        appendix = ' '*self.nl                  # add some spaces at the end
        news.append(appendix)
        delimiter = '      +++      '           # shown between the messages
        self.news = delimiter.join(news)
        newsLength = len(text)                  # number of letters in news = frameRange 
        lps = 4                                 # letters per second 
        dur = int(newsLength*1000/lps)          # duration until the whole string is shown in milliseconds                                          
        timeLine = QTimeLine(dur)
        timeLine.setFrameRange(0, newsLength) 
        timeLine.start()

    def setText(self, number_of_frame):   
        if number_of_frame < self.nl:
            start = 0
        else:
            start = number_of_frame - self.nl
        text = '{}'.format(self.news[start:number_of_frame])        
        self.alert_label.setText(text)

    def nextNews(self):
        self.feed()                             # start again

    def setTlText(self, text):
        string = '{} pressed'.format(text)
        self.alert_label.setText(string)
        
    # Flash the background color by changing opacity from nothing to everything
    def flash(self, cycles, flash_time, color):
        n=0
        for n in range(cycles):
            self.change_opacity(1)
            time.sleep(flash_time/2)
            self.change_opacity(100)
            time.sleep(flash_time/2)
        value = self.user_display.opacity_slider.value()
        self.change_opacity(value)

    def audio_alert(self, user, message):
        tts = gTTS("From "+user+". "+message, lang='en')
        audio = io.BytesIO()
        tts.write_to_fp(audio)
        audio.seek(0)
        sound = pygame.mixer.Sound(audio)
        volume = self.user_display.volume_slider.value()
        sound.set_volume(volume/100)
        sound.play()
        
    def display_alert(self, text, color):
        self.alert_label.setText(text)
        self.toolbar.setStyleSheet("background:"+color+";")
        QCoreApplication.processEvents()

        klaxon = None

        if color == "lightgreen":
            klaxon = pygame.mixer.Sound(local_file('green_alarm.mp3'))
        if color == "blue":
            klaxon = pygame.mixer.Sound(local_file('blue_alarm.mp3'))
        if color == "purple":
            klaxon = pygame.mixer.Sound(local_file('purple_alarm.mp3'))
        elif color == "yellow":
            klaxon = pygame.mixer.Sound(local_file('yellow_alarm.mp3'))
        elif color == "red":
            self.feed(text)
            klaxon = pygame.mixer.Sound(local_file('red_alarm.mp3'))

        if klaxon:
            volume = self.user_display.volume_slider.value()
            klaxon.set_volume(volume/100)
            klaxon.play()     
            self.flash(4, 0.5, color)
            
    def closeEvent(self, event):
        self.exit()
        event.accept()

    # Disconnect and exit application - user session persists
    def exit(self):
        pygame.mixer.quit()
        self.disconnect()
        QCoreApplication.quit()
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
    QCoreApplication.processEvents()

    alert_display.update_ui()
    app.exec()

# Run "main" function on start
if __name__ == '__main__':
    main()
