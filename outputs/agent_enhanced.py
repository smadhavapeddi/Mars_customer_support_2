"""
MARS Customer Support Automation Agent - Enhanced with DO Serverless Inference
Multi-turn agent with DigitalOcean Serverless Inference for model inference
"""

import json
import os
from datetime import datetime
from typing import Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from do_inference_client import DigitalOceanInferenceClient, InferenceModelRegistry
import logging

logger = logging.getLogger(__name__)

# Database connection
def get_db_connection():
    """Create and return a PostgreSQL connection."""
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME", "support_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432")
    )

class EnhancedCustomerSupportAgent:
    """
    Enhanced customer support agent using DigitalOcean Serverless Inference.

    Features:
    - Uses DO Serverless Inference for model calls
    - Tracks usage and costs
    - Multi-model support with fallback
    - Advanced conversation history management
    """

    def __init__(self, model: str = "claude-3-5-sonnet"):
        """Initialize agent with DO Serverless Inference client."""
        self.inference_client = DigitalOceanInferenceClient(
            primary_model=model
        )
        self.model = model
        self.conversation_history = []
        self.session_metadata = {}

    def search_faq(self, query: str) -> list:
        """Search FAQ database for relevant answers."""
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            cursor.execute("""
                SELECT id, question, answer, category, priority
                FROM faq
                WHERE to_tsvector('english', question || ' ' || answer)
                      @@ plainto_tsquery('english', %s)
                ORDER BY priority DESC
                LIMIT 5
            """, (query,))
            results = cursor.fetchall()
            return results if results else []
        finally:
            cursor.close()
            conn.close()

    def create_ticket(self, customer_id: str, subject: str,
                     description: str, priority: str, category: str) -> dict:
        """Create a support ticket in the database."""
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            cursor.execute("""
                INSERT INTO tickets (customer_id, subject, description,
                                    priority, category, status, created_at)
                VALUES (%s, %s, %s, %s, %s, 'open', NOW())
                RETURNING id, ticket_number, created_at
            """, (customer_id, subject, description, priority, category))

            result = cursor.fetchone()
            conn.commit()

            return {
                "ticket_id": result['id'],
                "ticket_number": result['ticket_number'],
                "created_at": result['created_at'].isoformat(),
                "status": "created"
            }
        finally:
            cursor.close()
            conn.close()

    def log_conversation(self, session_id: str, customer_id: str,
                        role: str, message: str, metadata: Optional[dict] = None):
        """Log conversation messages to database."""
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO conversations
                (session_id, customer_id, role, message, metadata, created_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
            """, (session_id, customer_id, role, message,
                  json.dumps(metadata) if metadata else None))

            conn.commit()
        finally:
            cursor.close()
            conn.close()

    def escalate_to_human(self, session_id: str, customer_id: str,
                         reason: str, ticket_id: Optional[str] = None) -> dict:
        """Escalate conversation to human agent."""
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            # Get conversation history for context
            cursor.execute("""
                SELECT message, role, created_at
                FROM conversations
                WHERE session_id = %s
                ORDER BY created_at DESC
                LIMIT 10
            """, (session_id,))

            history = cursor.fetchall()

            # Create escalation record
            cursor.execute("""
                INSERT INTO escalations
                (session_id, customer_id, ticket_id, reason, status, created_at)
                VALUES (%s, %s, %s, %s, 'pending', NOW())
                RETURNING id, created_at
            """, (session_id, customer_id, ticket_id, reason))

            result = cursor.fetchone()
            conn.commit()

            return {
                "escalation_id": result['id'],
                "status": "escalated",
                "assigned_to": "human_queue",
                "context": [dict(h) for h in history]
            }
        finally:
            cursor.close()
            conn.close()

    def classify_ticket(self, customer_message: str) -> dict:
        """Use DO Inference to classify the customer's issue."""
        classification_prompt = f"""
        Analyze this customer support message and provide:
        1. Category (billing, technical, account, feature_request, other)
        2. Priority (low, medium, high, critical)
        3. Sentiment (positive, neutral, negative)
        4. Requires_escalation (yes/no)

        Customer message: {customer_message}

        Respond in JSON format only.
        """

        try:
            response = self.inference_client.chat_completion(
                messages=[{"role": "user", "content": classification_prompt}],
                max_tokens=500,
                temperature=0.3
            )

            response_text = response["content"]

            # Log inference usage
            logger.info(f"Classification cost: ${response['cost']}")

            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                return {
                    "category": "other",
                    "priority": "medium",
                    "sentiment": "neutral",
                    "requires_escalation": False
                }
        except Exception as e:
            logger.error(f"Classification failed: {str(e)}")
            return {
                "category": "other",
                "priority": "medium",
                "sentiment": "neutral",
                "requires_escalation": False
            }

    def process_message(self, session_id: str, customer_id: str,
                       customer_message: str) -> dict:
        """Process customer message and generate response."""

        # Log customer message
        self.log_conversation(session_id, customer_id, "customer", customer_message)

        # Classify the message
        classification = self.classify_ticket(customer_message)

        # Search FAQ for relevant answers
        faq_results = self.search_faq(customer_message)

        # Build context for Claude
        faq_context = ""
        if faq_results:
            faq_context = "Relevant FAQ entries:\n"
            for faq in faq_results:
                faq_context += f"- Q: {faq['question']}\n  A: {faq['answer']}\n"

        # Build system prompt
        system_prompt = f"""
        You are a helpful customer support agent for a software company.
        Your role is to:
        1. Answer common questions using FAQ data when available
        2. Classify issues and suggest ticket creation if needed
        3. Escalate to human agents when appropriate
        4. Maintain a professional and empathetic tone

        Classification of this issue:
        - Category: {classification['category']}
        - Priority: {classification['priority']}
        - Sentiment: {classification['sentiment']}

        {faq_context}

        Guidelines:
        - If the customer needs technical troubleshooting beyond FAQ, offer to create a ticket
        - If sentiment is negative or priority is high/critical, prepare to escalate
        - Always ask clarifying questions if needed
        - Provide clear next steps
        """

        # Add to conversation history
        self.conversation_history.append({
            "role": "user",
            "content": customer_message
        })

        # Generate response using DO Serverless Inference
        try:
            response_data = self.inference_client.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt}
                ] + self.conversation_history,
                max_tokens=1000,
                temperature=0.7
            )

            assistant_message = response_data["content"]

            # Log inference cost
            inference_metadata = {
                "classification": classification,
                "faq_matched": len(faq_results) > 0,
                "model_used": response_data["model"],
                "inference_cost": response_data["cost"],
                "tokens_used": response_data["usage"]["total_tokens"]
            }

        except Exception as e:
            logger.error(f"Inference failed: {str(e)}")
            assistant_message = "I apologize, but I'm having trouble processing your request. Please try again or contact our support team."
            inference_metadata = {
                "error": str(e),
                "classification": classification
            }

        # Log agent response
        self.log_conversation(
            session_id, customer_id, "agent", assistant_message,
            metadata=inference_metadata
        )

        # Add to conversation history
        self.conversation_history.append({
            "role": "assistant",
            "content": assistant_message
        })

        # Check if escalation is needed
        escalation_triggered = False
        if classification['requires_escalation'] or classification['priority'] == 'critical':
            escalation = self.escalate_to_human(
                session_id, customer_id,
                f"Escalated due to {classification['category']} issue with {classification['priority']} priority"
            )
            assistant_message += f"\n\n[System: This has been escalated to our specialist team. Reference ID: {escalation['escalation_id']}]"
            escalation_triggered = True

        return {
            "message": assistant_message,
            "classification": classification,
            "escalation_triggered": escalation_triggered,
            "model_used": response_data.get("model"),
            "cost": response_data.get("cost", 0),
            "metadata": inference_metadata
        }

    def get_usage_summary(self) -> dict:
        """Get inference usage and cost summary."""
        return self.inference_client.get_usage_summary()

    def stream_message(self, session_id: str, customer_id: str,
                      customer_message: str):
        """Stream response for real-time display."""
        # Log customer message
        self.log_conversation(session_id, customer_id, "customer", customer_message)

        # Classify the message
        classification = self.classify_ticket(customer_message)

        # Search FAQ
        faq_results = self.search_faq(customer_message)

        faq_context = ""
        if faq_results:
            faq_context = "Relevant FAQ entries:\n"
            for faq in faq_results:
                faq_context += f"- Q: {faq['question']}\n  A: {faq['answer']}\n"

        system_prompt = f"""
        You are a helpful customer support agent.

        Classification:
        - Category: {classification['category']}
        - Priority: {classification['priority']}

        {faq_context}

        Provide helpful, clear support responses.
        """

        self.conversation_history.append({
            "role": "user",
            "content": customer_message
        })

        # Stream response
        full_response = ""
        for chunk in self.inference_client.stream_completion(
            messages=[
                {"role": "system", "content": system_prompt}
            ] + self.conversation_history,
            max_tokens=1000
        ):
            full_response += chunk
            yield chunk

        # Log complete response
        self.log_conversation(session_id, customer_id, "agent", full_response)
        self.conversation_history.append({
            "role": "assistant",
            "content": full_response
        })


