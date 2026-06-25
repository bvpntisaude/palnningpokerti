import mysql.connector
from mysql.connector import pooling
import os
from dotenv import load_dotenv
import uuid
from datetime import datetime

load_dotenv()

db_config = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "planning_poker"),
}

connection_pool = pooling.MySQLConnectionPool(
    pool_name="poker_pool",
    pool_size=10,
    **db_config,
)


def get_connection():
    return connection_pool.get_connection()


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            id VARCHAR(8) PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            status ENUM('waiting', 'voting', 'revealed') DEFAULT 'waiting',
            current_story VARCHAR(200) DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id VARCHAR(36) PRIMARY KEY,
            room_id VARCHAR(8) NOT NULL,
            name VARCHAR(50) NOT NULL,
            is_moderator BOOLEAN DEFAULT FALSE,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS votes (
            id INT AUTO_INCREMENT PRIMARY KEY,
            room_id VARCHAR(8) NOT NULL,
            player_id VARCHAR(36) NOT NULL,
            vote VARCHAR(5),
            round INT DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY unique_vote (room_id, player_id, round),
            FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE,
            FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()


# ── Rooms ──────────────────────────────────────────────────────────────────────

def create_room(name: str) -> str:
    room_id = str(uuid.uuid4())[:8].upper()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO rooms (id, name) VALUES (%s, %s)",
        (room_id, name),
    )
    conn.commit()
    cursor.close()
    conn.close()
    return room_id


def get_room(room_id: str) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM rooms WHERE id = %s", (room_id.upper(),))
    room = cursor.fetchone()
    cursor.close()
    conn.close()
    return room


def update_room_status(room_id: str, status: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE rooms SET status = %s WHERE id = %s",
        (status, room_id),
    )
    conn.commit()
    cursor.close()
    conn.close()


def update_room_story(room_id: str, story: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE rooms SET current_story = %s, status = 'voting' WHERE id = %s",
        (story, room_id),
    )
    conn.commit()
    cursor.close()
    conn.close()


def reset_round(room_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM votes WHERE room_id = %s",
        (room_id,),
    )
    cursor.execute(
        "UPDATE rooms SET status = 'voting', current_story = '' WHERE id = %s",
        (room_id,),
    )
    conn.commit()
    cursor.close()
    conn.close()


# ── Players ────────────────────────────────────────────────────────────────────

def add_player(room_id: str, name: str, is_moderator: bool = False) -> str:
    player_id = str(uuid.uuid4())
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO players (id, room_id, name, is_moderator) VALUES (%s, %s, %s, %s)",
        (player_id, room_id, name, is_moderator),
    )
    conn.commit()
    cursor.close()
    conn.close()
    return player_id


def get_players(room_id: str) -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM players WHERE room_id = %s ORDER BY created_at ASC",
        (room_id,),
    )
    players = cursor.fetchall()
    cursor.close()
    conn.close()
    return players


def heartbeat(player_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE players SET last_seen = NOW() WHERE id = %s",
        (player_id,),
    )
    conn.commit()
    cursor.close()
    conn.close()


def remove_inactive_players(room_id: str, seconds: int = 30):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM players WHERE room_id = %s AND last_seen < NOW() - INTERVAL %s SECOND",
        (room_id, seconds),
    )
    conn.commit()
    cursor.close()
    conn.close()


# ── Votes ──────────────────────────────────────────────────────────────────────

def cast_vote(room_id: str, player_id: str, vote: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO votes (room_id, player_id, vote)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE vote = %s
    """, (room_id, player_id, vote, vote))
    conn.commit()
    cursor.close()
    conn.close()


def get_votes(room_id: str) -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT v.player_id, v.vote, p.name
        FROM votes v
        JOIN players p ON v.player_id = p.id
        WHERE v.room_id = %s
    """, (room_id,))
    votes = cursor.fetchall()
    cursor.close()
    conn.close()
    return votes


def player_voted(room_id: str, player_id: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM votes WHERE room_id = %s AND player_id = %s",
        (room_id, player_id),
    )
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result is not None
