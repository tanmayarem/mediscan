"""
User Authentication and Personalization Module

This module handles:
- User registration and login
- Storing user medical history
- Allergies tracking
- Personal details (age, weight, height, etc.)
- Cross-referencing medicines with user allergies
"""

import sqlite3
import hashlib
import secrets
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


class UserAuthManager:
    """
    Manages user authentication and personal medical information.
    """
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self._init_user_db()
    
    def _init_user_db(self):
        """Initialize user database tables."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        # Users table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        """)
        
        # User medical profile
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_medical_profile (
                user_id INTEGER PRIMARY KEY,
                age INTEGER,
                weight_kg REAL,
                height_cm REAL,
                gender TEXT,
                medical_conditions TEXT,
                current_medications TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # User allergies
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_allergies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                allergen_name TEXT NOT NULL,
                allergen_type TEXT,
                severity TEXT,
                notes TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(user_id, allergen_name)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _hash_password(self, password: str, salt: str) -> str:
        """Hash password with salt."""
        return hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
    
    def register_user(self, username: str, email: str, password: str) -> Dict:
        """
        Register a new user.
        
        Returns:
            {"status": "success/error", "message": "...", "user_id": ...}
        """
        try:
            salt = secrets.token_hex(16)
            password_hash = self._hash_password(password, salt)
            
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            
            try:
                cur.execute("""
                    INSERT INTO users (username, email, password_hash, salt)
                    VALUES (?, ?, ?, ?)
                """, (username, email, password_hash, salt))
                
                user_id = cur.lastrowid
                conn.commit()
                conn.close()
                
                return {
                    "status": "success",
                    "message": "User registered successfully",
                    "user_id": user_id
                }
            except sqlite3.IntegrityError as e:
                conn.close()
                if "username" in str(e):
                    return {"status": "error", "message": "Username already exists"}
                elif "email" in str(e):
                    return {"status": "error", "message": "Email already registered"}
                return {"status": "error", "message": "Registration failed"}
        except Exception as e:
            logger.error(f"Error registering user: {e}")
            return {"status": "error", "message": str(e)}
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """
        Authenticate user login.
        
        Returns:
            User dict if successful, None otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("""
                SELECT id, username, email, password_hash, salt
                FROM users WHERE username = ? OR email = ?
            """, (username, username))
            
            row = cur.fetchone()
            conn.close()
            
            if not row:
                return None
            
            user_id, db_username, email, db_hash, salt = row
            
            # Verify password
            if self._hash_password(password, salt) == db_hash:
                # Update last login
                conn = sqlite3.connect(self.db_path)
                cur = conn.cursor()
                cur.execute("""
                    UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?
                """, (user_id,))
                conn.commit()
                conn.close()
                
                return {
                    "id": user_id,
                    "username": db_username,
                    "email": email
                }
            
            return None
        except Exception as e:
            logger.error(f"Error authenticating user: {e}")
            return None
    
    def update_medical_profile(self, user_id: int, **kwargs) -> Dict:
        """
        Update user medical profile.
        
        Args:
            user_id: User ID
            **kwargs: age, weight_kg, height_cm, gender, medical_conditions, current_medications
        
        Returns:
            Success/error status
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            
            # Check if profile exists
            cur.execute("SELECT user_id FROM user_medical_profile WHERE user_id = ?", (user_id,))
            exists = cur.fetchone()
            
            if exists:
                # Update existing
                updates = []
                values = []
                for key in ["age", "weight_kg", "height_cm", "gender", "medical_conditions", "current_medications"]:
                    if key in kwargs:
                        updates.append(f"{key} = ?")
                        # Convert lists/dicts to JSON strings
                        value = kwargs[key]
                        if isinstance(value, (list, dict)):
                            value = json.dumps(value)
                        values.append(value)
                
                if updates:
                    values.append(user_id)
                    cur.execute(f"""
                        UPDATE user_medical_profile
                        SET {', '.join(updates)}
                        WHERE user_id = ?
                    """, values)
            else:
                # Insert new
                cur.execute("""
                    INSERT INTO user_medical_profile
                    (user_id, age, weight_kg, height_cm, gender, medical_conditions, current_medications)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    kwargs.get("age"),
                    kwargs.get("weight_kg"),
                    kwargs.get("height_cm"),
                    kwargs.get("gender"),
                    json.dumps(kwargs.get("medical_conditions")) if isinstance(kwargs.get("medical_conditions"), list) else kwargs.get("medical_conditions"),
                    json.dumps(kwargs.get("current_medications")) if isinstance(kwargs.get("current_medications"), list) else kwargs.get("current_medications")
                ))
            
            conn.commit()
            conn.close()
            
            return {"status": "success", "message": "Profile updated"}
        except Exception as e:
            logger.error(f"Error updating profile: {e}")
            return {"status": "error", "message": str(e)}
    
    def get_medical_profile(self, user_id: int) -> Optional[Dict]:
        """Get user medical profile."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM user_medical_profile WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
            conn.close()
            
            if row:
                profile = dict(row)
                # Parse JSON fields
                if profile.get("medical_conditions"):
                    try:
                        profile["medical_conditions"] = json.loads(profile["medical_conditions"])
                    except:
                        pass
                if profile.get("current_medications"):
                    try:
                        profile["current_medications"] = json.loads(profile["current_medications"])
                    except:
                        pass
                return profile
            return None
        except Exception as e:
            logger.error(f"Error getting profile: {e}")
            return None
    
    def add_allergy(self, user_id: int, allergen_name: str, allergen_type: str = None, 
                    severity: str = "moderate", notes: str = None) -> Dict:
        """Add allergy for user."""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("""
                INSERT OR REPLACE INTO user_allergies
                (user_id, allergen_name, allergen_type, severity, notes)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, allergen_name, allergen_type, severity, notes))
            conn.commit()
            conn.close()
            return {"status": "success", "message": "Allergy added"}
        except Exception as e:
            logger.error(f"Error adding allergy: {e}")
            return {"status": "error", "message": str(e)}
    
    def get_allergies(self, user_id: int) -> List[Dict]:
        """Get all allergies for user."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM user_allergies WHERE user_id = ?", (user_id,))
            rows = cur.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting allergies: {e}")
            return []
    
    def check_allergy_conflict(self, user_id: int, medicine_composition: str) -> Dict:
        """
        Check if medicine contains allergens user is allergic to.
        
        Returns:
            {
                "has_conflict": bool,
                "conflicts": [{"allergen": "...", "found_in": "..."}],
                "warnings": [...]
            }
        """
        allergies = self.get_allergies(user_id)
        if not allergies:
            return {"has_conflict": False, "conflicts": [], "warnings": []}
        
        composition_lower = medicine_composition.lower()
        conflicts = []
        warnings = []
        
        for allergy in allergies:
            allergen_name = allergy["allergen_name"].lower()
            
            # Check if allergen appears in composition
            if allergen_name in composition_lower:
                conflicts.append({
                    "allergen": allergy["allergen_name"],
                    "severity": allergy.get("severity", "moderate"),
                    "found_in": medicine_composition,
                    "notes": allergy.get("notes")
                })
                
                severity = allergy.get("severity", "moderate")
                if severity == "severe":
                    warnings.append({
                        "type": "danger",
                        "message": f"⚠️ CRITICAL: This medicine contains {allergy['allergen_name']} which you are severely allergic to. DO NOT TAKE THIS MEDICINE."
                    })
                else:
                    warnings.append({
                        "type": "warning",
                        "message": f"⚠️ WARNING: This medicine contains {allergy['allergen_name']} which you are allergic to. Consult your doctor before taking."
                    })
        
        return {
            "has_conflict": len(conflicts) > 0,
            "conflicts": conflicts,
            "warnings": warnings
        }

