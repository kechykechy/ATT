import os
import logging
from flask import Flask, request, Response
from dotenv import load_dotenv
import africastalking
import google.generativeai as genai

# --- Configuration & Initialization --- #

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env file
load_dotenv()

# Get credentials from environment
AT_USERNAME = os.getenv('AT_USERNAME')
AT_API_KEY = os.getenv('AT_API_KEY')
AT_SHORTCODE = os.getenv('AT_SHORTCODE') # Your AT Shortcode or Alphanumeric Sender ID
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

# --- Input Validation --- #
if not all([AT_USERNAME, AT_API_KEY, AT_SHORTCODE, GOOGLE_API_KEY]):
    logging.error("Missing required environment variables. Please check your .env file.")
    # In a real app, you might exit or raise a more specific configuration error
    # For simplicity here, we log and continue, but API calls will likely fail.

# Initialize Flask app
app = Flask(__name__)

# Initialize Africa's Talking SDK
try:
    africastalking.initialize(AT_USERNAME, AT_API_KEY)
    sms = africastalking.SMS
    logging.info("Africa's Talking SDK initialized successfully.")
except Exception as e:
    logging.error(f"Failed to initialize Africa's Talking SDK: {e}")
    sms = None # Ensure sms object is None if initialization fails

# Initialize Google Gemini
try:
    genai.configure(api_key=GOOGLE_API_KEY)
    gemini_model = genai.GenerativeModel('gemini-1.5-flash') # Or 'gemini-pro'
    logging.info("Google Gemini configured successfully.")
except Exception as e:
    logging.error(f"Failed to configure Google Gemini: {e}")
    gemini_model = None # Ensure model is None if configuration fails

# --- Flask Route for Incoming SMS --- #

@app.route('/incoming-messages', methods=['POST'])
def incoming_sms():
    # Get data from AT POST request
    data = request.form
    sender = data.get('from')
    message_text = data.get('text')
    message_id = data.get('id') # Africa's Talking message ID

    logging.info(f"Received message ID {message_id} from {sender}: '{message_text}'")

    if not sender or not message_text:
        logging.warning("Received incomplete message data.")
        return Response(status=400) # Bad request

    # --- Call Gemini API --- #
    ai_response_text = "Sorry, I couldn't process that request right now."
    if gemini_model:
        try:
            logging.info(f"Sending to Gemini: '{message_text}'")
            response = gemini_model.generate_content(message_text)
            # Handle potential safety blocks or empty responses
            if response.parts:
                ai_response_text = response.text
                logging.info(f"Received from Gemini: '{ai_response_text}'")
            else:
                ai_response_text = "I received your message, but couldn't generate a response."
                logging.warning("Gemini response was empty or blocked.")
        except Exception as e:
            logging.error(f"Error calling Gemini API: {e}")
            # Keep the default error message
    else:
        logging.error("Gemini model not available.")
        # Keep the default error message

    # --- Send Reply SMS via Africa's Talking --- #
    if sms:
        try:
            logging.info(f"Sending reply to {sender}: '{ai_response_text}'")
            # Ensure recipient is a list
            recipients = [sender]
            response = sms.send(ai_response_text, recipients, AT_SHORTCODE)
            logging.info(f"Africa's Talking Send Response: {response}")
        except Exception as e:
            logging.error(f"Error sending SMS via Africa's Talking: {e}")
    else:
        logging.error("Africa's Talking SMS service not available.")

    # Respond to Africa's Talking API to acknowledge receipt
    # AT doesn't typically require a body, just a 200 OK
    return Response(status=200)

# --- Run Flask App --- #

if __name__ == '__main__':
    # Use a default port if not specified in environment
    port = int(os.getenv('PORT', 5000)) # Changed default port to 5000
    logging.info(f"Starting Flask server on port {port}")
    # Set debug=False for production; use debug=True only for development
    app.run(host='0.0.0.0', port=port, debug=True)
