/**
 * Customer Support Portal Backend
 * Node.js/Express server integrating MARS agent and Serverless Inference
 */

const express = require('express');
const cors = require('cors');
const { spawn } = require('child_process');
const pg = require('pg');
const path = require('path');
const fs = require('fs');
const crypto = require('crypto');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static(__dirname));
app.use(express.static('public'));

// PostgreSQL Pool
const pool = new pg.Pool({
    user: process.env.DB_USER || 'postgres',
    password: process.env.DB_PASSWORD,
    host: process.env.DB_HOST || 'localhost',
    port: process.env.DB_PORT || 5432,
    database: process.env.DB_NAME || 'support_db'
});

pool.on('error', (err) => {
    console.error('Unexpected error on idle client', err);
});

// Python process cache
let pythonProcess = null;

/**
 * Call the MARS agent via Python subprocess
 */
function callMARSAgent(sessionId, customerId, message) {
    return new Promise((resolve, reject) => {
        try {
            // Prepare the Python script
            const pythonScript = path.join(__dirname, 'mars_agent_handler.py');

            // Call Python subprocess
            const python = spawn('python', [pythonScript, sessionId, customerId, message]);

            let stdout = '';
            let stderr = '';

            python.stdout.on('data', (data) => {
                stdout += data.toString();
            });

            python.stderr.on('data', (data) => {
                stderr += data.toString();
            });

            python.on('close', (code) => {
                if (code === 0) {
                    try {
                        const result = JSON.parse(stdout);
                        resolve(result);
                    } catch (e) {
                        reject(new Error('Invalid JSON response from MARS agent'));
                    }
                } else {
                    reject(new Error(`MARS agent failed: ${stderr}`));
                }
            });

            // Timeout after 30 seconds
            setTimeout(() => {
                python.kill();
                reject(new Error('MARS agent request timed out'));
            }, 30000);

        } catch (error) {
            reject(error);
        }
    });
}

// ============ STATIC FILES ============

/**
 * Serve portal.html for root
 */
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'portal.html'));
});

/**
 * Serve portal.html for /portal route
 */
app.get('/portal', (req, res) => {
    res.sendFile(path.join(__dirname, 'portal.html'));
});

// ============ API ENDPOINTS ============

/**
 * Health check
 */
app.get('/health', (req, res) => {
    res.json({
        status: 'healthy',
        service: 'mars-support-portal',
        timestamp: new Date().toISOString(),
        version: '1.0.0'
    });
});

/**
 * Get all conversations
 */
app.get('/api/v1/conversations', async (req, res) => {
    try {
        const result = await pool.query(`
            SELECT DISTINCT ON (session_id)
                session_id,
                customer_id,
                message,
                created_at,
                created_at as updated_at
            FROM conversations
            ORDER BY session_id, created_at DESC
            LIMIT 50
        `);

        // Get summary for each conversation
        const conversations = await Promise.all(result.rows.map(async (conv) => {
            const ticket = await pool.query(
                'SELECT id, ticket_number, subject FROM tickets WHERE customer_id = $1 LIMIT 1',
                [conv.customer_id]
            );

            return {
                session_id: conv.session_id,
                customer_id: conv.customer_id,
                subject: ticket.rows[0]?.subject || 'Conversation',
                updated_at: conv.updated_at
            };
        }));

        res.json({ conversations });
    } catch (error) {
        console.error('Error fetching conversations:', error);
        res.status(500).json({ error: error.message });
    }
});

/**
 * Get conversation messages
 */
app.get('/api/v1/conversations/:sessionId/messages', async (req, res) => {
    try {
        const { sessionId } = req.params;

        const result = await pool.query(`
            SELECT id, role, message, created_at
            FROM conversations
            WHERE session_id = $1
            ORDER BY created_at ASC
        `, [sessionId]);

        res.json({ messages: result.rows });
    } catch (error) {
        console.error('Error fetching messages:', error);
        res.status(500).json({ error: error.message });
    }
});

/**
 * Send message and get agent response
 */
app.post('/api/v1/conversations/:sessionId/message', async (req, res) => {
    try {
        const { sessionId } = req.params;
        const { customer_id, message } = req.body;

        if (!message || !customer_id) {
            return res.status(400).json({ error: 'Missing required fields' });
        }

        // Call MARS agent
        const marsResult = await callMARSAgent(sessionId, customer_id, message);

        // Extract results
        const response = marsResult.response || 'Unable to process your message at this time.';
        const ticketCreated = marsResult.ticket && marsResult.ticket.status === 'created';
        const escalated = marsResult.escalation && marsResult.escalation.status === 'escalated';
        const referenceId = marsResult.escalation?.escalation_id || null;

        res.json({
            response,
            ticketCreated,
            escalated,
            reference_id: referenceId,
            timestamp: new Date().toISOString()
        });

    } catch (error) {
        console.error('Error processing message:', error);
        res.status(500).json({
            error: error.message,
            response: 'I apologize, but I encountered an error processing your request. Please try again.'
        });
    }
});

