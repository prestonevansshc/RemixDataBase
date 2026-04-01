from pymongo import MongoClient
import os
import csv
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get credentials from environment variables
mongobd_uri = os.getenv("MONGODB_URI")

if not mongobd_uri:
    raise ValueError("MONGODB_URI environment variable not set. Please check your .env file.")

def export_messages_to_csv(csv_path: str = "data/messages.csv"):
    """Export messages from MongoDB to CSV file"""
    try:
        client = MongoClient(mongobd_uri)
        Twilio = client["TwilioDB"]
        Messages = Twilio["Messages"]
        
        # Create data directory if it doesn't exist
        Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Get all messages from the database
        messages = list(Messages.find())
        
        existing_sids = set()
        
        if os.path.exists(csv_path):
            with open(csv_path, 'r', newline='') as f:
                reader = csv.reader(f)
                next(reader, None)  # skip header
                for row in reader:
                    if row:
                        existing_sids.add(row[0])
        
        new_messages_count = 0
        with open(csv_path, 'a', newline='') as f:
            writer = csv.writer(f)
            if not existing_sids:  # if file didn't exist, write header
                writer.writerow(['SID', 'Body', 'From', 'To', 'Status', 'Date Created', 'Date Sent', 'Date Updated', 'Error'])
            for msg in messages:
                sid = msg.get('sid', 'N/A')
                if sid not in existing_sids:
                    row = [
                        sid,
                        msg.get('body', 'N/A'),
                        msg.get('from_', 'N/A'),
                        msg.get('to', 'N/A'),
                        msg.get('status', 'N/A'),
                        str(msg.get('date_created', 'N/A')),
                        str(msg.get('date_sent', 'N/A')),
                        str(msg.get('date_updated', 'N/A')),
                        msg.get('error', 'None')
                    ]
                    writer.writerow(row)
                    existing_sids.add(sid)
                    new_messages_count += 1
        
        print(f"CSV file '{csv_path}' updated with {new_messages_count} new messages.")
        print(f"Total messages in database: {len(messages)}")
        
    except Exception as e:
        print(f"Error connecting to database: {e}")

def export_lookups_to_csv(csv_path: str = "data/phone_lookups.csv"):
    """Export phone lookups from MongoDB to CSV file"""
    try:
        client = MongoClient(mongobd_uri)
        Twilio = client["TwilioDB"]
        PhoneLookups = Twilio["PhoneLookups"]
        
        # Create data directory if it doesn't exist
        Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Get all lookups from the database
        lookups = list(PhoneLookups.find())
        
        existing_phone_numbers = set()
        
        if os.path.exists(csv_path):
            with open(csv_path, 'r', newline='') as f:
                reader = csv.reader(f)
                next(reader, None)  # skip header
                for row in reader:
                    if row:
                        existing_phone_numbers.add(row[0])
        
        new_lookups_count = 0
        with open(csv_path, 'a', newline='') as f:
            writer = csv.writer(f)
            if not existing_phone_numbers:  # if file didn't exist, write header
                writer.writerow([
                    'Phone Number', 'Carrier Name', 'Carrier Type', 'Mobile Country Code', 
                    'Mobile Network Code', 'Caller Name', 'Caller Type', 'Caller Name Error Code',
                    'Country Code', 'National Format', 'Lookup Timestamp', 'URL'
                ])
            for lookup in lookups:
                phone_number = lookup.get('phone_number', 'N/A')
                if phone_number not in existing_phone_numbers:
                    carrier = lookup.get('carrier', {})
                    caller_name = lookup.get('caller_name', {})
                    
                    row = [
                        phone_number,
                        carrier.get('name', 'N/A'),
                        carrier.get('type', 'N/A'),
                        carrier.get('mobile_country_code', 'N/A'),
                        carrier.get('mobile_network_code', 'N/A'),
                        caller_name.get('caller_name', 'N/A'),
                        caller_name.get('caller_type', 'N/A'),
                        caller_name.get('error_code', 'N/A'),
                        lookup.get('country_code', 'N/A'),
                        lookup.get('national_format', 'N/A'),
                        str(lookup.get('lookup_timestamp', 'N/A')),
                        lookup.get('url', 'N/A')
                    ]
                    writer.writerow(row)
                    existing_phone_numbers.add(phone_number)
                    new_lookups_count += 1
        
        print(f"CSV file '{csv_path}' updated with {new_lookups_count} new phone lookups.")
        print(f"Total phone lookups in database: {len(lookups)}")
        
    except Exception as e:
        print(f"Error connecting to database: {e}")

def main():
    """Export messages and phone lookups to CSV"""
    export_messages_to_csv()
    export_lookups_to_csv()

if __name__ == "__main__":
    main()
