"""
Flask API Server for MARS Customer Support Agent with DO Serverless Inference
Exposes endpoints with usage tracking and cost monitoring
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
from agent_enhanced import EnhancedCustomerSupportAgent, handle_multi_turn_conversation
from do_inference_client import InferenceModelRegistry
from datetime import datetime
import uuid
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()

app = Flask(__name__)
CORS(app)

# Global agent instance (in production, use session-based instances)
agent_instances = {}

def get_agent(model: str = "claude-3-5-sonnet"):
    """Get or create agent instance for model."""
    if model not in agent_instances:
        agent_instances[model] = EnhancedCustomerSupportAgent(model=model)
    return agent_instances[model]

def get_db_connection():
    """Create database connection."""
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME", "support_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432")
    )

# Health check endpoint
@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "mars-customer-support-agent-enhanced",
        "inference": "DigitalOcean Serverless Inference",
        "version": "2.0"
    }), 200

# Start a new support conversation
@app.route('/api/v2/conversations/start', methods=['POST'])
def start_conversation():
    """Start a new customer support conversation session."""
    try:
        data = request.json

        if not data.get('customer_id') or not data.get('email'):
            return jsonify({
                "error": "Missing required fields: customer_id, email"
            }), 400

        session_id = f"session_{uuid.uuid4().hex[:12]}"
        model = data.get('model', 'claude-3-5-sonnet')

        # Validate model
        if model not in InferenceModelRegistry.list_models():
            return jsonify({
                "error": f"Model '{model}' not supported. Available: {InferenceModelRegistry.list_models()}"
            }), 400

        return jsonify({
            "session_id": session_id,
            "customer_id": data['customer_id'],
            "model": model,
            "started_at": datetime.now().isoformat(),
            "status": "active"
        }), 201

    except Exception as e:
        return jsonify({
            "error": f"Failed to start conversation: {str(e)}"
        }), 500

# Send message and get response
@app.route('/api/v2/conversations/<session_id>/message', methods=['POST'])
def send_message(session_id):
    """Send a message in an active conversation."""
    try:
        data = request.json

        if not data.get('message') or not data.get('customer_id'):
            return jsonify({
                "error": "Missing required fields: message, customer_id"
            }), 400

        model = data.get('model', 'claude-3-5-sonnet')

        # Get agent for model
        agent = get_agent(model)

        # Process message
        response = agent.process_message(
            session_id,
            data['customer_id'],
            data['message']
        )

        return jsonify({
            "session_id": session_id,
            "customer_id": data['customer_id'],
            "message": data['message'],
            "response": response['message'],
            "model_used": response['model_used'],
            "cost_usd": response['cost'],
            "classification": response['classification'],
            "escalation_triggered": response['escalation_triggered'],
            "timestamp": datetime.now().isoformat()
        }), 200

    except Exception as e:
        return jsonify({
            "error": f"Failed to process message: {str(e)}"
        }), 500

# Get conversation history
@app.route('/api/v2/conversations/<session_id>/history', methods=['GET'])
def get_conversation_history(session_id):
    """Retrieve the conversation history for a session."""
    try:
        conn = get_db_connection()
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

        # Calculate session cost
        session_cost = 0.0
        for msg in messages:
            if msg.get('metadata') and isinstance(msg['metadata'], str):
                import json
                metadata = json.loads(msg['metadata'])
                session_cost += metadata.get('inference_cost', 0)

        return jsonify({
            "session_id": session_id,
            "message_count": len(messages),
            "session_cost_usd": round(session_cost, 6),
            "messages": [dict(msg) for msg in messages]
        }), 200

    except Exception as e:
        return jsonify({
            "error": f"Failed to retrieve history: {str(e)}"
        }), 500

# Multi-turn conversation (batch)
@app.route('/api/v2/conversations/batch', methods=['POST'])
def batch_conversation():
    """Process multiple messages in a conversation."""
    try:
        data = request.json

        required_fields = ['customer_id', 'messages']
        if not all(field in data for field in required_fields):
            return jsonify({
                "error": f"Missing required fields: {', '.join(required_fields)}"
            }), 400

        session_id = f"session_{uuid.uuid4().hex[:12]}"
        model = data.get('model', 'claude-3-5-sonnet')

        result = handle_multi_turn_conversation(
            session_id,
            data['customer_id'],
            data['messages'],
            model=model
        )

        return jsonify({
            "session_id": result['session_id'],
            "customer_id": data['customer_id'],
            "model": model,
            "total_messages": len(data['messages']),
            "responses": result['responses'],
            "usage_summary": result['usage_summary'],
            "completed_at": datetime.now().isoformat()
        }), 200

    except Exception as e:
        return jsonify({
            "error": f"Failed to process batch: {str(e)}"
        }), 500

# List available models
@app.route('/api/v2/models', methods=['GET'])
def list_models():
    """List available inference models."""
    try:
        models = InferenceModelRegistry.list_models()
        model_details = {}

        for model in models:
            info = InferenceModelRegistry.get_model_info(model)
            model_details[model] = info

        return jsonify({
            "available_models": models,
            "model_details": model_details,
            "default_model": "claude-3-5-sonnet"
        }), 200

    except Exception as e:
        return jsonify({
            "error": f"Failed to list models: {str(e)}"
        }), 500

# Get model recommendations
@app.route('/api/v2/models/recommendation', methods=['POST'])
def get_model_recommendation():
    """Get model recommendation for use case."""
    try:
        data = request.json
        use_case = data.get('use_case', 'customer_support')

        recommended = InferenceModelRegistry.get_recommended_model(use_case)
        info = InferenceModelRegistry.get_model_info(recommended)

        return jsonify({
            "use_case": use_case,
            "recommended_model": recommended,
            "model_info": info
        }), 200

    except Exception as e:
        return jsonify({
            "error": f"Failed to get recommendation: {str(e)}"
        }), 500

# Get session usage and costs
@app.route('/api/v2/conversations/<session_id>/usage', methods=['GET'])
def get_session_usage(session_id):
    """Get usage and cost details for a session."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Get all messages for this session
        cursor.execute("""
            SELECT role, metadata, created_at
            FROM conversations
            WHERE session_id = %s
            ORDER BY created_at ASC
        """, (session_id,))

        messages = cursor.fetchall()
        cursor.close()
        conn.close()

        import json

        total_cost = 0.0
        total_tokens = 0
        models_used = set()
        requests_count = 0

        for msg in messages:
            if msg['role'] == 'agent' and msg.get('metadata'):
                metadata = json.loads(msg['metadata'])
                total_cost += metadata.get('inference_cost', 0)
                total_tokens += metadata.get('tokens_used', 0)
                model = metadata.get('model_used')
                if model:
                    models_used.add(model)
                requests_count += 1

        return jsonify({
            "session_id": session_id,
            "total_cost_usd": round(total_cost, 6),
            "total_tokens": total_tokens,
            "inference_requests": requests_count,
            "models_used": list(models_used),
            "average_cost_per_request": round(total_cost / requests_count, 6) if requests_count > 0 else 0
        }), 200

    except Exception as e:
        return jsonify({
            "error": f"Failed to get usage: {str(e)}"
        }), 500

