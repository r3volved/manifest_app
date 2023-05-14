import socketio

from PyQt5.QtCore import QObject, pyqtSignal

class WebSocket(QObject):
    user_profile = pyqtSignal(dict)
    password_changed = pyqtSignal(bool, str, str, str)
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
                self.sio.emit("get_data", { "token":self.parent.user.get("token"), "table":"alerts" })

        @self.sio.event
        def disconnect():
            self.disconnected.emit()

        @self.sio.event
        def user_profile(data):
            self.user_profile.emit(data)

        @self.sio.event
        def receive_alert(data):
            text = data.get("text")
            color = data.get("color")
            username = data.get("username")
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
        def alerts_list(data):
            if self.parent.user.get("role") is None or self.parent.user.get("role") > 3:
                return
            self.load_alerts.emit(data)

        @self.sio.event
        def online_users_list(data):
            self.load_users.emit(data)

        @self.sio.event
        def password_changed(data):
            success = data.get("success")
            error = data.get("error")
            color = data.get("color")
            username = data.get("username")
            self.password_changed.emit(success, error, color, username)

    def get_user_profile(self, data):
        self.sio.emit("get_user_profile", data)

    def change_password(self, data):
        self.sio.emit("change_password", data)

    def send_alert(self, data):
        self.sio.emit("send_alert", data)

    def isConnected(self):
        return self.sio.connected

    def connect(self):
        # Connect to server when AlertDisplay initialized
        self.sio.connect(self.parent.SERVER_URL)

    def disconnect(self):
        self.sio.disconnect()

