# Quick Start - MARS Support Portal with Serverless Inference

Get the full support portal running in 10 minutes!

## 🎯 What You'll Get

- Professional support chat portal (http://localhost:3000)
- MARS agent processing customer messages
- DigitalOcean Serverless Inference for AI responses
- PostgreSQL database with conversation history
- Automatic ticket creation and escalation

## 📋 Prerequisites

1. **DigitalOcean Account** - For Serverless Inference
2. **Docker & Docker Compose** - For easy setup
3. **Git** - To clone the project

## 🚀 Setup (Docker - 5 minutes)

### Step 1: Get Your API Key

1. Go to [DigitalOcean Control Panel](https://cloud.digitalocean.com)
2. Click **Inference** → **Serverless Inference**
3. Create or copy your **Model Access Key**
4. Save it (starts with `dop_v1_...`)

### Step 2: Clone & Configure

```bash
# Clone or download the project
cd mars-support-portal

# Copy environment template
cp .env.portal.example .env

# Edit .env and add your key
# Windows: notepad .env
# Mac/Linux: nano .env
```

Edit `.env` and set:
```
MODEL_ACCESS_KEY=your_key_from_step_1
DB_PASSWORD=postgres_password_dev
```

### Step 3: Start Services

```bash
# Start all services (takes 15-30 seconds)
docker-compose -f docker-compose-portal.yml up -d

# Watch startup logs
docker-compose -f docker-compose-portal.yml logs -f

# When you see "Running on http://0.0.0.0:3000" - you're ready!
```

### Step 4: Access Portal

Open your browser:
- **Portal:** http://localhost:3000
- **API Health:** http://localhost:3000/health
- **API Docs:** http://localhost:3000/api/v1

## 💬 Try It Out

1. Click **"+ New Conversation"**
2. Type a message:
   - **"How do I reset my password?"** → Gets FAQ answer
   - **"I can't log in and it's urgent!"** → Creates ticket + escalates
   - **"Can I cancel my subscription?"** → FAQ response

3. Watch as the agent:
   - Classifies your issue (category, priority)
   - Searches FAQ for answers
   - Generates smart response via Serverless Inference
   - Creates tickets if needed
   - Escalates to humans for urgent issues

## 🔍 See It In Action

### Example 1: FAQ Response
```
You: How do I upgrade my plan?

Agent: You can upgrade from Settings > Billing:
1) Click "Change Plan"
2) Select your tier
3) Review pricing
4) Click "Upgrade"

Changes take effect immediately!
```

### Example 2: Escalation
```
You: I've been locked out for 3 days, this is critical!

Agent: I understand this is urgent. Let me create a support 
ticket and escalate to our team.

[System Notice] Ticket TK-2026-001 created. 
Reference: ESC-12345. A specialist will contact you shortly.
```

## 🛑 Stop Services

```bash
# Stop all containers
docker-compose -f docker-compose-portal.yml down

# Stop and remove database
docker-compose -f docker-compose-portal.yml down -v
```

## 🐛 Troubleshooting

### "API connection refused"
```bash
# Check if container is running
docker ps

# View logs
docker-compose -f docker-compose-portal.yml logs node-api

# Restart
docker-compose -f docker-compose-portal.yml restart
```

### "Model access key error"
- Verify API key in `.env` is correct
- Check DigitalOcean account has inference enabled
- Try key with: `curl -H "Authorization: Bearer KEY" https://inference.do-ai.run/v1/models`

### "Database connection error"
```bash
# Check PostgreSQL is running
docker ps | grep postgres

# View database logs
docker-compose -f docker-compose-portal.yml logs postgres

# Verify password in .env matches
```

### "Portal won't load"
- Wait 15-30 seconds after `docker-compose up`
- Verify services are healthy: `docker ps`
- Check browser console (F12) for errors
- Try hard refresh (Ctrl+Shift+R)

## 📊 View Portal Stats

```bash
# Get today's conversation metrics
curl http://localhost:3000/api/v1/analytics/conversations
```

Returns:
```json
{
  "total_conversations": 5,
  "total_messages": 23,
  "customer_messages": 11,
  "agent_messages": 12,
  "avg_response_time": 1.8
}
```

## 🔧 Manual Setup (Alternative)

If you prefer not to use Docker:

### Prerequisites
- Node.js 18+
- Python 3.9+
- PostgreSQL 14+

### Setup Steps

```bash
# 1. Install Node dependencies
npm install

# 2. Install Python dependencies
pip install -r requirements-portal.txt

# 3. Create database
createdb -U postgres support_db
psql -U postgres -d support_db -f schema_portal.sql

# 4. Configure .env (as above)

# 5. Start Node server
npm start

# 6. Open http://localhost:3000
```

## 📚 Next Steps

1. **Explore the portal**
   - Send different types of messages
   - Watch tickets get created
   - Check conversation history

2. **Review the code**
   - `portal.html` - Beautiful chat UI
   - `server.js` - Node API endpoints
   - `mars_agent.py` - Agent logic
   - `serverless_inference.py` - Inference wrapper

3. **Customize for your use**
   - Edit FAQ in `schema_portal.sql`
   - Modify agent prompts
   - Add integrations (Slack, Jira, etc.)

4. **Deploy to production**
   - Follow `PORTAL_README.md` deployment section
   - Set up proper secrets management
   - Configure monitoring and alerts

## 📖 Documentation

- **Full Docs:** See `PORTAL_README.md`
- **API Reference:** See `PORTAL_README.md` API section
- **Architecture:** See `PORTAL_README.md` Architecture

## 💡 Tips

- **Auto-escalation:** Messages with "urgent", "critical", "help" in critical priority
- **FAQ Management:** Add more FAQs by editing `schema_portal.sql`
- **Custom Prompts:** Modify agent instructions in `mars_agent.py`
- **Performance:** Portal handles 100+ concurrent conversations

## 🆘 Need Help?

1. Check **Troubleshooting** section above
2. Review logs: `docker-compose -f docker-compose-portal.yml logs`
3. Check DigitalOcean status: https://status.digitalocean.com/
4. Contact support: support@digitalocean.com

## ✅ Checklist

Before going live:

- [ ] Tested FAQ responses
- [ ] Tested ticket creation
- [ ] Tested escalation flow
- [ ] Verified database connectivity
- [ ] Checked agent response time
- [ ] Reviewed conversation history
- [ ] Tested on multiple browsers
- [ ] Set up monitoring/alerts
- [ ] Configured backup strategy
- [ ] Trained support team

---

**Ready?** Start with step 1 and you'll have a production-ready support portal in 10 minutes! 🎉
