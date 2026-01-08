-- Run this in your MySQL database
CREATE DATABASE IF NOT EXISTS soul_connect;
USE soul_connect;

-- Users table (anonymous)
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    anonymous_id VARCHAR(100) UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Messages table
CREATE TABLE IF NOT EXISTS messages (
    id VARCHAR(36) PRIMARY KEY,
    session_id VARCHAR(36),
    sender_type VARCHAR(20),
    message_text TEXT,
    emotion_label VARCHAR(50),
    emotion_score FLOAT,
    risk_level VARCHAR(20),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Crisis logs table
CREATE TABLE IF NOT EXISTS crisis_logs (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36),
    trigger_message TEXT,
    severity_level INT,
    action_taken VARCHAR(255),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sample data (optional)
INSERT INTO users (id, anonymous_id) VALUES 
('sample-user-1', 'user_abc123'),
('sample-user-2', 'user_def456');