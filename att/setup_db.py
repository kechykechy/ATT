import sqlite3
import os

DB_NAME = 'construction.db'
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(PROJECT_DIR, DB_NAME)

def create_connection():
    """ create a database connection to the SQLite database """
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        print(f"SQLite version: {sqlite3.sqlite_version}")
        print(f"Database created/connected at: {DB_PATH}")
        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
    return conn

def create_table(conn, create_table_sql):
    """ create a table from the create_table_sql statement """
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
        print(f"Table created successfully: {create_table_sql.split('(')[0].split()[-1]}")
    except sqlite3.Error as e:
        print(f"Error creating table: {e}")

def setup_database():
    sql_create_materials_table = """ CREATE TABLE IF NOT EXISTS materials (
                                        id integer PRIMARY KEY,
                                        name text NOT NULL UNIQUE,
                                        unit text NOT NULL,
                                        current_quantity integer DEFAULT 0
                                    ); """

    sql_create_stakeholders_table = """CREATE TABLE IF NOT EXISTS stakeholders (
                                        id integer PRIMARY KEY,
                                        name text,
                                        phone_number text NOT NULL UNIQUE
                                    );"""

    # create a database connection
    conn = create_connection()

    # create tables
    if conn is not None:
        create_table(conn, sql_create_materials_table)
        create_table(conn, sql_create_stakeholders_table)

        # --- Optional: Add initial data --- 
        try:
            cursor = conn.cursor()
            # Add some sample materials if the table is newly created or empty
            cursor.execute("INSERT OR IGNORE INTO materials (name, unit) VALUES (?, ?)", ('Cement', 'bags'))
            cursor.execute("INSERT OR IGNORE INTO materials (name, unit) VALUES (?, ?)", ('Sand', 'tonnes'))
            cursor.execute("INSERT OR IGNORE INTO materials (name, unit) VALUES (?, ?)", ('Steel Rods', 'metres'))
            cursor.execute("INSERT OR IGNORE INTO materials (name, unit) VALUES (?, ?)", ('Gravel', 'tonnes'))
            print("Sample materials added (if they didn't exist).")

            # Add a sample stakeholder (REPLACE with actual numbers)
            cursor.execute("INSERT OR IGNORE INTO stakeholders (name, phone_number) VALUES (?, ?)", ('Test User', '+255756584341')) 
            print("Test stakeholder added (if they didn't exist).")
            
            conn.commit()
        except sqlite3.Error as e:
            print(f"Error adding initial data: {e}")
        finally:
            conn.close()
            print("Database connection closed.")
    else:
        print("Error! cannot create the database connection.")

if __name__ == '__main__':
    setup_database()
