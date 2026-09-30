"""
MARS Customer Support Agent
Integrates with DigitalOcean Serverless Inference for intelligent customer support
Uses MARS for agent orchestration and state management
"""

import json
import logging
import os
from datetime import datetime
from typing import Optional, Dict, List, Any
import psycopg2
from psycopg2.extras import RealDictCursor
from serverless_inference import get_inference_client

logger = logging.getLogger(__name__)

class MARSCustomerSupportAgent:
    """
    Customer support agent running on DigitalOcean MARS
    Leverages Serverless Inference for AI-powered responses
    """

    def __init__(self):
        """Initialize the MARS agent."""
        self.inference_client = get_inference_client()
        self.db_config = {
            "dbname": os.getenv("DB_NAME", "support_db"),
            "user": os.getenv("DB_USER", "postgres"),
            "password": os.getenv("DB_PASSWORD"),
            "host": os.getenv("DB_HOST", "localhost"),
            "port": os.getenv("DB_PORT", "5432")
        }

    def get_db_connection(self):
        """Get a PostgreSQL connection."""
        return psycopg2.connect(**self.db_config)

    def search_faq(self, query: str, limit: int = 5) -> List[Dict]:
        """Search FAQ database for relevant answers."""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute("""
                SELECT id, question, answer, category, priority
                FROM faq
                WHERE to_tsvector('english', question || ' ' || answer)
                      @@ plainto_tsquery('english', %s)
                ORDER BY priority DESC
                LIMIT %s
            """, (query, limit))

            results = cursor.fetchall()
            cursor.close()
            conn.close()

            return [dict(r) for r in results] if results else []

        except Exception as e:
            logger.error(f"Error searching FAQ: {str(e)}")
            return []

    def classify_issue(self, message: str) -> Dict[str, Any]:
        """Classify the customer issue using Serverless Inference."""
        try:
            return self.inference_client.classify_message(message)
        except Exception as e:
            logger.error(f"Error classifying issue: {str(e)}")
            return {
                "category": "other",
                "priority": "medium",
                "sentiment": "neutral",
                "requires_escalation": False,
                "keywords": []
            }

    def create_ticket(self, session_id: str, customer_id: str,
                     subject: str, description: str,
                     classification: Dict) -> Dict:
        """Create a support ticket."""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute("""
                INSERT INTO tickets
                (customer_id, subject, description, category, priority, status, created_at)
                VALUES (%s, %s, %s, %s, %s, 'open', NOW())
                RETURNING id, ticket_number
            """, (
                customer_id,
                subject,
                description,
                classification.get('category', 'other'),
                classification.get('priority', 'medium')
            ))

            result = cursor.fetchone()
            conn.commit()
            cursor.close()
            conn.close()

            return {
                "ticket_id": result['id'],
                "ticket_number": result['ticket_number'],
                "status": "created"
            }

        except Exception as e:
            logger.error(f"Error creating ticket: {str(e)}")
            return {"status": "error", "message": str(e)}

    def log_conversation(self, session_id: str, customer_id: str,
                        role: str, message: str, metadata: Optional[Dict] = None):
        """Log conversation message to database."""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO conversations
                (session_id, customer_id, role, message, metadata, created_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
            """, (
                session_id,
                customer_id,
                role,
                message,
                json.dumps(metadata) if metadata else None
            ))

            conn.commit()
            cursor.close()
            conn.close()

        except Exception as e:
            logger.error(f"Error logging conversation: {str(e)}")

    def get_conversation_context(self, session_id: str, limit: int = 10) -> List[Dict]:
        """Get conversation history for context."""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute("""
                SELECT role, message, created_at
                FROM conversations
                WHERE session_id = %s
                ORDER BY created_at ASC
                LIMIT %s
            """, (session_id, limit))

            results = cursor.fetchall()
            cursor.close()
            conn.close()

            return [dict(r) for r in results] if results else []

        except Exception as e:
            logger.error(f"Error getting conversation context: {str(e)}")
            return []

    def escalate_to_human(self, session_id: str, customer_id: str,
                         reason: str, ticket_id: Optional[int] = None) -> Dict:
        """Escalate to human agent with full context."""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Get conversation history for summary
            context = self.get_conversation_context(session_id, limit=20)

            # Generate summary
            try:
                summary = self.inference_client.summarize_conversation(context)
            except:
                summary = "Unable to generate summary"

            # Create escalation record
            cursor.execute("""
                INSERT INTO escalations
                (session_id, customer_id, ticket_id, reason, status, context, created_at)
                VALUES (%s, %s, %s, %s, 'pending', %s, NOW())
                RETURNING id
            """, (
                session_id,
                customer_id,
                ticket_id,
                reason,
                json.dumps({
                    "messages": context,
                    "summary": summary,
                    "escalation_time": datetime.now().isoformat()
                })
            ))

            result = cursor.fetchone()
            conn.commit()
            cursor.close()
            conn.close()

            logger.info(f"Escalation created: {result['id']} for session {session_id}")

            return {
                "escalation_id": result['id'],
                "status": "escalated",
                "summary": summary,
                "assigned_to": "human_queue"
            }

        except Exception as e:
            logger.error(f"Error escalating: {str(e)}")
            return {"status": "error", "message": str(e)}

    def process_message(self, session_id: str, customer_id: str,
                       message: str) -> Dict:
        """
        Main entry point for processing a customer message.
        Returns agent response and any actions taken.
        """
        logger.info(f"Processing message for session {session_id}: {message[:50]}...")

        # Log customer message
        self.log_conversation(session_id, customer_id, "customer", message)

        # Classify the issue
        classification = self.classify_issue(message)
        logger.debug(f"Classification: {classification}")

        # Search FAQ
        faq_results = self.search_faq(message)
        faq_context = ""
        if faq_results:
            faq_context = "\n\nRelevant FAQ entries:\n"
            for faq in faq_results:
                faq_context += f"- **Q:** {faq['question']}\n"
                faq_context += f"  **A:** {faq['answer']}\n"

        # Get conversation context
        context = self.get_conversation_context(session_id)

        # Generate response using Serverless Inference
        try:
            agent_response = self.inference_client.generate_response(
                message,
                context,
                faq_results
            )
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            agent_response = "I apologize for the delay. Let me connect you with a specialist who can better assist you."

        # Add FAQ context to response if relevant
        if faq_results:
            agent_response += faq_context

        # Log agent response
        self.log_conversation(
            session_id,
            customer_id,
            "agent",
            agent_response,
            metadata={
                "classification": classification,
                "faq_matched": len(faq_results) > 0,
                "faq_count": len(faq_results)
            }
        )

        # Check if escalation is needed
        escalation_result = None
        ticket_result = None
        should_escalate = (
            classification.get('requires_escalation', False) or
            classification.get('priority') == 'critical' or
            classification.get('sentiment') == 'negative'
        )

        if should_escalate:
            logger.info(f"Escalation triggered for session {session_id}")

            # Create ticket first
            ticket_result = self.create_ticket(
                session_id,
                customer_id,
                "Support Request: " + message[:50],
                message,
                classification
            )

            # Escalate to human
            escalation_result = self.escalate_to_human(
                session_id,
                customer_id,
                f"Escalated due to {classification['category']} issue with {classification['priority']} priority",
                ticket_result.get('ticket_id') if ticket_result.get('status') == 'created' else None
            )

            if escalation_result.get('status') == 'escalated':
                agent_response += f"\n\n**[System Notice]** I've escalated your issue to our specialist team. Your reference ID is **{escalation_result['escalation_id']}**. Someone will contact you shortly."

        return {
            "response": agent_response,
            "classification": classification,
            "faq_matched": len(faq_results) > 0,
            "ticket": ticket_result,
            "escalation": escalation_result,
            "timestamp": datetime.now().isoformat()
        }


def create_mars_agent() -> MARSCustomerSupportAgent:
    """Factory function to create a MARS agent instance."""
    return MARSCustomerSupportAgent()
