#!/usr/bin/env python3
"""
MARS Agent Handler
Entry point for processing messages through the MARS agent
Called as a subprocess from Node.js server
"""

import sys
import json
import logging
from mars_agent import create_mars_agent

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """
    Main entry point for MARS agent handler
    Arguments: session_id customer_id message
    """
    if len(sys.argv) < 4:
        print(json.dumps({
            "error": "Missing required arguments",
            "usage": "python mars_agent_handler.py <session_id> <customer_id> <message>"
        }))
        sys.exit(1)

    session_id = sys.argv[1]
    customer_id = sys.argv[2]
    message = sys.argv[3]

    try:
        # Create agent
        agent = create_mars_agent()

        # Process message
        result = agent.process_message(session_id, customer_id, message)

        # Output as JSON to stdout
        print(json.dumps(result))
        sys.exit(0)

    except Exception as e:
        logger.error(f"Error processing message: {str(e)}", exc_info=True)
        print(json.dumps({
            "error": str(e),
            "response": "I apologize, but I encountered an error. Please try again."
        }))
        sys.exit(1)

if __name__ == "__main__":
    main()
