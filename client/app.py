import sys
import requests
import pygame
import time
import io

from PyQt5.QtWidgets import QApplication, QMainWindow, QMenu, QToolBar, QSizePolicy, QToolButton, QAction, QHBoxLayout, QWidget, QLabel
from PyQt5.QtCore import Qt, QCoreApplication, QTimeLine
from PyQt5.QtGui import QFontMetrics
from pypref import Preferences
from gtts import gTTS

from def_utilities import local_file, read_json, make_icon
from def_windows import LoginWindow, UserWindow, PasswordWindow, ManageUserWindow
from def_websocket import WebSocket

pygame.mixer.init()

# Define the main alert bar
class AlertWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = read_json(local_file("config.json"))
        self.SERVER_URL = self.config.get("SERVER_URL")
        self.user = Preferences(filename="manifest_cache.py")
        self.alerts = None
        self.init_ui()

        self.ws = WebSocket(self)
        # self.ws.password_changed.connect(self.password_changed)
        self.ws.load_users.connect(self.populate_users)
        self.ws.load_alerts.connect(self.populate_alerts)
        self.ws.audio_alert.connect(self.audio_alert)
        self.ws.display_alert.connect(self.display_alert)
        self.ws.disconnected.connect(self.websocket_disconnected)
        self.ws.connected.connect(self.websocket_connected)
        self.ws.logout.connect(self.logout)

        self.user_window = UserWindow(self)
        self.login_window = LoginWindow(self)
        self.password_window = PasswordWindow(self)
        self.manage_user_window = ManageUserWindow(self)

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

        self.control_options = QToolButton(self.toolbar_container)
        self.control_options.setText('Login')
        self.control_options.setStyleSheet("QToolButton { padding:0.5em; } QToolButton::menu-indicator { width:0; height:0; }")
        self.control_options.setPopupMode(QToolButton.InstantPopup)
        self.toolbar_layout.addWidget(self.control_options)
        self.control_options_menu = QMenu()

        self.control_options_settings = QAction(make_icon("login"), "Login", self.control_options_menu)
        self.control_options_settings.triggered.connect(self.user_menu)
        self.control_options_menu.addAction(self.control_options_settings)

        self.control_options_profile = QAction(make_icon("edit"), "User Profile", self.control_options_menu)
        self.control_options_profile.triggered.connect(lambda checked: self.manage_user_window.edit_user())
        self.control_options_profile.setVisible(False) #Show when connected
        self.control_options_menu.addAction(self.control_options_profile)

        self.control_options_password = QAction(make_icon("edit"), "Change Password", self.control_options_menu)
        self.control_options_password.triggered.connect(lambda checked: self.password_window.show())
        self.control_options_password.setVisible(False) #Show when connected
        self.control_options_menu.addAction(self.control_options_password)

        self.control_options_websocket = QAction(make_icon("websocket"), "Connect", self.control_options_menu)
        self.control_options_websocket.triggered.connect(self.websocket_toggler)
        self.control_options_websocket.setVisible(False) #Show when logged in
        self.control_options_menu.addAction(self.control_options_websocket)

        self.control_options_logout = QAction(make_icon("logout"), "Logout", self.control_options_menu)
        self.control_options_logout.triggered.connect(self.logout)
        self.control_options_logout.setVisible(False) #Show when logged in
        self.control_options_menu.addAction(self.control_options_logout)

        self.control_options_quit = QAction(make_icon("exit"), "Quit", self.control_options_menu)
        self.control_options_quit.triggered.connect(self.exit)
        self.control_options_menu.addAction(self.control_options_quit)

        self.control_options.setMenu(self.control_options_menu)

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

        self.toolbar.addWidget(self.toolbar_container)
        QCoreApplication.processEvents()

    def update_ui(self):
        self.control_users.hide()
        self.control_alerts.hide()
        if self.user.get("username"):
            self.control_options_settings.setText("Settings")
            self.control_options_settings.setIcon(make_icon("settings"))
            self.control_options_websocket.setVisible(True)
            self.control_options_logout.setVisible(True)
            self.control_options.setText(self.user.get("username"))
            self.display_alert("Connecting to mothership ...","lightgrey")
            if not self.ws.isConnected():
                self.ws.connect()
        else:
            self.control_options_settings.setText("Login")
            self.control_options_settings.setIcon(make_icon("login"))
            self.control_options_websocket.setVisible(False)
            self.control_options_logout.setVisible(False)
            self.display_alert("Please login ...","lightgrey")
            self.control_options.setText("Login")               
            if self.ws.isConnected():
                self.ws.disconnect()

    def websocket_connected(self):
        self.control_options_profile.setVisible(True)
        self.control_options_password.setVisible(True)
        self.control_options_websocket.setText("Disconnect")
        self.control_options_websocket.setIcon(make_icon("connected"))
        self.display_alert("Connected!", "lightgrey")
        self.control_users.show()
        if self.alerts is not None:
            self.control_alerts.show()

    def websocket_disconnected(self):
        self.control_options_profile.setVisible(False)
        self.control_options_password.setVisible(False)
        self.control_options_websocket.setText("Connect")
        self.control_options_websocket.setIcon(make_icon("disconnected"))
        self.display_alert("Disconnected!", "orange")
        self.control_users.hide()
        self.control_alerts.hide()

    def websocket_toggler(self):
        if self.ws.isConnected():
            self.ws.disconnect()
        else:
            self.ws.connect()
        QCoreApplication.processEvents()


    # Open the login window if no session, otherwise open user window
    def user_menu(self):
        if self.user.get("token") is None:
            self.login_window.show()
        else:
            self.user_window.init_user()
            self.user_window.show()


    # Only disconnect from websocket - user session persists 
    def disconnect(self):
        if self.ws.isConnected():
            self.ws.disconnect()

    # Disconnect from websocket and then flush user from client and server
    def logout(self):
        self.login_window.hide()
        self.user_window.hide()
        QCoreApplication.processEvents()

        self.disconnect()
        if self.user.get("token") is not None:
            requests.post(f"{self.SERVER_URL}/logout", data={"token": self.user.get("token")})
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
            name = user.get('name')
            color = user.get('color')
            if color is None:
                color = 'lightgreen'
    
            if user.get("icon") is None:
                icon = make_icon('spock-fill', color)
            else:
                icon = make_icon(user.get("icon"), color)
    
            action = QAction(icon, name, menu)

            if self.user.get("role") <= 3:
                if self.user.get("role") < user.get("role"):
                    action.triggered.connect(lambda checked, i=user.get("id"): self.manage_user_window.edit_user(i))
                else:
                    action.triggered.connect(lambda checked, i=user.get("id"): self.manage_user_window.view_user(i))

            menu.addAction(action)
        self.control_users.setText('Users ('+str(len(users))+')')
        self.control_users.setMenu(menu)

    def populate_alerts(self, alerts):
        if self.alerts is not None:
            return
        
        def sort_index(e):
            return e.get("sort_index")
        
        self.alerts = alerts
        self.alerts.sort(key=sort_index)
        menu = QMenu()
        for alert in self.alerts:
            text = alert.get("text")
            color = alert.get("color")
            icon = make_icon('circle',color)
            action = QAction(icon, text, menu)
            if alert.get("shortcut"):
                action.setShortcut(alert.get("shortcut")) 
            action.triggered.connect(lambda checked, t=text, c=color: self.send_alert(t,c))
            menu.addAction(action)

        self.control_alerts.setMenu(menu)
        self.control_alerts.show()
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
    def flash(self, cycles, flash_time):
        for n in range(cycles):
            self.change_opacity(1)
            time.sleep(flash_time/2)
            self.change_opacity(100)
            time.sleep(flash_time/2)
        value = self.user_window.opacity_slider.value()
        self.change_opacity(value)

    def setTextColor(self,color): 
        self.alert_label.setStyleSheet("padding:0.5em 1em; color: "+color+";")
        self.control_options.setStyleSheet("QToolButton { color: "+color+"; padding:0.5em; } QToolButton::menu-indicator { width:0; height:0; }")
        self.control_users.setStyleSheet("QToolButton { color: "+color+"; padding:0.5em; } QToolButton::menu-indicator { width:0; height:0; }")
        self.control_alerts.setStyleSheet("QToolButton { color: "+color+"; padding:0.5em; } QToolButton::menu-indicator { width:0; height:0; }")
        QCoreApplication.processEvents()

    def audio_alert(self, user, message):
        tts = gTTS("From "+user+". "+message, lang='en')
        audio = io.BytesIO()
        tts.write_to_fp(audio)
        audio.seek(0)
        sound = pygame.mixer.Sound(audio)
        volume = self.user_window.volume_slider.value()
        sound.set_volume(volume/100)
        sound.play()
        
    def display_alert(self, text, color):
        self.alert_label.setText(text)
        self.toolbar.setStyleSheet("background:"+color+";")
        self.setTextColor("black")
        QCoreApplication.processEvents()

        klaxon = None

        if color == "lightgreen":
            klaxon = pygame.mixer.Sound(local_file('green_alarm.mp3'))
        if color == "blue":
            klaxon = pygame.mixer.Sound(local_file('blue_alarm.mp3'))
            self.setTextColor("white")
        if color == "purple":
            klaxon = pygame.mixer.Sound(local_file('purple_alarm.mp3'))
            self.setTextColor("white")
        elif color == "yellow":
            klaxon = pygame.mixer.Sound(local_file('yellow_alarm.mp3'))
        elif color == "red":
            self.feed(text)
            klaxon = pygame.mixer.Sound(local_file('red_alarm.mp3'))
            self.setTextColor("white")
        else:
            self.feed(text)

        if klaxon:
            volume = self.user_window.volume_slider.value()
            klaxon.set_volume(volume/100)
            klaxon.play()     
            self.flash(4, 0.5)
            
    def closeEvent(self, event):
        self.exit()
        event.accept()

    # Disconnect and exit application - user session persists
    def exit(self):
        pygame.mixer.quit()
        self.disconnect()
        QCoreApplication.quit()
        quit()

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