def handle_multi_turn_conversation(session_id: str, customer_id: str,
                                  messages: list, model: str = "claude-3-5-sonnet") -> list:
    """Handle a multi-turn conversation with the enhanced agent."""
    agent = EnhancedCustomerSupportAgent(model=model)
    responses = []

    for message in messages:
        response = agent.process_message(session_id, customer_id, message)
        responses.append({
            "timestamp": datetime.now().isoformat(),
            "response": response
        })

    # Get final usage summary
    usage_summary = agent.get_usage_summary()

    return {
        "session_id": session_id,
        "responses": responses,
        "usage_summary": usage_summary
    }


# Example usage
if __name__ == "__main__":
    import sys

    # Test the enhanced agent
    session_id = "session_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    customer_id = "cust_12345"

    test_messages = [
        "Hi, I'm having trouble logging into my account",
        "I've tried resetting my password but it's not working",
        "This is really frustrating, I need to access this urgently for work"
    ]

    print("Starting enhanced customer support conversation...\n")
    print(f"Using model: {os.getenv('INFERENCE_MODEL', 'claude-3-5-sonnet')}\n")

    try:
        result = handle_multi_turn_conversation(session_id, customer_id, test_messages)

        print(f"Session: {result['session_id']}\n")

        for i, resp in enumerate(result['responses'], 1):
            print(f"Response {i}:")
            print(resp['response']['message'])
            print(f"Cost: ${resp['response']['cost']:.6f}")
            print("-" * 80)

        print("\nUsage Summary:")
        summary = result['usage_summary']
        print(f"Total Requests: {summary['total_requests']}")
        print(f"Total Tokens: {summary['total_tokens']}")
        print(f"Total Cost: ${summary['total_cost_usd']}")
        print(f"Models Used: {', '.join(summary['models_used'])}")

    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
