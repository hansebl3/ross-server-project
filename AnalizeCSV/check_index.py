import pymysql
import config_manager
import pandas as pd

def check_indexes():
    config = config_manager.load_config()
    if not config:
        print("No configuration found.")
        return

    print(f"Connecting to database: {config.get('database')} at {config.get('host')}...")
    
    try:
        conn = pymysql.connect(
            host=config['host'],
            port=int(config['port']),
            user=config['user'],
            password=config['password'],
            database=config['database']
        )
        
        table = config['table']
        print(f"Checking indexes for table: {table}")
        
        with conn.cursor() as cursor:
            cursor.execute(f"SHOW INDEX FROM {table}")
            indexes = cursor.fetchall()
            
            if not indexes:
                print("No indexes found.")
            else:
                print(f"Found {len(indexes)} indexes:")
                for idx in indexes:
                    # Index_name is typically the 3rd column (index 2)
                    # Column_name is typically the 5th column (index 4)
                    print(f"  - Name: {idx[2]}, Column: {idx[4]}")
                    
        conn.close()
        
    except Exception as e:
        print(f"Error connecting to database: {e}")

if __name__ == "__main__":
    check_indexes()
