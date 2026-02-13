"""
Main Streamlit application for Insane Finance App.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Any
import json
import os
import sys
import math


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
from db.models import Database, default_db
from app.utils import calculate_next_payday, calculate_paycheque_windows, assign_bills_to_windows, format_currency, format_date, get_pay_schedule_options


# Page configuration
st.set_page_config(
    page_title="Insane Finance App",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'user_profile' not in st.session_state:
    st.session_state.user_profile = None
if 'tax_tables' not in st.session_state:
    st.session_state.tax_tables = None
if 'budget_profile' not in st.session_state:
    st.session_state.budget_profile = None
if 'db' not in st.session_state:
    st.session_state.db = default_db
    st.session_state.db.init_db()

# Tax calculation results
if 'tax_calc' not in st.session_state:
    st.session_state.tax_calc = None

# Pay schedule settings
if 'settings_next_pay_date' not in st.session_state:
    st.session_state.settings_next_pay_date = date.today() + timedelta(days=14)
if 'settings_pay_cycle' not in st.session_state:
    st.session_state.settings_pay_cycle = "BIWEEKLY"

# Planner net pay overrides
if 'planner_net_override' not in st.session_state:
    st.session_state.planner_net_override = {}

# Demo data flag
if 'demo_data_loaded' not in st.session_state:
    st.session_state.demo_data_loaded = False


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
    """Create a sample budget profile for demonstration (only when explicitly requested)."""
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


def delete_item(item_type: str, item_id: str):
    """Delete an item from the budget profile."""
    if not st.session_state.budget_profile:
        return
    
    if item_type == "bill":
        st.session_state.budget_profile.bills = [
            b for b in st.session_state.budget_profile.bills if b.id != item_id
        ]
    elif item_type == "debt":
        st.session_state.budget_profile.debts = [
            d for d in st.session_state.budget_profile.debts if d.id != item_id
        ]
    elif item_type == "envelope":
        st.session_state.budget_profile.envelopes = [
            e for e in st.session_state.budget_profile.envelopes if e.id != item_id
        ]
    elif item_type == "sinking_fund":
        st.session_state.budget_profile.sinking_funds = [
            sf for sf in st.session_state.budget_profile.sinking_funds if sf.id != item_id
        ]
    elif item_type == "savings_goal":
        st.session_state.budget_profile.savings_goals = [
            sg for sg in st.session_state.budget_profile.savings_goals if sg.id != item_id
        ]
    
    st.success(f"{item_type.replace('_', ' ').title()} deleted successfully!")
    st.rerun()


def main():
    """Main application."""
    st.title("💰 Insane Finance App")
    st.markdown("### Personal Finance & Paycheck Budgeting for Canada")
    
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
    
    # Next payday and predicted balance
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Next Payday")
        next_payday = date.today() + timedelta(days=14)  # Example: biweekly
        st.metric("Date", next_payday.strftime("%B %d, %Y"))
        
        # Example paycheck - only show if tax calculation has been done
        if st.session_state.tax_calc:
            estimated_net = st.session_state.tax_calc.get("annual_net", 0) / 26
            st.metric("Estimated Net", f"${estimated_net:,.2f}")
        else:
            st.metric("Estimated Net", "$0.00")
    
    with col2:
        st.subheader("Predicted Balance")
        
        # Simple cashflow forecast
        if st.session_state.budget_profile:
            forecaster = CashflowForecaster(st.session_state.budget_profile)
            
            start_date = date.today()
            end_date = start_date + timedelta(days=30)
            
            # Create sample paycheck allocations
            paycheck_allocations = []
            if st.session_state.tax_calc:
                paycheck_allocation = {
                    "date": start_date + timedelta(days=14),
                    "net_amount": st.session_state.tax_calc.get("annual_net", 0) / 26
                }
                paycheck_allocations.append(paycheck_allocation)
            
            # This would be populated with real data
            forecast = CashflowForecast(
                start_date=start_date,
                end_date=end_date,
                starting_balance=0.00,  # Start with 0 balance
                daily_balances={},
                transactions=[],
                alerts=[]
            )
            
            st.metric("Current Balance", "$0.00")
            st.metric("30-day Min", "$0.00")
    
    st.divider()
    
    # Upcoming bills
    st.subheader("📅 Upcoming Bills (Next 30 Days)")
    
    if st.session_state.budget_profile:
        today = date.today()
        next_30_days = today + timedelta(days=30)
        
        upcoming_bills = [
            bill for bill in st.session_state.budget_profile.bills
            if not bill.paid and today <= bill.due_date <= next_30_days
        ]
        
        if upcoming_bills:
            bill_data = []
            for bill in upcoming_bills:
                envelope = st.session_state.budget_profile.get_envelope(bill.envelope_id)
                bill_data.append({
                    "Bill": bill.name,
                    "Amount": f"${bill.amount:,.2f}",
                    "Due Date": bill.due_date.strftime("%b %d, %Y"),
                    "Envelope": envelope.name if envelope else "Unknown",
                    "Status": "Paid" if bill.paid else "Pending"
                })
            
            df_bills = pd.DataFrame(bill_data)
            st.dataframe(df_bills, use_container_width=True, hide_index=True)
        else:
            st.info("No upcoming bills in the next 30 days.")
    
    # Alerts section
    st.divider()
    st.subheader("⚠️ Alerts")
    
    # Only show alerts if there are actual items
    if st.session_state.budget_profile:
        alerts = []
        
        # Check for sinking funds
        for fund in st.session_state.budget_profile.sinking_funds:
            progress = (fund.current_balance / fund.target_amount * 100) if fund.target_amount > 0 else 0
            days_remaining = (fund.deadline - date.today()).days
            if days_remaining > 0 and days_remaining <= 30:
                alerts.append(f"{fund.name} sinking fund is {progress:.0f}% funded ({days_remaining} days remaining)")
        
        # Check for debts due soon
        for debt in st.session_state.budget_profile.get_active_debts():
            days_until = (debt.due_date - date.today()).days
            if 0 <= days_until <= 7:
                alerts.append(f"{debt.name} payment due in {days_until} days")
        
        # Check for savings goals
        for goal in st.session_state.budget_profile.savings_goals:
            progress = (goal.current_balance / goal.target_amount * 100) if goal.target_amount > 0 else 0
            if progress < 50:
                alerts.append(f"{goal.name} is {progress:.0f}% of target")
        
        if alerts:
            for alert in alerts:
                st.warning(alert)
        else:
            st.info("No alerts at this time.")


def show_paycheck_planner_page():
    """Show paycheck planner page."""
    st.header("💵 Paycheck Planner")
    
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
            st.metric("Total Net Pay (3 months)", f"${total_net:,.2f}")
        else:
            st.info("No paycheck windows calculated.")
    
    st.divider()
    
    # Bill assignment
    st.subheader("📋 Assign Bills to Paycheck Windows")
    
    if st.session_state.budget_profile and windows:
        # Get unpaid bills
        unpaid_bills = [b for b in st.session_state.budget_profile.bills if not b.paid]
        
        if unpaid_bills:
            # Convert bills to dict format for assignment
            bill_dicts = []
            for bill in unpaid_bills:
                envelope = st.session_state.budget_profile.get_envelope(bill.envelope_id)
                bill_dicts.append({
                    "id": bill.id,
                    "name": bill.name,
                    "amount": bill.amount,
                    "due_date": bill.due_date,
                    "envelope": envelope.name if envelope else "Unknown"
                })
            
            # Assign bills to windows
            assignments = assign_bills_to_windows(bill_dicts, windows)
            
            # Display assignments
            for i, window_bills in assignments.items():
                if window_bills:
                    with st.expander(f"Window {i+1}: {windows[i]['start_date'].strftime('%b %d')} - {windows[i]['end_date'].strftime('%b %d')}"):
                        bill_summary = []
                        total_window_bills = 0
                        
                        for bill in window_bills:
                            bill_summary.append({
                                "Bill": bill["name"],
                                "Amount": f"${bill['amount']:,.2f}",
                                "Due Date": bill["due_date"].strftime("%b %d"),
                                "Envelope": bill["envelope"]
                            })
                            total_window_bills += bill["amount"]
                        
                        if bill_summary:
                            df_summary = pd.DataFrame(bill_summary)
                            st.dataframe(df_summary, use_container_width=True, hide_index=True)
                            st.metric("Total Bills in Window", f"${total_window_bills:,.2f}")
                            
                            # Calculate remaining after bills
                            remaining = net_amount - total_window_bills
                            st.metric("Remaining After Bills", f"${remaining:,.2f}")
        else:
            st.info("No unpaid bills to assign.")
    else:
        st.info("No budget profile loaded or no windows calculated.")


def show_tax_calculator_page():
    """Show tax calculator page."""
    st.header("🧮 Tax Calculator")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Income Details")
        
        # Gross income
        gross_income = st.number_input(
            "Annual Gross Income ($)",
            min_value=0.0,
            value=60000.0,
            step=1000.0,
            format="%.2f"
        )
        
        # Province selection
        province_options = [p.value for p in Province]
        province_display = [p.name.replace("_", " ").title() for p in Province]
        
        selected_province = st.selectbox(
            "Province",
            options=province_options,
            format_func=lambda x: dict(zip(province_options, province_display))[x]
        )
        
        # Tax year
        tax_year = st.selectbox(
            "Tax Year",
            options=[2024, 2023, 2022],
            index=0
        )
    
    with col2:
        st.subheader("Calculation")
        
        if st.button("Calculate Tax", type="primary"):
            with st.spinner("Calculating taxes..."):
                result = calculate_tax(gross_income, Province(selected_province), tax_year)
                
                if result:
                    st.success("Tax calculation complete!")
                    
                    # Display results
                    col_a, col_b = st.columns(2)
                    
                    with col_a:
                        st.metric("Gross Income", f"${result['gross_income']:,.2f}")
                        st.metric("Federal Tax", f"${result['federal_tax']:,.2f}")
                        st.metric("Provincial Tax", f"${result['provincial_tax']:,.2f}")
                    
                    with col_b:
                        st.metric("CPP Contribution", f"${result['cpp_contribution']:,.2f}")
                        st.metric("EI Contribution", f"${result['ei_contribution']:,.2f}")
                        st.metric("Total Tax", f"${result['total_tax']:,.2f}")
                    
                    st.divider()
                    
                    # Net income and effective rate
                    col_c, col_d = st.columns(2)
                    
                    with col_c:
                        st.metric("Net Income", f"${result['net_income']:,.2f}")
                    
                    with col_d:
                        st.metric("Effective Tax Rate", f"{result['effective_tax_rate']:.1f}%")
                    
                    # Per pay period breakdown
                    st.subheader("Per Pay Period")
                    
                    net_by_freq = result.get("net_by_frequency", {})
                    freq_data = []
                    
                    for freq, amount in net_by_freq.items():
                        freq_data.append({
                            "Frequency": freq.title(),
                            "Net Amount": f"${amount:,.2f}"
                        })
                    
                    if freq_data:
                        df_freq = pd.DataFrame(freq_data)
                        st.dataframe(df_freq, use_container_width=True, hide_index=True)
    
    # Tax table status
    st.divider()
    st.subheader("Tax Table Status")
    
    if st.session_state.tax_tables:
        st.success(f"Tax tables for {st.session_state.tax_tables.year} are loaded.")
    else:
        st.warning("No tax tables loaded. Click 'Load Tax Tables' in the sidebar.")


def show_bills_calendar_page():
    """Show bills and calendar page."""
    st.header("📅 Bills & Calendar")
    
    # Initialize empty budget profile if needed
    if not st.session_state.budget_profile:
        st.session_state.budget_profile = create_empty_budget_profile()
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Your Bills")
        
        # Display existing bills
        if st.session_state.budget_profile.bills:
            bill_data = []
            for bill in st.session_state.budget_profile.bills:
                envelope = st.session_state.budget_profile.get_envelope(bill.envelope_id)
                bill_data.append({
                    "ID": bill.id,
                    "Name": bill.name,
                    "Amount": f"${bill.amount:,.2f}",
                    "Type": bill.bill_type,
                    "Due Date": bill.due_date.strftime("%Y-%m-%d"),
                    "Envelope": envelope.name if envelope else "Unknown",
                    "Paid": "✅" if bill.paid else "❌"
                })
            
            df_bills = pd.DataFrame(bill_data)
            st.dataframe(df_bills, use_container_width=True, hide_index=True)
        else:
            st.info("No bills added yet.")
    
    with col2:
        st.subheader("Add New Bill")
        
        with st.form("add_bill_form"):
            bill_name = st.text_input("Bill Name")
            bill_amount = st.number_input("Amount", min_value=0.0, value=100.0, step=10.0)
            bill_type = st.selectbox("Type", ["fixed", "variable"])
            due_date = st.date_input("Due Date", value=date.today() + timedelta(days=30))
            
            # Envelope selection
            envelope_options = ["None"] + [e.name for e in st.session_state.budget_profile.envelopes]
            selected_envelope = st.selectbox("Envelope", options=envelope_options)
            
            submitted = st.form_submit_button("Add Bill")
            
            if submitted:
                if bill_name:
                    # Find envelope ID
                    envelope_id = ""
                    if selected_envelope != "None":
                        for envelope in st.session_state.budget_profile.envelopes:
                            if envelope.name == selected_envelope:
                                envelope_id = envelope.id
                                break
                    
                    # Create new bill
                    new_bill = Bill(
                        id=f"bill_{len(st.session_state.budget_profile.bills) + 1}",
                        name=bill_name,
                        amount=bill_amount,
                        bill_type=bill_type,
                        envelope_id=envelope_id,
                        due_date=due_date,
                        paid=False
                    )
                    
                    st.session_state.budget_profile.bills.append(new_bill)
                    st.success(f"Bill '{bill_name}' added successfully!")
                    st.rerun()
                else:
                    st.error("Please enter a bill name.")
        
        st.divider()
        
        # Delete bill section
        if st.session_state.budget_profile.bills:
            st.subheader("Delete Bill")
            bill_to_delete = st.selectbox(
                "Select bill to delete",
                options=[b.name for b in st.session_state.budget_profile.bills]
            )
            
            if st.button("Delete Bill", type="secondary"):
                # Find bill ID
                bill_id = None
                for bill in st.session_state.budget_profile.bills:
                    if bill.name == bill_to_delete:
                        bill_id = bill.id
                        break
                
                if bill_id:
                    delete_item("bill", bill_id)


def show_debts_page():
    """Show debts management page."""
    st.header("💳 Debts")
    
    # Initialize empty budget profile if needed
    if not st.session_state.budget_profile:
        st.session_state.budget_profile = create_empty_budget_profile()
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Your Debts")
        
        # Display existing debts
        active_debts = st.session_state.budget_profile.get_active_debts()
        if active_debts:
            debt_data = []
            for debt in active_debts:
                envelope = st.session_state.budget_profile.get_envelope(debt.envelope_id)
                debt_data.append({
                    "ID": debt.id,
                    "Name": debt.name,
                    "Balance": f"${debt.balance:,.2f}",
                    "APR": f"{debt.apr * 100:.2f}%",
                    "Min Payment": f"${debt.minimum_payment:,.2f}",
                    "Due Date": debt.due_date.strftime("%Y-%m-%d"),
                    "Envelope": envelope.name if envelope else "Unknown",
                    "Strategy": debt.strategy.value.title()
                })
            
            df_debts = pd.DataFrame(debt_data)
            st.dataframe(df_debts, use_container_width=True, hide_index=True)
            
            # Total debt
            total_debt = sum(d.balance for d in active_debts)
            st.metric("Total Debt", f"${total_debt:,.2f}")
        else:
            st.info("No debts added yet.")
    
    with col2:
        st.subheader("Add New Debt")
        
        with st.form("add_debt_form"):
            debt_name = st.text_input("Debt Name")
            debt_balance = st.number_input("Balance", min_value=0.0, value=1000.0, step=100.0)
            debt_apr = st.number_input("APR (%)", min_value=0.0, value=19.99, step=0.1) / 100
            min_payment = st.number_input("Minimum Payment", min_value=0.0, value=100.0, step=10.0)
            due_date = st.date_input("Due Date", value=date.today() + timedelta(days=30))
            
            # Strategy selection
            strategy_options = [s.value for s in DebtStrategy]
            strategy_display = [s.name.title() for s in DebtStrategy]
            selected_strategy = st.selectbox(
                "Strategy",
                options=strategy_options,
                format_func=lambda x: dict(zip(strategy_options, strategy_display))[x]
            )
            
            # Envelope selection
            envelope_options = ["None"] + [e.name for e in st.session_state.budget_profile.envelopes]
            selected_envelope = st.selectbox("Envelope", options=envelope_options)
            
            submitted = st.form_submit_button("Add Debt")
            
            if submitted:
                if debt_name:
                    # Find envelope ID
                    envelope_id = ""
                    if selected_envelope != "None":
                        for envelope in st.session_state.budget_profile.envelopes:
                            if envelope.name == selected_envelope:
                                envelope_id = envelope.id
                                break
                    
                    # Create new debt
                    new_debt = Debt(
                        id=f"debt_{len(st.session_state.budget_profile.debts) + 1}",
                        name=debt_name,
                        balance=debt_balance,
                        apr=debt_apr,
                        minimum_payment=min_payment,
                        due_date=due_date,
                        envelope_id=envelope_id,
                        strategy=DebtStrategy(selected_strategy),
                        paid_off=False
                    )
                    
                    st.session_state.budget_profile.debts.append(new_debt)
                    st.success(f"Debt '{debt_name}' added successfully!")
                    st.rerun()
                else:
                    st.error("Please enter a debt name.")
        
        st.divider()
        
        # Delete debt section
        if st.session_state.budget_profile.debts:
            st.subheader("Delete Debt")
            debt_to_delete = st.selectbox(
                "Select debt to delete",
                options=[d.name for d in st.session_state.budget_profile.debts]
            )
            
            if st.button("Delete Debt", type="secondary"):
                # Find debt ID
                debt_id = None
                for debt in st.session_state.budget_profile.debts:
                    if debt.name == debt_to_delete:
                        debt_id = debt.id
                        break
                
                if debt_id:
                    delete_item("debt", debt_id)


def show_sinking_funds_page():
    """Show sinking funds management page."""
    st.header("🎯 Sinking Funds")
    
    # Initialize empty budget profile if needed
    if not st.session_state.budget_profile:
        st.session_state.budget_profile = create_empty_budget_profile()
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Your Sinking Funds")
        
        # Display existing sinking funds
        if st.session_state.budget_profile.sinking_funds:
            fund_data = []
            for fund in st.session_state.budget_profile.sinking_funds:
                envelope = st.session_state.budget_profile.get_envelope(fund.envelope_id)
                progress = (fund.current_balance / fund.target_amount * 100) if fund.target_amount > 0 else 0
                days_remaining = (fund.deadline - date.today()).days
                
                fund_data.append({
                    "ID": fund.id,
                    "Name": fund.name,
                    "Target": f"${fund.target_amount:,.2f}",
                    "Current": f"${fund.current_balance:,.2f}",
                    "Progress": f"{progress:.1f}%",
                    "Deadline": fund.deadline.strftime("%Y-%m-%d"),
                    "Days Left": days_remaining if days_remaining > 0 else "Past due",
                    "Envelope": envelope.name if envelope else "Unknown"
                })
            
            df_funds = pd.DataFrame(fund_data)
            st.dataframe(df_funds, use_container_width=True, hide_index=True)
            
            # Total sinking funds
            total_target = sum(f.target_amount for f in st.session_state.budget_profile.sinking_funds)
            total_current = sum(f.current_balance for f in st.session_state.budget_profile.sinking_funds)
            st.metric("Total Target", f"${total_target:,.2f}")
            st.metric("Total Saved", f"${total_current:,.2f}")
        else:
            st.info("No sinking funds added yet.")
    
    with col2:
        st.subheader("Add New Sinking Fund")
        
        with st.form("add_sinking_fund_form"):
            fund_name = st.text_input("Fund Name")
            target_amount = st.number_input("Target Amount", min_value=0.0, value=1000.0, step=100.0)
            current_balance = st.number_input("Current Balance", min_value=0.0, value=0.0, step=100.0)
            deadline = st.date_input("Deadline", value=date.today() + timedelta(days=90))
            
            # Envelope selection
            envelope_options = ["None"] + [e.name for e in st.session_state.budget_profile.envelopes]
            selected_envelope = st.selectbox("Envelope", options=envelope_options)
            
            submitted = st.form_submit_button("Add Sinking Fund")
            
            if submitted:
                if fund_name:
                    # Find envelope ID
                    envelope_id = ""
                    if selected_envelope != "None":
                        for envelope in st.session_state.budget_profile.envelopes:
                            if envelope.name == selected_envelope:
                                envelope_id = envelope.id
                                break
                    
                    # Create new sinking fund
                    new_fund = SinkingFund(
                        id=f"sinking_{len(st.session_state.budget_profile.sinking_funds) + 1}",
                        name=fund_name,
                        target_amount=target_amount,
                        current_balance=current_balance,
                        deadline=deadline,
                        envelope_id=envelope_id
                    )
                    
                    st.session_state.budget_profile.sinking_funds.append(new_fund)
                    st.success(f"Sinking fund '{fund_name}' added successfully!")
                    st.rerun()
                else:
                    st.error("Please enter a fund name.")
        
        st.divider()
        
        # Delete sinking fund section
        if st.session_state.budget_profile.sinking_funds:
            st.subheader("Delete Sinking Fund")
            fund_to_delete = st.selectbox(
                "Select sinking fund to delete",
                options=[f.name for f in st.session_state.budget_profile.sinking_funds]
            )
            
            if st.button("Delete Sinking Fund", type="secondary"):
                # Find fund ID
                fund_id = None
                for fund in st.session_state.budget_profile.sinking_funds:
                    if fund.name == fund_to_delete:
                        fund_id = fund.id
                        break
                
                if fund_id:
                    delete_item("sinking_fund", fund_id)


def show_reports_page():
    """Show reports and analytics page."""
    st.header("📈 Reports & Analytics")
    
    if not st.session_state.budget_profile:
        st.info("No budget profile loaded. Please add data or load demo data.")
        return
    
    # Create tabs for different reports
    tab1, tab2, tab3 = st.tabs(["Envelope Summary", "Cash Flow", "Debt Progress"])
    
    with tab1:
        st.subheader("Envelope Summary")
        
        if st.session_state.budget_profile.envelopes:
            # Prepare envelope data
            envelope_data = []
            for envelope in st.session_state.budget_profile.envelopes:
                progress = (envelope.current_balance / envelope.target_amount * 100) if envelope.target_amount > 0 else 0
                envelope_data.append({
                    "Category": envelope.category.value.title(),
                    "Name": envelope.name,
                    "Target": envelope.target_amount,
                    "Current": envelope.current_balance,
                    "Progress": progress,
                    "Priority": envelope.priority
                })
            
            df_envelopes = pd.DataFrame(envelope_data)
            
            # Display table
            st.dataframe(df_envelopes, use_container_width=True, hide_index=True)
            
            # Create bar chart
            fig = px.bar(
                df_envelopes,
                x="Name",
                y=["Target", "Current"],
                title="Envelope Targets vs Current Balances",
                barmode="group",
                color_discrete_sequence=["#FF6B6B", "#4ECDC4"]
            )
            fig.update_layout(xaxis_title="Envelope", yaxis_title="Amount ($)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No envelopes to display.")
    
    with tab2:
        st.subheader("Cash Flow Analysis")
        
        # Simple cash flow analysis
        if st.session_state.budget_profile.bills:
            # Group bills by month
            bill_data = []
            for bill in st.session_state.budget_profile.bills:
                if not bill.paid:
                    bill_data.append({
                        "Month": bill.due_date.strftime("%Y-%m"),
                        "Amount": bill.amount,
                        "Type": bill.bill_type
                    })
            
            if bill_data:
                df_bills = pd.DataFrame(bill_data)
                monthly_totals = df_bills.groupby("Month")["Amount"].sum().reset_index()
                
                # Display monthly totals
                st.dataframe(monthly_totals, use_container_width=True, hide_index=True)
                
                # Create line chart
                fig = px.line(
                    monthly_totals,
                    x="Month",
                    y="Amount",
                    title="Monthly Bill Expenses",
                    markers=True
                )
                fig.update_layout(xaxis_title="Month", yaxis_title="Total Bills ($)")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No unpaid bills to analyze.")
        else:
            st.info("No bills to analyze.")
    
    with tab3:
        st.subheader("Debt Progress")
        
        active_debts = st.session_state.budget_profile.get_active_debts()
        if active_debts:
            # Prepare debt data
            debt_data = []
            for debt in active_debts:
                debt_data.append({
                    "Name": debt.name,
                    "Balance": debt.balance,
                    "APR": debt.apr * 100,
                    "Min Payment": debt.minimum_payment,
                    "Strategy": debt.strategy.value.title()
                })
            
            df_debts = pd.DataFrame(debt_data)
            
            # Display table
            st.dataframe(df_debts, use_container_width=True, hide_index=True)
            
            # Create pie chart for debt distribution
            fig = px.pie(
                df_debts,
                values="Balance",
                names="Name",
                title="Debt Distribution by Balance",
                hole=0.3
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Calculate total interest if only minimum payments are made
            total_interest = sum(debt.balance * debt.apr for debt in active_debts)
            st.metric("Estimated Annual Interest", f"${total_interest:,.2f}")
        else:
            st.info("No active debts to analyze.")


def show_settings_page():
    """Show application settings page."""
    st.header("⚙️ Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Pay Schedule")
        
        # Pay cycle
        pay_cycle_options = get_pay_schedule_options()
        pay_cycle_display = [opt["label"] for opt in pay_cycle_options]
        pay_cycle_values = [opt["value"] for opt in pay_cycle_options]
        
        selected_pay_cycle = st.selectbox(
            "Pay Cycle",
            options=pay_cycle_values,
            format_func=lambda x: dict(zip(pay_cycle_values, pay_cycle_display))[x],
            index=pay_cycle_values.index(st.session_state.settings_pay_cycle.lower())
        )
        
        # Next pay date
        next_pay_date = st.date_input(
            "Next Pay Date",
            value=st.session_state.settings_next_pay_date
        )
        
        if st.button("Save Pay Schedule", type="primary"):
            st.session_state.settings_pay_cycle = selected_pay_cycle.upper()
            st.session_state.settings_next_pay_date = next_pay_date
            st.success("Pay schedule saved successfully!")
    
    with col2:
        st.subheader("Budget Settings")
        
        if st.session_state.budget_profile:
            settings = st.session_state.budget_profile.settings
            
            # Checking buffer
            checking_buffer = st.number_input(
                "Checking Account Buffer ($)",
                min_value=0.0,
                value=float(settings.checking_buffer),
                step=100.0
            )
            
            # Emergency fund target
            emergency_fund_target = st.number_input(
                "Emergency Fund Target ($)",
                min_value=0.0,
                value=float(settings.emergency_fund_target),
                step=1000.0
            )
            
            # Debt strategy
            strategy_options = [s.value for s in DebtStrategy]
            strategy_display = [s.name.title() for s in DebtStrategy]
            selected_strategy = st.selectbox(
                "Debt Payoff Strategy",
                options=strategy_options,
                format_func=lambda x: dict(zip(strategy_options, strategy_display))[x],
                index=strategy_options.index(settings.debt_strategy.value)
            )
            
            # Savings rate
            savings_rate = st.slider(
                "Savings Rate (%)",
                min_value=0,
                max_value=50,
                value=int(settings.savings_rate * 100),
                step=1
            ) / 100
            
            # Discretionary percentage
            discretionary_percentage = st.slider(
                "Discretionary Spending (%)",
                min_value=0,
                max_value=50,
                value=int(settings.discretionary_percentage * 100),
                step=1
            ) / 100
            
            if st.button("Save Budget Settings", type="primary"):
                st.session_state.budget_profile.settings = BudgetSettings(
                    checking_buffer=checking_buffer,
                    emergency_fund_target=emergency_fund_target,
                    debt_strategy=DebtStrategy(selected_strategy),
                    savings_rate=savings_rate,
                    discretionary_percentage=discretionary_percentage,
                    round_to_nearest=settings.round_to_nearest
                )
                st.success("Budget settings saved successfully!")
        else:
            st.info("No budget profile loaded. Settings will be created when you add data.")
    
    st.divider()
    
    # Data management
    st.subheader("Data Management")
    
    col3, col4 = st.columns(2)
    
    with col3:
        if st.button("Clear All Data", type="secondary"):
            st.session_state.budget_profile = create_empty_budget_profile()
            st.session_state.demo_data_loaded = False
            st.success("All data cleared! Starting with empty budget profile.")
            st.rerun()
    
    with col4:
        if st.button("Export Data", type="secondary"):
            # This would export data to JSON
            st.info("Export functionality would be implemented here.")


# Run the app
if __name__ == "__main__":
    main()
