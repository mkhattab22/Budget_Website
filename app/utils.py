"""
Utility functions for the finance application.
"""
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
import calendar


class PaySchedule(Enum):
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    SEMIMONTHLY = "semimonthly"
    MONTHLY = "monthly"


def calculate_next_payday(
    pay_schedule: PaySchedule,
    last_payday: Optional[date] = None,
    reference_date: Optional[date] = None
) -> date:
    """
    Calculate the next payday based on pay schedule.
    
    Args:
        pay_schedule: Pay schedule enum
        last_payday: Last payday date (optional)
        reference_date: Reference date for calculation (defaults to today)
        
    Returns:
        Next payday date
    """
    if reference_date is None:
        reference_date = date.today()
    
    if last_payday is None:
        # If no last payday, calculate based on reference date
        if pay_schedule == PaySchedule.WEEKLY:
            # Next Friday (assuming weekly on Fridays)
            days_ahead = 4 - reference_date.weekday()  # 4 = Friday
            if days_ahead <= 0:  # Target day already happened this week
                days_ahead += 7
            return reference_date + timedelta(days=days_ahead)
        
        elif pay_schedule == PaySchedule.BIWEEKLY:
            # Next Friday, then every 2 weeks
            days_ahead = 4 - reference_date.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            next_friday = reference_date + timedelta(days=days_ahead)
            # If today is Friday, use next Friday (2 weeks from now)
            if reference_date.weekday() == 4:
                return next_friday + timedelta(weeks=2)
            return next_friday
        
        elif pay_schedule == PaySchedule.SEMIMONTHLY:
            # 15th and last day of month
            if reference_date.day < 15:
                return date(reference_date.year, reference_date.month, 15)
            else:
                # Last day of current month
                last_day = calendar.monthrange(reference_date.year, reference_date.month)[1]
                return date(reference_date.year, reference_date.month, last_day)
        
        elif pay_schedule == PaySchedule.MONTHLY:
            # Last day of current month
            last_day = calendar.monthrange(reference_date.year, reference_date.month)[1]
            if reference_date.day < last_day:
                return date(reference_date.year, reference_date.month, last_day)
            else:
                # Last day of next month
                next_month = reference_date.month + 1
                next_year = reference_date.year
                if next_month > 12:
                    next_month = 1
                    next_year += 1
                last_day = calendar.monthrange(next_year, next_month)[1]
                return date(next_year, next_month, last_day)
    
    else:
        # Calculate based on last payday
        if pay_schedule == PaySchedule.WEEKLY:
            return last_payday + timedelta(weeks=1)
        elif pay_schedule == PaySchedule.BIWEEKLY:
            return last_payday + timedelta(weeks=2)
        elif pay_schedule == PaySchedule.SEMIMONTHLY:
            # Calculate based on day of month
            if last_payday.day == 15:
                # Last day of same month
                last_day = calendar.monthrange(last_payday.year, last_payday.month)[1]
                return date(last_payday.year, last_payday.month, last_day)
            else:
                # 15th of next month
                next_month = last_payday.month + 1
                next_year = last_payday.year
                if next_month > 12:
                    next_month = 1
                    next_year += 1
                return date(next_year, next_month, 15)
        elif pay_schedule == PaySchedule.MONTHLY:
            # Last day of next month
            next_month = last_payday.month + 1
            next_year = last_payday.year
            if next_month > 12:
                next_month = 1
                next_year += 1
            last_day = calendar.monthrange(next_year, next_month)[1]
            return date(next_year, next_month, last_day)
    
    return reference_date  # Fallback


def calculate_paycheque_windows(
    start_date: date,
    end_date: date,
    pay_schedule: str,
    next_payday: Optional[date] = None
) -> List[Dict[str, Any]]:
    """
    Calculate paycheque windows between two dates.
    
    Args:
        start_date: Start date for windows
        end_date: End date for windows
        pay_schedule: Pay schedule string (weekly, biweekly, semimonthly, monthly)
        next_payday: Next payday date (optional)
        
    Returns:
        List of window dictionaries with start_date, end_date, and payday
    """
    windows = []
    
    # Convert string to PaySchedule enum
    try:
        pay_schedule_enum = PaySchedule(pay_schedule.lower())
    except ValueError:
        # Default to biweekly if invalid
        pay_schedule_enum = PaySchedule.BIWEEKLY
    
    if next_payday is None:
        next_payday = calculate_next_payday(pay_schedule_enum, reference_date=start_date)
    
    current_payday = next_payday
    window_start = start_date
    
    while window_start < end_date:
        # Calculate window end (day before next payday)
        window_end = current_payday - timedelta(days=1)
        
        # Adjust if window_end is beyond our end_date
        if window_end > end_date:
            window_end = end_date
        
        windows.append({
            "start_date": window_start,
            "end_date": window_end,
            "payday": current_payday,
            "pay_schedule": pay_schedule
        })
        
        # Move to next window
        window_start = current_payday
        current_payday = calculate_next_payday(pay_schedule_enum, last_payday=current_payday)
        
        # Stop if we've gone beyond end_date
        if window_start > end_date:
            break
    
    return windows


def assign_bills_to_windows(
    bills: List[Dict[str, Any]],
    windows: List[Dict[str, Any]]
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Assign bills to paycheque windows based on due dates.
    
    Args:
        bills: List of bill dictionaries with 'due_date' and 'amount'
        windows: List of window dictionaries with 'start_date' and 'end_date'
        
    Returns:
        Dictionary mapping window index to list of bills
    """
    assignments = {i: [] for i in range(len(windows))}
    
    for bill in bills:
        bill_due_date = bill.get("due_date")
        if not bill_due_date:
            continue
        
        # Find the window that contains the due date
        assigned = False
        for i, window in enumerate(windows):
            if window["start_date"] <= bill_due_date <= window["end_date"]:
                assignments[i].append(bill)
                assigned = True
                break
        
        # If bill due date is before first window, assign to first window
        if not assigned and bill_due_date < windows[0]["start_date"]:
            assignments[0].append(bill)
        # If bill due date is after last window, assign to last window
        elif not assigned and bill_due_date > windows[-1]["end_date"]:
            assignments[len(windows) - 1].append(bill)
    
    return assignments


def format_currency(amount: float) -> str:
    """Format currency amount with commas and 2 decimal places."""
    return f"${amount:,.2f}"


def format_date(d: date) -> str:
    """Format date as YYYY-MM-DD."""
    return d.strftime("%Y-%m-%d")


def calculate_days_until(d: date, reference_date: Optional[date] = None) -> int:
    """Calculate days until a date."""
    if reference_date is None:
        reference_date = date.today()
    return (d - reference_date).days


def get_pay_schedule_options() -> List[Dict[str, str]]:
    """Get pay schedule options for UI dropdown."""
    return [
        {"value": "weekly", "label": "Weekly (every Friday)"},
        {"value": "biweekly", "label": "Bi-weekly (every 2 weeks)"},
        {"value": "semimonthly", "label": "Semi-monthly (15th and last day)"},
        {"value": "monthly", "label": "Monthly (last day of month)"}
    ]