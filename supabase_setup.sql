-- Supabase Database Setup for Insane Finance App
-- Run this in Supabase SQL Editor

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW())
);

-- Budget Profiles table
CREATE TABLE IF NOT EXISTS budget_profiles (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL DEFAULT 'Default',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW())
);

-- Envelopes table
CREATE TABLE IF NOT EXISTS envelopes (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    profile_id UUID REFERENCES budget_profiles(id) ON DELETE CASCADE,
    category VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    target_amount DECIMAL(10, 2) DEFAULT 0.00,
    current_balance DECIMAL(10, 2) DEFAULT 0.00,
    priority INTEGER DEFAULT 10,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW())
);

-- Bills table
CREATE TABLE IF NOT EXISTS bills (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    profile_id UUID REFERENCES budget_profiles(id) ON DELETE CASCADE,
    envelope_id UUID REFERENCES envelopes(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    bill_type VARCHAR(50) NOT NULL,
    due_date DATE NOT NULL,
    paid BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW())
);

-- Debts table
CREATE TABLE IF NOT EXISTS debts (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    profile_id UUID REFERENCES budget_profiles(id) ON DELETE CASCADE,
    envelope_id UUID REFERENCES envelopes(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    balance DECIMAL(10, 2) NOT NULL,
    apr DECIMAL(5, 4) NOT NULL,
    minimum_payment DECIMAL(10, 2) NOT NULL,
    due_date DATE NOT NULL,
    strategy VARCHAR(50) NOT NULL,
    paid_off BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW())
);

-- Sinking Funds table
CREATE TABLE IF NOT EXISTS sinking_funds (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    profile_id UUID REFERENCES budget_profiles(id) ON DELETE CASCADE,
    envelope_id UUID REFERENCES envelopes(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    target_amount DECIMAL(10, 2) NOT NULL,
    current_balance DECIMAL(10, 2) DEFAULT 0.00,
    deadline DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW())
);

-- Savings Goals table
CREATE TABLE IF NOT EXISTS savings_goals (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    profile_id UUID REFERENCES budget_profiles(id) ON DELETE CASCADE,
    envelope_id UUID REFERENCES envelopes(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    target_amount DECIMAL(10, 2) NOT NULL,
    current_balance DECIMAL(10, 2) DEFAULT 0.00,
    target_date DATE NOT NULL,
    monthly_contribution DECIMAL(10, 2) DEFAULT 0.00,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW())
);

-- Settings table
CREATE TABLE IF NOT EXISTS budget_settings (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    profile_id UUID REFERENCES budget_profiles(id) ON DELETE CASCADE UNIQUE,
    checking_buffer DECIMAL(10, 2) DEFAULT 500.00,
    emergency_fund_target DECIMAL(10, 2) DEFAULT 10000.00,
    debt_strategy VARCHAR(50) DEFAULT 'AVALANCHE',
    savings_rate DECIMAL(5, 4) DEFAULT 0.20,
    discretionary_percentage DECIMAL(5, 4) DEFAULT 0.30,
    round_to_nearest DECIMAL(10, 2) DEFAULT 10.00,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW())
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_envelopes_profile_id ON envelopes(profile_id);
CREATE INDEX IF NOT EXISTS idx_bills_profile_id ON bills(profile_id);
CREATE INDEX IF NOT EXISTS idx_bills_due_date ON bills(due_date);
CREATE INDEX IF NOT EXISTS idx_debts_profile_id ON debts(profile_id);
CREATE INDEX IF NOT EXISTS idx_sinking_funds_profile_id ON sinking_funds(profile_id);
CREATE INDEX IF NOT EXISTS idx_savings_goals_profile_id ON savings_goals(profile_id);

-- Enable Row Level Security (RLS)
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE budget_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE envelopes ENABLE ROW LEVEL SECURITY;
ALTER TABLE bills ENABLE ROW LEVEL SECURITY;
ALTER TABLE debts ENABLE ROW LEVEL SECURITY;
ALTER TABLE sinking_funds ENABLE ROW LEVEL SECURITY;
ALTER TABLE savings_goals ENABLE ROW LEVEL SECURITY;
ALTER TABLE budget_settings ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for users table
DROP POLICY IF EXISTS "Users can read own data" ON users;
CREATE POLICY "Users can read own data" ON users
    FOR SELECT USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users can insert own data" ON users;
CREATE POLICY "Users can insert own data" ON users
    FOR INSERT WITH CHECK (auth.uid() = id);

