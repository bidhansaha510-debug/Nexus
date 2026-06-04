"""
NEXUS AI - User Account Manager
Handles user registration, authentication, and chat history persistence.
Uses SQLite for storage and hashlib+secrets for password hashing.
"""

import sqlite3
import hashlib
import secrets
import threading
import time
import random
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import DATA_DIR
from utils.logger import get_logger
logger = get_logger("user_manager")

DB_PATH = Path(DATA_DIR) / "users.db"


class UserManager:
    """Manages user accounts and chat history with SQLite storage."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._db_lock = threading.Lock()
        self._init_db()
        logger.info(f"UserManager initialized — DB at {DB_PATH}")

    # ── Database Setup ──

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(DB_PATH), timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self):
        with self._db_lock:
            conn = self._get_conn()
            try:
                conn.executescript("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL COLLATE NOCASE,
                        password_hash TEXT NOT NULL,
                        salt TEXT NOT NULL,
                        display_name TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_login TIMESTAMP
                    );

                    CREATE TABLE IF NOT EXISTS chat_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        emotion TEXT DEFAULT 'neutral',
                        intensity REAL DEFAULT 0.5,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id)
                    );

                    CREATE INDEX IF NOT EXISTS idx_chat_user_time
                        ON chat_history(user_id, timestamp DESC);

                    CREATE TABLE IF NOT EXISTS otp_codes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email TEXT NOT NULL COLLATE NOCASE,
                        code TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP NOT NULL,
                        used INTEGER DEFAULT 0
                    );

                    CREATE INDEX IF NOT EXISTS idx_otp_email
                        ON otp_codes(email, used, expires_at);
                """)
                conn.commit()

                # ── Schema migrations ──
                migration_cols = [
                    ("profile_picture", "TEXT"),
                    ("bio", "TEXT"),
                    ("email", "TEXT"),
                    ("auth_provider", "TEXT DEFAULT 'local'"),
                ]
                for col, col_type in migration_cols:
                    try:
                        conn.execute(f"ALTER TABLE users ADD COLUMN {col} {col_type}")
                        conn.commit()
                        logger.info(f"Added column users.{col}")
                    except sqlite3.OperationalError:
                        pass  # Column already exists

                logger.info("User database tables ready")
            finally:
                conn.close()

    # ── Password Hashing ──

    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        return hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            iterations=100_000
        ).hex()

    # ── User CRUD ──

    def create_user(self, username: str, password: str,
                    display_name: str = "") -> Dict[str, Any]:
        """
        Create a new user account.
        Returns user dict on success, raises ValueError on duplicate.
        """
        username = username.strip()
        if not username or len(username) < 3:
            raise ValueError("Username must be at least 3 characters")
        if not password or len(password) < 4:
            raise ValueError("Password must be at least 4 characters")

        salt = secrets.token_hex(16)
        password_hash = self._hash_password(password, salt)
        display = display_name.strip() or username

        with self._db_lock:
            conn = self._get_conn()
            try:
                conn.execute(
                    "INSERT INTO users (username, password_hash, salt, display_name) "
                    "VALUES (?, ?, ?, ?)",
                    (username, password_hash, salt, display)
                )
                conn.commit()
                user_id = conn.execute(
                    "SELECT id FROM users WHERE username = ?", (username,)
                ).fetchone()["id"]

                logger.info(f"User created: {username} (id={user_id})")
                return {
                    "id": user_id,
                    "username": username,
                    "display_name": display,
                }
            except sqlite3.IntegrityError:
                raise ValueError(f"Username '{username}' already exists")
            finally:
                conn.close()

    def authenticate(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user. Returns user dict or None."""
        with self._db_lock:
            conn = self._get_conn()
            try:
                row = conn.execute(
                    "SELECT * FROM users WHERE username = ?",
                    (username.strip(),)
                ).fetchone()
                if not row:
                    return None

                expected = self._hash_password(password, row["salt"])
                if expected != row["password_hash"]:
                    return None

                # Update last login
                conn.execute(
                    "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
                    (row["id"],)
                )
                conn.commit()

                logger.info(f"User authenticated: {username}")
                return {
                    "id": row["id"],
                    "username": row["username"],
                    "display_name": row["display_name"] or row["username"],
                }
            finally:
                conn.close()

    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        with self._db_lock:
            conn = self._get_conn()
            try:
                row = conn.execute(
                    "SELECT id, username, display_name, created_at FROM users WHERE id = ?",
                    (user_id,)
                ).fetchone()
                if not row:
                    return None
                return dict(row)
            finally:
                conn.close()

    def get_full_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get full user profile including bio and avatar."""
        with self._db_lock:
            conn = self._get_conn()
            try:
                row = conn.execute(
                    "SELECT id, username, display_name, bio, profile_picture, "
                    "created_at, last_login FROM users WHERE id = ?",
                    (user_id,)
                ).fetchone()
                if not row:
                    return None
                return dict(row)
            finally:
                conn.close()

    def update_profile(self, user_id: int, display_name: str = "",
                       bio: str = "") -> Dict[str, Any]:
        """Update user display_name and bio."""
        with self._db_lock:
            conn = self._get_conn()
            try:
                conn.execute(
                    "UPDATE users SET display_name = ?, bio = ? WHERE id = ?",
                    (display_name.strip(), bio.strip(), user_id)
                )
                conn.commit()
                logger.info(f"Profile updated for user {user_id}")
                return self.get_full_profile(user_id) or {}
            finally:
                conn.close()

    def change_password(self, user_id: int, old_password: str,
                        new_password: str) -> bool:
        """Change password after verifying old password. Returns True on success."""
        if not new_password or len(new_password) < 4:
            raise ValueError("New password must be at least 4 characters")

        with self._db_lock:
            conn = self._get_conn()
            try:
                row = conn.execute(
                    "SELECT password_hash, salt FROM users WHERE id = ?",
                    (user_id,)
                ).fetchone()
                if not row:
                    raise ValueError("User not found")

                expected = self._hash_password(old_password, row["salt"])
                if expected != row["password_hash"]:
                    raise ValueError("Current password is incorrect")

                new_salt = secrets.token_hex(16)
                new_hash = self._hash_password(new_password, new_salt)
                conn.execute(
                    "UPDATE users SET password_hash = ?, salt = ? WHERE id = ?",
                    (new_hash, new_salt, user_id)
                )
                conn.commit()
                logger.info(f"Password changed for user {user_id}")
                return True
            finally:
                conn.close()

    def update_avatar(self, user_id: int, base64_data: str) -> bool:
        """Store a base64-encoded profile picture."""
        with self._db_lock:
            conn = self._get_conn()
            try:
                conn.execute(
                    "UPDATE users SET profile_picture = ? WHERE id = ?",
                    (base64_data, user_id)
                )
                conn.commit()
                logger.info(f"Avatar updated for user {user_id}")
                return True
            finally:
                conn.close()

    # ── Chat History ──

    def save_message(self, user_id: int, role: str, content: str,
                     emotion: str = "neutral", intensity: float = 0.5):
        """Save a chat message to the database."""
        with self._db_lock:
            conn = self._get_conn()
            try:
                conn.execute(
                    "INSERT INTO chat_history (user_id, role, content, emotion, intensity) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (user_id, role, content, emotion, intensity)
                )
                conn.commit()
            finally:
                conn.close()

    def get_chat_history(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent chat history for a user, oldest first."""
        with self._db_lock:
            conn = self._get_conn()
            try:
                rows = conn.execute(
                    "SELECT role, content, emotion, intensity, timestamp "
                    "FROM chat_history WHERE user_id = ? "
                    "ORDER BY timestamp DESC LIMIT ?",
                    (user_id, limit)
                ).fetchall()
                # Reverse so oldest is first
                return [dict(r) for r in reversed(rows)]
            finally:
                conn.close()

    def clear_chat_history(self, user_id: int):
        """Clear all chat history for a user."""
        with self._db_lock:
            conn = self._get_conn()
            try:
                conn.execute(
                    "DELETE FROM chat_history WHERE user_id = ?", (user_id,)
                )
                conn.commit()
                logger.info(f"Chat history cleared for user {user_id}")
            finally:
                conn.close()


    # ── Email OTP ──

    def create_or_get_email_user(self, email: str) -> Dict[str, Any]:
        """Find or create a user from email OTP login."""
        with self._db_lock:
            conn = self._get_conn()
            try:
                row = conn.execute(
                    "SELECT id, username, display_name FROM users WHERE email = ?",
                    (email.strip(),)
                ).fetchone()
                if row:
                    conn.execute(
                        "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
                        (row["id"],)
                    )
                    conn.commit()
                    return {"id": row["id"], "username": row["username"],
                            "display_name": row["display_name"] or row["username"]}

                # Create new user from email
                username = email.split("@")[0]
                base_username = username
                counter = 1
                while conn.execute("SELECT 1 FROM users WHERE username = ?",
                                   (username,)).fetchone():
                    username = f"{base_username}{counter}"
                    counter += 1

                salt = secrets.token_hex(16)
                pwd_hash = self._hash_password(secrets.token_hex(32), salt)

                conn.execute(
                    "INSERT INTO users (username, password_hash, salt, display_name, "
                    "email, auth_provider) VALUES (?, ?, ?, ?, ?, 'email_otp')",
                    (username, pwd_hash, salt, username, email.strip())
                )
                conn.commit()
                user_id = conn.execute(
                    "SELECT id FROM users WHERE email = ?", (email.strip(),)
                ).fetchone()["id"]
                logger.info(f"Email OTP user created: {username} (id={user_id})")
                return {"id": user_id, "username": username, "display_name": username}
            finally:
                conn.close()

    def generate_otp(self, email: str) -> str:
        """Generate a 4-digit OTP for the given email, valid for 5 minutes."""
        code = str(random.randint(1000, 9999))
        expires = datetime.utcnow() + timedelta(minutes=5)
        with self._db_lock:
            conn = self._get_conn()
            try:
                # Invalidate previous unused OTPs for this email
                conn.execute(
                    "UPDATE otp_codes SET used = 1 WHERE email = ? AND used = 0",
                    (email.strip(),)
                )
                conn.execute(
                    "INSERT INTO otp_codes (email, code, expires_at) VALUES (?, ?, ?)",
                    (email.strip(), code, expires.strftime("%Y-%m-%d %H:%M:%S"))
                )
                conn.commit()
                logger.info(f"OTP generated for {email}")
            finally:
                conn.close()
        return code

    def verify_otp(self, email: str, code: str) -> Optional[Dict[str, Any]]:
        """Verify a 4-digit OTP. Returns user dict on success, None on failure."""
        with self._db_lock:
            conn = self._get_conn()
            try:
                row = conn.execute(
                    "SELECT id FROM otp_codes WHERE email = ? AND code = ? "
                    "AND used = 0 AND expires_at > ? ORDER BY created_at DESC LIMIT 1",
                    (email.strip(), code.strip(),
                     datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
                ).fetchone()
                if not row:
                    return None
                # Mark as used
                conn.execute("UPDATE otp_codes SET used = 1 WHERE id = ?", (row["id"],))
                conn.commit()
            finally:
                conn.close()

        # Create or get user by email
        return self.create_or_get_email_user(email)

    def send_otp_email(self, email: str, code: str) -> bool:
        """Send OTP code to the given email via SMTP."""
        smtp_email = "shayaksaha03@gmail.com"
        smtp_password = "vfsl lrpx zuow urlb"
        if not smtp_email or not smtp_password:
            logger.error("SMTP credentials not configured")
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"NEXUS AI — Your login code is {code}"
            msg["From"] = smtp_email
            msg["To"] = email

            html = f"""\
            <html>
            <body style="font-family:Inter,Arial,sans-serif;background:#0a0a0f;color:#fff;padding:40px;text-align:center">
                <div style="max-width:400px;margin:0 auto;background:#1a1a2e;border-radius:16px;padding:40px;border:1px solid rgba(0,212,255,0.2)">
                    <div style="font-size:40px;margin-bottom:16px">🧠</div>
                    <h1 style="color:#00d4ff;margin:0 0 8px">NEXUS AI</h1>
                    <p style="color:#94a3b8;margin:0 0 24px">Your verification code</p>
                    <div style="font-size:36px;font-weight:700;letter-spacing:12px;color:#fff;background:#0a0a0f;border-radius:12px;padding:16px;margin:0 0 24px">{code}</div>
                    <p style="color:#64748b;font-size:13px;margin:0">This code expires in 5 minutes. Don't share it.</p>
                </div>
            </body>
            </html>
            """
            msg.attach(MIMEText(html, "html"))

            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(smtp_email, smtp_password)
                server.sendmail(smtp_email, email, msg.as_string())

            logger.info(f"OTP email sent to {email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send OTP email: {e}")
            return False

    def cleanup_expired_otps(self):
        """Remove expired OTP entries."""
        with self._db_lock:
            conn = self._get_conn()
            try:
                conn.execute(
                    "DELETE FROM otp_codes WHERE expires_at < ? OR used = 1",
                    (datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),)
                )
                conn.commit()
            finally:
                conn.close()


# Global instance
user_manager = UserManager()
