import sys
import os
import sqlite3
import json

def sqlite_to_json(db_path, json_path):
    # Connect to the SQLite database
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # allows us to access rows by column name

    # Create a cursor
    cur = conn.cursor()

    # Fetch the names of all tables in the database
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    table_names = [row[0] for row in cur.fetchall()]

    # Create a dictionary to hold the data
    data = {}

    # Fetch the data from each table
    for table_name in table_names:
        cur.execute(f'SELECT * FROM "{table_name}";')
        records = []
        for row in cur.fetchall():
            # convert rows to dictionaries and convert bytes to str
            record = {}
            for key in row.keys():
                if isinstance(row[key], bytes):
                    record[key] = "********"
                else:
                    record[key] = row[key]
            records.append(record)
        data[table_name] = records

    # Write the data to a JSON file
    with open(json_path, 'w') as f:
        json.dump(data, f, indent=2)

    # Close the connection
    conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python sqlite_to_json.py <db_file_path>")
        sys.exit(1)

    db_filename = sys.argv[1]
    json_filename = os.path.splitext(db_filename)[0] + '.json'
    sqlite_to_json(db_filename, json_filename)
