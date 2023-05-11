# Turn a simple json structure into an sqlite database 
# Assumes the top level json keys represent values for the ID field

import sqlite3
import json
import sys
import os

def dump_data(conn, table_name):
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()

    print(f"Dumping data from {table_name} table:")
    for row in rows:
        print(row)

def create_table(cursor, table_name, data):
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
        columns.append(f'"{key}" {col_type}')

    create_table_sql = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        id TEXT PRIMARY KEY,
        {', '.join(columns)}
    )
    """
    cursor.execute(create_table_sql)

def insert_data(conn, table_name, data):
    cursor = conn.cursor()
    for record in data:
        columns = list(record.keys())
        placeholders = ", ".join("?" * len(columns))
        sql = f"INSERT OR REPLACE INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
        values = list(record.values())
        cursor.execute(sql, values)
    conn.commit()

def process_data(conn, key, value, default_table_name):
    if isinstance(value, list):
        create_table(conn.cursor(), key, value[0])
        insert_data(conn, key, value)
        dump_data(conn, key)
    elif isinstance(value, dict):
        create_table(conn.cursor(), default_table_name, next(iter(value.values())))
        insert_data(conn, default_table_name, value)
        dump_data(conn, default_table_name)
    else:
        raise ValueError("Unsupported JSON structure")

def main(json_file_path):
    # Read JSON data
    with open(json_file_path, "r") as json_file:
        data = json.load(json_file)

    # Create SQLite database
    db_name = os.path.splitext(json_file_path)[0] + ".db"
    conn = sqlite3.connect(db_name)
    default_table_name = os.path.splitext(os.path.basename(json_file_path))[0]

    # Process JSON data
    for key, value in data.items():
        process_data(conn, key, value, default_table_name)

    # Close the database connection
    conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python json_to_sqlite.py <json_file_path>")
        sys.exit(1)

    json_file_path = sys.argv[1]
    main(json_file_path)
