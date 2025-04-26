import os
import sqlite3
import logging
from flask import Flask, request
from dotenv import load_dotenv
import africastalking

# --- Configuration & Initialization --- #

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

AT_USERNAME = os.getenv('AT_USERNAME', 'sandbox') # Default to sandbox if not set
AT_API_KEY = os.getenv('AT_API_KEY')
AT_SHORTCODE = os.getenv('AT_SHORTCODE')

# Database path
DB_NAME = 'construction.db'
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(PROJECT_DIR, DB_NAME)

# Validate mandatory config
if not AT_API_KEY or not AT_SHORTCODE:
    logging.error("Missing AT_API_KEY or AT_SHORTCODE in .env file. SMS sending will fail.")

# Initialize Flask app
app = Flask(__name__)

# Initialize Africa's Talking SDK
try:
    africastalking.initialize(AT_USERNAME, AT_API_KEY)
    sms = africastalking.SMS
    logging.info("Africa's Talking SDK initialized successfully.")
except Exception as e:
    logging.error(f"Failed to initialize Africa's Talking SDK: {e}")
    sms = None

# --- Database Helper Functions --- #

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
    """Fetches name and unit for a specific material ID."""
    conn = db_connect()
    material = None
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name, unit, current_quantity FROM materials WHERE id = ?", (material_id,))
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
            # Use COALESCE to handle potential NULL in current_quantity if needed, though DEFAULT 0 helps
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
            # Extract the phone number string from each row
            numbers = [row['phone_number'] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Error fetching stakeholder numbers: {e}")
        finally:
            conn.close()
    return numbers

# --- USSD Callback Logic --- #

@app.route('/', methods=['POST', 'GET'])
def ussd_callback():
    response = ""
    session_id = request.values.get("sessionId", None)
    service_code = request.values.get("serviceCode", None)
    phone_number = request.values.get("phoneNumber", None)
    text = request.values.get("text", "")

    logging.info(f"Session {session_id}: Received input '{text}' from {phone_number}")

    parts = text.split('*')
    level = len(parts) if text else 0

    materials = get_materials() # Get materials early for potential use

    try:
        if level == 0:
            # Level 0: Main Menu
            response = "CON Welcome to Construction Tracker\n"
            response += "1. Record Material Received\n"
            response += "2. Check Stock Level"

        elif level == 1:
            # Level 1: Action Selection (Record or Check)
            choice = parts[0]
            if choice in ['1', '2']: # Record or Check
                if not materials:
                    response = "END No materials found in the database."
                else:
                    response = "CON Select Material:\n"
                    for i, material in enumerate(materials):
                        response += f"{i+1}. {material['name']}\n"
            else:
                response = "END Invalid choice. Please try again."

        elif level == 2:
            # Level 2: Material Selection
            main_choice = parts[0]
            try:
                material_index = int(parts[1]) - 1
                if 0 <= material_index < len(materials):
                    selected_material = materials[material_index]
                    if main_choice == '1': # Record
                        response = f"CON Enter quantity of {selected_material['name']} ({selected_material['unit']}):"
                    elif main_choice == '2': # Check
                        mat_details = get_material_details(selected_material['id'])
                        if mat_details:
                            response = f"END {mat_details['name']}: {mat_details['current_quantity']} {mat_details['unit']} currently in stock."
                        else:
                            response = "END Error retrieving stock details."
                    else:
                        response = "END Invalid action selection from previous menu."
                else:
                    response = "END Invalid material selection."
            except (ValueError, IndexError):
                response = "END Invalid input. Please select a valid material number."

        elif level == 3:
            # Level 3: Quantity Input (only for Record action)
            main_choice = parts[0]
            try:
                material_index = int(parts[1]) - 1
                quantity_str = parts[2]

                if main_choice == '1': # Ensure this level is only for Record
                    if 0 <= material_index < len(materials):
                        selected_material = materials[material_index]
                        if quantity_str.isdigit() and int(quantity_str) > 0:
                            quantity = int(quantity_str)
                            # Update database
                            if update_material_quantity(selected_material['id'], quantity):
                                response = f"END {quantity} {selected_material['unit']} of {selected_material['name']} recorded successfully.\n"
                                # Send SMS Notification
                                stakeholders = get_stakeholder_numbers()
                                if stakeholders and sms:
                                    message = f"{quantity} {selected_material['unit']} of {selected_material['name']} recorded via USSD by {phone_number}."
                                    try:
                                        sms_response = sms.send(message, stakeholders, AT_SHORTCODE)
                                        logging.info(f"SMS notification sent: {sms_response}")
                                        response += " Stakeholders notified."
                                    except Exception as e:
                                        logging.error(f"Failed to send SMS notification: {e}")
                                        response += " SMS notification failed."
                                elif not sms:
                                    logging.warning("SMS service not initialized. Cannot send notification.")
                                    response += " SMS notification disabled."
                                elif not stakeholders:
                                    logging.warning("No stakeholders found to notify.")
                                    response += " No stakeholders to notify."
                            else:
                                response = "END Failed to update database. Please try again."
                        else:
                            response = "END Invalid quantity. Please enter a positive number."
                    else:
                        response = "END Invalid material selection from previous menu."
                else:
                     response = "END Invalid sequence. Expected quantity input."
            except (ValueError, IndexError):
                response = "END Invalid input. Please ensure correct format (e.g., 1*1*50)."

        else:
            # Handle unexpected deeper levels or invalid text sequences
            response = "END Invalid input or session state. Please restart."

    except Exception as e:
        logging.exception(f"An unexpected error occurred during USSD processing: {e}")
        response = "END An internal error occurred. Please try again later."

    # Ensure response is a string before returning
    if not isinstance(response, str):
        logging.error(f"Invalid response type generated: {type(response)}. Defaulting to error message.")
        response = "END Internal error generating response."
    
    logging.info(f"Session {session_id}: Sending response '{response[:50]}...'" ) # Log snippet
    return response

# --- Run Flask App --- #

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001)) # Use a different port maybe, e.g., 5001
    logging.info(f"Starting Flask server for USSD on port {port}")
    # Set debug=False for production
    # Host 0.0.0.0 makes it accessible on the network
    app.run(host='0.0.0.0', port=port, debug=True)
