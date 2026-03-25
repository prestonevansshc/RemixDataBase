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

from_number = "+18447913654"

numbers = [
    "+12283433254"
]

for to_number in numbers:
    message = twilio_client.messages.create(
        body="Test message from Twilio",
        from_=from_number,
        to=to_number
    )
    print(f"Message SID: {message.sid}")
    print(f"Status: {message.status}")
    
    # Check message status after a few seconds
    import time
    time.sleep(2)
    msg = twilio_client.messages(message.sid).fetch()
    print(f"Updated Status: {msg.status}")