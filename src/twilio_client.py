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
Polls = Twilio["Polls"]

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

def create_poll(question, options):
    """Create a new poll in the database.
    
    Args:
        question (str): The poll question
        options (list): List of voting options (e.g., ['Yes', 'No', 'Maybe'])
    
    Returns:
        str: The poll ID for reference
    """
    import uuid
    poll_id = str(uuid.uuid4())
    
    poll_data = {
        "_id": poll_id,
        "question": question,
        "options": options,
        "votes": {option: [] for option in options},  # {option: [phone_numbers]}
        "vote_count": {option: 0 for option in options},
        "created_at": time.time(),
        "status": "active"
    }
    
    Polls.insert_one(poll_data)
    print(f"Poll created with ID: {poll_id}")
    print(f"Question: {question}")
    print(f"Options: {', '.join(options)}")
    
    return poll_id

def send_poll(poll_id, phone_numbers, from_number=None):
    """Send a poll to multiple phone numbers.
    
    Args:
        poll_id (str): The ID of the poll to send
        phone_numbers (list): List of phone numbers to send the poll to
        from_number (str): The Twilio phone number to send from (uses env default if not provided)
    
    Returns:
        dict: Summary of sent messages with success/failure count
    """
    if from_number is None:
        from_number = globals()['from_number']
    
    # Retrieve poll data
    poll = Polls.find_one({"_id": poll_id})
    if not poll:
        print(f"Poll {poll_id} not found")
        return {"success": 0, "failed": 0, "errors": []}
    
    # Format poll message
    question = poll["question"]
    options = poll["options"]
    options_text = "\n".join([f"{i+1}. {option}" for i, option in enumerate(options)])
    
    message_body = f"{question}\n\n{options_text}\n\nReply with the number of your choice (1-{len(options)})"
    
    success_count = 0
    failed_count = 0
    errors = []
    
    for phone_number in phone_numbers:
        try:
            message = twilio_client.messages.create(
                body=message_body,
                from_=from_number,
                to=phone_number
            )
            
            # Store poll message in database
            poll_message_data = {
                "poll_id": poll_id,
                "recipient": phone_number,
                "message_sid": message.sid,
                "status": "sent",
                "sent_at": time.time(),
                "vote": None
            }
            Polls.update_one(
                {"_id": poll_id},
                {"$push": {"messages": poll_message_data}}
            )
            
            success_count += 1
            print(f"Poll sent to {phone_number} (SID: {message.sid})")
            
        except Exception as e:
            failed_count += 1
            error_msg = f"Failed to send poll to {phone_number}: {str(e)}"
            errors.append(error_msg)
            print(error_msg)
    
    summary = {
        "poll_id": poll_id,
        "success": success_count,
        "failed": failed_count,
        "errors": errors
    }
    
    return summary

def record_vote(poll_id, phone_number, vote):
    """Record a vote for a poll.
    
    Args:
        poll_id (str): The ID of the poll
        phone_number (str): The phone number of the voter
        vote (str or int): The vote choice (either option name or option number 1-indexed)
    
    Returns:
        dict: Vote result with success status and message
    """
    poll = Polls.find_one({"_id": poll_id})
    if not poll:
        return {"success": False, "message": f"Poll {poll_id} not found"}
    
    if poll["status"] != "active":
        return {"success": False, "message": f"Poll is no longer active"}
    
    options = poll["options"]
    
    # Handle numeric vote (1-indexed)
    if isinstance(vote, (int, str)) and str(vote).isdigit():
        vote_index = int(vote) - 1
        if 0 <= vote_index < len(options):
            selected_option = options[vote_index]
        else:
            return {"success": False, "message": f"Invalid vote. Please choose 1-{len(options)}"}
    else:
        # Handle string vote (option name)
        if vote in options:
            selected_option = vote
        else:
            return {"success": False, "message": f"Invalid vote. Please choose from: {', '.join(options)}"}
    
    # Check if user already voted
    if phone_number in poll["votes"].get(selected_option, []):
        return {"success": False, "message": "You have already voted in this poll"}
    
    # Record the vote
    Polls.update_one(
        {"_id": poll_id},
        {
            "$push": {f"votes.{selected_option}": phone_number},
            "$inc": {f"vote_count.{selected_option}": 1}
        }
    )
    
    return {"success": True, "message": f"Your vote for '{selected_option}' has been recorded"}

def get_poll_results(poll_id):
    """Get the results of a poll.
    
    Args:
        poll_id (str): The ID of the poll
    
    Returns:
        dict: Poll data with results, or None if poll not found
    """
    poll = Polls.find_one({"_id": poll_id})
    if not poll:
        return None
    
    # Calculate total votes
    total_votes = sum(poll["vote_count"].values())
    
    # Calculate percentages
    results = {
        "poll_id": poll_id,
        "question": poll["question"],
        "status": poll["status"],
        "created_at": poll["created_at"],
        "total_votes": total_votes,
        "votes_by_option": {}
    }
    
    for option in poll["options"]:
        vote_count = poll["vote_count"].get(option, 0)
        percentage = (vote_count / total_votes * 100) if total_votes > 0 else 0
        results["votes_by_option"][option] = {
            "count": vote_count,
            "percentage": round(percentage, 2),
            "voters": poll["votes"].get(option, [])
        }
    
    return results

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
