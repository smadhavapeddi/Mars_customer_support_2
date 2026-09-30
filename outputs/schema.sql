-- PostgreSQL Schema for Customer Support Agent
-- Run this script to initialize the database

-- Create tables
CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    customer_id VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    company VARCHAR(255),
    tier VARCHAR(50), -- free, pro, enterprise
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    customer_id VARCHAR(50) NOT NULL REFERENCES customers(customer_id),
    role VARCHAR(20) NOT NULL, -- 'customer', 'agent', 'system'
    message TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_session (session_id),
    INDEX idx_customer (customer_id),
    INDEX idx_created (created_at)
);

CREATE TABLE IF NOT EXISTS tickets (
    id SERIAL PRIMARY KEY,
    ticket_number VARCHAR(20) UNIQUE NOT NULL,
    customer_id VARCHAR(50) NOT NULL REFERENCES customers(customer_id),
    subject VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(50), -- 'billing', 'technical', 'account', 'feature_request', 'other'
    priority VARCHAR(20), -- 'low', 'medium', 'high', 'critical'
    status VARCHAR(50), -- 'open', 'in_progress', 'resolved', 'closed'
    assigned_to VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP,
    INDEX idx_customer (customer_id),
    INDEX idx_status (status),
    INDEX idx_priority (priority)
);

CREATE TABLE IF NOT EXISTS faq (
    id SERIAL PRIMARY KEY,
    question VARCHAR(500) NOT NULL,
    answer TEXT NOT NULL,
    category VARCHAR(100), -- 'account', 'billing', 'technical', 'features', etc.
    priority INTEGER DEFAULT 0, -- Higher priority shows first in search
    tags VARCHAR(500), -- Comma-separated tags
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_category (category),
    FULLTEXT INDEX idx_search (question, answer)
);

CREATE TABLE IF NOT EXISTS escalations (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    customer_id VARCHAR(50) NOT NULL REFERENCES customers(customer_id),
    ticket_id INTEGER REFERENCES tickets(id),
    reason TEXT NOT NULL,
    status VARCHAR(50), -- 'pending', 'assigned', 'resolved'
    assigned_to VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP,
    INDEX idx_session (session_id),
    INDEX idx_status (status),
    INDEX idx_created (created_at)
);

CREATE TABLE IF NOT EXISTS agent_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) UNIQUE NOT NULL,
    customer_id VARCHAR(50) NOT NULL REFERENCES customers(customer_id),
    started_at TIMESTAMP DEFAULT NOW(),
    ended_at TIMESTAMP,
    message_count INTEGER DEFAULT 0,
    final_status VARCHAR(50), -- 'resolved', 'escalated', 'abandoned'
    created_at TIMESTAMP DEFAULT NOW()
);

-- Sample FAQ data
INSERT INTO faq (question, answer, category, priority, tags) VALUES
(
    'How do I reset my password?',
    'To reset your password: 1) Click "Forgot Password" on the login page. 2) Enter your email address. 3) Check your email for a reset link. 4) Click the link and create a new password. If you don''t receive an email, check your spam folder or contact support.',
    'account',
    10,
    'password,reset,login,account'
),
(
    'How can I upgrade my subscription?',
    'You can upgrade your subscription from your account dashboard: 1) Go to Settings > Subscription. 2) Click "Change Plan". 3) Select your desired tier. 4) Review the billing details. 5) Click "Upgrade" to confirm. Your new features will be available immediately.',
    'billing',
    9,
    'upgrade,subscription,billing,plan'
),
(
    'What payment methods do you accept?',
    'We accept all major credit cards (Visa, Mastercard, American Express), PayPal, and wire transfers. For annual plans, we also offer special billing options. You can add and manage payment methods in your account settings.',
    'billing',
    8,
    'payment,credit,card,billing'
),
(
    'Why is my integration not working?',
    'Common reasons include: 1) API key is incorrect or expired. 2) Network connectivity issues. 3) Rate limiting - check your usage. 4) Webhook endpoints are unreachable. First, verify your API key in account settings. Check our API documentation for rate limits. If issues persist, contact technical support with your API request logs.',
    'technical',
    7,
    'integration,api,connection,technical'
),
(
    'How do I contact customer support?',
    'You can reach our support team through: 1) Email: support@company.com. 2) Live chat (available 9am-6pm EST). 3) Support tickets through your dashboard. 4) Phone support for enterprise customers. Response times: Standard (24-48 hours), Priority (4-8 hours for paid plans).',
    'account',
    6,
    'support,contact,help'
),
(
    'Is my data secure?',
    'Yes, we take security seriously. We use industry-standard SSL/TLS encryption, regular security audits, and comply with GDPR, CCPA, and other privacy regulations. All data is stored in secure data centers with daily backups. See our security policy page for detailed information.',
    'technical',
    8,
    'security,encryption,data,privacy'
),
(
    'Can I cancel my subscription?',
    'Yes, you can cancel anytime. To cancel: 1) Go to Settings > Subscription. 2) Click "Cancel Subscription". 3) Tell us why (optional). 4) Confirm cancellation. Your access will continue until the end of your current billing period. There are no cancellation fees.',
    'billing',
    8,
    'cancel,subscription,refund'
),
(
    'How do I export my data?',
    'You can export your data from Dashboard > Settings > Data Export. Available formats: CSV, JSON, XML. Click "Request Export" and we''ll prepare your data within 24 hours. The export link will be sent to your email and is valid for 7 days. For large accounts, please contact support.',
    'technical',
    7,
    'export,data,download,csv'
);

-- Create indexes for performance
CREATE INDEX idx_conversations_session_id ON conversations(session_id);
CREATE INDEX idx_conversations_customer_id ON conversations(customer_id);
CREATE INDEX idx_conversations_created_at ON conversations(created_at);
CREATE INDEX idx_tickets_customer_id ON tickets(customer_id);
CREATE INDEX idx_tickets_status ON tickets(status);
CREATE INDEX idx_tickets_priority ON tickets(priority);
CREATE INDEX idx_escalations_session_id ON escalations(session_id);
CREATE INDEX idx_escalations_status ON escalations(status);
CREATE INDEX idx_escalations_created_at ON escalations(created_at);
CREATE INDEX idx_faq_category ON faq(category);

-- Create fulltext search index for FAQ (PostgreSQL)
CREATE INDEX idx_faq_search ON faq USING GIN(to_tsvector('english', question || ' ' || answer));
