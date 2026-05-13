import sqlite3
import os
import datetime
from .config import DB_PATH, DB_DIR

def init_db():
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create conversations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            user_message TEXT,
            jinu_reply TEXT,
            context_tags TEXT
        )
    ''')
    
    # Create user profile table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_profile (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    # Create activity log table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            app_name TEXT,
            window_title TEXT,
            duration_seconds INTEGER
        )
    ''')
    
    conn.commit()
    conn.close()

def save_conversation(user_message, jinu_reply, tags=""):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    timestamp = datetime.datetime.now().isoformat()
    cursor.execute('''
        INSERT INTO conversations (timestamp, user_message, jinu_reply, context_tags)
        VALUES (?, ?, ?, ?)
    ''', (timestamp, user_message, jinu_reply, tags))
    conn.commit()
    conn.close()
    
    save_to_vector_db(timestamp, user_message, jinu_reply)

def get_recent_history(limit=10):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT user_message, jinu_reply FROM conversations 
        ORDER BY id DESC LIMIT ?
    ''', (limit,))
    rows = cursor.fetchall()
    conn.close()
    
    # Reverse to get chronological order
    history = []
    for row in reversed(rows):
        history.append({"role": "user", "content": row[0]})
        history.append({"role": "assistant", "content": row[1]})
        
    return history

try:
    import chromadb
    chroma_client = chromadb.PersistentClient(path=os.path.join(DB_DIR, "chroma"))
    chroma_collection = chroma_client.get_or_create_collection(name="jinu_memories")
except Exception as e:
    print(f"ChromaDB error: {e}")
    chroma_collection = None

def save_to_vector_db(timestamp, user_message, jinu_reply):
    if chroma_collection:
        doc = f"User asked: {user_message}. JINU replied: {jinu_reply}"
        chroma_collection.add(documents=[doc], ids=[timestamp])

def get_relevant_memories(query: str, limit=3) -> str:
    if chroma_collection:
        try:
            results = chroma_collection.query(query_texts=[query], n_results=limit)
            if results and results['documents'] and results['documents'][0]:
                docs = results['documents'][0]
                return "\n".join(docs)
        except Exception as e:
            print(f"Chroma query error: {e}")
    return ""

def log_activity(app_name, window_title, duration_seconds):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    timestamp = datetime.datetime.now().isoformat()
    cursor.execute('''
        INSERT INTO activity_log (timestamp, app_name, window_title, duration_seconds)
        VALUES (?, ?, ?, ?)
    ''', (timestamp, app_name, window_title, duration_seconds))
    conn.commit()
    conn.close()

def get_core_facts(limit=10):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT key, value FROM user_profile LIMIT ?', (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def save_core_fact(key, value):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO user_profile (key, value)
        VALUES (?, ?)
    ''', (key, value))
    conn.commit()
    conn.close()

def should_extract_facts():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM conversations')
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0 and count % 5 == 0
