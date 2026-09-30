"""
MARS Customer Support Automation Agent
Multi-turn agent for ticket triage, FAQ responses, and escalation

This agent handles customer support conversations with the following capabilities:
- Multi-turn conversation management
- Automatic ticket triage and classification
- FAQ-based response generation
- Escalation to human agents with context
- Conversation history in PostgreSQL
"""

import json
import os
from datetime import datetime
from typing import Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import anthropic

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

class CustomerSupportAgent:
    """Customer support automation agent with MARS integration."""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "claude-3-5-sonnet-20241022"
        self.conversation_history = []

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
        """Use Claude to classify the customer's issue."""
        classification_prompt = f"""
        Analyze this customer support message and provide:
        1. Category (billing, technical, account, feature_request, other)
        2. Priority (low, medium, high, critical)
        3. Sentiment (positive, neutral, negative)
        4. Requires_escalation (yes/no)

        Customer message: {customer_message}

        Respond in JSON format only.
        """

        response = self.client.messages.create(
            model=self.model,
            max_tokens=500,
            messages=[{"role": "user", "content": classification_prompt}]
        )

        try:
            return json.loads(response.content[0].text)
        except json.JSONDecodeError:
            return {
                "category": "other",
                "priority": "medium",
                "sentiment": "neutral",
                "requires_escalation": False
            }

    def process_message(self, session_id: str, customer_id: str,
                       customer_message: str) -> str:
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

        # Generate response
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1000,
            system=system_prompt,
            messages=self.conversation_history
        )

        assistant_message = response.content[0].text

        # Log agent response
        self.log_conversation(
            session_id, customer_id, "agent", assistant_message,
            metadata={
                "classification": classification,
                "faq_matched": len(faq_results) > 0,
                "tokens_used": response.usage.input_tokens + response.usage.output_tokens
            }
        )

        # Add to conversation history
        self.conversation_history.append({
            "role": "assistant",
            "content": assistant_message
        })

        # Check if escalation is needed
        if classification['requires_escalation'] or classification['priority'] == 'critical':
            escalation = self.escalate_to_human(
                session_id, customer_id,
                f"Escalated due to {classification['category']} issue with {classification['priority']} priority"
            )
            assistant_message += f"\n\n[System: This has been escalated to our specialist team. Reference ID: {escalation['escalation_id']}]"

        return assistant_message


def handle_multi_turn_conversation(session_id: str, customer_id: str, messages: list) -> list:
    """Handle a multi-turn conversation with the agent."""
    agent = CustomerSupportAgent()
    responses = []

    for message in messages:
        response = agent.process_message(session_id, customer_id, message)
        responses.append({
            "timestamp": datetime.now().isoformat(),
            "response": response
        })

    return responses


# Example usage and testing
if __name__ == "__main__":
    # Test the agent with sample conversation
    session_id = "session_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    customer_id = "cust_12345"

    test_messages = [
        "Hi, I'm having trouble logging into my account",
        "I've tried resetting my password but it's not working",
        "This is really frustrating, I need to access this urgently for work"
    ]

    print("Starting customer support conversation...\n")
    responses = handle_multi_turn_conversation(session_id, customer_id, test_messages)

    for i, resp in enumerate(responses, 1):
        print(f"Response {i}:")
        print(resp['response'])
        print("-" * 80)
