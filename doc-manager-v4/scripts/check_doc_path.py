import os
import sys
from dotenv import load_dotenv

# Setup paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from database import Database

def check_db():
    load_dotenv('../.env')
    db = Database()
    
    # Search for documents by part of the path
    conn = db.get_connection()
    with conn.cursor(cursor_factory=lambda *args: db.get_connection().cursor(cursor_factory=__import__('psycopg2.extras').extras.DictCursor)) as cur:
        query = "SELECT uuid, path, category, updated_at FROM documents WHERE path LIKE '%노즐에 금속성 이물질 끼임%'"
        cur.execute(query)
        rows = cur.fetchall()
        for row in rows:
            print(f"UUID: {row['uuid']}")
            print(f"Path: {row['path']}")
            print(f"Category: {row['category']}")
            print(f"Updated: {row['updated_at']}")
            print("---")

if __name__ == "__main__":
    check_db()
