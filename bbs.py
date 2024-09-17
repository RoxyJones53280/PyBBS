import sqlite3
import getpass
import re
import pytz
from datetime import datetime

# Connect to the SQLite database (or create it)
conn = sqlite3.connect('/home/bbs/bbs.db')
cursor = conn.cursor()

# Create the users table
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL
)
''')
cursor.execute('''
CREATE TABLE IF NOT EXISTS mailbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id INTEGER NOT NULL,
    recipient_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sender_id) REFERENCES users(id),
    FOREIGN KEY (recipient_id) REFERENCES users(id)
);
''')
def ensure_last_login_column():
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN last_login DATETIME DEFAULT CURRENT_TIMESTAMP")
        conn.commit()
    except sqlite3.OperationalError:
        # Column already exists, do nothing
        pass

def ensure_admin_column():
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
        conn.commit()
    except sqlite3.OperationalError:
        # Column already exists, do nothing
        pass
def ensure_system_user():
    cursor.execute("SELECT id FROM users WHERE username = 'SYSTEM'")
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", ('SYSTEM', ''))
        conn.commit()
ensure_admin_column()
ensure_last_login_column()
ensure_system_user()
def send_system_notification(message, recipient_id=None):
    if recipient_id:
        # Send notification to specific user
        cursor.execute(
            "INSERT INTO mailbox (sender_id, recipient_id, message) VALUES ((SELECT id FROM users WHERE username = 'SYSTEM'), ?, ?)",
            (recipient_id, message)
        )
    else:
        # Send notification to all users
        cursor.execute("SELECT id FROM users WHERE username != 'SYSTEM'")
        users = cursor.fetchall()

        for user in users:
            recipient_id = user[0]
            cursor.execute(
                "INSERT INTO mailbox (sender_id, recipient_id, message) VALUES ((SELECT id FROM users WHERE username = 'SYSTEM'), ?, ?)",
                (recipient_id, message)
            )
    conn.commit()
    print("Notification sent.")

# Create the messages table
# Modify the messages table creation
cursor.execute('''
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    content TEXT NOT NULL,
    subboard TEXT DEFAULT 'main',
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
)
''')


conn.commit()

# Help dictionary with help text for each command
help_pages = {
    "post": "Usage: post\nAllows you to post a message in the current sub-board.",
    "read": "Usage: read\nDisplays all messages in the current sub-board.",
    "switch": "Usage: switch\nAllows you to switch between sub-boards. You will be prompted for the sub-board name.",
    "logout": "Usage: logout\nLogs you out of the current session.",
    "quit": "Usage: quit\nExits the BBS system.",
    "exit": "Usage: exit\nExits the BBS, for Unix users.",
    "help": "How are you in a situation where you need help to get help?",
    "register": "Usage: register\nCreate a new account in the BBS.",
    "login": "Usage: login\nLog into your account with your username and password."
}

def display_help(command):
    if command in help_pages:
        print(help_pages[command])
    else:
        print(f"No help available for '{command}'. Available commands: {', '.join(help_pages.keys())}")

def bash_prompt(username, current_subboard, is_admin):
    prompt_symbol = '#' if is_admin else '$'
    return f"{username}@PyBBS:{current_subboard}{prompt_symbol} "

def display_last_login(utc_time):
    # Timezone for Northwest Territories (Yellowknife)
    local_tz = pytz.timezone('America/Yellowknife')

    # Convert UTC time to local time
    utc_dt = datetime.strptime(utc_time, '%Y-%m-%d %H:%M:%S')
    utc_dt = utc_dt.replace(tzinfo=pytz.utc)
    local_dt = utc_dt.astimezone(local_tz)

    # Format and display the local time
    return local_dt.strftime('%Y-%m-%d %H:%M:%S')

def welcome_screen():
    print("""
     ███████████             ███████████  ███████████   █████████ 
   ░░███░░░░░███           ░░███░░░░░███░░███░░░░░███ ███░░░░░███
    ░███    ░███ █████ ████ ░███    ░███ ░███    ░███░███    ░░░ 
    ░██████████ ░░███ ░███  ░██████████  ░██████████ ░░█████████ 
    ░███░░░░░░   ░███ ░███  ░███░░░░░███ ░███░░░░░███ ░░░░░░░░███
    ░███         ░███ ░███  ░███    ░███ ░███    ░███ ███    ░███
    █████        ░░███████  ███████████  ███████████ ░░█████████ 
   ░░░░░          ░░░░░███ ░░░░░░░░░░░  ░░░░░░░░░░░   ░░░░░░░░░  
                  ███ ░███                                       
                 ░░██████                                        
                  ░░░░░░ 
                
    Your favourite python-based bulletin board system software!
    
    Commands:
    - register : Create a new account
    - login    : Login to your account
    - quit     : Exit the BBS
    - exit     : Also exit the BBS
    - help     : Type anywhere for help
    - CTRL+C   : Forcibly end session
    """)

def register():
    username = input("PyBBS login: ")
    password = getpass.getpass(prompt='Password: ', stream=None)
    
    # Determine if the first user should be admin
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        is_admin = 1
        print(f"{username} will be registered as an admin.")
    else:
        is_admin = 0
    
    cursor.execute("INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)", (username, password, is_admin))
    conn.commit()
    print(f"User {username} registered successfully!")


def login():
    username = input("PyBBS login: ")
    password = getpass.getpass(prompt='Password: ', stream=None)
    
    cursor.execute("SELECT id, is_admin, last_login FROM users WHERE username = ? AND password = ?", (username, password))
    user = cursor.fetchone()
    
    if user:
        user_id = user[0]
        is_admin = user[1]
        last_login = user[2]
        print(f"PyBBS v0.1 - {username}@PyBBS")
        print(f"Last login: {display_last_login(last_login)}")
        # Get the current local time
        cursor.execute("UPDATE users SET last_login = datetime('now') WHERE id = ?", (user_id,))
        conn.commit()
        return user_id, username, is_admin
    else:
        print("Invalid login credentials.")
        return None, None, None

        

def notify_mentions(message):
    mentioned_usernames = re.findall(r'@(\w+)', message)  # Find all mentions in the message

    for username in mentioned_usernames:
        recipient_id = get_user_id(username)
        if recipient_id:
            # Send notification from SYSTEM
            send_system_notification(f"You were mentioned in a message: {message}", recipient_id)
        else:
            print(f"User '{username}' not found.")
def send_message(sender_id, recipient_username):
    recipient_id = get_user_id(recipient_username)
    
    if recipient_id:
        message = input("Enter your message: ")
        cursor.execute(
            "INSERT INTO mailbox (sender_id, recipient_id, message) VALUES (?, ?, ?)",
            (sender_id, recipient_id, message)
        )
        conn.commit()
        print("Message sent successfully!")
    else:
        print(f"User '{recipient_username}' not found.")
        
def get_user_id(username):
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    return user[0] if user else None
def post_message(user_id, subboard_id):
    print("Enter your message. Type '.' on a new line to end:")
    
    lines = []
    while True:
        line = input()
        if line == ".":
            break
        lines.append(line)
    
    message = "\n".join(lines)  # Join all lines with new line characters

    # Store the message in the database
    cursor.execute('''INSERT INTO messages (user_id, subboard, content, timestamp)
                      VALUES (?, ?, ?, datetime('now'))''', 
                      (user_id, subboard_id, message))
    conn.commit()

    notify_mentions(message)
    print("Message posted successfully to " + subboard_id + ".")

def read_messages(subboard="main"):
    cursor.execute('''
    SELECT users.username, messages.content, messages.timestamp
    FROM messages
    JOIN users ON messages.user_id = users.id
    WHERE messages.subboard = ?
    ORDER BY messages.timestamp DESC
    ''', (subboard,))

    messages = cursor.fetchall()
    
    if messages:
        for message in messages:
            print(f"[{message[2]}] {message[0]}: {message[1]}")
    else:
        print(f"No messages in sub-board '{subboard}'.")
def view_mailbox(user_id):
    cursor.execute(
        "SELECT sender_id, message, timestamp FROM mailbox WHERE recipient_id = ?",
        (user_id,)
    )
    messages = cursor.fetchall()
    
    if messages:
        for sender_id, message, timestamp in messages:
            sender_name = get_username_by_id(sender_id)
            print(f"From: {sender_name}\nReceived: {timestamp}\nMessage: {message}\n")
    else:
        print("Your mailbox is empty.")
        
def get_username_by_id(user_id):
    cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    return user[0] if user else "Unknown"


def main():
    welcome_screen()
    
    user_id = None
    username = ""
    is_admin = False  # Default non-admin
    current_subboard = "main"  # Default sub-board
    while True:
        if user_id:
            prompt = bash_prompt(username, current_subboard, is_admin)
            command = input(prompt).strip().lower()

            if command == "post":
                post_message(user_id, current_subboard)
            elif command == "read":
                read_messages(current_subboard)
            elif command == "switch":
                current_subboard = input("Enter sub-board name: ")
                print(f"Switched to sub-board: {current_subboard}")
            elif command == "logout":
                user_id = None
                username = ""
                print("Logged out.")
            elif command == "exit":
                print("Thank you for using PyBBS!")
                break
            elif command == "quit":
                print("Thank you for using PyBBS!")
                break
            elif command == "send":
                recipient = input("Enter recipient's username: ")
                send_message(user_id, recipient)
            elif command == "inbox":
                view_mailbox(user_id)
            elif command.startswith("help"):
                _, *args = command.split()
                if args:
                    display_help(args[0])
                else:
                    print("Usage: help <command>\nAvailable commands: post, read, switch, logout, quit, exit, send, inbox.")
            else:
                print(f"Unknown command: {command}. Type 'help' for available commands.")
        else:
            command = input("PyBBS$ ").strip().lower()
            if command == "register":
                register()
            elif command == "login":
                user_id, username, is_admin = login()  # Now handle both variables
                if user_id is None:  # If login fails, stay in the loop
                    username = ""
            elif command == "exit":
                print("Thank you for using PyBBS!")
                break
            elif command == "quit":
                print("Thank you for using PyBBS!")
                break
            elif command.startswith("help"):
                _, *args = command.split()
                if args:
                    display_help(args[0])
                else:
                    print("Usage: help <command>\nAvailable commands: register, login, exit, quit.")
            else:
                print(f"PyBBS: {command}: command not found")


if __name__ == "__main__":
    main()
