-- ============================================================
--  AI Lead Generation CRM  –  MySQL Schema
-- ============================================================

CREATE DATABASE IF NOT EXISTS ai_lead_crm CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE ai_lead_crm;

-- ------------------------------------------------------------
-- LEADS table – one row per qualified / tracked lead
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS leads (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    name              VARCHAR(255),
    platform          ENUM('instagram','facebook','reddit','website','unknown') DEFAULT 'unknown',
    contact_details   VARCHAR(500),
    interest_level    ENUM('hot','warm','cold') DEFAULT 'cold',
    conversation_summary TEXT,
    sender_id         VARCHAR(255),          -- platform user/page id
    escalated         TINYINT(1) DEFAULT 0,  -- 1 = handed over to human
    escalation_reason VARCHAR(500),
    created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at        DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------
-- MESSAGES table – full conversation history per lead
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS messages (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    lead_id     INT NOT NULL,
    direction   ENUM('inbound','outbound') DEFAULT 'inbound',
    platform    VARCHAR(50),
    content     TEXT,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE
);

-- ------------------------------------------------------------
-- ESCALATIONS table – audit trail for human hand-overs
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS escalations (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    lead_id     INT NOT NULL,
    reason      VARCHAR(500),
    notified_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE
);

-- ------------------------------------------------------------
-- Indexes
-- ------------------------------------------------------------
CREATE INDEX idx_leads_platform      ON leads(platform);
CREATE INDEX idx_leads_interest      ON leads(interest_level);
CREATE INDEX idx_leads_escalated     ON leads(escalated);
CREATE INDEX idx_messages_lead       ON messages(lead_id);
