"""
Enhanced Demo Script for MARS Customer Support Agent with DO Serverless Inference
Shows model selection, cost tracking, and advanced features
"""

import requests
import json
from datetime import datetime
from typing import Optional
import time

# API Base URL
BASE_URL = "http://localhost:5000/api/v2"

def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")

def print_cost(cost: float):
    """Print cost in a nice format."""
    return f"${cost:.6f}"

def demo_health_check():
    """Demo: Health check with service info."""
    print_section("Demo 0: Health Check")

    response = requests.get("http://localhost:5000/health")
    health_data = response.json()

    print(f"Status: {health_data['status']}")
    print(f"Service: {health_data['service']}")
    print(f"Inference: {health_data['inference']}")
    print(f"Version: {health_data['version']}\n")

def demo_list_models():
    """Demo: List available inference models."""
    print_section("Demo 1: Available Inference Models")

    response = requests.get(f"{BASE_URL}/models")
    data = response.json()

    print(f"Available Models: {len(data['available_models'])}\n")

    for model in data['available_models']:
        info = data['model_details'][model]
        print(f"📦 {model}")
        print(f"   Provider: {info['provider']}")
        print(f"   Context Window: {info['context_window']:,} tokens")
        print(f"   {info['description']}\n")

def demo_model_recommendations():
    """Demo: Get model recommendations for different use cases."""
    print_section("Demo 2: Model Recommendations by Use Case")

    use_cases = [
        "customer_support",
        "fast_responses",
        "high_accuracy",
        "cost_effective",
        "lightweight"
    ]

    for use_case in use_cases:
        response = requests.post(
            f"{BASE_URL}/models/recommendation",
            json={"use_case": use_case}
        )
        data = response.json()

        model = data['recommended_model']
        info = data['model_info']

        print(f"Use Case: {use_case.replace('_', ' ').title()}")
        print(f"  → Recommended: {model}")
        print(f"  → {info['description']}\n")

def demo_single_turn_with_cost():
    """Demo: Single message with cost tracking."""
    print_section("Demo 3: Single-Turn Conversation with Cost Tracking")

    model = "claude-3-5-sonnet"

    # Start conversation
    start_response = requests.post(f"{BASE_URL}/conversations/start", json={
        "customer_id": "demo_cust_001",
        "email": "customer@example.com",
        "model": model
    })

    session_data = start_response.json()
    session_id = session_data['session_id']
    print(f"✓ Conversation started: {session_id}")
    print(f"  Model: {model}\n")

    # Send a message
    message = "I'm having trouble logging into my account"
    print(f"Customer: {message}\n")

    response = requests.post(
        f"{BASE_URL}/conversations/{session_id}/message",
        json={
            "customer_id": "demo_cust_001",
            "message": message,
            "model": model
        }
    )

    msg_data = response.json()
    print(f"Agent: {msg_data['response']}\n")
    print(f"Model Used: {msg_data['model_used']}")
    print(f"Inference Cost: {print_cost(msg_data['cost_usd'])}")
    print(f"Classification: {json.dumps(msg_data['classification'], indent=2)}\n")

    # Get session usage
    usage_response = requests.get(f"{BASE_URL}/conversations/{session_id}/usage")
    usage_data = usage_response.json()

    print(f"Session Summary:")
    print(f"  Total Cost: {print_cost(usage_data['total_cost_usd'])}")
    print(f"  Total Tokens: {usage_data['total_tokens']}")
    print(f"  Inference Requests: {usage_data['inference_requests']}\n")

    return session_id

