"""
Flask API Server for MARS Customer Support Agent
Exposes endpoints for initiating and managing support conversations
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
from agent import CustomerSupportAgent, handle_multi_turn_conversation
from datetime import datetime
import uuid

load_dotenv()

app = Flask(__name__)
CORS(app)

# Health check endpoint
@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "mars-customer-support-agent"
    }), 200

# Start a new support conversation
@app.route('/api/v1/conversations/start', methods=['POST'])
def start_conversation():
    """Start a new customer support conversation session."""
    try:
        data = request.json

        # Validate required fields
        if not data.get('customer_id') or not data.get('email'):
            return jsonify({
                "error": "Missing required fields: customer_id, email"
            }), 400

        # Generate session ID
        session_id = f"session_{uuid.uuid4().hex[:12]}"

        return jsonify({
            "session_id": session_id,
            "customer_id": data['customer_id'],
            "started_at": datetime.now().isoformat(),
            "status": "active"
        }), 201

    except Exception as e:
        return jsonify({
            "error": f"Failed to start conversation: {str(e)}"
        }), 500

# Send message and get response
@app.route('/api/v1/conversations/<session_id>/message', methods=['POST'])
def send_message(session_id):
    """Send a message in an active conversation."""
    try:
        data = request.json

        if not data.get('message') or not data.get('customer_id'):
            return jsonify({
                "error": "Missing required fields: message, customer_id"
            }), 400

        # Process message with agent
        agent = CustomerSupportAgent()
        response = agent.process_message(
            session_id,
            data['customer_id'],
            data['message']
        )

        return jsonify({
            "session_id": session_id,
            "customer_id": data['customer_id'],
            "message": data['message'],
            "response": response,
            "timestamp": datetime.now().isoformat()
        }), 200

    except Exception as e:
        return jsonify({
            "error": f"Failed to process message: {str(e)}"
        }), 500

# Get conversation history
@app.route('/api/v1/conversations/<session_id>/history', methods=['GET'])
def get_conversation_history(session_id):
    """Retrieve the conversation history for a session."""
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor

        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME", "support_db"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432")
        )
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT id, role, message, metadata, created_at
            FROM conversations
            WHERE session_id = %s
            ORDER BY created_at ASC
        """, (session_id,))

        messages = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify({
            "session_id": session_id,
            "message_count": len(messages),
            "messages": [dict(msg) for msg in messages]
        }), 200

    except Exception as e:
        return jsonify({
            "error": f"Failed to retrieve history: {str(e)}"
        }), 500

# Multi-turn conversation (batch)
@app.route('/api/v1/conversations/batch', methods=['POST'])
def batch_conversation():
    """Process multiple messages in a conversation."""
    try:
        data = request.json

        required_fields = ['customer_id', 'messages']
        if not all(field in data for field in required_fields):
            return jsonify({
                "error": f"Missing required fields: {', '.join(required_fields)}"
            }), 400

        # Generate session ID
        session_id = f"session_{uuid.uuid4().hex[:12]}"

        # Process all messages
        responses = handle_multi_turn_conversation(
            session_id,
            data['customer_id'],
            data['messages']
        )

        return jsonify({
            "session_id": session_id,
            "customer_id": data['customer_id'],
            "total_messages": len(data['messages']),
            "responses": responses,
            "completed_at": datetime.now().isoformat()
        }), 200

    except Exception as e:
        return jsonify({
            "error": f"Failed to process batch: {str(e)}"
        }), 500

# Get ticket by session
@app.route('/api/v1/conversations/<session_id>/ticket', methods=['GET'])
def get_session_ticket(session_id):
    """Get any ticket created during a conversation."""
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor

        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME", "support_db"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432")
        )
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT t.id, t.ticket_number, t.subject, t.priority, t.status, t.created_at
            FROM tickets t
            INNER JOIN escalations e ON t.id = e.ticket_id
            WHERE e.session_id = %s
            LIMIT 1
        """, (session_id,))

        ticket = cursor.fetchone()
        cursor.close()
        conn.close()

        if ticket:
            return jsonify({
                "session_id": session_id,
                "ticket": dict(ticket)
            }), 200
        else:
            return jsonify({
                "session_id": session_id,
                "ticket": None,
                "message": "No ticket created in this session"
            }), 200

    except Exception as e:
        return jsonify({
            "error": f"Failed to retrieve ticket: {str(e)}"
        }), 500

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "error": "Endpoint not found",
        "status": 404
    }), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({
        "error": "Internal server error",
        "status": 500
    }), 500

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=os.getenv("FLASK_ENV") == "development")
