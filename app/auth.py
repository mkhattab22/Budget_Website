"""
Authentication module for Insane Finance App using Supabase Auth.
"""
import streamlit as st
import os
import sys
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from db.supabase_client import supabase_client
    SUPABASE_AVAILABLE = supabase_client is not None
except ImportError:
    SUPABASE_AVAILABLE = False
    supabase_client = None

class AuthManager:
    """Authentication manager for Supabase."""
    
    def __init__(self):
        self.supabase = supabase_client.client if supabase_client else None
    
    def sign_up(self, email: str, password: str) -> Dict[str, Any]:
        """Sign up a new user."""
        try:
            response = self.supabase.auth.sign_up({
                "email": email,
                "password": password
            })
            return {
                "success": True,
                "user": response.user,
                "session": response.session
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def sign_in(self, email: str, password: str) -> Dict[str, Any]:
        """Sign in an existing user."""
        try:
            response = self.supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            return {
                "success": True,
                "user": response.user,
                "session": response.session
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def sign_out(self) -> bool:
        """Sign out the current user."""
        try:
            self.supabase.auth.sign_out()
            return True
        except Exception as e:
            print(f"Sign out error: {str(e)}")
            return False
    
    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """Get the current authenticated user."""
        try:
            if not self.supabase:
                return None
            response = self.supabase.auth.get_user()
            if hasattr(response, 'user'):
                return response.user
            return None
        except Exception as e:
            print(f"Get user error: {str(e)}")
            return None
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated."""
        return self.get_current_user() is not None

def show_auth_page():
    """Show authentication page with sign up and sign in options."""
    st.title("🔐 Authentication")
    
    if not SUPABASE_AVAILABLE or not supabase_client:
        st.error("Supabase authentication is not available. Please check your configuration.")
        st.info("You can still use the app with local session storage.")
        return False
    
    auth_manager = AuthManager()
    
    # Check if user is already authenticated
    current_user = auth_manager.get_current_user()
    if current_user:
        st.success(f"✅ Already signed in as: {current_user.email}")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Continue to App"):
                st.session_state.authenticated = True
                st.session_state.user_email = current_user.email
                st.session_state.user_id = current_user.id
                st.rerun()
        
        with col2:
            if st.button("Sign Out"):
                if auth_manager.sign_out():
                    st.session_state.authenticated = False
                    st.session_state.user_email = None
                    st.session_state.user_id = None
                    st.success("Signed out successfully!")
                    st.rerun()
                else:
                    st.error("Failed to sign out")
        
        return True
    
    # Create tabs for sign in and sign up
    tab1, tab2 = st.tabs(["Sign In", "Sign Up"])
    
    with tab1:
        st.subheader("Sign In to Your Account")
        
        with st.form("sign_in_form"):
            email = st.text_input("Email", key="sign_in_email")
            password = st.text_input("Password", type="password", key="sign_in_password")
            remember = st.checkbox("Remember me", value=True)
            
            submitted = st.form_submit_button("Sign In")
            
            if submitted:
                if not email or not password:
                    st.error("Please enter both email and password")
                else:
                    with st.spinner("Signing in..."):
                        result = auth_manager.sign_in(email, password)
                        
                        if result["success"]:
                            st.success("✅ Signed in successfully!")
                            st.session_state.authenticated = True
                            st.session_state.user_email = email
                            st.session_state.user_id = result["user"].id
                            st.rerun()
                        else:
                            st.error(f"Sign in failed: {result['error']}")
    
    with tab2:
        st.subheader("Create New Account")
        
        with st.form("sign_up_form"):
            email = st.text_input("Email", key="sign_up_email")
            password = st.text_input("Password", type="password", key="sign_up_password")
            confirm_password = st.text_input("Confirm Password", type="password", key="sign_up_confirm")
            
            submitted = st.form_submit_button("Sign Up")
            
            if submitted:
                if not email or not password:
                    st.error("Please enter both email and password")
                elif password != confirm_password:
                    st.error("Passwords do not match")
                elif len(password) < 6:
                    st.error("Password must be at least 6 characters")
                else:
                    with st.spinner("Creating account..."):
                        result = auth_manager.sign_up(email, password)
                        
                        if result["success"]:
                            st.success("✅ Account created successfully!")
                            st.info("Please check your email to verify your account.")
                            
                            # Auto sign in after sign up
                            sign_in_result = auth_manager.sign_in(email, password)
                            if sign_in_result["success"]:
                                st.session_state.authenticated = True
                                st.session_state.user_email = email
                                st.session_state.user_id = sign_in_result["user"].id
                                st.rerun()
                        else:
                            st.error(f"Sign up failed: {result['error']}")
    
    # Demo mode option
    st.divider()
    st.subheader("Quick Start")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Try Demo Mode", type="secondary"):
            st.session_state.authenticated = True
            st.session_state.user_email = "demo@example.com"
            st.session_state.user_id = "demo-user-id"
            st.session_state.demo_mode = True
            st.success("Entering demo mode...")
            st.rerun()
    
    with col2:
        if st.button("Skip Authentication", type="secondary"):
            st.session_state.authenticated = True
            st.session_state.user_email = "local@example.com"
            st.session_state.user_id = "local-user-id"
            st.session_state.demo_mode = False
            st.info("Using local session storage only")
            st.rerun()
    
    return False

def check_auth():
    """Check if user is authenticated, show auth page if not."""
    # Initialize session state
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user_email' not in st.session_state:
        st.session_state.user_email = None
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'demo_mode' not in st.session_state:
        st.session_state.demo_mode = False
    
    # If not authenticated, show auth page
    if not st.session_state.authenticated:
        show_auth_page()
        st.stop()  # Stop execution until authenticated
    
    # Return user info
    return {
        "authenticated": True,
        "email": st.session_state.user_email,
        "user_id": st.session_state.user_id,
        "demo_mode": st.session_state.demo_mode
    }

def show_user_profile():
    """Show user profile in sidebar."""
    with st.sidebar:
        if st.session_state.authenticated:
            st.divider()
            st.subheader("👤 User Profile")
            
            if st.session_state.demo_mode:
                st.info("Demo Mode")
            else:
                st.success(f"Signed in as: {st.session_state.user_email}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Sign Out", type="secondary"):
                    if SUPABASE_AVAILABLE and supabase_client:
                        auth_manager = AuthManager()
                        auth_manager.sign_out()
                    
                    st.session_state.authenticated = False
                    st.session_state.user_email = None
                    st.session_state.user_id = None
                    st.session_state.demo_mode = False
                    st.success("Signed out successfully!")
                    st.rerun()
            
            with col2:
                if st.button("Switch Account", type="secondary"):
                    st.session_state.authenticated = False
                    st.session_state.user_email = None
                    st.session_state.user_id = None
                    st.session_state.demo_mode = False
                    st.rerun()

def get_user_profile_id() -> str:
    """Get or create a budget profile ID for the current user."""
    if not st.session_state.authenticated:
        return None
    
    # For demo mode, use a fixed ID
    if st.session_state.demo_mode:
        return "demo-profile-id"
    
    # For authenticated users, check if they have a profile
    if 'current_profile_id' not in st.session_state:
        st.session_state.current_profile_id = None
    
    # If we have Supabase, try to get/create profile
    if SUPABASE_AVAILABLE and supabase_client and st.session_state.user_id:
        try:
            # Check if user has any profiles
            profiles = supabase_client.get_user_budget_profiles(st.session_state.user_id)
            
            if profiles:
                # Use the first profile
                st.session_state.current_profile_id = profiles[0]['id']
            else:
                # Create a new profile
                response = supabase_client.create_budget_profile(
                    st.session_state.user_id,
                    "My Budget"
                )
                if response.data:
                    st.session_state.current_profile_id = response.data[0]['id']
        
        except Exception as e:
            print(f"Error getting user profile: {str(e)}")
            # Fall back to local ID
            st.session_state.current_profile_id = f"local-profile-{st.session_state.user_id}"
    
    # If still no profile ID, create a local one
    if not st.session_state.current_profile_id:
        st.session_state.current_profile_id = f"local-profile-{st.session_state.user_id}"
    
    return st.session_state.current_profile_id