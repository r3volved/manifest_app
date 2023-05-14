import sys
import os
import json
import random
import bcrypt

# Return filename prefixed with client path
def local_file(filename):
    # If the application is run as a bundle, the PyInstaller bootloader
    # extends the sys module by a flag frozen=True and sets the app 
    # path into variable _MEIPASS'.
    if getattr(sys, 'frozen', False):
        application_path = sys._MEIPASS
    else:
        application_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(application_path, filename)

# Return content of a json file
def read_json(filename):
    with open(filename, 'r') as f:
        config = json.load(f)
    return config

def make_token():
    return str(random.getrandbits(128))

def hash_password(password):
    if not isinstance(password, bytes):
        password = password.encode('utf-8')  # Passwords should be bytes
    salt = bcrypt.gensalt()  # Generate a random salt
    return bcrypt.hashpw(password, salt)  # Hash the password


def test_password(password, hash):
    if not isinstance(password, bytes):
        return bcrypt.checkpw(password.encode('utf-8'), hash)
    else:
        return bcrypt.checkpw(password, hash)
    
