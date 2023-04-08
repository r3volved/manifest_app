import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QSlider
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPalette
import requests
import socketio

name = "main"
SERVER_URL = "http://localhost:5000/"

class AlertDisplay(QWidget):
    def init(self, user_id, role):
        #super().init()

        self.user_id = user_id
        self.role = role

        self.init_ui()
        self.connect_socketio()

    def init_ui(self):
        self.setWindowTitle('Alert App')
        self.setAutoFillBackground(True)

        palette = self.palette()
        palette.setColor(QPalette.Background, QColor('green'))
        self.setPalette(palette)

        self.alert_label = QLabel('No alert')
        self.alert_label.setAlignment(Qt.AlignCenter)
        self.alert_label.setWordWrap(True)

        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.valueChanged.connect(self.change_opacity)

        layout = QVBoxLayout()
        layout.addWidget(self.alert_label)
        layout.addWidget(self.opacity_slider)

        self.setLayout(layout)

    def change_opacity(self, value):
        opacity = value / 100
        self.setWindowOpacity(opacity)

    def display_alert(self, text, color):
        self.alert_label.setText(text)

        palette = self.palette()
        palette.setColor(QPalette.Background, QColor(color))
        self.setPalette(palette)

    def send_alert(self, text, color):
        if self.role <= 3:  
            data = {  
                "user_id": self.user_id,
                "text": text,
                "color": color
            }
            print(data)
            self.sio.emit("send_alert", data)
        else:
            print("User does not have permission to send alerts")

    def connect_socketio(self):
        self.sio = socketio.Client()

        @self.sio.event
        def connect():
            print("Connected to server")

        @self.sio.event
        def disconnect():
            print("Disconnected from server")

        @self.sio.event
        def receive_alert(data):
            text = data['text']
            color = data['color']
            self.display_alert(text, color)

        self.sio.connect(SERVER_URL)

def main():
    app = QApplication(sys.argv)

    # Replace these values with valid user_id and password
    user_id = "user1"
    password = "password1"

    response = requests.post(f"{SERVER_URL}/login", data={"user_id": user_id, "password": password})
        
    if response.status_code == 200:
        data = response.json()
        print(data)
        role = data["role"]
        print(role)

        alert_display = AlertDisplay()
        alert_display.init(user_id, role)
        alert_display.show()

        alert_display.send_alert("wowiwow","red")        
        
        sys.exit(app.exec())
    else:
        print("Invalid user credentials")

if name == 'main':
    main()
