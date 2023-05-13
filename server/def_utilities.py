import sys
import os
import json

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

