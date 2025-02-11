-- Create prompt_versions table
CREATE TABLE IF NOT EXISTS prompt_versions (
    id SERIAL PRIMARY KEY,
    version VARCHAR(50) NOT NULL,
    prompt TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(version)
);

-- Create index on version for faster lookups
CREATE INDEX IF NOT EXISTS idx_prompt_versions_version ON prompt_versions(version);

-- Function to update timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to automatically update updated_at
CREATE TRIGGER update_prompt_versions_updated_at
    BEFORE UPDATE ON prompt_versions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Insert initial version
INSERT INTO prompt_versions (version, prompt) 
VALUES ('1.0.0', 'You are a helpful AI assistant. Please help me with my questions.')
ON CONFLICT (version) DO NOTHING;
