import pymysql
import os

# DB Config
MARIADB_HOST = "127.0.0.1"
MARIADB_USER = "root"
MARIADB_PASSWORD = os.getenv("MARIADB_PASSWORD", "your_password_here")
MARIADB_DB = "rag_diary_db"
TARGET_UUID = "615141d2-4c7e-4f38-bd8d-739f4eb0d782"

def debug_mariadb():
    print(f"🔌 Connecting to MariaDB {MARIADB_DB}...")
    try:
        conn = pymysql.connect(
            host=MARIADB_HOST, user=MARIADB_USER, password=MARIADB_PASSWORD, database=MARIADB_DB,
            charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor
        )
        with conn.cursor() as cursor:
            # Check Table
            cursor.execute(f"SELECT COUNT(*) as cnt FROM tb_knowledge_base")
            res = cursor.fetchone()
            print(f"📊 Total Rows in 'tb_knowledge_base': {res['cnt']}")
            
            # Check UUID
            print(f"🔎 Searching for UUID: {TARGET_UUID}")
            cursor.execute(f"SELECT * FROM tb_knowledge_base WHERE uuid = %s", (TARGET_UUID,))
            row = cursor.fetchone()
            
            if row:
                print("✅ Found UUID in MariaDB!")
                print(f"   Subject: {row.get('subject')}")
                print(f"   Category: {row.get('category')}")
                print(f"   Content Length: {len(row.get('content', ''))}")
            else:
                print("❌ UUID NOT FOUND in MariaDB. Hybrid Link Broken.")
                
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if 'conn' in locals() and conn.open:
            conn.close()

if __name__ == "__main__":
    debug_mariadb()
