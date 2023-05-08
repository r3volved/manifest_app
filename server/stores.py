import sys
import os
import sqlite3
import json

from pypref import Preferences

if getattr(sys, 'frozen', False):
    # If the application is run as a bundle, the PyInstaller bootloader
    # extends the sys module by a flag frozen=True and sets the app 
    # path into variable _MEIPASS'.
    application_path = sys._MEIPASS
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

# Return filename prefixed with client path
def local_file(filename):
    return os.path.join(application_path, filename)

# Simple data store model
# Scale this with more appropriate data storage
class SimpleStore():
    def __init__(self, store):
        # TODO: connect to database
        self.source = store["source"]
        self.type = store["type"]
        self.conn = None
        if self.type == "dict":
            if self.source:
                self.data = self.source #dict
            else:
                self.data = {}
        elif self.type == "py":
            self.data = Preferences(filename=self.source)
        elif self.type == "json":
            with open(local_file(self.source), 'r') as f:
                self.data = json.load(f)
        elif self.type == "sqlite":
            self.conn = sqlite3.connect(local_file(self.source))
            cursor = self.conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    password TEXT NOT NULL,
                    role INTEGER NOT NULL,
                    username TEXT NOT NULL,
                    icon TEXT,
                    color TEXT,
                    token TEXT,
                    last_login TIMESTAMP,
                    last_connect TIMESTAMP,
                    last_disconnect TIMESTAMP
                )
            ''')
            self.conn.commit()

    def connected(self):
        if self.type == "sqlite":
            return self.conn is not None
        return True
            
    def reset(self):
        # No reset for json files
        # No reset for sqlite
        if self.type == "dict":
            self.data = {}
        elif self.type == "py":
            self.data.set_preferences({})

    def get(self, key):
        if self.type == "dict":
            return self.data[key]
        elif self.type == "py":
            return self.data.get(key)
        elif self.type == "json":
            return self.data.get(key)
        elif self.type == "sqlite":
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id=?", (key,))
            result = cursor.fetchone()
            return result[0] if result else None

    def set(self, key, value):
        if self.type == "dict":
            self.data[key] = value
        elif self.type == "py":
            update = {}
            update[key] = value
            self.data.update_preferences(update)
        elif self.type == "json":
            self.data[key] = value
            json_object = json.dumps(self.data, indent=0)
            with open(local_file(self.source), "w") as f:
                f.write(json_object)
        elif self.type == "sqlite":
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO users (
                    id, password, role, username, icon, color, token,
                    last_login, last_connect, last_disconnect
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                value["id"], value["password"], value["role"], value["username"],
                value["icon"], value["color"], value["token"],
                value["last_login"], value["last_connect"], value["last_disconnect"]
            ))
            self.conn.commit()
    
    def rem(self, key):
        if self.type == "dict":
            del self.data[key]
        elif self.type == "py":
            update = {}
            update[key] = None
            self.data.update_preferences(update)
        elif self.type == "json":
            self.data.pop(key,None)
            json_object = json.dumps(self.data, indent=0)
            with open(local_file(self.source), "w") as f:
                f.write(json_object)
        elif self.type == "sqlite":
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM users WHERE id=?", (key,))
            self.conn.commit()

    def edit(self, key, new_data):
        if self.type == "dict":
            self.data[key] = new_data
        elif self.type == "py":
            update = {}
            update[key] = new_data
            self.data.update_preferences(update)
        elif self.type == "json":
            data = self.data.get(key)
            data.update(new_data)
            self.data[key] = data
            json_object = json.dumps(self.data, indent=0)
            with open(local_file(self.source), "w") as f:
                f.write(json_object)
        elif self.type == "sqlite":
            cursor = self.conn.cursor()
            cursor.execute("UPDATE users SET value=? WHERE id=?", (new_data, key))
            self.conn.commit()

    def close(self):
        if self.type == "sqlite":
            self.conn.close()
            self.conn = None

