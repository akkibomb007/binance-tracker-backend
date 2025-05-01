from flask import Flask, jsonify, request
import sqlite3
from flask_cors import CORS
import os
import json
import random
import string
from datetime import datetime, timedelta
import socket

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})  # Enable CORS for all API routes

# Database setup
DB_PATH = "red_packets.db"  # Adjust path as needed
USE_IN_MEMORY_DB = False  # Set to True if file access is restricted

# Connect to the database
def get_db_connection():
    global USE_IN_MEMORY_DB
    try:
        if USE_IN_MEMORY_DB:
            # Use in-memory database if file access is restricted
            conn = sqlite3.connect(":memory:")
            print("Using in-memory database")
        else:
            # Try to use file-based database
            try:
                # Ensure the directory exists
                os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
                conn = sqlite3.connect(DB_PATH)
                print(f"Connected to database at {DB_PATH}")
            except Exception as e:
                print(f"Error connecting to file database: {e}")
                print("Falling back to in-memory database")
                conn = sqlite3.connect(":memory:")
                USE_IN_MEMORY_DB = True
        
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"Critical database error: {e}")
        return None

# Initialize database if it doesn't exist
def initialize_database():
    try:
        conn = get_db_connection()
        if conn is None:
            print("Skipping database initialization - no connection available")
            return False
            
        cursor = conn.cursor()
        
        # Create table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS red_packets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            type TEXT NOT NULL,
            source TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            isUsed BOOLEAN DEFAULT FALSE
        )
        ''')
        
        conn.commit()
        conn.close()
        print("Database initialized successfully")
        return True
    except Exception as e:
        print(f"Error initializing database: {e}")
        return False

# Generate sample data for when database is not available
def generate_sample_data(count=15):
    sources = ["SBDBOX", "ahcryptos", "redboxpro"]
    types = ["8-digit", "BP"]
    sample_data = []
    
    for i in range(count):
        packet_type = random.choice(types)
        if packet_type == "BP":
            code = "BP" + ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(8))
        else:
            code = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(8))
        
        timestamp = (datetime.now() - timedelta(minutes=random.randint(0, 60))).isoformat()
        
        sample_data.append({
            "id": i + 1,
            "code": code,
            "type": packet_type,
            "source": random.choice(sources),
            "timestamp": timestamp,
            "isUsed": False
        })
    
    return sample_data

@app.route('/api/red-packets', methods=['GET', 'OPTIONS'])
def get_red_packets():
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response
        
    try:
        # Get filter parameter if provided
        packet_type = request.args.get('type', 'all')
        
        # Try to get from database first
        try:
            conn = get_db_connection()
            if conn is not None:
                cursor = conn.cursor()
                
                # Build query based on filter
                query = "SELECT * FROM red_packets"
                params = []
                
                if packet_type != 'all':
                    query += " WHERE type = ?"
                    params.append(packet_type)
                
                query += " ORDER BY timestamp DESC LIMIT 15"
                
                # Execute query
                cursor.execute(query, params)
                
                # Convert to list of dictionaries
                red_packets = []
                for row in cursor.fetchall():
                    packet = dict(row)
                    red_packets.append(packet)
                
                conn.close()
                
                if red_packets:
                    return jsonify(red_packets)
        except Exception as e:
            print(f"Database error: {e}")
            print("Falling back to sample data")
        
        # If we get here, either the database failed or returned no results
        # Generate sample data instead
        sample_data = generate_sample_data()
        
        # Apply filter if needed
        if packet_type != 'all':
            sample_data = [p for p in sample_data if p['type'] == packet_type]
            
        return jsonify(sample_data)
    except Exception as e:
        print(f"Error in get_red_packets: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/status', methods=['GET', 'OPTIONS'])
def get_status():
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response
        
    # Simple status endpoint to check if the API is running
    return jsonify({
        "status": "online",
        "mode": "simulation" if USE_IN_MEMORY_DB else "database",
        "message": "API is running in simulation mode"
    })

# Function to find an available port
def find_available_port(start_port=8000, max_port=9000):
    for port in range(start_port, max_port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('', port))
                return port
            except OSError:
                continue
    return None

if __name__ == '__main__':
    # Initialize database before starting the server
    db_initialized = initialize_database()
    if not db_initialized:
        print("Running with sample data only (no database persistence)")
    
    # Find an available port
    port = find_available_port(8000, 9000)
    if port is None:
        print("Could not find an available port between 8000-9000. Using port 8080.")
        port = 8080
    
    # Start the server
    print(f"Starting API server on http://localhost:{port}")
    print(f"If you're running on anywherepython.com, your API will be available at:")
    print(f"https://your-username.anywherepython.com:{port}")
    
    try:
        app.run(debug=True, port=port, host='0.0.0.0')
    except OSError as e:
        print(f"Error starting server: {e}")
        print("Trying one more time with a different port...")
        try:
            port = find_available_port(8080, 9000)
            if port is None:
                port = 8888
            app.run(debug=True, port=port, host='0.0.0.0')
        except Exception as e:
            print(f"Failed to start server: {e}")
            print("Please check if you have permission to bind to ports or try a different port.")