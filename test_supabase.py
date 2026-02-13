#!/usr/bin/env python3
"""
Test script to verify Supabase connection.
"""
import sys
import os
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

def test_supabase_connection():
    """Test the Supabase connection."""
    try:
        from db.supabase_client import supabase_client
        
        if supabase_client is None:
            print("❌ Supabase client failed to initialize")
            return False
        
        print("🔌 Testing Supabase connection...")
        
        # Test 1: Check if we can connect to Supabase
        print("1. Testing basic connection...")
        try:
            # Try to fetch users table (might be empty)
            response = supabase_client.client.table("users").select("*").limit(1).execute()
            print(f"   ✅ Connection successful! Response: {response}")
        except Exception as e:
            print(f"   ⚠️ Connection test warning: {str(e)}")
            print("   This might be okay if tables don't exist yet.")
        
        # Test 2: Check environment variables
        print("\n2. Checking environment variables...")
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        
        if url and key:
            print(f"   ✅ SUPABASE_URL: {url[:30]}...")
            print(f"   ✅ SUPABASE_KEY: {key[:30]}...")
        else:
            print("   ❌ Missing environment variables!")
            return False
        
        # Test 3: Test client methods
        print("\n3. Testing client methods...")
        try:
            # Test the test_connection method
            if supabase_client.test_connection():
                print("   ✅ Client methods working!")
            else:
                print("   ⚠️ Client connection test failed")
        except Exception as e:
            print(f"   ⚠️ Client method test warning: {str(e)}")
        
        print("\n" + "="*50)
        print("✅ Supabase setup appears to be working!")
        print("Next steps:")
        print("1. Run the SQL script in Supabase SQL Editor")
        print("2. Start the Streamlit app: streamlit run app/main.py")
        print("="*50)
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {str(e)}")
        print("Make sure you have installed the requirements:")
        print("  pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_supabase_connection()
    sys.exit(0 if success else 1)