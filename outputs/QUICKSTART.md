# Quick Start Guide - MARS Customer Support Agent

Get the demo running in 5 minutes!

## Option 1: Using Docker Compose (Easiest)

### Prerequisites
- Docker and Docker Compose installed
- Anthropic API key

### Steps

1. **Clone/Download the files**
   ```bash
   cd mars-customer-support-demo
   ```

2. **Set your API key**
   ```bash
   export OPENAI_API_KEY="your_anthropic_api_key"
   ```

3. **Start the services**
   ```bash
   docker-compose up
   ```

4. **Wait for startup** (about 10-15 seconds)
   ```
   api_1       | * Running on http://0.0.0.0:5000
   ```

5. **Run the demo in another terminal**
   ```bash
   python demo.py
   ```

## Option 2: Local Development Setup

### Prerequisites
- Python 3.9+
- PostgreSQL 14+ running locally
- Anthropic API key

### Steps

1. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Setup environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and fill in:
   # - OPENAI_API_KEY=your_key
   # - DB_PASSWORD=your_db_password
   # - DB_HOST=localhost (or your DB host)
   ```

4. **Create database**
   ```bash
   createdb -U postgres support_db
   psql -U postgres -d support_db -f schema.sql
   ```

5. **Start API server**
   ```bash
   python api_server.py
   ```
   You should see:
   ```
   * Running on http://127.0.0.1:5000
   ```

6. **In a new terminal, run the demo**
   ```bash
   source venv/bin/activate
   python demo.py
   ```

## Testing the API Manually

### Start a conversation
```bash
curl -X POST http://localhost:5000/api/v1/conversations/start \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "test_001",
    "email": "test@example.com",
    "name": "Test User"
  }'
```

### Send a message
```bash
curl -X POST http://localhost:5000/api/v1/conversations/{session_id}/message \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "test_001",
    "message": "How do I reset my password?"
  }'
```

### Get conversation history
```bash
curl http://localhost:5000/api/v1/conversations/{session_id}/history
```

## What Each Demo Shows

**Demo 1: Single-Turn Conversation**
- Basic customer question
- Agent response using FAQ data

**Demo 2: Multi-Turn Conversation**
- Multiple back-and-forth messages
- Escalation handling
- Context persistence

**Demo 3: FAQ Handling**
- How the agent uses the knowledge base
- Quick responses to common questions

**Demo 4: Conversation History**
- Retrieving stored conversations
- Full audit trail of interactions

**Demo 5: Escalation Scenario**
- Critical issue handling
- Ticket creation
- Human agent handoff

**Demo 6: Performance Test**
- Multiple concurrent conversations
- Response time measurement

## Example Conversation

```
Customer: I'm having trouble logging into my account

Agent: I understand you're having trouble logging in. Let me help you with that.

Have you tried resetting your password? Here's how:

1. Click "Forgot Password" on the login page
2. Enter your email address
3. Check your email for a reset link
4. Click the link and create a new password

If you don't receive an email, check your spam folder.

Let me know if this helps!
```

## Database Schema Overview

The system uses 6 tables:

- **conversations** - All customer-agent messages
- **tickets** - Support tickets created during conversations
- **faq** - Knowledge base articles
- **escalations** - Escalations to human agents
- **customers** - Customer information
- **agent_sessions** - Session metadata

All conversations and tickets are automatically logged to PostgreSQL for compliance and analytics.

## Environment Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `OPENAI_API_KEY` | Anthropic API key | `sk-ant-...` |
| `DB_HOST` | Database host | `localhost` |
| `DB_PORT` | Database port | `5432` |
| `DB_NAME` | Database name | `support_db` |
| `DB_USER` | Database user | `postgres` |
| `DB_PASSWORD` | Database password | `****` |
| `FLASK_ENV` | Environment | `development` |
| `PORT` | API port | `5000` |

## Troubleshooting

### "Connection refused" error
- Make sure PostgreSQL is running
- Check DB_HOST and DB_PORT in .env

### "API key not set" error
- Set OPENAI_API_KEY environment variable
- Verify your API key is valid

### "Database does not exist"
- Run: `createdb -U postgres support_db`
- Run: `psql -U postgres -d support_db -f schema.sql`

### Docker compose fails to start
- Ensure Docker is running
- Check port 5000 and 5432 are available
- Run: `docker-compose logs api`

## Next Steps

1. **Explore the code**
   - `agent.py` - Main agent logic
   - `api_server.py` - Flask API endpoints
   - `schema.sql` - Database schema

2. **Customize for your use case**
   - Add more FAQ entries to `schema.sql`
   - Modify agent prompts in `agent.py`
   - Add Slack/Jira integrations

3. **Deploy to DigitalOcean**
   - See README.md for MARS deployment steps
   - Use `app.yaml` configuration

4. **Monitor in production**
   - Track conversation metrics
   - Monitor escalation rates
   - Analyze customer sentiment

## Getting Help

- Check the full README.md for detailed documentation
- Review demo.py for usage examples
- Check API endpoints in README.md

Enjoy the demo! 🚀
