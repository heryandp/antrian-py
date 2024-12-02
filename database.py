import logging
import json

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('Database')

import sqlite3
from config import get_counter_list

def create_connection():
    try:
        conn = sqlite3.connect('queue.db')
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        raise

def init_database():
    """Initialize database with tables and default data"""
    conn = create_connection()
    cursor = conn.cursor()
    
    logger.info("Creating database tables...")
    
    # Create counter table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS counter (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        service_code TEXT NOT NULL,
        status INTEGER DEFAULT 1
    )
    ''')
    
    # Create queue table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS queue (
        id INTEGER PRIMARY KEY,
        number TEXT NOT NULL,
        service_code TEXT NOT NULL,
        counter_id INTEGER,
        status TEXT DEFAULT 'waiting',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        called_at TIMESTAMP,
        FOREIGN KEY (counter_id) REFERENCES counter(id)
    )
    ''')
    
    # Load configuration
    try:
        with open('queue_config.json', 'r') as f:
            config = json.load(f)
            
        # Insert counters from configuration if they don't exist
        cursor.execute("SELECT COUNT(*) FROM counter")
        count = cursor.fetchone()[0]
        
        if count == 0:
            logger.info("Adding counters from configuration...")
            counter_list = []
            
            for service_code, count in config['counters'].items():
                for i in range(1, count + 1):
                    counter_name = f"Loket {service_code}{i}"
                    counter_list.append((counter_name, service_code))
            
            cursor.executemany(
                'INSERT INTO counter (name, service_code) VALUES (?, ?)',
                counter_list
            )
            logger.info(f"Added {len(counter_list)} counters from configuration")
            
    except FileNotFoundError:
        logger.warning("queue_config.json not found, using default configuration")
        # Insert default counters if config not found
        default_counters = [
            ('Loket A1', 'A'),
            ('Loket B1', 'B')
        ]
        cursor.executemany(
            'INSERT INTO counter (name, service_code) VALUES (?, ?)',
            default_counters
        )
        logger.info("Added default counters")
    except Exception as e:
        logger.error(f"Error initializing counters: {e}")
        raise
    
    conn.commit()
    conn.close()
    logger.info("Database initialization completed")

