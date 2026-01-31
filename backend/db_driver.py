import sqlite3
from typing import Optional
from dataclasses import dataclass
from contextlib import contextmanager
from datetime import datetime
import json
import uuid


@dataclass
class Car:
    vin: str
    make: str
    model: str
    year: str
    mileage: int = 0
    owner_name: str = ""
    owner_phone: str = ""


class DatabaseDriver:
    def __init__(self, db_path: str = 'auto_db.sqlite'):
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()
    
    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Vehicles table (updated)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cars(
                    vin TEXT PRIMARY KEY,
                    make TEXT NOT NULL,
                    model TEXT NOT NULL,
                    year INTEGER NOT NULL,
                    mileage INTEGER DEFAULT 0,
                    owner_name TEXT,
                    owner_phone TEXT,
                    owner_email TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )"""
            )
            
            # User sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    user_identifier TEXT NOT NULL,
                    identifier_type TEXT NOT NULL,
                    vehicle_vin TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT,
                    FOREIGN KEY (vehicle_vin) REFERENCES cars(vin)
                )
            """)
            
            # Conversation history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """)
            
            # Service history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS service_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vehicle_vin TEXT NOT NULL,
                    service_type TEXT NOT NULL,
                    description TEXT,
                    cost REAL,
                    service_date DATE,
                    technician TEXT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (vehicle_vin) REFERENCES cars(vin)
                )
            """)
            
            # Appointments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS appointments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    vehicle_vin TEXT,
                    customer_name TEXT NOT NULL,
                    customer_phone TEXT,
                    service_type TEXT NOT NULL,
                    appointment_date DATE NOT NULL,
                    appointment_time TEXT NOT NULL,
                    status TEXT DEFAULT 'scheduled',
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (vehicle_vin) REFERENCES cars(vin)
                )
            """)
            
            conn.commit()
    
    def create_car(self, vin: str, make: str, model: str, year: int, 
                   mileage: int = 0, owner_name: str = "", owner_phone: str = "") -> Car:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO cars (vin, make, model, year, mileage, owner_name, owner_phone) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (vin, make, model, year, mileage, owner_name, owner_phone)
            )
            conn.commit()
            return Car(vin=vin, make=make, model=model, year=year, 
                      mileage=mileage, owner_name=owner_name, owner_phone=owner_phone)
    
    def get_car_by_vin(self, vin: str) -> Optional[Car]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT vin, make, model, year, mileage, owner_name, owner_phone FROM cars WHERE vin = ?", (vin,))
            row = cursor.fetchone()
            if not row:
                return None
            
            return Car(
                vin=row[0],
                make=row[1],
                model=row[2],
                year=row[3],
                mileage=row[4] or 0,
                owner_name=row[5] or "",
                owner_phone=row[6] or ""
            )
    
    def update_mileage(self, vin: str, mileage: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE cars SET mileage = ?, updated_at = ? WHERE vin = ?",
                (mileage, datetime.now(), vin)
            )
            conn.commit()
            return cursor.rowcount > 0


class SessionManager:
    """Manages user sessions and conversation history"""
    
    def __init__(self, db_path: str = 'auto_db.sqlite'):
        self.db_path = db_path
    
    def _get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def create_session(self, user_identifier: str, identifier_type: str = "phone") -> str:
        """Create a new session or return existing one for the user"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Check if user has an existing active session
        cursor.execute("""
            SELECT session_id FROM sessions 
            WHERE user_identifier = ? AND identifier_type = ?
            ORDER BY last_active DESC LIMIT 1
        """, (user_identifier, identifier_type))
        
        result = cursor.fetchone()
        
        if result:
            session_id = result[0]
            # Update last active time
            cursor.execute("""
                UPDATE sessions SET last_active = ? WHERE session_id = ?
            """, (datetime.now(), session_id))
        else:
            # Create new session
            session_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO sessions (session_id, user_identifier, identifier_type)
                VALUES (?, ?, ?)
            """, (session_id, user_identifier, identifier_type))
        
        conn.commit()
        conn.close()
        return session_id
    
    def get_session(self, session_id: str) -> Optional[dict]:
        """Get session details"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT session_id, user_identifier, identifier_type, vehicle_vin, 
                   created_at, last_active, metadata
            FROM sessions WHERE session_id = ?
        """, (session_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                "session_id": result[0],
                "user_identifier": result[1],
                "identifier_type": result[2],
                "vehicle_vin": result[3],
                "created_at": result[4],
                "last_active": result[5],
                "metadata": json.loads(result[6]) if result[6] else {}
            }
        return None
    
    def link_vehicle_to_session(self, session_id: str, vin: str):
        """Link a vehicle to the current session"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE sessions SET vehicle_vin = ?, last_active = ?
            WHERE session_id = ?
        """, (vin, datetime.now(), session_id))
        
        conn.commit()
        conn.close()
    
    def add_message(self, session_id: str, role: str, content: str, metadata: dict = None):
        """Add a message to conversation history"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO conversation_history (session_id, role, content, metadata)
            VALUES (?, ?, ?, ?)
        """, (session_id, role, content, json.dumps(metadata) if metadata else None))
        
        # Update session last active
        cursor.execute("""
            UPDATE sessions SET last_active = ? WHERE session_id = ?
        """, (datetime.now(), session_id))
        
        conn.commit()
        conn.close()
    
    def get_conversation_history(self, session_id: str, limit: int = 20) -> list:
        """Get recent conversation history for a session"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT role, content, timestamp, metadata
            FROM conversation_history
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (session_id, limit))
        
        results = cursor.fetchall()
        conn.close()
        
        # Return in chronological order
        history = []
        for row in reversed(results):
            history.append({
                "role": row[0],
                "content": row[1],
                "timestamp": row[2],
                "metadata": json.loads(row[3]) if row[3] else {}
            })
        return history
    
    def get_session_by_user(self, user_identifier: str, identifier_type: str = "phone") -> Optional[dict]:
        """Find a session by user identifier (phone/email)"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT session_id FROM sessions 
            WHERE user_identifier = ? AND identifier_type = ?
            ORDER BY last_active DESC LIMIT 1
        """, (user_identifier, identifier_type))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return self.get_session(result[0])
        return None