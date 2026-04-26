"""
Main entry point for RemixDataBase application
"""
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio_client import record_vote, get_poll_results
import os
from dotenv import load_dotenv
import re

load_dotenv()

app = Flask(__name__)

@app.route("/webhook/sms", methods=['POST'])
def handle_incoming_sms():
    """
    Webhook endpoint to handle incoming SMS messages from Twilio.
    
    Expected message format: "<poll_id> <vote>"
    Example: "550e8400-e29b-41d4-a716-446655440000 1"
    
    Returns:
        TwiML response to Twilio
    """
    # Get the incoming message details
    from_number = request.form.get('From')
    message_body = request.form.get('Body', '').strip()
    message_sid = request.form.get('MessageSid')
    
    response = MessagingResponse()
    
    try:
        # Parse the message format: "<poll_id> <vote>"
        parts = message_body.split(maxsplit=1)
        
        if len(parts) < 2:
            response.message("Invalid format. Please send: <poll_id> <vote_number>\nExample: 550e8400-e29b-41d4-a716-446655440000 1")
            return str(response)
        
        poll_id = parts[0]
        vote = parts[1]
        
        # Validate poll_id format (UUID)
        uuid_pattern = r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$'
        if not re.match(uuid_pattern, poll_id, re.IGNORECASE):
            response.message("Invalid poll ID format. Please check and try again.")
            return str(response)
        
        # Record the vote
        result = record_vote(poll_id, from_number, vote)
        
        if result["success"]:
            response.message(f"✓ {result['message']}")
            print(f"Vote recorded - Poll: {poll_id}, Phone: {from_number}, Vote: {vote}")
        else:
            response.message(f"✗ {result['message']}")
            print(f"Vote failed - Poll: {poll_id}, Phone: {from_number}, Error: {result['message']}")
        
        return str(response)
    
    except Exception as e:
        print(f"Error processing SMS from {from_number}: {str(e)}")
        response.message("An error occurred processing your vote. Please try again.")
        return str(response)

@app.route("/poll/results/<poll_id>", methods=['GET'])
def get_results(poll_id):
    """
    REST endpoint to retrieve poll results.
    
    Returns:
        JSON with poll results
    """
    try:
        results = get_poll_results(poll_id)
        
        if not results:
            return {"error": f"Poll {poll_id} not found"}, 404
        
        return results, 200
    
    except Exception as e:
        print(f"Error retrieving results for poll {poll_id}: {str(e)}")
        return {"error": "Failed to retrieve poll results"}, 500

@app.route("/health", methods=['GET'])
def health_check():
    """Health check endpoint"""
    return {"status": "ok"}, 200

def main():
    """Main function to start the application"""
    print("Welcome to RemixDataBase!")
    print("\nStarting Flask webhook server...")
    print("\nAvailable endpoints:")
    print("  POST /webhook/sms - Incoming SMS webhook from Twilio")
    print("  GET  /poll/results/<poll_id> - Get poll results")
    print("  GET  /health - Health check")
    print("\nAvailable modules:")
    print("  - twilio_client: Twilio messaging and phone lookup")
    print("  - database: MongoDB database operations")
    print("\n" + "="*60)
    
    # Start Flask development server
    port = int(os.getenv("FLASK_PORT", 5000))
    app.run(debug=False, port=port, host='0.0.0.0')


if __name__ == "__main__":
    main()
