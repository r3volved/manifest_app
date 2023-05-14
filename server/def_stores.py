import sqlite3

from def_utilities import local_file

class UserStore():
    def __init__(self, userstore):
        self.source = userstore.get("source")
        self.type = userstore.get("type")
        self.conn = sqlite3.connect(local_file(self.source), check_same_thread=False)

    def connected(self):
        return self.conn is not None
    
    def close(self):
        self.conn.close()
        self.conn = None

    def set_token(self,token,user_id):
        if user_id is None or token is None:
            return
        
        cursor = self.conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO tokens ( id, token ) VALUES (?, ?)", (user_id, token))
        self.conn.commit()

    def clear_token(self,token):
        cursor = self.conn.cursor()
        user_id = self.get_user_id_from_token(token)
        if user_id is None:
            return 
        cursor.execute("DELETE FROM tokens WHERE token=?", (token,))
        self.conn.commit()
        
    def get_user_id_from_token(self, token):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM tokens WHERE token=?", (token,))
        row = cursor.fetchone()
        if row is None:
            return None
        else:
            return row[0]
        
    def get_user_from_token(self, token):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users JOIN tokens ON tokens.id = users.id WHERE tokens.token=?", (token,))
        result = cursor.fetchone()
        if result:
            column_names = [description[0] for description in cursor.description]
            return dict(zip(column_names, result))
        else:
            return None

    def get_profile(self, id):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT 
                id, 
                role,
                rank,
                department, 
                username, 
                icon, 
                color, 
                last_login, 
                last_connect, 
                last_disconnect 
            FROM users 
            WHERE id=?
        ''', (id,))
        result = cursor.fetchone()
        if result:
            column_names = [description[0] for description in cursor.description]
            return dict(zip(column_names, result))
        else:
            return None

    def get_all(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT 
                id, 
                role,
                rank,
                department, 
                username, 
                icon, 
                color, 
                last_login, 
                last_connect, 
                last_disconnect 
            FROM users
        ''')
        columns = [column[0] for column in cursor.description]
        data = []
        for row in cursor.fetchall():
            data.append(dict(zip(columns, row)))
        return data

    def get(self, id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id=?", (id,))
        result = cursor.fetchone()
        if result:
            column_names = [description[0] for description in cursor.description]
            return dict(zip(column_names, result))
        else:
            return None

    def set(self, user_data):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO users (
                id, 
                password, 
                role, 
                rank,
                department,
                username, 
                icon, 
                color, 
                last_login, 
                last_connect, 
                last_disconnect
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_data.get("id"),
            user_data.get("password"),
            user_data.get("role"),
            user_data.get("rank"),
            user_data.get("department"),
            user_data.get("username"),
            user_data.get("icon"),
            user_data.get("color"),
            user_data.get("last_login"),
            user_data.get("last_connect"),
            user_data.get("last_disconnect")
        ))
        self.conn.commit()

    def rem(self, id):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM users WHERE id=?", (id,))
        self.conn.commit()

    def edit(self, id, new_data):
        cursor = self.conn.cursor()

        # Generate the SQL statement
        columns = ", ".join(f"{key}=?" for key in new_data.keys())
        sql = f"UPDATE users SET {columns} WHERE id=?"

        # Prepare the values for the SQL statement
        values = list(new_data.values())
        values.append(id)

        # Execute the SQL statement
        cursor.execute(sql, tuple(values))
        self.conn.commit()

class DataStore():
    def __init__(self, datastore):
        self.source = datastore.get("source")
        self.type = datastore.get("type")
        self.conn = sqlite3.connect(local_file(self.source), check_same_thread=False)
        # will do this the slower programmatic way instead of attach
        # self.cursor.execute("ATTACH DATABASE 'data.db' AS data")

    def connected(self):
        return self.conn is not None
    
    def close(self):
        self.conn.close()
        self.conn = None

    def get_all(self, table_name):
        cursor = self.conn.cursor()
        cursor.execute(f"SELECT * FROM {table_name}")
        columns = [column[0] for column in cursor.description]
        data = []
        for row in cursor.fetchall():
            data.append(dict(zip(columns, row)))
        return data

    