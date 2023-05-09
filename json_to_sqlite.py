# Turn a simple json structure into an sqlite database 
# Assumes the top level json keys represent values for the ID field

import sqlite3
import json
import sys
import os

def create_table(cursor, data):
    columns = []
    for key, value in data.items():
        if isinstance(value, int):
            col_type = "INTEGER"
        elif isinstance(value, str):
            col_type = "TEXT"
        elif value is None:
            col_type = "TEXT"
        else:
            raise ValueError(f"Unsupported data type for column '{key}': {type(value)}")
        columns.append(f"{key} {col_type}")

    create_table_sql = f"""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        {', '.join(columns)}
    )
    """
    cursor.execute(create_table_sql)

def insert_data(conn, data):
    cursor = conn.cursor()
    for user_id, user_data in data.items():
        columns = ["id"] + list(user_data.keys())
        placeholders = ", ".join("?" * len(columns))
        sql = f"INSERT OR REPLACE INTO users ({', '.join(columns)}) VALUES ({placeholders})"
        values = [user_id] + list(user_data.values())
        cursor.execute(sql, values)
    conn.commit()

def dump_data(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    rows = cursor.fetchall()

    print("Dumping data from users table:")
    for row in rows:
        print(row)

def main(json_file_path):
    # Read JSON data
    with open(json_file_path, "r") as json_file:
        data = json.load(json_file)

    # Create SQLite database
    db_name = os.path.splitext(json_file_path)[0] + ".db"
    conn = sqlite3.connect(db_name)

    # Create table and insert data
    cursor = conn.cursor()
    create_table(cursor, next(iter(data.values())))
    insert_data(conn, data)

    # Dump data from the users table
    dump_data(conn)

    # Close the database connection
    conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python json_to_sqlite.py <json_file_path>")
        sys.exit(1)

    json_file_path = sys.argv[1]
    main(json_file_path)
