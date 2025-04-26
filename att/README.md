# Construction Site Material Tracker (USSD & SMS AI Assistant)

This project provides a system for tracking construction materials using a USSD interface and allows users to query stock levels and ask general questions via SMS, which are answered by Google Gemini AI.

## Features

*   **USSD Interface:**
    *   Record materials received (e.g., Cement, Sand, Gravel).
    *   Check current stock levels for specific materials.
    *   Sends SMS notifications to registered stakeholders when materials are recorded.
*   **SMS AI Assistant:**
    *   Receive SMS messages sent to a designated Africa's Talking number.
    *   Fetch current material stock levels from the database.
    *   Provide stock levels and user query as context to Google Gemini.
    *   Reply to the user's SMS with the AI-generated answer.
*   **Database:** Uses SQLite (`construction.db`) to store material details, quantities, and stakeholder phone numbers.
*   **API Integration:** Uses Africa's Talking for USSD and SMS, and Google Gemini for AI responses.

## Prerequisites

*   Python 3 (Developed with Python 3.10+)
*   `pip` (Python package installer)
*   `git` (for cloning the repository)
*   [ngrok](https://ngrok.com/download) (to expose the local Flask server to the internet for Africa's Talking callbacks)
*   An Africa's Talking account with:
    *   A registered USSD code (e.g., `*384*XXXX#`)
    *   A registered SMS Shortcode or Alphanumeric Sender ID
    *   API Credentials (Username and API Key)
*   A Google Cloud account with the Gemini API enabled and an API Key.

## Setup Instructions

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/kechykechy/ATT.git
    cd att # Or your repository directory name
    ```

2.  **Create and Activate Virtual Environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    # On Windows use: .\venv\Scripts\activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install Flask africastalking python-dotenv google-generativeai
    ```

4.  **Configure Environment Variables:**
    *   Create a file named `.env` in the project root directory.
    *   Add the following lines, replacing the placeholder values with your actual credentials:
        ```dotenv
        # Africa's Talking Credentials
        AT_USERNAME=YOUR_AT_USERNAME
        AT_API_KEY=YOUR_AT_API_KEY
        AT_SHORTCODE=YOUR_AT_SHORTCODE_OR_SENDERID # Used for SMS replies/notifications

        # Google Gemini API Key
        GOOGLE_API_KEY=YOUR_GOOGLE_API_KEY
        ```

5.  **Set Up the Database:**
    *   Run the setup script. This creates the `construction.db` file and populates initial `materials` and `stakeholders` data.
    *   You can modify `setup_db.py` to add different materials or stakeholders.
    ```bash
    python3 setup_db.py
    ```

## Running the Application

1.  **Start Ngrok:**
    *   The consolidated Flask application (`main_app.py`) runs on port 5000 by default. Expose this port using ngrok:
    ```bash
    ngrok http 5000
    ```
    *   Note the `https://` Forwarding URL provided by ngrok (e.g., `https://xxxxx.ngrok-free.app`).

2.  **Configure Africa's Talking Callbacks:**
    *   Go to your Africa's Talking Dashboard.
    *   **USSD Callback:** Navigate to USSD -> Callback URL. Set the URL to the ngrok `https://` address (e.g., `https://xxxxx.ngrok-free.app/`).
    *   **Incoming SMS Callback:** Navigate to SMS -> Callback URLs -> Incoming Messages. Set the URL to the ngrok `https://` address followed by `/incoming-messages` (e.g., `https://xxxxx.ngrok-free.app/incoming-messages`).

3.  **Run the Flask Application:**
    *   Make sure your virtual environment is activated.
    *   Run the main application script in your terminal:
    ```bash
    python3 main_app.py
    ```
    *   The server should start listening on port 5000.

## Usage

*   **USSD:** Dial your registered USSD code from a phone. Follow the on-screen prompts to record received materials or check stock levels.
*   **SMS AI:** Send an SMS message to your registered Africa's Talking Shortcode/SenderID (the one specified in `AT_SHORTCODE` in your `.env` file). Ask questions about stock levels (e.g., "How much cement is left?", "Is sand below stock?") or general questions. The application will forward your query (with stock context) to Gemini and reply with the AI's response.

## Files

*   `main_app.py`: The main Flask application handling both USSD and incoming SMS requests.
*   `setup_db.py`: Script to initialize the SQLite database (`construction.db`) and tables.
*   `construction.db`: SQLite database file.
*   `.env`: Stores environment variables (API keys, AT credentials).
*   `README.md`: This file.
*   `ussd.py`: (Legacy) Original USSD-only application code. Not actively used if running `main_app.py`.
*   `app.py`: (Legacy) Original SMS-to-AI-only application code. Not actively used if running `main_app.py`.
*   `send_sms.py`: (Example) Script demonstrating how to send an outbound SMS using the SDK.
*   `send_whatsapp.py`: (Example) Script demonstrating how to send an outbound WhatsApp message using the AT API.
*   `requirements.txt`: (Optional) Could be generated using `pip freeze > requirements.txt`.
*   `.gitignore`: (Optional) To exclude files like `.env`, `venv`, `__pycache__`, `construction.db` from Git.