/**
 * Get ticket information for a conversation
 */
app.get('/api/v1/conversations/:sessionId/ticket', async (req, res) => {
    try {
        const { sessionId } = req.params;

        // First get customer_id from conversation
        const convResult = await pool.query(
            'SELECT customer_id FROM conversations WHERE session_id = $1 LIMIT 1',
            [sessionId]
        );

        if (convResult.rows.length === 0) {
            return res.json({ ticket: null });
        }

        const customerId = convResult.rows[0].customer_id;

        // Get ticket for this customer
        const ticketResult = await pool.query(`
            SELECT id, ticket_number, subject, description, category, priority, status, assigned_to, created_at
            FROM tickets
            WHERE customer_id = $1
            ORDER BY created_at DESC
            LIMIT 1
        `, [customerId]);

        if (ticketResult.rows.length === 0) {
            return res.json({ ticket: null });
        }

        const ticket = ticketResult.rows[0];
        res.json({
            ticket: {
                id: ticket.id,
                ticket_number: ticket.ticket_number,
                subject: ticket.subject,
                description: ticket.description,
                category: ticket.category,
                priority: ticket.priority,
                status: ticket.status,
                assigned_to: ticket.assigned_to,
                created_at: ticket.created_at
            }
        });

    } catch (error) {
        console.error('Error fetching ticket:', error);
        res.status(500).json({ error: error.message, ticket: null });
    }
});

/**
 * Get FAQ entries
 */
app.get('/api/v1/faq', async (req, res) => {
    try {
        const { search } = req.query;

        let query = 'SELECT id, question, answer, category FROM faq';
        const params = [];

        if (search) {
            query += ` WHERE to_tsvector('english', question || ' ' || answer)
                           @@ plainto_tsquery('english', $1)`;
            params.push(search);
        }

        query += ' ORDER BY priority DESC LIMIT 20';

        const result = await pool.query(query, params);
        res.json({ faq: result.rows });

    } catch (error) {
        console.error('Error fetching FAQ:', error);
        res.status(500).json({ error: error.message });
    }
});

/**
 * Get agent status
 */
app.get('/api/v1/agent/status', async (req, res) => {
    try {
        // Check if inference endpoint is accessible
        const inferenceUrl = process.env.SERVERLESS_INFERENCE_URL || 'https://inference.do-ai.run';
        const hasApiKey = !!process.env.MODEL_ACCESS_KEY;

        res.json({
            status: hasApiKey ? 'ready' : 'unconfigured',
            inference_url: inferenceUrl,
            model: process.env.INFERENCE_MODEL || 'claude-3-5-sonnet-20241022',
            serverless_inference_configured: hasApiKey,
            mars_ready: true
        });

    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

/**
 * Get conversation analytics
 */
app.get('/api/v1/analytics/conversations', async (req, res) => {
    try {
        const result = await pool.query(`
            SELECT
                COUNT(DISTINCT session_id) as total_conversations,
                COUNT(*) as total_messages,
                COUNT(CASE WHEN role = 'customer' THEN 1 END) as customer_messages,
                COUNT(CASE WHEN role = 'agent' THEN 1 END) as agent_messages,
                AVG(EXTRACT(EPOCH FROM (
                    SELECT created_at FROM conversations c2
                    WHERE c2.role = 'agent'
                    AND c2.session_id = c1.session_id
                    LIMIT 1
                )) - EXTRACT(EPOCH FROM created_at)) as avg_response_time
            FROM conversations c1
            WHERE created_at > NOW() - INTERVAL '24 hours'
        `);

        res.json(result.rows[0]);

    } catch (error) {
        console.error('Error fetching analytics:', error);
        res.status(500).json({ error: error.message });
    }
});

/**
 * Fallback - Serve portal.html for any unmatched routes
 */
app.use((req, res) => {
    // If it's an API request, return 404
    if (req.path.startsWith('/api/')) {
        return res.status(404).json({ error: 'API endpoint not found' });
    }
    // Otherwise serve the portal
    res.sendFile(path.join(__dirname, 'portal.html'));
});

/**
 * Error handler
 */
app.use((err, req, res, next) => {
    console.error('Unhandled error:', err);
    res.status(500).json({
        error: 'Internal server error',
        message: err.message
    });
});

// Start server
app.listen(PORT, () => {
    console.log(`🚀 Support Portal running on http://localhost:${PORT}`);
    console.log(`📊 Portal UI: http://localhost:${PORT}`);
    console.log(`🔧 API Base: http://localhost:${PORT}/api/v1`);
});

// Graceful shutdown
process.on('SIGINT', async () => {
    console.log('Shutting down gracefully...');
    await pool.end();
    process.exit(0);
});
