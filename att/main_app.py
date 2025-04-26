import os
import sqlite3
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
AT_USERNAME = os.getenv('AT_USERNAME', 'sandbox') # Default to sandbox if not set
AT_API_KEY = os.getenv('AT_API_KEY')
AT_SHORTCODE = os.getenv('AT_SHORTCODE') # Your AT Shortcode or Alphanumeric Sender ID for SMS replies/notifications
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

# Database path
DB_NAME = 'construction.db'
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(PROJECT_DIR, DB_NAME)

# --- Input Validation --- #
if not all([AT_USERNAME, AT_API_KEY, AT_SHORTCODE]):
    logging.warning("Missing Africa's Talking credentials (AT_USERNAME, AT_API_KEY, AT_SHORTCODE) in .env file. SMS features may fail.")
if not GOOGLE_API_KEY:
    logging.warning("Missing GOOGLE_API_KEY in .env file. AI features will fail.")

# Initialize Flask app
app = Flask(__name__)

# Initialize Africa's Talking SDK
sms = None # Initialize sms to None
try:
    # Check if API Key is present before initializing
    if AT_USERNAME and AT_API_KEY:
        africastalking.initialize(AT_USERNAME, AT_API_KEY)
        sms = africastalking.SMS
        logging.info("Africa's Talking SDK initialized successfully.")
    else:
        logging.warning("Skipping Africa's Talking SDK initialization due to missing credentials.")
except Exception as e:
    logging.error(f"Failed to initialize Africa's Talking SDK: {e}")

# Initialize Google Gemini
gemini_model = None # Initialize gemini_model to None
try:
    if GOOGLE_API_KEY:
        genai.configure(api_key=GOOGLE_API_KEY)
        # Using 1.5 Flash as it supports text and vision, though we only use text here for now
        gemini_model = genai.GenerativeModel('gemini-1.5-flash') 
        logging.info("Google Gemini configured successfully.")
    else:
         logging.warning("Skipping Google Gemini configuration due to missing API key.")
except Exception as e:
    logging.error(f"Failed to configure Google Gemini: {e}")

# --- Database Helper Functions (from ussd.py) --- #

