import os
import json
from flask import Flask, request, render_template, redirect, url_for, session
import firebase_admin
from firebase_admin import credentials, db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)

# Secret key for Flask session
app.secret_key = os.getenv("FLASK_SECRET_KEY", "default-secret-key")
ADMIN_PASSWORD = "Derik1408"

# Initialize Firebase Admin SDK
firebase_credentials = os.getenv("FIREBASE_CREDENTIALS")  # Get Firebase credentials from environment
cred = credentials.Certificate(json.loads(firebase_credentials))  # Parse JSON string
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://derikchat-1408-default-rtdb.firebaseio.com/'  # Replace with your Firebase DB URL
})


# Custom filter to convert newlines to <br> tags
@app.template_filter('nl2br')
def nl2br_filter(value):
    return value.replace('\n', '<br>')


# Firebase Helper Functions
def save_message_to_firebase(username, message):
    """Save a new message to Firebase."""
    ref = db.reference("messages")
    ref.push({
        "username": username,
        "message": message,
        "timestamp": datetime.now().isoformat()  # ISO 8601 format for consistency
    })


def load_messages_from_firebase():
    """Load all messages from Firebase."""
    ref = db.reference("messages")
    messages = ref.order_by_child("timestamp").get()
    return [(msg["username"], msg["message"]) for msg in messages.values()] if messages else []


def save_user_to_firebase(username, password):
    """Save a new user to Firebase."""
    ref = db.reference("users")
    ref.child(username).set({
        "username": username,
        "password": generate_password_hash(password)
    })



def authenticate_user(username, password):
    """Authenticate a user using Firebase."""
    ref = db.reference("users")
    user = ref.child(username).get()
    if user and check_password_hash(user["password"], password):
        return True
    return False


# Routes
@app.route("/", methods=["GET", "POST"])
def home():
    error_message = None  # Initialize error message

    if 'username' in session:
        # User is logged in, show the chat
        if request.method == "POST":
            message = request.form.get("message")
            if message and message.strip():
                username = session['username']
                save_message_to_firebase(username, message)
            else:
                error_message = "Message cannot be blank."

            clear_password = request.form.get("clear_password")
            if clear_password:
                if clear_password == ADMIN_PASSWORD:
                    db.reference("messages").delete()  # Clear all messages in Firebase
                    return redirect(url_for('home'))
                else:
                    error_message = "Incorrect password. Access denied."

        messages = load_messages_from_firebase()

        # Preprocess messages using the nl2br filter to handle newlines properly
        processed_messages = []
        for username, message in messages:
            # Apply nl2br filter to handle newlines as <br> tags
            message = message.replace('\n', '<br>')  # Convert newlines to <br>
            processed_messages.append((username, message))

        return render_template("index.html", messages=reversed(processed_messages), error_message=error_message)

    return redirect(url_for('login'))


@app.route("/register", methods=["GET", "POST"])
def register():
    error_message = None

    if request.method == "POST":
        username = request.form.get("username").strip()  # Remove leading/trailing spaces
        password = request.form.get("password").strip()  # Remove leading/trailing spaces

        if username and password:
            ref = db.reference("users")
            if ref.child(username).get():
                error_message = "Username already taken."
            else:
                save_user_to_firebase(username, password)
                return redirect(url_for('login'))
        else:
            error_message = "Both fields are required."

    return render_template("register.html", error_message=error_message)


@app.route("/login", methods=["GET", "POST"])
def login():
    error_message = None

    if request.method == "POST":
        username = request.form.get("username").strip()  # Remove leading/trailing spaces
        password = request.form.get("password").strip()  # Remove leading/trailing spaces

        if username and password:
            if authenticate_user(username, password):
                session['username'] = username
                return redirect(url_for('home'))
            else:
                error_message = "Invalid username or password."
        else:
            error_message = "Both fields are required."

    return render_template("login.html", error_message=error_message)


@app.route("/logout")
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))


if __name__ == "__main__":
    # Ensures that the app binds to the port Render provides
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
