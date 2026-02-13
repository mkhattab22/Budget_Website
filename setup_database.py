#!/usr/bin/env python3
"""
Script to help set up the Supabase database.
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def print_supabase_instructions():
    """Print instructions for setting up Supabase database."""
    print("=" * 70)
    print("SUPABASE DATABASE SETUP INSTRUCTIONS")
    print("=" * 70)
    
    print("\n📋 STEP 1: Go to your Supabase Dashboard")
    print("   URL: https://app.supabase.com")
    print("   Select your project: yqsjfmyeogmdydhjxinj")
    
    print("\n📋 STEP 2: Open SQL Editor")
    print("   In the left sidebar, click 'SQL Editor'")
    
    print("\n📋 STEP 3: Create a new query")
    print("   Click 'New query' button")
    
    print("\n📋 STEP 4: Copy and paste the SQL script")
    print("   Open the file: supabase_setup.sql")
    print("   Copy ALL the SQL code")
    print("   Paste it into the SQL Editor")
    
    print("\n📋 STEP 5: Run the SQL script")
    print("   Click the 'Run' button (or press Ctrl+Enter)")
    print("   Wait for execution to complete")
    
    print("\n📋 STEP 6: Verify the tables were created")
    print("   Go to 'Table Editor' in the left sidebar")
    print("   You should see these tables:")
    print("     - users")
    print("     - budget_profiles")
    print("     - envelopes")
    print("     - bills")
    print("     - debts")
    print("     - sinking_funds")
    print("     - savings_goals")
    print("     - budget_settings")
    
    print("\n📋 STEP 7: Test the connection")
    print("   Run: python test_supabase.py")
    print("   You should see '✅ Connection successful!'")
    
    print("\n" + "=" * 70)
    print("TROUBLESHOOTING")
    print("=" * 70)
    
    print("\n🔧 If you get connection errors:")
    print("   1. Check your internet connection")
    print("   2. Verify your Supabase project is active")
    print("   3. Make sure the SQL script ran successfully")
    print("   4. Check that your API keys in .env are correct")
    
    print("\n🔧 If tables don't appear:")
    print("   1. Refresh the Table Editor page")
    print("   2. Check for SQL errors in the SQL Editor")
    print("   3. Make sure you ran the entire SQL script")
    
    print("\n" + "=" * 70)
    print("NEXT STEPS AFTER DATABASE SETUP")
    print("=" * 70)
    
    print("\n🚀 1. Install dependencies:")
    print("   pip install -r requirements.txt")
    
    print("\n🚀 2. Test the full connection:")
    print("   python test_supabase.py")
    
    print("\n🚀 3. Start the application:")
    print("   streamlit run app/main.py")
    
    print("\n🚀 4. For Supabase integration:")
    print("   Use app/main_supabase.py as a reference")
    print("   Or update app/main.py to use the Supabase client")

def check_environment():
    """Check if environment variables are set."""
    print("🔍 Checking environment variables...")
    
    required_vars = ['SUPABASE_URL', 'SUPABASE_KEY', 'DATABASE_URL']
    all_set = True
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"   ✅ {var}: Set")
            if var == 'SUPABASE_KEY':
                print(f"      Value: {value[:30]}...")
            elif var == 'DATABASE_URL':
                # Hide password in output
                safe_url = value.replace(os.getenv('DATABASE_URL', '').split('@')[0].split(':')[2], '***')
                print(f"      Value: {safe_url}")
        else:
            print(f"   ❌ {var}: Missing")
            all_set = False
    
    return all_set

if __name__ == "__main__":
    print("🔧 Supabase Database Setup Helper")
    print("-" * 40)
    
    # Check environment
    if not check_environment():
        print("\n⚠️  Some environment variables are missing.")
        print("   Make sure .env file exists and contains all required variables.")
    
    # Print instructions
    print_supabase_instructions()
    
    # Ask if user wants to proceed
    print("\n" + "=" * 70)
    response = input("Ready to proceed with database setup? (yes/no): ")
    
    if response.lower() in ['yes', 'y']:
        print("\n✅ Great! Follow the instructions above.")
        print("   After setting up the database, run: python test_supabase.py")
    else:
        print("\n⚠️  Database setup postponed.")
        print("   You can run this script again when ready.")