def db_connect():
    """Creates and returns a database connection."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row # Return rows as dict-like objects
        return conn
    except sqlite3.Error as e:
        logging.error(f"Database connection error: {e}")
        return None

def get_materials():
    """Fetches all materials from the database."""
    conn = db_connect()
    materials = []
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, unit FROM materials ORDER BY name ASC")
            materials = cursor.fetchall()
        except sqlite3.Error as e:
            logging.error(f"Error fetching materials: {e}")
        finally:
            conn.close()
    return materials

def get_material_details(material_id):
    """Fetches name, unit, and quantity for a specific material ID."""
    conn = db_connect()
    material = None
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, unit, current_quantity FROM materials WHERE id = ?", (material_id,))
            material = cursor.fetchone()
        except sqlite3.Error as e:
            logging.error(f"Error fetching material details for ID {material_id}: {e}")
        finally:
            conn.close()
    return material

def update_material_quantity(material_id, quantity_change):
    """Updates the quantity for a specific material ID."""
    conn = db_connect()
    success = False
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE materials SET current_quantity = COALESCE(current_quantity, 0) + ? WHERE id = ?", (quantity_change, material_id))
            conn.commit()
            success = True
            logging.info(f"Updated quantity for material ID {material_id} by {quantity_change}")
        except sqlite3.Error as e:
            logging.error(f"Error updating quantity for material ID {material_id}: {e}")
            conn.rollback()
        finally:
            conn.close()
    return success

def get_stakeholder_numbers():
    """Fetches all stakeholder phone numbers."""
    conn = db_connect()
    numbers = []
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT phone_number FROM stakeholders")
            numbers = [row['phone_number'] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Error fetching stakeholder numbers: {e}")
        finally:
            conn.close()
    return numbers

def get_all_material_stock():
    """Fetches name, unit, and current quantity for all materials."""
    conn = db_connect()
    stock_data = []
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name, unit, current_quantity FROM materials ORDER BY name ASC")
            stock_data = cursor.fetchall()
        except sqlite3.Error as e:
            logging.error(f"Error fetching all material stock: {e}")
        finally:
            conn.close()
    return stock_data

# --- USSD Callback Logic (from ussd.py) --- #

@app.route('/', methods=['POST', 'GET']) # Route for USSD
def ussd_callback():
    response = ""
    session_id = request.values.get("sessionId", None)
    service_code = request.values.get("serviceCode", None)
    phone_number = request.values.get("phoneNumber", None)
    text = request.values.get("text", "")

    logging.info(f"USSD Session {session_id}: Received input '{text}' from {phone_number}")

    parts = text.split('*')
    level = len(parts) if text else 0

    materials_list = get_materials() # Renamed to avoid conflict with module name

    try:
        if level == 0:
            response = "CON Welcome to Construction Tracker\n1. Record Material Received\n2. Check Stock Level"
        elif level == 1:
            choice = parts[0]
            if choice in ['1', '2']:
                if not materials_list:
                    response = "END No materials found."
                else:
                    response = "CON Select Material:\n"
                    for i, material in enumerate(materials_list):
                        response += f"{i+1}. {material['name']}\n"
            else:
                response = "END Invalid choice."
        elif level == 2:
            main_choice = parts[0]
            try:
                material_index = int(parts[1]) - 1
                if 0 <= material_index < len(materials_list):
                    selected_material = materials_list[material_index]
                    if main_choice == '1': # Record
                        response = f"CON Enter quantity of {selected_material['name']} ({selected_material['unit']}):"
                    elif main_choice == '2': # Check
                        mat_details = get_material_details(selected_material['id'])
                        response = f"END {mat_details['name']}: {mat_details['current_quantity']} {mat_details['unit']} in stock." if mat_details else "END Error retrieving stock."
                    else:
                        response = "END Invalid action."
                else:
                    response = "END Invalid material selection."
            except (ValueError, IndexError):
                response = "END Invalid selection number."
        elif level == 3:
            main_choice = parts[0]
            try:
                material_index = int(parts[1]) - 1
                quantity_str = parts[2]
                if main_choice == '1':
                    if 0 <= material_index < len(materials_list):
                        selected_material = materials_list[material_index]
                        if quantity_str.isdigit() and int(quantity_str) > 0:
                            quantity = int(quantity_str)
                            if update_material_quantity(selected_material['id'], quantity):
                                response = f"END {quantity} {selected_material['unit']} of {selected_material['name']} recorded."
                                # Send SMS Notification (using shared 'sms' object)
                                stakeholders = get_stakeholder_numbers()
                                if stakeholders and sms and AT_SHORTCODE:
                                    message = f"{quantity} {selected_material['unit']} of {selected_material['name']} recorded via USSD by {phone_number}."
                                    try:
                                        sms_response = sms.send(message, stakeholders, AT_SHORTCODE)
                                        logging.info(f"USSD Record SMS notification sent: {sms_response}")
                                        response += " Stakeholders notified."
                                    except Exception as e:
                                        logging.error(f"Failed to send USSD record SMS notification: {e}")
                                        response += " SMS notification failed."
                                elif not sms or not AT_SHORTCODE:
                                    logging.warning("SMS service/shortcode not available for USSD notification.")
                                    response += " SMS notification disabled."
                                elif not stakeholders:
                                    logging.warning("No stakeholders found for USSD notification.")
                            else:
                                response = "END DB update failed."
                        else:
                            response = "END Invalid quantity."
                    else:
                        response = "END Invalid material selection."
                else:
                    response = "END Invalid sequence."
            except (ValueError, IndexError):
                response = "END Invalid input format."
        else:
            response = "END Invalid input."
    except Exception as e:
        logging.exception(f"USSD Error: {e}")
        response = "END Internal error."

    if not isinstance(response, str): response = "END Response error."
    logging.info(f"USSD Session {session_id}: Sending response '{response[:50]}...'" )
    return response

# --- Incoming SMS Logic (from app.py) --- #

@app.route('/incoming-messages', methods=['POST']) # Route for SMS-to-AI
def incoming_sms():
    data = request.form
    sender = data.get('from')
    message_text = data.get('text')
    message_id = data.get('id')

    logging.info(f"SMS Received ID {message_id} from {sender}: '{message_text}'")

    if not sender or not message_text:
        logging.warning("Incomplete SMS data received.")
        return Response(status=400)

    # --- Fetch current stock context ---
    current_stock = get_all_material_stock()
    stock_context = "Current Stock Levels:\\n"
    if current_stock:
        stock_context += "\\n".join([f"- {item['name']}: {item['current_quantity']} {item['unit']}" for item in current_stock])
    else:
        stock_context += "Could not retrieve stock data."
    # --- Create prompt for Gemini ---
    # Combine context and user's message
    prompt_for_ai = f"Context:\\n{stock_context}\\n\\nStock Level Definitions:\\n- Below Stock: Quantity < 50\\n- Sufficient Stock: Quantity >= 50\\n- High Stock: Quantity > 100\\n\\nUser Query:\\n{message_text}\\n\\n---\\nBased ONLY on the provided context, stock level definitions, and user query, answer the query concisely."


    # Call Gemini API
    ai_response_text = "AI Error: Could not process request."
    if gemini_model:
        try:
            # Use the combined prompt
            logging.info(f"Sending to Gemini: '{prompt_for_ai}'")
            gen_response = gemini_model.generate_content(prompt_for_ai) # Pass the combined prompt
            if gen_response.parts:
                ai_response_text = gen_response.text
                logging.info(f"Received from Gemini: '{ai_response_text}'")
            else:
                ai_response_text = "AI Warning: No content generated."
                logging.warning("Gemini response was empty or blocked.")
        except Exception as e:
            logging.error(f"Error calling Gemini API: {e}")
    else:
        ai_response_text = "AI Error: Model not available."
        logging.error("Gemini model not available for SMS processing.")

    # Send Reply SMS via Africa's Talking (using shared 'sms' object)
    if sms and AT_SHORTCODE:
        try:
            logging.info(f"Sending AI reply to {sender}: '{ai_response_text}'")
            recipients = [sender]
            sms_reply_response = sms.send(ai_response_text, recipients, AT_SHORTCODE)
            logging.info(f"Africa's Talking SMS Reply Response: {sms_reply_response}")
        except Exception as e:
            logging.error(f"Error sending AI reply SMS: {e}")
    else:
        logging.error("SMS service/shortcode not available for AI reply.")

    return Response(status=200) # Acknowledge receipt to AT

# --- Run Flask App --- #

if __name__ == '__main__':
    # Use port 5000 by default, consistent with original app.py
    port = int(os.getenv('PORT', 5000))
    logging.info(f"Starting Consolidated Flask server on port {port}")
    # Set debug=False for production; host 0.0.0.0 makes it accessible
    app.run(host='0.0.0.0', port=port, debug=True)