DROP POLICY IF EXISTS "Users can update own data" ON users;
CREATE POLICY "Users can update own data" ON users
    FOR UPDATE USING (auth.uid() = id);

-- Create RLS policies for budget_profiles
DROP POLICY IF EXISTS "Users can read own profiles" ON budget_profiles;
CREATE POLICY "Users can read own profiles" ON budget_profiles
    FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own profiles" ON budget_profiles;
CREATE POLICY "Users can insert own profiles" ON budget_profiles
    FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update own profiles" ON budget_profiles;
CREATE POLICY "Users can update own profiles" ON budget_profiles
    FOR UPDATE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can delete own profiles" ON budget_profiles;
CREATE POLICY "Users can delete own profiles" ON budget_profiles
    FOR DELETE USING (auth.uid() = user_id);

-- Create RLS policies for envelopes
DROP POLICY IF EXISTS "Users can read own envelopes" ON envelopes;
CREATE POLICY "Users can read own envelopes" ON envelopes
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM budget_profiles 
            WHERE budget_profiles.id = envelopes.profile_id 
            AND budget_profiles.user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "Users can insert own envelopes" ON envelopes;
CREATE POLICY "Users can insert own envelopes" ON envelopes
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM budget_profiles 
            WHERE budget_profiles.id = profile_id 
            AND budget_profiles.user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "Users can update own envelopes" ON envelopes;
CREATE POLICY "Users can update own envelopes" ON envelopes
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM budget_profiles 
            WHERE budget_profiles.id = profile_id 
            AND budget_profiles.user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "Users can delete own envelopes" ON envelopes;
CREATE POLICY "Users can delete own envelopes" ON envelopes
    FOR DELETE USING (
        EXISTS (
            SELECT 1 FROM budget_profiles 
            WHERE budget_profiles.id = profile_id 
            AND budget_profiles.user_id = auth.uid()
        )
    );

-- Create similar policies for other tables (bills, debts, sinking_funds, savings_goals, budget_settings)
-- The pattern is the same: check if the user owns the parent budget_profile

-- For bills table
DROP POLICY IF EXISTS "Users can manage own bills" ON bills;
CREATE POLICY "Users can manage own bills" ON bills
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM budget_profiles 
            WHERE budget_profiles.id = bills.profile_id 
            AND budget_profiles.user_id = auth.uid()
        )
    );

-- For debts table
DROP POLICY IF EXISTS "Users can manage own debts" ON debts;
CREATE POLICY "Users can manage own debts" ON debts
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM budget_profiles 
            WHERE budget_profiles.id = debts.profile_id 
            AND budget_profiles.user_id = auth.uid()
        )
    );

-- For sinking_funds table
DROP POLICY IF EXISTS "Users can manage own sinking funds" ON sinking_funds;
CREATE POLICY "Users can manage own sinking funds" ON sinking_funds
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM budget_profiles 
            WHERE budget_profiles.id = sinking_funds.profile_id 
            AND budget_profiles.user_id = auth.uid()
        )
    );

-- For savings_goals table
DROP POLICY IF EXISTS "Users can manage own savings goals" ON savings_goals;
CREATE POLICY "Users can manage own savings goals" ON savings_goals
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM budget_profiles 
            WHERE budget_profiles.id = savings_goals.profile_id 
            AND budget_profiles.user_id = auth.uid()
        )
    );

-- For budget_settings table
DROP POLICY IF EXISTS "Users can manage own settings" ON budget_settings;
CREATE POLICY "Users can manage own settings" ON budget_settings
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM budget_profiles 
            WHERE budget_profiles.id = budget_settings.profile_id 
            AND budget_profiles.user_id = auth.uid()
        )
    );

-- Insert a test user (optional - for testing)
-- INSERT INTO users (email) VALUES ('test@example.com')
-- ON CONFLICT (email) DO NOTHING;

-- Create a function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = TIMEZONE('utc'::text, NOW());
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for all tables
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_budget_profiles_updated_at BEFORE UPDATE ON budget_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_envelopes_updated_at BEFORE UPDATE ON envelopes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_bills_updated_at BEFORE UPDATE ON bills
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_debts_updated_at BEFORE UPDATE ON debts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sinking_funds_updated_at BEFORE UPDATE ON sinking_funds
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_savings_goals_updated_at BEFORE UPDATE ON savings_goals
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_budget_settings_updated_at BEFORE UPDATE ON budget_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Display success message
SELECT '✅ Database setup completed successfully!' as message;