# MARS Customer Support Portal
## Full-Stack Deployment with Serverless Inference & MARS

A production-ready support portal that integrates DigitalOcean's **MARS** (Managed Agents Runtime Services) with **Serverless Inference Endpoint** for intelligent customer support automation.

## 🎯 Features

✅ **Beautiful Support Portal UI** - Professional chat interface  
✅ **MARS Integration** - Managed agent orchestration  
✅ **Serverless Inference** - AI-powered responses via DigitalOcean  
✅ **Multi-turn Conversations** - Full conversation context  
✅ **Automatic Ticket Creation** - Smart ticket triage  
✅ **FAQ Integration** - Knowledge base responses  
✅ **Escalation Management** - Human handoff with context  
✅ **Conversation History** - Complete audit trail  
✅ **Analytics Dashboard** - Real-time metrics  
✅ **PostgreSQL Backend** - Persistent storage  

## 📋 Architecture

```
┌─────────────────────────────────────────────────────────┐
│           Support Portal (React/HTML)                   │
│  - Live chat interface                                  │
│  - Conversation management                              │
│  - Ticket tracking                                      │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────┴──────────────────────────────────────┐
│         Node.js/Express API Server                      │
│  - REST endpoints                                       │
│  - CORS handling                                        │
│  - Request routing                                      │
└──────────────────┬──────────────────────────────────────┘
                   │
        ┌──────────┴──────────┬────────────────┐
        │                     │                │
    ┌───▼────┐          ┌────▼──┐      ┌─────▼──────┐
    │  MARS  │          │Python │      │ PostgreSQL │
    │ Agent  │          │Agent  │      │ Database   │
    └───┬────┘          └────┬──┘      └────────────┘
        │                    │
    ┌───▼────────────────────▼────────────┐
    │ Serverless Inference Endpoint       │
    │ (DigitalOcean)                      │
    │ - Claude 3.5 Sonnet                 │
    │ - Message classification            │
    │ - Response generation               │
    │ - Conversation summary              │
    └────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- **Docker & Docker Compose** (easiest)
- **Node.js 18+** (for local development)
- **Python 3.9+** (for agent)
- **PostgreSQL 14+** (for local dev)
- **DigitalOcean Account** (for Serverless Inference)

### Option 1: Docker Compose (Recommended)

1. **Set up environment**
   ```bash
   cd mars-support-portal
   cp .env.portal.example .env
   # Edit .env and add your MODEL_ACCESS_KEY
   ```

2. **Start services**
   ```bash
   docker-compose -f docker-compose-portal.yml up -d
   ```

3. **Wait for startup** (15-30 seconds)
   ```bash
   docker-compose -f docker-compose-portal.yml logs -f
   ```

4. **Access the portal**
   - Portal UI: http://localhost:3000
   - API: http://localhost:3000/api/v1
   - Database: localhost:5432

### Option 2: Local Development Setup

1. **Setup Python environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements-portal.txt
   ```

2. **Setup Node.js**
   ```bash
   npm install
   ```

3. **Create database**
   ```bash
   createdb -U postgres support_db
   psql -U postgres -d support_db -f schema_portal.sql
   ```

4. **Configure environment**
   ```bash
   cp .env.portal.example .env
   # Edit .env with your settings
   ```

5. **Start services**
   ```bash
   # Terminal 1: Node API
   npm start

   # Terminal 2: Portal (open in browser)
   open http://localhost:3000
   ```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `MODEL_ACCESS_KEY` | DigitalOcean Inference API key | `dop_v1_...` |
| `SERVERLESS_INFERENCE_URL` | Inference endpoint URL | `https://inference.do-ai.run` |
| `INFERENCE_MODEL` | Model to use | `claude-3-5-sonnet-20241022` |
| `DB_HOST` | PostgreSQL host | `localhost` |
| `DB_PASSWORD` | Database password | `secure_password` |
| `PORT` | API port | `3000` |

### Getting DigitalOcean API Key

1. Log in to DigitalOcean Control Panel
2. Navigate to **Inference** > **Serverless Inference**
3. Create or copy your **Model Access Key**
4. Add to `.env` as `MODEL_ACCESS_KEY`

## 📱 Using the Portal

### Starting a Conversation

1. Click **"New Conversation"** in the sidebar
2. Type your question or issue
3. Press **Send** or **Shift+Enter**

### Portal Features

- **Real-time chat** with AI agent
- **Automatic ticket creation** for complex issues
- **Escalation tracking** with reference IDs
- **Conversation history** for reference
- **FAQ suggestions** for quick answers
- **Priority indicators** for urgent issues

### Example Conversations

**Example 1: FAQ Response**
```
Customer: How do I reset my password?
Agent: [Provides FAQ-based answer]
Result: No ticket created, resolved in 1 turn
```

**Example 2: Technical Issue with Escalation**
```
Customer: I can't access my account for 3 days
Agent: [Troubleshoots the issue]
Customer: I've tried everything, this is critical!
Agent: [Creates ticket, escalates to human]
Result: Ticket TK-2026-001, assigned to specialist
```

## 🔌 API Endpoints

