#!/usr/bin/env python3
"""
Complete setup test for Supabase integration.
"""
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_complete_setup():
    """Test the complete Supabase setup."""
    print("🔧 COMPLETE SUPABASE SETUP TEST")
    print("=" * 50)
    
    # Test 1: Environment variables
    print("\n1. Testing environment variables...")
    required_vars = ['SUPABASE_URL', 'SUPABASE_KEY', 'DATABASE_URL']
    env_ok = True
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"   ✅ {var}: OK")
        else:
            print(f"   ❌ {var}: MISSING")
            env_ok = False
    
    if not env_ok:
        print("\n⚠️  Fix environment variables before continuing.")
        return False
    
    # Test 2: Python dependencies
    print("\n2. Testing Python dependencies...")
    try:
        import supabase
        import streamlit
        import pandas
        import plotly
        from dotenv import load_dotenv
        print("   ✅ All required packages installed")
    except ImportError as e:
        print(f"   ❌ Missing package: {str(e)}")
        print("   Run: pip install -r requirements.txt")
        return False
    
    # Test 3: Supabase connection
    print("\n3. Testing Supabase connection...")
    try:
        from db.supabase_client import supabase_client
        
        if supabase_client is None:
            print("   ❌ Supabase client failed to initialize")
            return False
        
        # Try to connect
        try:
            response = supabase_client.client.table("users").select("*").limit(1).execute()
            print("   ✅ Supabase connection successful!")
            
            # Check if tables exist
            print("\n4. Checking database tables...")
            tables_to_check = ['users', 'budget_profiles', 'envelopes', 'bills', 'debts', 
                             'sinking_funds', 'savings_goals', 'budget_settings']
            
            for table in tables_to_check:
                try:
                    response = supabase_client.client.table(table).select("*").limit(1).execute()
                    print(f"   ✅ Table '{table}' exists")
                except Exception as e:
                    if "Could not find the table" in str(e):
                        print(f"   ❌ Table '{table}' not found")
                        print(f"      Run the SQL script in Supabase SQL Editor")
                        return False
                    else:
                        print(f"   ⚠️  Error checking table '{table}': {str(e)[:50]}...")
            
            print("\n" + "=" * 50)
            print("🎉 COMPLETE SETUP SUCCESSFUL!")
            print("=" * 50)
            print("\nYour Insane Finance App is now fully connected to Supabase!")
            print("\nNext steps:")
            print("1. Start the app: streamlit run app/main.py")
            print("2. Add data through the app interface")
            print("3. Check Supabase Table Editor to see your data")
            print("4. Data will persist across sessions in the cloud")
            
            return True
            
        except Exception as e:
            error_msg = str(e)
            if "Could not find the table" in error_msg:
                print("   ⚠️  Connected but tables don't exist yet")
                print("   Run the SQL script in Supabase SQL Editor")
                print(f"   Error: {error_msg[:100]}...")
            else:
                print(f"   ❌ Connection error: {error_msg[:100]}...")
            return False
            
    except Exception as e:
        print(f"   ❌ Failed to import Supabase client: {str(e)}")
        return False

def main():
    """Main function."""
    success = test_complete_setup()
    
    if not success:
        print("\n" + "=" * 50)
        print("⚠️  SETUP INCOMPLETE")
        print("=" * 50)
        print("\nFollow these steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Run SQL script in Supabase SQL Editor")
        print("3. Run this test again: python test_complete_setup.py")
        print("\nDetailed instructions in: SUPABASE_SETUP.md")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()