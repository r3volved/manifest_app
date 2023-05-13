import requests

from PyQt5.QtWidgets import QDialog, QFrame, QRadioButton, QHBoxLayout, QTextEdit, QFormLayout, QLineEdit, QPushButton, QSlider, QLabel
from PyQt5.QtCore import Qt, QCoreApplication, QEvent

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

    # Automagic-close this window when loses focus
    def changeEvent(self, event):
        if event.type() == QEvent.ActivationChange and not self.isActiveWindow():
            self.hide()

    def login(self):
        user_id = self.login_user.text()
        password = self.login_password.text()
        if user_id and password:
            self.parent.display_alert("Logging in ...","lightgrey")
            self.hide()
            QCoreApplication.processEvents()

            response = requests.post(f"{self.parent.SERVER_URL}/login", data={"user_id": user_id, "password": password})
            if response.status_code == 200:
                data = response.json()
                newuser = { "token":data["token"], "role":data["role"], "username":data["username"] }
                self.parent.user.update_preferences(newuser)
                self.parent.update_ui()
            else:
                self.parent.display_alert("Invalid credentials","orange")

# Define the login window
class PasswordWindow(QDialog):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('Change your password')
        self.setAutoFillBackground(True)
        self.setWindowModality(Qt.WindowModal)
        self.setFixedWidth(300)

        self.form = QFormLayout()

        self.error_label = QLabel("...")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        self.form.addRow(self.error_label)

        self.old_password = QLineEdit()
        self.old_password.setEchoMode(QLineEdit.Password)
        self.form.addRow("Current Password", self.old_password)

        self.new_password = QLineEdit()
        self.new_password.setEchoMode(QLineEdit.Password)
        self.form.addRow("New Password", self.new_password)
        
        self.confirm_new_password = QLineEdit()
        self.confirm_new_password.returnPressed.connect(self.change_password)
        self.confirm_new_password.setEchoMode(QLineEdit.Password)
        self.form.addRow("Confirm Password", self.confirm_new_password)

        self.submit_button = QPushButton()
        self.submit_button.setText('Change Passord')
        self.submit_button.clicked.connect(self.change_password)
        self.form.addRow(self.submit_button)
        self.setLayout(self.form)

    # Automagic-close this window when loses focus
    def changeEvent(self, event):
        if event.type() == QEvent.ActivationChange and not self.isActiveWindow():
            self.hide()

    def change_password(self):
        old_password = self.old_password.text()
        new_password = self.new_password.text()
        confirm_password = self.confirm_new_password.text()
        if new_password != confirm_password:
            return self.password_error("Your new passwords do not match","red")

        if len(new_password) < 8:
            return self.password_error("Password must be at least 8 characters","red")

        self.error_label.hide()
        if self.parent.user.get("token") and self.parent.ws.isConnected():
            self.parent.ws.change_password({ "token":self.parent.user.get("token"), "old_password":old_password, "new_password":new_password })

    def password_error(self, error, color):
        if color is None:
            color = 'red'
        self.error_label.setStyleSheet(f"color:{color}; padding-top:0.5em; padding-bottom:0.5em;")
        self.error_label.setText(error)
        self.error_label.show()
    
    def close(self):
        self.error_label.hide()
        self.hide()

# Define the user profile window
class UserWindow(QDialog):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.init_ui()

    # Automagic-close this window when loses focus
    def changeEvent(self, event):
        if event.type() == QEvent.ActivationChange and not self.isActiveWindow():
            self.hide()

    def init_ui(self):
        self.setAutoFillBackground(True)
        self.setWindowModality(Qt.WindowModal)
        self.setFixedWidth(800)
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



