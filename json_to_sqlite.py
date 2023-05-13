import json
import sqlite3
import os
import sys
import bcrypt

from typing import Dict, Any

def dump_data(cursor, table_name):
    print(f"Dumping data from {table_name} table:")
    cursor.execute(f"PRAGMA table_info({table_name})")
    column_info = cursor.fetchall()
    
    # column[1] contains the column name
    column_names = [column[1] for column in column_info]
    print(f"{', '.join(column_names)}")

    # column[2] contains the data type
    column_types = [column[2] for column in column_info]
    print(f"{', '.join(column_types)}")
        
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    for row in rows:
        print(row)

def infer_datatype(value):
    if isinstance(value, int):
        return 'INTEGER'
    elif isinstance(value, float):
        return 'REAL'
    elif isinstance(value, bool):
        return 'BOOLEAN'
    elif isinstance(value, str):
        return 'TEXT'
    else:
        return 'TEXT'

def accumulate_columns(data: Dict[str, Any]) -> Dict[str, Any]:
    columns = {}
    for table_name, records in data.items():
        for record in records:
            if table_name not in columns:
                columns[table_name] = {}
            for col, val in record.items():
                columns[table_name][col] = infer_datatype(val)
    return columns

def create_tables(cursor, columns: Dict[str, Any]) -> None:
    for table_name, column_info in columns.items():
        cols = ', '.join([f'"{col}" {datatype} {("PRIMARY KEY" if col=="id" else "")}' for col, datatype in column_info.items()])
        cursor.execute(f'CREATE TABLE IF NOT EXISTS "{table_name}" ({cols});')

def hash_password(password: str) -> bytes:
    password = password.encode('utf-8')  # Passwords should be bytes
    salt = bcrypt.gensalt()  # Generate a random salt
    return bcrypt.hashpw(password, salt)  # Hash the password

def insert_records(cursor, data: Dict[str, Any], columns: Dict[str, Any]) -> None:
    for table_name, records in data.items():
        for record in records:
            values = []
            for col in columns[table_name].keys():
                value = record.get(col, None)
                if col == "password" and value is not None:
                    value = hash_password(value)
                values.append(value)
            
            column_names = ', '.join([f'"{col}"' for col in columns[table_name].keys()])
            cursor.execute(f'INSERT INTO "{table_name}" ({column_names}) VALUES ({",".join("?"*len(values))});', values)
        dump_data(cursor, table_name)

def json_to_sqlite(json_filename: str, db_filename: str) -> None:
    with open(json_filename, 'r') as f:
        data = json.load(f)
    
    columns = accumulate_columns(data)

    with sqlite3.connect(db_filename) as conn:
        cursor = conn.cursor()
        create_tables(cursor, columns)
        conn.commit()
        insert_records(cursor, data, columns)
        conn.commit()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python json_to_sqlite.py <json_file_path>")
        sys.exit(1)

    json_filename = sys.argv[1]
    db_filename = os.path.splitext(json_filename)[0] + '.db'
    json_to_sqlite(json_filename, db_filename)
