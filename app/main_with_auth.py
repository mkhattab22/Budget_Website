"""
Main Streamlit application for Insane Finance App with Authentication.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Any
import json
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import authentication module
from app.auth import check_auth, show_user_profile, get_user_profile_id

# Import other modules
from tax.models import Province, PaySchedule, UserTaxProfile, IncomeStream
from tax.loader import TaxTableLoader
from tax.calculator import TaxCalculator
from budget.models import (
    UserBudgetProfile, Envelope, Bill, Debt, SinkingFund, SavingsGoal,
    BudgetSettings, EnvelopeCategory, DebtStrategy, CashflowForecast
)
from budget.allocator import PaycheckAllocator, CashflowForecaster
from app.utils import calculate_next_payday, calculate_paycheque_windows, assign_bills_to_windows, format_currency, format_date, get_pay_schedule_options

# Import Supabase client
try:
    from db.supabase_client import supabase_client
    SUPABASE_AVAILABLE = supabase_client is not None
except ImportError:
    SUPABASE_AVAILABLE = False
    supabase_client = None

# Page configuration
st.set_page_config(
    page_title="Insane Finance App",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

def init_session_state():
    """Initialize session state variables."""
    # Authentication is handled by check_auth()
    
    # Tax and budget states
    if 'tax_tables' not in st.session_state:
        st.session_state.tax_tables = None
    if 'budget_profile' not in st.session_state:
        st.session_state.budget_profile = None
    if 'tax_calc' not in st.session_state:
        st.session_state.tax_calc = None
    
    # Settings
    if 'settings_next_pay_date' not in st.session_state:
        st.session_state.settings_next_pay_date = date.today() + timedelta(days=14)
    if 'settings_pay_cycle' not in st.session_state:
        st.session_state.settings_pay_cycle = "BIWEEKLY"
    
    # Planner
    if 'planner_net_override' not in st.session_state:
        st.session_state.planner_net_override = {}
    
    # Demo data
    if 'demo_data_loaded' not in st.session_state:
        st.session_state.demo_data_loaded = False
    
    # Supabase data cache
    if 'supabase_data' not in st.session_state:
        st.session_state.supabase_data = {
            'envelopes': [],
            'bills': [],
            'debts': [],
            'sinking_funds': [],
            'savings_goals': [],
            'settings': None
        }

def load_tax_tables(year: int) -> bool:
    """Load tax tables for a specific year."""
    try:
        loader = TaxTableLoader()
        tax_tables = loader.load_year(year)
        if tax_tables:
            st.session_state.tax_tables = tax_tables
            return True
        else:
            st.error(f"No tax tables found for year {year}. Please import tax tables first.")
            return False
    except Exception as e:
        st.error(f"Error loading tax tables: {str(e)}")
        return False

def calculate_tax(gross_income: float, province: Province, tax_year: int) -> Dict[str, Any]:
    """Calculate tax for given income and province."""
    if not st.session_state.tax_tables or st.session_state.tax_tables.year != tax_year:
        if not load_tax_tables(tax_year):
            return {}
    
    try:
        # Create a temporary user profile
        profile = UserTaxProfile(
            province=province,
            tax_year=tax_year,
            pay_schedule=PaySchedule.BIWEEKLY,
            income_streams=[
                IncomeStream(
                    name="Primary Job",
                    type="salary",
                    gross_amount=gross_income,
                    frequency=PaySchedule.BIWEEKLY,
                    start_date=date.today()
                )
            ]
        )
        
        calculator = TaxCalculator(st.session_state.tax_tables)
        result = calculator.calculate_annual_tax(profile)
        
        # Store tax calculation results in session state
        tax_result = {
            "gross_income": result.gross_income,
            "federal_tax": result.federal_tax,
            "provincial_tax": result.provincial_tax,
            "cpp_contribution": result.cpp_contribution,
            "ei_contribution": result.ei_contribution,
            "total_tax": result.total_tax,
            "net_income": result.net_income,
            "effective_tax_rate": result.effective_tax_rate,
            "per_pay_period": result.per_pay_period,
            "annual_net": result.net_income,
            "annual_gross": result.gross_income,
            "net_by_frequency": {
                "WEEKLY": result.net_income / 52,
                "BIWEEKLY": result.net_income / 26,
                "SEMIMONTHLY": result.net_income / 24,
                "MONTHLY": result.net_income / 12
            }
        }
        
        st.session_state.tax_calc = tax_result
        return tax_result
    except Exception as e:
        st.error(f"Error calculating tax: {str(e)}")
        return {}

def create_empty_budget_profile() -> UserBudgetProfile:
    """Create an empty budget profile."""
    # Create empty collections
    envelopes = []
    bills = []
    debts = []
    sinking_funds = []
    savings_goals = []
    
    # Create default settings
    settings = BudgetSettings(
        checking_buffer=500.00,
        emergency_fund_target=10000.00,
        debt_strategy=DebtStrategy.AVALANCHE,
        savings_rate=0.20,
        discretionary_percentage=0.30,
        round_to_nearest=10.00
    )
    
    return UserBudgetProfile(
        envelopes=envelopes,
        bills=bills,
        debts=debts,
        sinking_funds=sinking_funds,
        savings_goals=savings_goals,
        settings=settings
    )

def create_sample_budget_profile() -> UserBudgetProfile:
    """Create a sample budget profile for demonstration."""
    # Create sample envelopes for demonstration
    envelopes = [
        Envelope(
            id="envelope_1",
            category=EnvelopeCategory.BILLS,
            name="Rent/Mortgage",
            target_amount=1500.00,
            current_balance=0.0,
            priority=1
        ),
        Envelope(
            id="envelope_2",
            category=EnvelopeCategory.BILLS,
            name="Utilities",
            target_amount=300.00,
            current_balance=0.0,
            priority=2
        ),
        Envelope(
            id="envelope_3",
            category=EnvelopeCategory.DEBT,
            name="Credit Card",
            target_amount=200.00,
            current_balance=0.0,
            priority=3
        ),
        Envelope(
            id="envelope_4",
            category=EnvelopeCategory.SINKING,
            name="Car Maintenance",
            target_amount=1000.00,
            current_balance=250.00,
            priority=4
        ),
        Envelope(
            id="envelope_5",
            category=EnvelopeCategory.SAVINGS,
            name="Emergency Fund",
            target_amount=10000.00,
            current_balance=3000.00,
            priority=5
        ),
        Envelope(
            id="envelope_6",
            category=EnvelopeCategory.DISCRETIONARY,
            name="Fun Money",
            target_amount=400.00,
            current_balance=0.0,
            priority=10
        )
    ]
    
    # Create sample bills for demonstration
    today = date.today()
    bills = [
        Bill(
            id="bill_1",
            name="Rent",
            amount=1500.00,
            bill_type="fixed",
            envelope_id="envelope_1",
            due_date=today.replace(day=1) + timedelta(days=30),
            paid=False
        ),
        Bill(
            id="bill_2",
            name="Electricity",
            amount=120.00,
            bill_type="variable",
            envelope_id="envelope_2",
            due_date=today + timedelta(days=15),
            paid=False
        )
    ]
    
    # Create sample debts for demonstration
    debts = [
        Debt(
            id="debt_1",
            name="Credit Card",
            balance=5000.00,
            apr=0.1999,  # 19.99%
            minimum_payment=200.00,
            due_date=today + timedelta(days=20),
            envelope_id="envelope_3",
            strategy=DebtStrategy.AVALANCHE,
            paid_off=False
        )
    ]
    
    # Create sample sinking fund for demonstration
    sinking_funds = [
        SinkingFund(
            id="sinking_1",
            name="Car Maintenance",
            target_amount=1000.00,
            current_balance=250.00,
            deadline=today + timedelta(days=90),
            envelope_id="envelope_4"
        )
    ]
    
    # Create sample savings goal for demonstration
    savings_goals = [
        SavingsGoal(
            id="savings_1",
            name="Emergency Fund",
            target_amount=10000.00,
            current_balance=3000.00,
            target_date=today + timedelta(days=365),
            monthly_contribution=500.00,
            envelope_id="envelope_5"
        )
    ]
    
    # Create default settings
    settings = BudgetSettings(
        checking_buffer=500.00,
        emergency_fund_target=10000.00,
        debt_strategy=DebtStrategy.AVALANCHE,
        savings_rate=0.20,
        discretionary_percentage=0.30,
        round_to_nearest=10.00
    )
    
    return UserBudgetProfile(
        envelopes=envelopes,
        bills=bills,
        debts=debts,
        sinking_funds=sinking_funds,
        savings_goals=savings_goals,
        settings=settings
    )

def load_demo_data():
    """Load demo data when user explicitly requests it."""
    st.session_state.budget_profile = create_sample_budget_profile()
    st.session_state.demo_data_loaded = True
    st.success("Demo data loaded! You can now explore the app with sample data.")
    st.rerun()

def main():
    """Main application."""
    # Initialize session state
    init_session_state()
    
    # Check authentication - this will show auth page if not authenticated
    user_info = check_auth()
    
    # Show user profile in sidebar
    show_user_profile()
    
    # Main app header
    st.title("💰 Insane Finance App")
    st.markdown("### Personal Finance & Paycheck Budgeting for Canada")
    
    # Welcome message
    if user_info['demo_mode']:
        st.info("👋 Welcome to Demo Mode! Your data will be saved locally.")
    else:
        st.success(f"👋 Welcome back, {user_info['email']}!")
    
    # Sidebar navigation
    with st.sidebar:
        st.image("https://img.icons8.com/color/96/000000/money-bag.png", width=80)
        st.title("Navigation")
        
        page = st.radio(
            "Go to",
            [
                "Overview",
                "Paycheck Planner", 
                "Tax Calculator",
                "Bills & Calendar",
                "Debts",
                "Sinking Funds",
                "Reports",
                "Settings"
            ]
        )
        
        st.divider()
        
        # Quick stats
        if st.session_state.budget_profile:
            st.subheader("Quick Stats")
            total_envelopes = len(st.session_state.budget_profile.envelopes)
            total_bills = len([b for b in st.session_state.budget_profile.bills if not b.paid])
            total_debts = len(st.session_state.budget_profile.get_active_debts())
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Envelopes", total_envelopes)
                st.metric("Active Debts", total_debts)
            with col2:
                st.metric("Pending Bills", total_bills)
        
        st.divider()
        
        # Demo data button
        if not st.session_state.demo_data_loaded:
            if st.button("📊 Load Demo Data", type="secondary"):
                load_demo_data()
        
        # Tax year selector
        tax_year = st.selectbox(
            "Tax Year",
            options=[2024, 2023, 2022],
            index=0
        )
        
        if st.button("Load Tax Tables"):
            with st.spinner("Loading tax tables..."):
                if load_tax_tables(tax_year):
                    st.success(f"Tax tables for {tax_year} loaded successfully!")
    
    # Page routing
    if page == "Overview":
        show_overview_page()
    elif page == "Paycheck Planner":
        show_paycheck_planner_page()
    elif page == "Tax Calculator":
        show_tax_calculator_page()
    elif page == "Bills & Calendar":
        show_bills_calendar_page()
    elif page == "Debts":
        show_debts_page()
    elif page == "Sinking Funds":
        show_sinking_funds_page()
    elif page == "Reports":
        show_reports_page()
    elif page == "Settings":
        show_settings_page()

def show_overview_page():
    """Show overview dashboard."""
    st.header("📊 Overview")
    
    # Initialize empty budget profile if needed
    if not st.session_state.budget_profile:
        st.session_state.budget_profile = create_empty_budget_profile()
    
    # Create columns for metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_envelopes = len(st.session_state.budget_profile.envelopes)
        st.metric("Total Envelopes", total_envelopes)
    
    with col2:
        pending_bills = len([b for b in st.session_state.budget_profile.bills if not b.paid])
        st.metric("Pending Bills", pending_bills)
    
    with col3:
        active_debts = len(st.session_state.budget_profile.get_active_debts())
        st.metric("Active Debts", active_debts)
    
    with col4:
        total_savings = sum(
            e.current_balance for e in st.session_state.budget_profile.envelopes 
            if e.category in [EnvelopeCategory.SAVINGS, EnvelopeCategory.INVESTING]
        )
        st.metric("Total Savings", f"${total_savings:,.2f}")
    
    st.divider()
    
    # Show Supabase status if available
    if SUPABASE_AVAILABLE and not st.session_state.get('demo_mode', False):
        st.info("📊 Your data is being saved to Supabase cloud database")
    
    # Rest of overview page...
    # (Keeping it simple for this example)

def show_paycheck_planner_page():
    """Show paycheck planner page."""
    st.header("💵 Paycheck Planner")
    st.write("This feature helps you plan your paycheck allocations.")
    
    # Simple form for demonstration
    with st.form("paycheck_form"):
        income = st.number_input("Monthly Income", value=5000.0)
        expenses = st.number_input("Monthly Expenses", value=3000.0)
        
        submitted = st.form_submit_button("Calculate")
        
        if submitted:
            savings = income - expenses
            st.success(f"Monthly Savings: ${savings:,.2f}")

def show_tax_calculator_page():
    """Show tax calculator page."""
    st.header("🧮 Tax Calculator")
    
    col1, col2 = st.columns(2)
    
    with col1:
        income = st.number_input("Annual Income", value=60000.0)
        province = st.selectbox("Province", ["Ontario", "Quebec", "British Columbia"])
    
    with col2:
        if st.button("Calculate Tax"):
            # Simplified calculation for demo
            tax_rate = 0.25  # Simplified average tax rate
            tax_amount = income * tax_rate
            net_income = income - tax_amount
            
            st.metric("Estimated Tax", f"${tax_amount:,.2f}")
            st.metric("Net Income", f"${net_income:,.2f}")

def show_bills_calendar_page():
    """Show bills and calendar page."""
    st.header("📅 Bills & Calendar")
    st.write("Manage your bills and payment schedule here.")
    
    # Simple bill entry form
    with st.form("bill_form"):
        name = st.text_input("Bill Name")
        amount = st.number_input("Amount", value=100.0)
        due_date = st.date_input("Due Date")
        
        submitted = st.form_submit_button("Add Bill")
        
        if submitted and name:
            st.success(f"Added bill: {name} for ${amount:,.2f} due {due_date}")

def show_debts_page():
    """Show debts management page."""
    st.header("💳 Debts")
    st.write("Track and manage your debts.")
    
    # Simple debt entry form
    with st.form("debt_form"):
        name = st.text_input("Debt Name")
        balance = st.number_input("Balance", value=5000.0)
        interest = st.number_input("Interest Rate (%)", value=5.0)
        
        submitted = st.form_submit_button("Add Debt")
        
        if submitted and name:
            st.success(f"Added debt: {name} with balance ${balance:,.2f}")

def show_sinking_funds_page():
    """Show sinking funds management page."""
    st.header("🎯 Sinking Funds")
    st.write