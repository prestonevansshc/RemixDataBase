import numpy
from pymongo import MongoClient
from twilio.rest import Client

client = MongoClient("mongodb://127.0.0.1:27017")
Twilio = client["TwilioDB"]
Messages = Twilio["Messages"]

Messages.insert_one({"message": "Hello, World!", "timestamp": "2023-10-01"})

account_sid = ""
auth_token = ""

twilio_client = Client(account_sid, auth_token)

from_number = ""

numbers = []

for to_number in numbers:
    try:
        message = twilio_client.messages.create(
            body="Test message from Twilio",
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
                    "status": msg.status,
                    "date_updated": msg.date_updated,
                    "error": getattr(msg, "error_message", None)
                }}
        )

    except Exception as e:
        print("Send error:", e)
        Messages.insert_one({
                "sid": None,
                "body": "Test message from Twilio",
                "from_": from_number,
                "to": to_number,
                "status": "send_failed",
                "date_created": None,
                "date_sent": None,
                "date_updated": None,
                "error": str(e)
            })
    
    # Check message status after a few seconds
    import time
    time.sleep(2)
    msg = twilio_client.messages(message.sid).fetch()
    print(f"Updated Status: {msg.status}")