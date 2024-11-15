import sqlite3
from datetime import datetime
import time
from contextlib import contextmanager

class Database:
    def __init__(self, db_name="requests.db"):
        self.db_name = db_name
        self.max_retries = 3
        self.retry_delay = 1
        self.initialize_database()
    
    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_name)
        try:
            yield conn
        finally:
            conn.close()
    
    def initialize_database(self):
        for attempt in range(self.max_retries):
            try:
                with self.get_connection() as conn:
                    conn.execute('PRAGMA encoding="UTF-8"')
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='requests'")
                    if not cursor.fetchone():
                        self.create_table(conn)
                    else:
                        cursor.execute('PRAGMA table_info(requests)')
                        columns = [col[1] for col in cursor.fetchall()]
                        required_columns = ['id', 'timestamp', 'project_number', 'project_name', 'amount', 'reason', 'original_text']
                        
                        if not all(col in columns for col in required_columns):
                            cursor.execute('ALTER TABLE requests RENAME TO requests_old')
                            self.create_table(conn)
                            cursor.execute('''
                                INSERT INTO requests (timestamp, project_number, project_name, amount, reason)
                                SELECT timestamp, project_number, project_name, amount, reason
                                FROM requests_old
                            ''')
                            cursor.execute('DROP TABLE requests_old')
                            conn.commit()
                return
            except sqlite3.OperationalError as e:
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                raise Exception(f"Could not initialize database after {self.max_retries} attempts: {str(e)}")
    
    def create_table(self, conn):
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                project_number TEXT,
                project_name TEXT,
                amount REAL,
                reason TEXT,
                original_text TEXT
            )
        ''')
        conn.commit()
    
    def add_request(self, project_number, project_name, amount, reason, original_text=""):
        for attempt in range(self.max_retries):
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO requests (timestamp, project_number, project_name, amount, reason, original_text)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (datetime.now(), project_number, project_name, amount, reason, original_text))
                    conn.commit()
                return
            except sqlite3.OperationalError as e:
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                raise Exception(f"Could not add request after {self.max_retries} attempts: {str(e)}")
    
    def get_all_requests(self):
        for attempt in range(self.max_retries):
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT * FROM requests ORDER BY timestamp DESC')
                    columns = [description[0] for description in cursor.description]
                    results = cursor.fetchall()
                    return [dict(zip(columns, row)) for row in results]
            except sqlite3.OperationalError as e:
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                raise Exception(f"Could not fetch requests after {self.max_retries} attempts: {str(e)}")