### Conversations
```bash
# Get all conversations
GET /api/v1/conversations

# Get conversation messages
GET /api/v1/conversations/{sessionId}/messages

# Send message
POST /api/v1/conversations/{sessionId}/message
{
  "customer_id": "cust_123",
  "message": "My question here"
}

# Get associated ticket
GET /api/v1/conversations/{sessionId}/ticket
```

### Knowledge Base
```bash
# Search FAQ
GET /api/v1/faq?search=password
```

### Analytics
```bash
# Get conversation analytics (24h)
GET /api/v1/analytics/conversations
```

### System
```bash
# Health check
GET /health

# Agent status
GET /api/v1/agent/status
```

## 💬 How It Works

### Message Processing Flow

```
1. Customer sends message
   ↓
2. API receives request
   ↓
3. MARS Agent processes:
   - Classifies (category, priority, sentiment)
   - Searches FAQ
   - Gets conversation context
   ↓
4. Serverless Inference generates response
   - Calls Claude via DigitalOcean
   - Includes FAQ context if relevant
   ↓
5. Agent evaluates escalation triggers:
   - Critical priority?
   - Negative sentiment?
   - FAQ didn't help?
   ↓
6. Response sent to customer
   - Logs to PostgreSQL
   - Creates ticket if needed
   - Escalates if required
```

### Classification Logic

The agent classifies each message:

```python
{
    "category": "billing|technical|account|feature_request|other",
    "priority": "low|medium|high|critical",
    "sentiment": "positive|neutral|negative",
    "requires_escalation": True/False,
    "keywords": ["keyword1", "keyword2"]
}
```

**Escalation Triggers:**
- Priority = critical
- Requires escalation = true
- Negative sentiment + high priority
- Multiple support attempts

## 📊 Database Schema

### Core Tables

**conversations** - All customer-agent messages
- session_id, customer_id, role, message, metadata

**tickets** - Support tickets
- ticket_number, customer_id, subject, category, priority, status

**faq** - Knowledge base
- question, answer, category, priority, tags

**escalations** - Escalations to humans
- session_id, customer_id, ticket_id, reason, status, context

**customers** - Customer information
- customer_id, email, name, company, tier

**portal_users** - Support staff
- user_id, email, name, role, status

### Views

- **conversation_summary** - Aggregated conversation data
- **ticket_stats** - Ticket metrics by category/priority

## 🚢 Deployment to DigitalOcean

### Using MARS (Recommended)

1. **Push to GitHub**
   ```bash
   git push origin main
   ```

2. **Create DigitalOcean App**
   ```bash
   doctl apps create --spec app-mars.yaml
   ```

3. **Configure MARS Agent**
   - Set environment variables
   - Link to Serverless Inference
   - Configure database

### app-mars.yaml Example

```yaml
name: mars-support-portal
services:
  - name: api
    github:
      repo: your-org/mars-support-portal
      branch: main
    http_port: 3000
    envs:
      - key: MODEL_ACCESS_KEY
        scope: RUN_AND_BUILD_TIME
        value: ${MODEL_ACCESS_KEY}
```

## 📈 Monitoring & Analytics

### Real-time Metrics

```bash
# Get 24h conversation stats
curl http://localhost:3000/api/v1/analytics/conversations
```

Returns:
```json
{
  "total_conversations": 42,
  "total_messages": 184,
  "customer_messages": 92,
  "agent_messages": 92,
  "avg_response_time": 2.3
}
```

### Key Metrics to Track

- **Conversation volume** - Messages/hour
- **Average resolution time** - Time to close ticket
- **Escalation rate** - % requiring human intervention
- **FAQ hit rate** - % resolved via FAQ
- **Customer satisfaction** - Sentiment analysis
- **Agent workload** - Messages per agent

## 🛠️ Troubleshooting

### Issue: "Cannot connect to Inference API"

**Solution:**
```bash
# Check MODEL_ACCESS_KEY is set
echo $MODEL_ACCESS_KEY

# Verify endpoint accessibility
curl -H "Authorization: Bearer $MODEL_ACCESS_KEY" \
  https://inference.do-ai.run/v1/models
```

### Issue: Database connection errors

**Solution:**
```bash
# Verify database is running
psql -U postgres -h localhost -c "SELECT version();"

# Check credentials in .env
# Ensure POSTGRES_PASSWORD matches DB_PASSWORD
```

### Issue: Portal not loading

**Solution:**
```bash
# Check Node server is running
curl http://localhost:3000/health

# View logs
docker-compose -f docker-compose-portal.yml logs node-api

# Restart services
docker-compose -f docker-compose-portal.yml restart
```

### Issue: Agent responses are slow

**Solution:**
- Check Serverless Inference API status
- Verify MODEL_ACCESS_KEY is valid
- Monitor network latency
- Check database query performance

## 📚 Additional Resources

- [DigitalOcean MARS Docs](https://docs.digitalocean.com/products/managed-agents/)
- [Serverless Inference API Docs](https://docs.digitalocean.com/products/inference/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Express.js Documentation](https://expressjs.com/)

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

MIT License - See LICENSE file for details

## 💬 Support

Need help? 

- 📖 Check the README
- 🐛 Review troubleshooting section
- 📧 Contact support@digitalocean.com
- 💻 Open an issue on GitHub

---

**Built with ❤️ using DigitalOcean MARS & Serverless Inference**
