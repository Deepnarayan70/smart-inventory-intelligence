from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

def email_exists(db, email):
    """Check if a user email already exists in the database."""
    return db.users.find_one({"email": email}) is not None

def create_user(db, name, email, password):
    """
    Hash the password and insert a new user document.
    Returns (success, user_id or error_message).
    """
    if email_exists(db, email):
        return False, "Email is already registered."

    user_doc = {
        "name": name.strip(),
        "email": email.strip().lower(),
        "password_hash": generate_password_hash(password),
        "created_at": datetime.now()
    }

    result = db.users.insert_one(user_doc)
    return True, str(result.inserted_id)

def verify_user(db, email, password):
    """
    Verify login credentials.
    Returns the user document if valid, None otherwise.
    """
    user = db.users.find_one({"email": email.strip().lower()})
    if user and check_password_hash(user["password_hash"], password):
        return user
    return None

def get_user_by_id(db, user_id):
    """
    Fetch a user document by their string representation of ObjectId.
    """
    from bson.objectid import ObjectId
    try:
        return db.users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        return None
