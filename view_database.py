from pymongo import MongoClient
import os
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get credentials from environment variables
mongobd_uri = os.getenv("MONGODB_URI")

if not mongobd_uri:
    raise ValueError("MONGODB_URI environment variable not set. Please check your .env file.")

try:
    client = MongoClient(mongobd_uri)
    Twilio = client["TwilioDB"]
    Messages = Twilio["Messages"]
    
    # Get all messages from the database
    messages = list(Messages.find())
    
    print("=" * 80)
    print("DATABASE CONTENTS - TwilioDB.Messages")
    print("=" * 80)
    print(f"Total Messages: {len(messages)}\n")
    
    if messages:
        for i, msg in enumerate(messages, 1):
            print(f"Message #{i}:")
            print(f"  SID: {msg.get('sid', 'N/A')}")
            print(f"  Body: {msg.get('body', 'N/A')}")
            print(f"  From: {msg.get('from_', 'N/A')}")
            print(f"  To: {msg.get('to', 'N/A')}")
            print(f"  Status: {msg.get('status', 'N/A')}")
            print(f"  Date Created: {msg.get('date_created', 'N/A')}")
            print(f"  Date Sent: {msg.get('date_sent', 'N/A')}")
            print(f"  Date Updated: {msg.get('date_updated', 'N/A')}")
            print(f"  Error: {msg.get('error', 'None')}")
            print("-" * 80)
    else:
        print("No messages found in the database.")
    
    print(f"\nLast checked: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
except Exception as e:
    print(f"Error connecting to database: {e}")