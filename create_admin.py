from getpass import getpass

from werkzeug.security import generate_password_hash

from db import execute, query_one

username = input("Admin username: ").strip()
password = getpass("Password (min 8 characters): ")

if len(username) < 3 or len(password) < 8:
    print("Username needs 3+ characters and password 8+ characters.")
elif query_one("SELECT admin_id FROM admins WHERE username = %s", (username,)):
    print("That username already exists.")
else:
    execute("INSERT INTO admins (username, password_hash) VALUES (%s, %s)",
            (username, generate_password_hash(password)))
    print(f"Admin '{username}' created.")
