-- Enhanced PostgreSQL Schema for Support Portal
-- Includes all tables needed for portal with analytics and real-time features

-- Drop existing tables (for fresh setup)
DROP TABLE IF EXISTS escalations CASCADE;
DROP TABLE IF EXISTS messages CASCADE;
DROP TABLE IF EXISTS conversations CASCADE;
DROP TABLE IF EXISTS tickets CASCADE;
DROP TABLE IF EXISTS faq CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS portal_users CASCADE;
DROP TABLE IF EXISTS analytics_events CASCADE;

-- Portal Users (staff)
CREATE TABLE portal_users (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    role VARCHAR(50), -- admin, agent, manager
    status VARCHAR(20), -- active, inactive
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Customers
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    customer_id VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    company VARCHAR(255),
    tier VARCHAR(50), -- free, pro, enterprise
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Conversations (all customer-agent interactions)
CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    customer_id VARCHAR(50) NOT NULL REFERENCES customers(customer_id),
    role VARCHAR(20) NOT NULL, -- customer, agent, system
    message TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_session (session_id),
    INDEX idx_customer (customer_id),
    INDEX idx_created (created_at)
);

-- Support Tickets
CREATE TABLE tickets (
    id SERIAL PRIMARY KEY,
    ticket_number VARCHAR(20) UNIQUE NOT NULL DEFAULT ('TK-' || TO_CHAR(NOW(), 'YYYY') || '-' || LPAD(NEXTVAL('ticket_seq')::TEXT, 5, '0')),
    customer_id VARCHAR(50) NOT NULL REFERENCES customers(customer_id),
    subject VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(50), -- billing, technical, account, feature_request, other
    priority VARCHAR(20), -- low, medium, high, critical
    status VARCHAR(50), -- open, in_progress, resolved, closed
    assigned_to VARCHAR(100) REFERENCES portal_users(user_id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP,
    INDEX idx_customer (customer_id),
    INDEX idx_status (status),
    INDEX idx_priority (priority),
    INDEX idx_assigned (assigned_to)
);

-- FAQ Knowledge Base
CREATE TABLE faq (
    id SERIAL PRIMARY KEY,
    question VARCHAR(500) NOT NULL,
    answer TEXT NOT NULL,
    category VARCHAR(100), -- account, billing, technical, features, etc.
    priority INTEGER DEFAULT 0, -- higher shows first
    tags VARCHAR(500), -- comma-separated
    views INTEGER DEFAULT 0,
    helpful_count INTEGER DEFAULT 0,
    unhelpful_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(50),
    INDEX idx_category (category)
);

-- Escalations
CREATE TABLE escalations (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    customer_id VARCHAR(50) NOT NULL REFERENCES customers(customer_id),
    ticket_id INTEGER REFERENCES tickets(id),
    reason TEXT NOT NULL,
    status VARCHAR(50), -- pending, assigned, resolved
    assigned_to VARCHAR(100) REFERENCES portal_users(user_id),
    context JSONB, -- conversation summary and context
    created_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP,
    INDEX idx_session (session_id),
    INDEX idx_status (status),
    INDEX idx_assigned (assigned_to)
);

-- Analytics Events
CREATE TABLE analytics_events (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(100), -- message_sent, ticket_created, escalation, etc.
    session_id VARCHAR(100),
    customer_id VARCHAR(50),
    user_id VARCHAR(50),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_event_type (event_type),
    INDEX idx_session (session_id),
    INDEX idx_customer (customer_id),
    INDEX idx_created (created_at)
);

-- Create sequence for ticket numbering
CREATE SEQUENCE IF NOT EXISTS ticket_seq START 1;

-- Create indexes for performance
CREATE INDEX idx_conversations_session_id ON conversations(session_id);
CREATE INDEX idx_conversations_customer_id ON conversations(customer_id);
CREATE INDEX idx_conversations_created_at ON conversations(created_at);
CREATE INDEX idx_tickets_customer_id ON tickets(customer_id);
CREATE INDEX idx_tickets_status ON tickets(status);
CREATE INDEX idx_tickets_priority ON tickets(priority);
CREATE INDEX idx_tickets_assigned_to ON tickets(assigned_to);
CREATE INDEX idx_escalations_session_id ON escalations(session_id);
CREATE INDEX idx_escalations_status ON escalations(status);
CREATE INDEX idx_escalations_created_at ON escalations(created_at);
CREATE INDEX idx_faq_category ON faq(category);

-- Create fulltext search index for FAQ (PostgreSQL)
CREATE INDEX idx_faq_search ON faq USING GIN(to_tsvector('english', question || ' ' || answer));

-- Insert sample FAQ data
INSERT INTO faq (question, answer, category, priority, tags, created_by) VALUES
(
    'How do I reset my password?',
    'To reset your password: 1) Click "Forgot Password" on the login page. 2) Enter your email address. 3) Check your email for a reset link. 4) Click the link and create a new password. If you don''t receive an email, check your spam folder.',
    'account',
    10,
    'password,reset,login,account',
    'admin'
),
(
    'How do I upgrade my plan?',
    'You can upgrade your plan from your account dashboard: 1) Go to Settings > Billing. 2) Click "Change Plan". 3) Select your desired tier. 4) Review the pricing. 5) Click "Upgrade" to confirm. Changes take effect immediately.',
    'billing',
    9,
    'upgrade,billing,plan,subscription',
    'admin'
),
(
    'What payment methods do you accept?',
    'We accept all major credit cards (Visa, Mastercard, American Express), PayPal, and bank transfers. For annual plans, we also offer special payment options. You can manage payment methods in your billing settings.',
    'billing',
    8,
    'payment,credit,card',
    'admin'
),
(
    'How do I integrate with third-party tools?',
    'We support integrations with popular tools through our API. Check our documentation for API endpoints and webhooks. You can also browse our integration marketplace for pre-built connectors. Contact support for custom integration assistance.',
    'technical',
    7,
    'integration,api,webhooks,tools',
    'admin'
),
(
    'Is my data secure?',
    'Yes, security is our top priority. We use industry-standard SSL/TLS encryption, regular security audits, and comply with GDPR and CCPA. All data is stored in secure data centers with daily backups. Review our security policy for more details.',
    'technical',
    8,
    'security,encryption,privacy,data',
    'admin'
),
(
    'Can I cancel my subscription?',
    'Yes, you can cancel anytime without penalties. Go to Settings > Subscription and click "Cancel". Your access continues until the end of your billing period. No cancellation fees or long-term contracts.',
    'billing',
    8,
    'cancel,subscription,refund',
    'admin'
),
(
    'How do I export my data?',
    'Export your data from Dashboard > Settings > Data Export. Available formats: CSV, JSON, XML. Request an export and we''ll prepare it within 24 hours. The download link is valid for 7 days.',
    'technical',
    7,
    'export,download,data,csv',
    'admin'
),
(
    'What is your uptime guarantee?',
    'We guarantee 99.9% uptime for all paid plans. Enterprise customers get 99.99% SLA with dedicated support. Check our status page for real-time system status and historical uptime reports.',
    'technical',
    9,
    'uptime,sla,availability,support',
    'admin'
);

-- Create views for analytics
CREATE VIEW conversation_summary AS
SELECT
    session_id,
    customer_id,
    COUNT(*) as message_count,
    COUNT(CASE WHEN role = 'customer' THEN 1 END) as customer_messages,
    COUNT(CASE WHEN role = 'agent' THEN 1 END) as agent_messages,
    MIN(created_at) as started_at,
    MAX(created_at) as ended_at,
    EXTRACT(EPOCH FROM (MAX(created_at) - MIN(created_at))) as duration_seconds
FROM conversations
GROUP BY session_id, customer_id;

CREATE VIEW ticket_stats AS
SELECT
    category,
    priority,
    status,
    COUNT(*) as count,
    AVG(EXTRACT(EPOCH FROM (resolved_at - created_at))) as avg_resolution_time
FROM tickets
GROUP BY category, priority, status;

-- Sample customer data
INSERT INTO customers (customer_id, email, name, company, tier) VALUES
('cust_demo_001', 'john@example.com', 'John Doe', 'Acme Corp', 'pro'),
('cust_demo_002', 'jane@example.com', 'Jane Smith', 'Tech Startup', 'enterprise');

-- Sample portal users
INSERT INTO portal_users (user_id, email, name, role, status) VALUES
('agent_001', 'agent1@company.com', 'Sarah Johnson', 'agent', 'active'),
('agent_002', 'agent2@company.com', 'Mike Chen', 'agent', 'active'),
('manager_001', 'manager@company.com', 'Alex Manager', 'manager', 'active');