# Get overall analytics
@app.route('/api/v2/analytics/summary', methods=['GET'])
def get_analytics_summary():
    """Get overall system analytics."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Get conversation stats
        cursor.execute("""
            SELECT
                COUNT(DISTINCT session_id) as total_sessions,
                COUNT(*) as total_messages,
                COUNT(DISTINCT customer_id) as unique_customers
            FROM conversations
        """)
        conv_stats = cursor.fetchone()

        # Get ticket stats
        cursor.execute("""
            SELECT
                COUNT(*) as total_tickets,
                COUNT(CASE WHEN status = 'open' THEN 1 END) as open_tickets,
                COUNT(CASE WHEN status = 'resolved' THEN 1 END) as resolved_tickets
            FROM tickets
        """)
        ticket_stats = cursor.fetchone()

        # Get escalation stats
        cursor.execute("""
            SELECT
                COUNT(*) as total_escalations,
                COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_escalations
            FROM escalations
        """)
        escalation_stats = cursor.fetchone()

        cursor.close()
        conn.close()

        return jsonify({
            "conversations": dict(conv_stats),
            "tickets": dict(ticket_stats),
            "escalations": dict(escalation_stats),
            "timestamp": datetime.now().isoformat()
        }), 200

    except Exception as e:
        return jsonify({
            "error": f"Failed to get analytics: {str(e)}"
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
