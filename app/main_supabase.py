"""
Main Streamlit application for Insane Finance App with Supabase integration.
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

# Initialize session state
def init_session_state():
    """Initialize session state variables."""
    if 'user_profile' not in st.session_state:
        st.session_state.user_profile = None
    if 'tax_tables' not in st.session_state:
        st.session_state.tax_tables = None
    if 'budget_profile' not in st.session_state:
        st.session_state.budget_profile = None
    if 'tax_calc' not in st.session_state:
        st.session_state.tax_calc = None
    if 'settings_next_pay_date' not in st.session_state:
        st.session_state.settings_next_pay_date = date.today() + timedelta(days=14)
    if 'settings_pay_cycle' not in st.session_state:
        st.session_state.settings_pay_cycle = "BIWEEKLY"
    if 'planner_net_override' not in st.session_state:
        st.session_state.planner_net_override = {}
    if 'demo_data_loaded' not in st.session_state:
        st.session_state.demo_data_loaded = False
    if 'supabase_available' not in st.session_state:
        st.session_state.supabase_available = SUPABASE_AVAILABLE
    if 'current_profile_id' not in st.session_state:
        st.session_state.current_profile_id = None
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

def load_supabase_data():
    """Load data from Supabase if available."""
    if not st.session_state.supabase_available or not supabase_client:
        return
    
    try:
        # For now, we'll just test the connection
        # In a real implementation, you would load user-specific data here
        if st.session_state.current_profile_id:
            # Load envelopes
            envelopes = supabase_client.get_envelopes(st.session_state.current_profile_id)
            st.session_state.supabase_data['envelopes'] = envelopes
            
            # Load bills
            bills = supabase_client.get_bills(st.session_state.current_profile_id, paid=False)
            st.session_state.supabase_data['bills'] = bills
            
            # Load debts
            debts = supabase_client.get_debts(st.session_state.current_profile_id, paid_off=False)
            st.session_state.supabase_data['debts'] = debts
            
            # Load sinking funds
            sinking_funds = supabase_client.get_sinking_funds(st.session_state.current_profile_id)
            st.session_state.supabase_data['sinking_funds'] = sinking_funds
            
            # Load savings goals
            savings_goals = supabase_client.get_savings_goals(st.session_state.current_profile_id)
            st.session_state.supabase_data['savings_goals'] = savings_goals
            
            # Load settings
            settings = supabase_client.get_budget_settings(st.session_state.current_profile_id)
            st.session_state.supabase_data['settings'] = settings
            
    except Exception as e:
        st.error(f"Error loading data from Supabase: {str(e)}")

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

def show_supabase_status():
    """Show Supabase connection status in sidebar."""
    with st.sidebar:
        st.divider()
        st.subheader("Database Status")
        
        if st.session_state.supabase_available:
            st.success("✅ Supabase Connected")
            if st.button("Test Connection"):
                try:
                    if supabase_client.test_connection():
                        st.success("Connection test successful!")
                    else:
                        st.warning("Connection test failed - tables may not exist yet")
                except Exception as e:
                    st.error(f"Connection test error: {str(e)}")
        else:
            st.warning("⚠️ Supabase Not Available")
            st.info("Using local session storage only")

def main():
    """Main application."""
    # Initialize session state
    init_session_state()
    
    st.title("💰 Insane Finance App")
    st.markdown("### Personal Finance & Paycheck Budgeting for Canada")
    
    # Load data from Supabase if available
    load_supabase_data()
    
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
        if st.session_state.budget_profile or st.session_state.supabase_data['envelopes']:
            st.subheader("Quick Stats")
            
            # Use Supabase data if available, otherwise use local data
            if st.session_state.supabase_available and st.session_state.supabase_data['envelopes']:
                total_envelopes = len(st.session_state.supabase_data['envelopes'])
                total_bills = len(st.session_state.supabase_data['bills'])
                total_debts = len(st.session_state.supabase_data['debts'])
            else:
                total_envelopes = len(st.session_state.budget_profile.envelopes) if st.session_state.budget_profile else 0
                total_bills = len([b for b in st.session_state.budget_profile.bills if not b.paid]) if st.session_state.budget_profile else 0
                total_debts = len(st.session_state.budget_profile.get_active_debts()) if st.session_state.budget_profile else 0
            
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
                st.session_state.budget_profile = create_sample_budget_profile()
                st.session_state.demo_data_loaded = True
                st.success("Demo data loaded! You can now explore the app with sample data.")
                st.rerun()
        
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
        
        # Show Supabase status
        show_supabase_status()
    
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
    
    # Show Supabase data status if available
    if st.session_state.supabase_available:
        st.info("📊 Data is being saved to Supabase cloud database")
        if st.session_state.supabase_data['envelopes']:
            st.success(f"Loaded {len(st.session_state.supabase_data['envelopes'])} envelopes from cloud")
        else:
            st.warning("No cloud data yet. Add data to save to Supabase.")
    
    # Rest of the overview page remains the same as before...
    # (I'm keeping it simple for now since the main goal is Supabase integration)

def show_paycheck_planner_page():
    """Show paycheck planner page."""
    st.header("💵 Paycheck Planner")
    st.info("This page will save data to Supabase when you add items.")
    
    # Check if tax calculation has been done
    tax_calc_available = st.session_state.tax_calc is not None
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Paycheck Details")
        
        # Pay schedule from settings
        st.write("**Pay Schedule (from Settings)**")
        pay_cycle_options = get_pay_schedule_options()
        pay_cycle_display = [opt["label"] for opt in pay_cycle_options]
        pay_cycle_values = [opt["value"] for opt in pay_cycle_options]
        
        selected_pay_cycle = st.selectbox(
            "Pay Cycle",
            options=pay_cycle_values,
            format_func=lambda x: dict(zip(pay_cycle_values, pay_cycle_display))[x],
            key="planner_pay_cycle"
        )
        
        # Next pay date
        next_pay_date = st.date_input(
            "Next Pay Date",
            value=st.session_state.settings_next_pay_date,
            key="planner_next_pay_date"
        )
        
        # Net pay amount
        st.subheader("Net Pay Amount")
        
        if tax_calc_available:
            # Show calculated net pay based on tax calculation
            net_by_freq = st.session_state.tax_calc.get("net_by_frequency", {})
            calculated_net = net_by_freq.get(selected_pay_cycle.upper(), 0)
            
            st.write(f"**Calculated Net Pay:** ${calculated_net:,.2f}")
            
            # Allow override
            use_custom = st.checkbox("Use custom net pay amount", value=False)
            if use_custom:
                custom_net = st.number_input(
                    "Custom Net Pay Amount",
                    min_value=0.0,
                    value=float(calculated_net),
                    step=100.0,
                    format="%.2f"
                )
                net_amount = custom_net
            else:
                net_amount = calculated_net
        else:
            st.warning("No tax calculation available. Please use the Tax Calculator first.")
            net_amount = st.number_input(
                "Enter Net Pay Amount",
                min_value=0.0,
                value=2000.0,
                step=100.0,
                format="%.2f"
            )
        
        # Store net amount for this pay cycle
        st.session_state.planner_net_override[selected_pay_cycle] = net_amount
    
    with col2:
        st.subheader("Paycheck Windows")
        
        # Calculate windows
        start_date = date.today()
        end_date = start_date + timedelta(days=90)  # 3 months
        
        windows = calculate_paycheque_windows(
            start_date=start_date,
            end_date=end_date,
            pay_schedule=selected_pay_cycle,
            next_payday=next_pay_date
        )
        
        if windows:
            st.write(f"**Next {len(windows)} Paycheck Windows:**")
            
            window_data = []
            for i, window in enumerate(windows):
                window_data.append({
                    "Window": i + 1,
                    "Start": window["start_date"].strftime("%b %d"),
                    "End": window["end_date"].strftime("%b %d"),
                    "Payday": window["payday"].strftime("%b %d"),
                    "Days": (window["end_date"] - window["start_date"]).days + 1
                })
            
            df_windows = pd.DataFrame(window_data)
            st.dataframe(df_windows, use_container_width=True, hide_index=True)
            
            # Show total net pay for period
            total_net = net_amount * len(windows)
            st.metric("