def get_counter_list():
    """Get list of all active counters"""
    try:
        conn = create_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, service_code, status 
            FROM counter 
            WHERE status = 1 
            ORDER BY id
        ''')
        
        counters = cursor.fetchall()
        logger.debug(f"Found {len(counters)} active counters")
        
        # Convert to list of dictionaries
        counter_list = [
            {
                'id': counter[0],
                'name': counter[1],
                'service_code': counter[2],
                'status': counter[3]
            }
            for counter in counters
        ]
        
        return counter_list
    except Exception as e:
        logger.error(f"Error getting counter list: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_next_number(counter_id):
    """Get next waiting number for a specific counter"""
    try:
        conn = create_connection()
        if not conn:
            logger.error("Failed to create database connection")
            return None
            
        cursor = conn.cursor()
        
        # Get the service code for this counter
        cursor.execute("SELECT service_code FROM counter WHERE id = ?", (counter_id,))
        result = cursor.fetchone()
        if not result:
            logger.error(f"Counter ID {counter_id} not found")
            return None
            
        service_code = result[0]
        logger.debug(f"Found service code {service_code} for counter {counter_id}")
        
        # Get the next waiting number for this service
        cursor.execute("""
            SELECT number 
            FROM queue 
            WHERE number LIKE ? AND status = 'waiting'
            ORDER BY id ASC 
            LIMIT 1
        """, (f"{service_code}%",))
        
        result = cursor.fetchone()
        if result:
            number = result[0]
            logger.debug(f"Found next number: {number}")
            
            # Update the status and counter_id
            cursor.execute("""
                UPDATE queue 
                SET status = 'called', counter_id = ?, called_at = CURRENT_TIMESTAMP
                WHERE number = ?
            """, (counter_id, number))
            
            conn.commit()
            logger.info(f"Updated number {number} status to 'called' for counter {counter_id}")
            return number
        else:
            logger.debug(f"No waiting numbers found for service {service_code}")
            return None
            
    except Exception as e:
        logger.error(f"Error in get_next_number: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        if conn:
            conn.close()

def create_new_number(service_code):
    """Create a new queue number for a service"""
    conn = create_connection()
    cursor = conn.cursor()
    
    try:
        # Get the last number for this service
        cursor.execute('''
            SELECT number FROM queue 
            WHERE number LIKE ?
            ORDER BY id DESC LIMIT 1
        ''', (f"{service_code}%",))
        
        last_number = cursor.fetchone()
        if last_number:
            # Extract the numeric part and increment
            num = int(last_number[0][1:]) + 1
        else:
            num = 1
        
        # Format new number (e.g., A001)
        new_number = f"{service_code}{num:03d}"
        
        # Get counter ID for this service
        cursor.execute('''
            SELECT id FROM counter 
            WHERE service_code = ? 
            LIMIT 1
        ''', (service_code,))
        counter_data = cursor.fetchone()
        counter_id = counter_data[0] if counter_data else None
        
        # Insert new number into queue
        cursor.execute('''
            INSERT INTO queue (number, counter_id, status)
            VALUES (?, ?, 'waiting')
        ''', (new_number, counter_id))
        
        conn.commit()
        return new_number
    finally:
        conn.close()

def get_queue_stats(service_code):
    """Get total and next queue numbers for a service"""
    conn = create_connection()
    cursor = conn.cursor()
    
    # Get total queue count
    cursor.execute('''
        SELECT COUNT(*) FROM queue 
        WHERE counter_id IN (
            SELECT id FROM counter WHERE service_code = ?
        )
    ''', (service_code,))
    total = cursor.fetchone()[0]
    
    # Get next number in queue
    cursor.execute('''
        SELECT number FROM queue 
        WHERE counter_id IN (
            SELECT id FROM counter WHERE service_code = ?
        )
        AND status = 'waiting'
        ORDER BY id LIMIT 1
    ''', (service_code,))
    next_row = cursor.fetchone()
    next_number = next_row[0] if next_row else None
    
    conn.close()
    return total, next_number

def get_queue_list(counter_id, limit=10):
    """Get list of called and upcoming queue numbers for a counter"""
    conn = create_connection()
    cursor = conn.cursor()
    
    try:
        # Get counter's service code
        cursor.execute('SELECT service_code FROM counter WHERE id = ?', (counter_id,))
        service_code = cursor.fetchone()[0]
        
        # Get recently called numbers
        cursor.execute('''
            SELECT number, status, created_at 
            FROM queue 
            WHERE counter_id = ? AND status = 'called'
            ORDER BY id DESC LIMIT ?
        ''', (counter_id, limit))
        called_numbers = cursor.fetchall()
        
        # Get upcoming numbers for this service
        cursor.execute('''
            SELECT number, created_at 
            FROM queue 
            WHERE number LIKE ? 
            AND status = 'waiting'
            ORDER BY id ASC LIMIT ?
        ''', (f"{service_code}%", limit))
        upcoming_numbers = cursor.fetchall()
        
        return called_numbers, upcoming_numbers
    finally:
        conn.close()

def has_waiting_numbers(counter_id):
    """Check if there are waiting numbers for this counter's service"""
    conn = create_connection()
    cursor = conn.cursor()
    
    try:
        # Get counter's service code
        cursor.execute('SELECT service_code FROM counter WHERE id = ?', (counter_id,))
        service_code = cursor.fetchone()[0]
        
        # Check for waiting numbers
        cursor.execute('''
            SELECT COUNT(*) FROM queue 
            WHERE number LIKE ? 
            AND status = 'waiting'
        ''', (f"{service_code}%",))
        
        count = cursor.fetchone()[0]
        return count > 0
    finally:
        conn.close()

if __name__ == '__main__':
    init_database()
