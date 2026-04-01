from pymongo import MongoClient
from twilio.rest import Client
import time
import os
from urllib.parse import quote_plus
from dotenv import load_dotenv
import json

# Load environment variables from .env file
load_dotenv()

# Get credentials from environment variables
mongobd_uri = os.getenv("MONGODB_URI")
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
from_number = os.getenv("TWILIO_FROM_NUMBER")
to_number = os.getenv("TWILIO_TO_NUMBER")

# Validate that all required credentials are set
if not all([mongobd_uri, account_sid, auth_token, from_number, to_number]):
    raise ValueError("Missing required environment variables. Please check your .env file.")

# Connect to MongoDB
client = MongoClient(mongobd_uri)
Twilio = client["TwilioDB"]
Messages = Twilio["Messages"]
PhoneLookups = Twilio["PhoneLookups"]

Messages.insert_one({"message": "Hello, World!", "timestamp": "2023-10-01"})

# Initialize Twilio client
twilio_client = Client(account_sid, auth_token)

def lookup_phone_number(phone_number):
    """Lookup phone number carrier and caller-name information using Twilio Lookup API"""
    try:
        # Fetch carrier and caller-name information
        lookup = twilio_client.lookups.v1.phone_numbers(phone_number).fetch(
            type=['carrier', 'caller-name']
        )
        
        lookup_data = {
            "phone_number": phone_number,
            "carrier": {
                "name": lookup.carrier.get('name'),
                "type": lookup.carrier.get('type'),
                "mobile_country_code": lookup.carrier.get('mobile_country_code'),
                "mobile_network_code": lookup.carrier.get('mobile_network_code')
            },
            "caller_name": {
                "caller_name": lookup.caller_name.get('caller_name'),
                "caller_type": lookup.caller_name.get('caller_type'),
                "error_code": lookup.caller_name.get('error_code')
            },
            "lookup_timestamp": time.time(),
            "country_code": lookup.country_code,
            "national_format": lookup.national_format,
            "url": lookup.url
        }
        
        # Store lookup data in MongoDB
        PhoneLookups.insert_one(lookup_data)
        
        # Print JSON output similar to CLI command
        print(f"Lookup result for {phone_number}:")
        print(json.dumps(lookup_data, indent=2, default=str))
        
        return lookup_data
        
    except Exception as e:
        print(f"Lookup error for {phone_number}: {e}")
        # Store error in database
        error_data = {
            "phone_number": phone_number,
            "error": str(e),
            "lookup_timestamp": time.time()
        }
        PhoneLookups.insert_one(error_data)
        return None

def send_message(to_number, from_number, body="Test message from Twilio"):
    """Send an SMS message and store in MongoDB"""
    try:
        message = twilio_client.messages.create(
            body=body,
            from_=from_number,
            to=to_number
        )
        print(f"Message SID: {message.sid}")
        print(f"Status: {message.status}")
        message_data = {
                "sid": message.sid,
                "body": message.body,
                "from_": message.from_,
                "to": message.to,
                "status": message.status,
                "date_created": message.date_created,
                "date_sent": message.date_sent,
                "date_updated": message.date_updated,
                "error": None
            }
        Messages.insert_one(message_data)
        Messages.update_one(
                {"sid": message.sid},
                {"$set": {
                    "status": message.status,
                    "date_updated": message.date_updated,
                    "error": getattr(message, "error_message", None)
                }}
        )
        
        # Check message status after a few seconds
        time.sleep(2)
        msg = twilio_client.messages(message.sid).fetch()
        print(f"Updated Status: {msg.status}")
        
        return message_data

    except Exception as e:
        print("Send error:", e)
        error_data = {
                "sid": None,
                "body": body,
                "from_": from_number,
                "to": to_number,
                "status": "send_failed",
                "date_created": None,
                "date_sent": None,
                "date_updated": None,
                "error": str(e)
            }
        Messages.insert_one(error_data)
        return None

def main():
    """Main function to lookup phone number and send message"""
    numbers = [to_number]
    
    for phone in numbers:
        # Perform phone number lookup before sending message
        print(f"Looking up information for {phone}...")
        lookup_result = lookup_phone_number(phone)
        
        if lookup_result:
            print(f"Carrier: {lookup_result['carrier'].get('name', 'Unknown')}")
            print(f"Caller Name: {lookup_result['caller_name'].get('caller_name', 'Unknown')}")
        else:
            print("Lookup failed, proceeding with message send...")
        
        send_message(phone, from_number)

if __name__ == "__main__":
    main()
