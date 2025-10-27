-- Initialize TradingAgents Database
-- This script runs when the PostgreSQL container is first created

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE tradingagents TO tradingagents;

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'TradingAgents database initialized successfully';
END $$;
