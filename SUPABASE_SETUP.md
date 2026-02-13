# Supabase Integration Guide for Insane Finance App

This guide provides step-by-step instructions to connect your Insane Finance App to Supabase for cloud database storage.

## 📋 Prerequisites

1. **Supabase Account**: Sign up at [supabase.com](https://supabase.com)
2. **Python 3.8+**: Installed on your system
3. **Git**: For version control
4. **Streamlit**: Already installed via requirements.txt

## 🚀 Step-by-Step Setup

### Step 1: Create a Supabase Project

1. Go to [app.supabase.com](https://app.supabase.com)
2. Click "New Project"
3. Enter project details:
   - **Name**: `insane-finance-app` (or your preferred name)
   - **Database Password**: Create a strong password (save this!)
   - **Region**: Choose closest to your users
   - **Pricing Plan**: Start with Free tier
4. Click "Create new project" (takes 1-2 minutes)

### Step 2: Get Your Supabase Credentials

After project creation, go to **Project Settings** → **API**:

1. **Project URL**: Copy the "Project URL" (e.g., `https://xxxxxxxxxxxx.supabase.co`)
2. **anon/public key**: Copy the "anon" public key
3. **service_role key**: Copy the "service_role" key (keep this secure!)
4. **Project ID**: Note your project ID

### Step 3: Install Supabase Python Client

Add Supabase to your requirements:

```bash
pip install supabase
```

Or update `requirements.txt`:
```txt
supabase>=2.0.0
python-dotenv>=1.0.0
```

### Step 4: Create Environment Configuration

Create a `.env` file in the project root:

```env
# Supabase Configuration
SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Optional: Database connection
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.xxxxxxxxxxxx.supabase.co:5432/postgres
```

**Important**: Add `.env` to `.gitignore` to keep secrets secure!

### Step 5: Create Database Tables in Supabase

Go to **SQL Editor** in Supabase dashboard and run these SQL commands:

```sql
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE users (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW())
);

-- Budget Profiles table
CREATE TABLE budget_profiles (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW())
);

-- Envelopes table
CREATE TABLE envelopes (
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
CREATE TABLE bills (
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
CREATE TABLE debts (
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
CREATE TABLE sinking_funds (
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
CREATE TABLE savings_goals (
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
CREATE TABLE budget_settings (
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
CREATE INDEX idx_envelopes_profile_id ON envelopes(profile_id);
CREATE INDEX idx_bills_profile_id ON bills(profile_id);
CREATE INDEX idx_bills_due_date ON bills(due_date);
CREATE INDEX idx_debts_profile_id ON debts(profile_id);
CREATE INDEX idx_sinking_funds_profile_id ON sinking_funds(profile_id);
CREATE INDEX idx_savings_goals_profile_id ON savings_goals(profile_id);
```

### Step 6: Update the Database Models

Create a new file `db/supabase_client.py`:

```python
"""
Supabase client for the finance application.
"""
import os
from typing import Optional, Dict, Any
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SupabaseClient:
    """Supabase client wrapper."""
    
    def __init__(self):
        self.url: str = os.getenv("SUPABASE_URL")
        self.key: str = os.getenv("SUPABASE_KEY")
        self.service_key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not self.url or not self.key:
            raise ValueError("Supabase URL and key must be set in environment variables")
        
        self.client: Client = create_client(self.url, self.key)
    
    # User operations
    def create_user(self, email: str) -> Dict[str, Any]:
        """Create a new user."""
        return self.client.table("users").insert({"email": email}).execute()
    
    def get_user(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email."""
        response = self.client.table("users").select("*").eq("email", email).execute()
        return response.data[0] if response.data else None
    
    # Budget profile operations
    def create_budget_profile(self, user_id: str, name: str = "Default") -> Dict[str, Any]:
        """Create a new budget profile."""
        return self.client.table("budget_profiles").insert({
            "user_id": user_id,
            "name": name
        }).execute()
    
    def get_budget_profile(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """Get budget profile by ID."""
        response = self.client.table("budget_profiles").select("*").eq("id", profile_id).execute()
        return response.data[0] if response.data else None
    
    def get_user_budget_profiles(self, user_id: str) -> list:
        """Get all budget profiles for a user."""
        response = self.client.table("budget_profiles").select("*").eq("user_id", user_id).execute()
        return response.data
    
    # Envelope operations
    def create_envelope(self, profile_id: str, envelope_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new envelope."""
        data = {
            "profile_id": profile_id,
            "category": envelope_data.get("category"),
            "name": envelope_data.get("name"),
            "target_amount": float(envelope_data.get("target_amount", 0)),
            "current_balance": float(envelope_data.get("current_balance", 0)),
            "priority": envelope_data.get("priority", 10)
        }
        return self.client.table("envelopes").insert(data).execute()
    
    def get_envelopes(self, profile_id: str) -> list:
        """Get all envelopes for a profile."""
        response = self.client.table("envelopes").select("*").eq("profile_id", profile_id).execute()
        return response.data
    
    # Bill operations
    def create_bill(self, profile_id: str, bill_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new bill."""
        data = {
            "profile_id": profile_id,
            "envelope_id": bill_data.get("envelope_id"),
            "name": bill_data.get("name"),
            "amount": float(bill_data.get("amount", 0)),
            "bill_type": bill_data.get("bill_type"),
            "due_date": bill_data.get("due_date").isoformat() if bill_data.get("due_date") else None,
            "paid": bill_data.get("paid", False)
        }
        return self.client.table("bills").insert(data).execute()
    
    def get_bills(self, profile_id: str, paid: bool = None) -> list:
        """Get bills for a profile."""
        query = self.client.table("bills").select("*").eq("profile_id", profile_id)
        if paid is not None:
            query = query.eq("paid", paid)
        response = query.execute()
        return response.data
    
    # Update other operations similarly for debts, sinking_funds, savings_goals, settings
    
    def delete_item(self, table_name: str, item_id: str) -> Dict[str, Any]:
        """Delete an item from any table."""
        return self.client.table(table_name).delete().eq("id", item_id).execute()

# Singleton instance
supabase_client = SupabaseClient()
```

### Step 7: Update Main Application

Update `app/main.py` to use Supabase:

1. **Add imports**:
```python
from db.supabase_client import supabase_client
from dotenv import load_dotenv
load_dotenv()
```

2. **Update session state initialization**:
```python
# Replace local database with Supabase
if 'supabase_client' not in st.session_state:
    try:
        st.session_state.supabase_client = supabase_client
    except Exception as e:
        st.error(f"Failed to connect to Supabase: {str(e)}")
        st.session_state.supabase_client = None
```

3. **Update data operations**:
Replace local list operations with Supabase client calls. For example:

```python
# Instead of: st.session_state.budget_profile.bills.append(new_bill)
# Use:
if st.session_state.supabase_client:
    response = st.session_state.supabase_client.create_bill(
        profile_id=st.session_state.current_profile_id,
        bill_data={
            "name": bill_name,
            "amount": bill_amount,
            "bill_type": bill_type,
            "due_date": due_date,
            "envelope_id": envelope_id,
            "paid": False
        }
    )
    if response.data:
        st.success(f"Bill '{bill_name}' saved to cloud!")
```

### Step 8: Set Up Row Level Security (RLS)

In Supabase SQL Editor, enable RLS and create policies:

```sql
-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE budget_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE envelopes ENABLE ROW LEVEL SECURITY;
ALTER TABLE bills ENABLE ROW LEVEL SECURITY;
ALTER TABLE debts ENABLE ROW LEVEL SECURITY;
ALTER TABLE sinking_funds ENABLE ROW LEVEL SECURITY;
ALTER TABLE savings_goals ENABLE ROW LEVEL SECURITY;
ALTER TABLE budget_settings ENABLE ROW LEVEL SECURITY;

-- Create policies for users table
CREATE POLICY "Users can read own data" ON users
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can insert own data" ON users
    FOR INSERT WITH CHECK (auth.uid() = id);

-- Create policies for budget_profiles
CREATE POLICY "Users can read own profiles" ON budget_profiles
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own profiles" ON budget_profiles
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Similar policies for other tables...
```

### Step 9: Add Authentication (Optional but Recommended)

1. **Install Supabase Auth helpers**:
```bash
pip install supabase-auth-helpers
```

2. **Create authentication component** in `app/auth.py`:

```python
import streamlit as st
from supabase_auth_helpers import supabase_auth

def show_auth_page():
    """Show authentication page."""
    st.title("🔐 Authentication")
    
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        
        if st.button("Login"):
            try:
                # Implement Supabase auth login
                user = supabase_auth.sign_in(email=email, password=password)
                st.session_state.user = user
                st.success("Logged in successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Login failed: {str(e)}")
    
    with tab2:
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_password")
        confirm_password = st.text_input("Confirm Password", type="password")
        
        if st.button("Sign Up"):
            if password != confirm_password:
                st.error("Passwords don't match!")
            else:
                try:
                    # Implement Supabase auth signup
                    user = supabase_auth.sign_up(email=email, password=password)
                    st.success("Account created! Please check your email to verify.")
                except Exception as e:
                    st.error(f"Signup failed: {str(e)}")
```

### Step 10: Deploy to Streamlit Cloud (Optional)

1. Push your code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repository
4. Add your environment variables in Streamlit Cloud:
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - `SUPABASE_SERVICE_ROLE_KEY`
5. Deploy!

## 🔧 Testing the Connection

Create a test script `test_supabase.py`:

```python
import sys
import os
sys.path.append('.')

from db.supabase_client import supabase_client

def test_connection():
    try:
        # Test connection by fetching users (empty at first)
        response = supabase_client.client.table("users").select("*").limit(1).execute()
        print("✅ Supabase connection successful!")
        print(f"Response: {response}")
        return True
    except Exception as e:
        print(f"❌ Supabase connection failed: {str(e)}")
        return False

if __name__ == "__main__":
    test_connection()
```

## 🚨 Security Notes

1. **Never commit `.env` file** to GitHub
2. **Use environment variables** in production
3. **Restrict RLS policies