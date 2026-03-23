import sqlite3
from datetime import datetime
import json

DB_NAME = "salaryscope_users.db"


# ---------------------------------------------------
# CONNECTION
# ---------------------------------------------------

def get_connection():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    return conn


# ---------------------------------------------------
# USERS + SESSIONS TABLE
# ---------------------------------------------------

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # USERS TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT,
        password_hash BLOB NOT NULL,
        created_at TEXT
    )
    """)

    # SESSIONS TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        session_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        token_hash TEXT UNIQUE NOT NULL,
        created_at TEXT,
        expires_at TEXT
    )
    """)

    conn.commit()
    conn.close()


# ---------------------------------------------------
# USER FUNCTIONS
# ---------------------------------------------------

def create_user(username, email, password_hash):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO users (username, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
        (username, email, password_hash, datetime.utcnow().isoformat())
    )

    conn.commit()
    conn.close()


def get_user(username):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT user_id, username, email, password_hash FROM users WHERE username=?",
        (username,)
    )

    user = cursor.fetchone()
    conn.close()

    return user


# ---------------------------------------------------
# SESSION FUNCTIONS (SECURE LOGIN)
# ---------------------------------------------------

def create_session(username, token_hash, expires_at):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO sessions (username, token_hash, created_at, expires_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            username,
            token_hash,
            datetime.utcnow().isoformat(),
            expires_at.isoformat()
        )
    )

    conn.commit()
    conn.close()


def get_session(token_hash):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT session_id, username, token_hash, expires_at FROM sessions WHERE token_hash=?",
        (token_hash,)
    )

    session = cursor.fetchone()
    conn.close()

    return session


def delete_session(token_hash):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM sessions WHERE token_hash=?",
        (token_hash,)
    )

    conn.commit()
    conn.close()


def delete_expired_sessions():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM sessions WHERE expires_at < ?",
        (datetime.utcnow().isoformat(),)
    )

    conn.commit()
    conn.close()


# ---------------------------------------------------
# PREDICTIONS TABLE
# ---------------------------------------------------

def create_prediction_table():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS predictions (
        prediction_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        model_used TEXT,
        input_data TEXT,
        predicted_salary REAL,
        created_at TEXT
    )
    """)

    conn.commit()
    conn.close()


def save_prediction(username, model_used, input_data, predicted_salary):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO predictions (username, model_used, input_data, predicted_salary, created_at) VALUES (?, ?, ?, ?, ?)",
        (
            username,
            model_used,
            json.dumps(input_data),
            predicted_salary,
            datetime.utcnow().isoformat()
        )
    )

    conn.commit()
    conn.close()


def get_user_predictions(username):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT prediction_id, model_used, input_data, predicted_salary, created_at FROM predictions WHERE username=? ORDER BY created_at DESC",
        (username,)
    )

    rows = cursor.fetchall()
    conn.close()

    return rows