def demo_multi_turn_comparison():
    """Demo: Compare costs across different models."""
    print_section("Demo 4: Model Cost Comparison - Multi-turn Conversation")

    customer_messages = [
        "I'm having a billing issue",
        "I see a charge I don't recognize",
        "Can you help me understand this?"
    ]

    models_to_compare = ["claude-3-5-sonnet", "gpt-4o-mini", "claude-3-5-haiku"]
    results = {}

    for model in models_to_compare:
        print(f"Testing with {model}...")

        response = requests.post(f"{BASE_URL}/conversations/batch", json={
            "customer_id": f"demo_cust_compare_{model}",
            "messages": customer_messages,
            "model": model
        })

        data = response.json()
        session_id = data['session_id']

        # Get usage details
        usage_response = requests.get(f"{BASE_URL}/conversations/{session_id}/usage")
        usage_data = usage_response.json()

        results[model] = {
            "session_id": session_id,
            "cost": usage_data['total_cost_usd'],
            "tokens": usage_data['total_tokens'],
            "avg_cost_per_request": usage_data['average_cost_per_request']
        }

    # Display comparison
    print("\n" + "-"*70)
    print(f"{'Model':<25} {'Total Cost':<15} {'Avg/Request':<15} {'Tokens':<10}")
    print("-"*70)

    for model, data in results.items():
        print(f"{model:<25} {print_cost(data['cost']):<15} {print_cost(data['avg_cost_per_request']):<15} {data['tokens']:<10}")

    cheapest_model = min(results.items(), key=lambda x: x[1]['cost'])
    print(f"\n💰 Cheapest Option: {cheapest_model[0]} at {print_cost(cheapest_model[1]['cost'])}\n")

def demo_escalation_scenario():
    """Demo: Escalation with cost tracking."""
    print_section("Demo 5: Escalation Scenario with Analytics")

    response = requests.post(f"{BASE_URL}/conversations/batch", json={
        "customer_id": "demo_cust_005",
        "messages": [
            "I can't access my account for the past 3 days",
            "I've tried everything and nothing works",
            "I need this fixed immediately, my business is affected!"
        ],
        "model": "claude-3-5-sonnet"
    })

    data = response.json()
    session_id = data['session_id']

    print(f"Session: {session_id}\n")

    for i, resp in enumerate(data['responses'], 1):
        model_used = resp['response'].get('model_used', 'unknown')
        cost = resp['response'].get('cost', 0)
        escalated = resp['response'].get('escalation_triggered', False)

        print(f"Turn {i}:")
        print(f"  Message length: {len(resp['response']['message'])} chars")
        print(f"  Cost: {print_cost(cost)}")
        print(f"  Model: {model_used}")
        print(f"  Escalation: {'✓ YES' if escalated else '✗ No'}\n")

    # Get usage summary
    usage = data['usage_summary']
    print(f"Session Summary:")
    print(f"  Total Cost: {print_cost(usage['total_cost_usd'])}")
    print(f"  Total Tokens: {usage['total_tokens']}")
    print(f"  Average Cost/Request: {print_cost(usage['average_cost_per_request'])}\n")

def demo_analytics():
    """Demo: System-wide analytics."""
    print_section("Demo 6: System Analytics Dashboard")

    response = requests.get(f"{BASE_URL}/analytics/summary")
    data = response.json()

    print("📊 Conversation Metrics:")
    conv = data['conversations']
    print(f"  Total Sessions: {conv['total_sessions']}")
    print(f"  Total Messages: {conv['total_messages']}")
    print(f"  Unique Customers: {conv['unique_customers']}\n")

    print("🎫 Ticket Metrics:")
    tickets = data['tickets']
    print(f"  Total Tickets: {tickets['total_tickets']}")
    print(f"  Open Tickets: {tickets['open_tickets']}")
    print(f"  Resolved Tickets: {tickets['resolved_tickets']}\n")

    print("⬆️  Escalation Metrics:")
    escalations = data['escalations']
    print(f"  Total Escalations: {escalations['total_escalations']}")
    print(f"  Pending Escalations: {escalations['pending_escalations']}\n")

def main():
    """Run all enhanced demos."""
    print("\n" + "="*70)
    print("  MARS Customer Support Agent - Enhanced with DO Serverless Inference")
    print("  Demo Suite v2.0")
    print("="*70)
    print("\nNote: Make sure the enhanced API server is running on port 5000")
    print("Run: python api_server_enhanced.py")

    try:
        # Run demos in sequence
        demo_health_check()
        time.sleep(1)

        demo_list_models()
        time.sleep(1)

        demo_model_recommendations()
        time.sleep(1)

        demo_single_turn_with_cost()
        time.sleep(1)

        demo_multi_turn_comparison()
        time.sleep(1)

        demo_escalation_scenario()
        time.sleep(1)

        demo_analytics()

        print("\n" + "="*70)
        print("  ✓ All enhanced demos completed successfully!")
        print("="*70 + "\n")

    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Cannot connect to API server")
        print("Make sure the server is running: python api_server_enhanced.py\n")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}\n")

if __name__ == "__main__":
    main()
