import hashlib
import secrets
import streamlit as st
from datetime import datetime, timedelta
from functools import wraps
import json
import os

# Simple in-memory user store (in production, use proper database)
USERS_FILE = "ehr_users.json"

def load_users():
    """Load users from file or create default admin user."""
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    else:
        # Create default admin user
        admin_password = hash_password("admin123")
        default_users = {
            "admin": {
                "password": admin_password,
                "role": "admin",
                "name": "System Administrator",
                "email": "admin@ehr.local",
                "created_at": datetime.now().isoformat(),
                "last_login": None,
                "failed_attempts": 0,
                "locked_until": None
            }
        }
        save_users(default_users)
        return default_users

def save_users(users):
    """Save users to file."""
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def hash_password(password):
    """Hash password using SHA-256 with salt."""
    salt = secrets.token_hex(16)
    password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}:{password_hash}"

def verify_password(password, hashed):
    """Verify password against hash."""
    try:
        salt, password_hash = hashed.split(':')
        return hashlib.sha256((password + salt).encode()).hexdigest() == password_hash
    except:
        return False

def is_account_locked(username):
    """Check if account is locked due to failed attempts."""
    users = load_users()
    user = users.get(username)
    if user and user.get("locked_until"):
        locked_until = datetime.fromisoformat(user["locked_until"])
        if datetime.now() < locked_until:
            return True
        else:
            # Unlock if lock period has expired
            user["locked_until"] = None
            user["failed_attempts"] = 0
            save_users(users)
    return False

def record_failed_login(username):
    """Record failed login attempt and lock account if necessary."""
    users = load_users()
    user = users.get(username)
    if user:
        user["failed_attempts"] = user.get("failed_attempts", 0) + 1
        if user["failed_attempts"] >= 3:
            # Lock for 30 minutes
            user["locked_until"] = (datetime.now() + timedelta(minutes=30)).isoformat()
        save_users(users)

def record_successful_login(username):
    """Record successful login and reset failed attempts."""
    users = load_users()
    user = users.get(username)
    if user:
        user["last_login"] = datetime.now().isoformat()
        user["failed_attempts"] = 0
        user["locked_until"] = None
        save_users(users)

def login_user(username, password):
    """Authenticate user."""
    if is_account_locked(username):
        return False, "Account locked due to multiple failed attempts. Please try again later."

    users = load_users()
    user = users.get(username)

    if user and verify_password(password, user["password"]):
        record_successful_login(username)
        return True, "Login successful"
    else:
        record_failed_login(username)
        return False, "Invalid username or password"

def register_user(username, password, name, email, role="doctor"):
    """Register a new user."""
    users = load_users()

    if username in users:
        return False, "Username already exists"

    users[username] = {
        "password": hash_password(password),
        "role": role,
        "name": name,
        "email": email,
        "created_at": datetime.now().isoformat(),
        "last_login": None,
        "failed_attempts": 0,
        "locked_until": None
    }

    save_users(users)
    return True, "User registered successfully"

def get_current_user():
    """Get current logged-in user from session state."""
    return st.session_state.get("current_user")

def require_auth(f):
    """Decorator to require authentication for a function."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not st.session_state.get("authenticated"):
            st.error("Please login to access this page.")
            st.stop()
        return f(*args, **kwargs)
    return wrapper

def require_role(allowed_roles):
    """Decorator to require specific role for access."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            current_user = get_current_user()
            if not current_user or current_user.get("role") not in allowed_roles:
                st.error("Access denied. Insufficient permissions.")
                st.stop()
            return f(*args, **kwargs)
        return wrapper
    return decorator

def logout():
    """Logout current user."""
    st.session_state["authenticated"] = False
    st.session_state["current_user"] = None
    st.session_state.clear()

def get_user_role():
    """Get current user's role."""
    user = get_current_user()
    return user.get("role") if user else None

def is_admin():
    """Check if current user is admin."""
    return get_user_role() == "admin"

def is_doctor():
    """Check if current user is doctor."""
    return get_user_role() == "doctor"

def is_nurse():
    """Check if current user is nurse."""
    return get_user_role() == "nurse"

def is_staff():
    """Check if current user is staff (doctor, nurse, or admin)."""
    return get_user_role() in ["admin", "doctor", "nurse"]

# Audit logging functions
def log_audit_event(user_id, action, details=None, patient_id=None):
    """Log audit events for compliance."""
    audit_log = {
        "timestamp": datetime.now().isoformat(),
        "user_id": user_id,
        "action": action,
        "details": details,
        "patient_id": patient_id,
        "ip_address": st.session_state.get("ip_address", "unknown")
    }

    # In production, save to secure audit log database
    audit_file = "ehr_audit.log"
    with open(audit_file, "a") as f:
        f.write(json.dumps(audit_log) + "\n")

def get_audit_logs(limit=100):
    """Get recent audit logs."""
    audit_file = "ehr_audit.log"
    if not os.path.exists(audit_file):
        return []

    logs = []
    with open(audit_file, "r") as f:
        for line in f:
            try:
                logs.append(json.loads(line.strip()))
            except:
                continue

    return sorted(logs, key=lambda x: x["timestamp"], reverse=True)[:limit]