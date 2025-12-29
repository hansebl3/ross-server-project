import psycopg2
import sys

users = ["ross", "postgres"]
passwords = [os.getenv("DB_PASSWORD", "your_password"), "postgres", "1234", ""]

for user in users:
    for pwd in passwords:
        try:
            conn = psycopg2.connect(dbname="postgres", user=user, password=pwd, host="localhost", port="5432")
            print(f"SUCCESS: Found user: '{user}', password: '{pwd}'")
            conn.close()
            sys.exit(0)
        except psycopg2.OperationalError as e:
            print(f"Failed with user '{user}', pwd '{pwd}': {e}")
        except Exception as e:
            print(f"Error with user '{user}', pwd '{pwd}': {e}")
print("Could not find correct password.")
