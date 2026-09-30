"""
Demo script for MARS Customer Support Agent
Shows various usage patterns and conversation flows
"""

import requests
import json
from datetime import datetime

# API Base URL (adjust if running locally on different port)
BASE_URL = "http://localhost:5000/api/v1"

def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def demo_single_turn_conversation():
    """Demo: Single message customer support conversation."""
    print_section("Demo 1: Single-Turn Conversation")

    # Start conversation
    start_response = requests.post(f"{BASE_URL}/conversations/start", json={
        "customer_id": "demo_cust_001",
        "email": "customer@example.com",
        "name": "Demo Customer"
    })

    session_data = start_response.json()
    session_id = session_data['session_id']
    print(f"✓ Conversation started: {session_id}\n")

    # Send a message
    message = "I'm having trouble logging into my account"
    print(f"Customer: {message}")

    response = requests.post(
        f"{BASE_URL}/conversations/{session_id}/message",
        json={
            "customer_id": "demo_cust_001",
            "message": message
        }
    )

    agent_response = response.json()
    print(f"\nAgent: {agent_response['response']}\n")

    return session_id

def demo_multi_turn_conversation():
    """Demo: Multi-turn conversation with escalation."""
    print_section("Demo 2: Multi-Turn Conversation with Escalation")

    customer_messages = [
        "Hi, I have a billing question",
        "I see a charge on my account that I don't recognize",
        "I definitely didn't authorize this charge. This is really frustrating!"
    ]

    # Process batch conversation
    response = requests.post(f"{BASE_URL}/conversations/batch", json={
        "customer_id": "demo_cust_002",
        "messages": customer_messages
    })

    batch_data = response.json()
    session_id = batch_data['session_id']

    print(f"Session: {session_id}")
    print(f"Processed {batch_data['total_messages']} messages\n")

    for i, (customer_msg, agent_resp) in enumerate(
        zip(customer_messages, batch_data['responses']), 1
    ):
        print(f"Turn {i}:")
        print(f"  Customer: {customer_msg}")
        print(f"  Agent: {agent_resp['response'][:200]}...\n")

    return session_id

def demo_faq_handling():
    """Demo: FAQ-based responses."""
    print_section("Demo 3: FAQ-Based Response")

    faq_questions = [
        "How do I reset my password?",
        "Can I cancel my subscription?",
        "What payment methods do you accept?"
    ]

    for question in faq_questions:
        print(f"Customer: {question}")

        response = requests.post(
            f"{BASE_URL}/conversations/batch",
            json={
                "customer_id": "demo_cust_003",
                "messages": [question]
            }
        )

        data = response.json()
        agent_response = data['responses'][0]['response']
        print(f"Agent: {agent_response[:250]}...\n")

def demo_conversation_history():
    """Demo: Retrieve conversation history."""
    print_section("Demo 4: Conversation History")

    # Start and send messages
    start_response = requests.post(f"{BASE_URL}/conversations/start", json={
        "customer_id": "demo_cust_004",
        "email": "customer@example.com"
    })
    session_id = start_response.json()['session_id']

    # Send multiple messages
    messages = [
        "How much does your service cost?",
        "Do you have a free trial?"
    ]

    for msg in messages:
        requests.post(
            f"{BASE_URL}/conversations/{session_id}/message",
            json={
                "customer_id": "demo_cust_004",
                "message": msg
            }
        )

    # Get history
    history_response = requests.get(f"{BASE_URL}/conversations/{session_id}/history")
    history_data = history_response.json()

    print(f"Conversation: {session_id}")
    print(f"Total messages: {history_data['message_count']}\n")

    for msg in history_data['messages']:
        role = "Customer" if msg['role'] == 'customer' else "Agent"
        print(f"{role}: {msg['message'][:100]}...")
        print(f"Time: {msg['created_at']}\n")

def demo_escalation():
    """Demo: Escalation to human agent."""
    print_section("Demo 5: Escalation Scenario")

    response = requests.post(f"{BASE_URL}/conversations/batch", json={
        "customer_id": "demo_cust_005",
        "messages": [
            "I can't access my account for the past 3 days",
            "I've tried everything and nothing works",
            "I need this fixed immediately, my business is affected!"
        ]
    })

    data = response.json()
    session_id = data['session_id']

    print(f"Session: {session_id}")
    print("Multi-turn conversation processed.")
    print("Expected: Escalation triggered due to urgency and critical priority\n")

    # Check if ticket was created
    ticket_response = requests.get(f"{BASE_URL}/conversations/{session_id}/ticket")
    ticket_data = ticket_response.json()

    if ticket_data['ticket']:
        print(f"✓ Ticket Created:")
        print(f"  Ticket #: {ticket_data['ticket']['ticket_number']}")
        print(f"  Priority: {ticket_data['ticket']['priority']}")
        print(f"  Status: {ticket_data['ticket']['status']}\n")
    else:
        print("No escalation ticket created in this session\n")

def demo_health_check():
    """Demo: Health check endpoint."""
    print_section("Demo 0: Health Check")

    response = requests.get("http://localhost:5000/health")
    health_data = response.json()

    print(f"Status: {health_data['status']}")
    print(f"Service: {health_data['service']}")
    print(f"Timestamp: {health_data['timestamp']}\n")

def demo_performance():
    """Demo: Performance and load simulation."""
    print_section("Demo 6: Performance Test")

    import time

    num_conversations = 5
    start_time = time.time()

    for i in range(num_conversations):
        customer_id = f"perf_cust_{i:03d}"

        # Start conversation
        requests.post(f"{BASE_URL}/conversations/start", json={
            "customer_id": customer_id,
            "email": f"customer{i}@example.com"
        })

        print(f"✓ Conversation {i+1}/{num_conversations} started")

    elapsed = time.time() - start_time
    rate = num_conversations / elapsed

    print(f"\nPerformance Results:")
    print(f"  Conversations: {num_conversations}")
    print(f"  Time: {elapsed:.2f}s")
    print(f"  Rate: {rate:.1f} conversations/sec\n")

def main():
    """Run all demos."""
    print("\n" + "="*60)
    print("  MARS Customer Support Agent - Demo Suite")
    print("="*60)
    print("\nNote: Make sure the API server is running on port 5000")
    print("Run: python api_server.py")

    try:
        # Health check first
        demo_health_check()

        # Run demos
        demo_single_turn_conversation()
        demo_faq_handling()
        demo_multi_turn_conversation()
        demo_conversation_history()
        demo_escalation()
        demo_performance()

        print("\n" + "="*60)
        print("  All demos completed successfully!")
        print("="*60 + "\n")

    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Cannot connect to API server")
        print("Make sure the server is running: python api_server.py\n")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}\n")

if __name__ == "__main__":
    main()
