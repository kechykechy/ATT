import requests
import json
import os

# --- Configuration - PLEASE REPLACE PLACEHOLDERS --- #
API_KEY = "YOUR_API_KEY"  # Your Africa's Talking API Key
USERNAME = "YOUR_USERNAME" # Your Africa's Talking Username (often 'sandbox' for testing)

SENDER_WA_NUMBER = "YOUR_SENDER_WHATSAPP_NUMBER" # Your AT WhatsApp number (e.g., +254...)
RECIPIENT_PHONE_NUMBER = "RECIPIENT_PHONE_NUMBER" # Destination number (e.g., +254...)

message_text = "Hello from Africa's Talking via Python!"

# API Endpoint
chat_endpoint = "https://chat.africastalking.com/whatsapp/message/send"

# --- Prepare Request --- #
headers = {
    "Content-Type": "application/json",
    "apiKey": os.getenv('AT_API_KEY'),
    "Accept": "application/json"
}

data = {
    "username": os.getenv('AT_USERNAME'),
    "waNumber": SENDER_WA_NUMBER,
    "phoneNumber": RECIPIENT_PHONE_NUMBER,
    "body": {
        "message": message_text
    }
}

# --- Send Request --- #
def send_whatsapp_message():
    try:
        print(f"Sending message to {RECIPIENT_PHONE_NUMBER} from {SENDER_WA_NUMBER}...")
        response = requests.post(chat_endpoint, headers=headers, data=json.dumps(data))
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

        print(f"Status Code: {response.status_code}")
        print("Response Body:")
        print(response.json())

    except requests.exceptions.RequestException as e:
        print(f"Error sending request: {e}")
        if e.response is not None:
            print(f"Error Status Code: {e.response.status_code}")
            try:
                print(f"Error Body: {e.response.json()}")
            except json.JSONDecodeError:
                print(f"Error Body (non-JSON): {e.response.text}")

if __name__ == "__main__":
    send_whatsapp_message()
