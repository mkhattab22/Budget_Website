"""
Paycheck allocation engine for budgeting.
"""
from typing import List, Dict, Optional, Tuple, Any
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
import math
from .models import (
    UserBudgetProfile, PaycheckAllocation, Envelope, Bill, Debt,
    SinkingFund, SavingsGoal, BudgetSettings, EnvelopeCategory,
    DebtStrategy, CashflowForecast, ReconciliationResult
)


class PaycheckAllocator:
    """Allocates paycheck funds to envelopes based on priority rules."""
    
    def __init__(self, profile: UserBudgetProfile):
        self.profile = profile
        self.settings = profile.settings
    
    def allocate_paycheck(self, net_amount: float, paycheck_date: date) -> PaycheckAllocation:
        """
        Allocate a paycheck to envelopes based on priority rules.
        
        Priority order:
        1. Ensure minimum buffer in checking
        2. Fund bills due before next payday
        3. Fund minimum debt payments
        4. Fund sinking funds by urgency
        5. Fund savings/investing per strategy
        6. Remaining goes to extra debt or discretionary
        
        Args:
            net_amount: Net paycheck amount after taxes
            paycheck_date: Date paycheck is received
            
        Returns:
            PaycheckAllocation with envelope allocations
        """
        allocation = PaycheckAllocation(
            date=paycheck_date,
            gross_amount=0,  # Will be set by caller
            net_amount=net_amount,
            remaining_amount=net_amount
        )
        
        # Calculate next payday based on typical pay schedule
        # (In real implementation, this would come from user profile)
        next_payday = self._calculate_next_payday(paycheck_date)
        
        # Step 1: Ensure minimum buffer (skip for now - handled in cashflow forecast)
        
        # Step 2: Fund bills due before next payday
        bills = self.profile.get_bills_due_before(next_payday)
        bills.sort(key=lambda b: b.due_date)  # Pay earliest bills first
        
        for bill in bills:
            envelope = self.profile.get_envelope(bill.envelope_id)
            if not envelope:
                continue
                
            # Check if envelope has enough, otherwise allocate from paycheck
            if envelope.current_balance >= bill.amount:
                # Bill can be paid from envelope balance
                continue
            
            amount_needed = bill.amount - envelope.current_balance
            if amount_needed <= allocation.remaining_amount:
                # Allocate to envelope
                allocation.allocations[bill.envelope_id] = allocation.allocations.get(bill.envelope_id, 0) + amount_needed
                allocation.remaining_amount -= amount_needed
            else:
                # Can't fully fund - allocate what we can
                allocation.allocations[bill.envelope_id] = allocation.allocations.get(bill.envelope_id, 0) + allocation.remaining_amount
                allocation.remaining_amount = 0
                break
        
        if allocation.remaining_amount <= 0:
            return self._finalize_allocation(allocation)
        
        # Step 3: Fund minimum debt payments
        debts = self.profile.get_active_debts()
        for debt in debts:
            envelope = self.profile.get_envelope(debt.envelope_id)
            if not envelope:
                continue
            
            # Check if envelope has enough for minimum payment
            if envelope.current_balance >= debt.minimum_payment:
                continue
            
            amount_needed = debt.minimum_payment - envelope.current_balance
            if amount_needed <= allocation.remaining_amount:
                allocation.allocations[debt.envelope_id] = allocation.allocations.get(debt.envelope_id, 0) + amount_needed
                allocation.remaining_amount -= amount_needed
            else:
                allocation.allocations[debt.envelope_id] = allocation.allocations.get(debt.envelope_id, 0) + allocation.remaining_amount
                allocation.remaining_amount = 0
                break
        
        if allocation.remaining_amount <= 0:
            return self._finalize_allocation(allocation)
        
        # Step 4: Fund sinking funds by urgency
        sinking_funds = self.profile.get_urgent_sinking_funds()
        sinking_funds.sort(key=lambda sf: sf.months_remaining)  # Most urgent first
        
        for sf in sinking_funds:
            envelope = self.profile.get_envelope(sf.envelope_id)
            if not envelope:
                continue
            
            recommended = sf.recommended_contribution
            if recommended <= 0:
                continue
            
            # Cap at monthly contribution if set
            if sf.monthly_contribution:
                recommended = min(recommended, sf.monthly_contribution)
            
            if recommended <= allocation.remaining_amount:
                allocation.allocations[sf.envelope_id] = allocation.allocations.get(sf.envelope_id, 0) + recommended
                allocation.remaining_amount -= recommended
            else:
                allocation.allocations[sf.envelope_id] = allocation.allocations.get(sf.envelope_id, 0) + allocation.remaining_amount
                allocation.remaining_amount = 0
                break
        
        if allocation.remaining_amount <= 0:
            return self._finalize_allocation(allocation)
        
        # Step 5: Fund savings/investing per strategy
        savings_rate = self.settings.savings_rate
        savings_amount = net_amount * savings_rate
        
        if savings_amount > 0:
            # Find savings/investing envelopes
            savings_envelopes = [
                e for e in self.profile.envelopes
                if e.category in [EnvelopeCategory.SAVINGS, EnvelopeCategory.INVESTING]
            ]
            
            if savings_envelopes:
                # Distribute proportionally based on target amounts
                total_target = sum(e.target_amount for e in savings_envelopes)
                if total_target > 0:
                    for envelope in savings_envelopes:
                        proportion = envelope.target_amount / total_target
                        amount = savings_amount * proportion
                        if amount <= allocation.remaining_amount:
                            allocation.allocations[envelope.id] = allocation.allocations.get(envelope.id, 0) + amount
                            allocation.remaining_amount -= amount
                        else:
                            allocation.allocations[envelope.id] = allocation.allocations.get(envelope.id, 0) + allocation.remaining_amount
                            allocation.remaining_amount = 0
                            break
        
        if allocation.remaining_amount <= 0:
            return self._finalize_allocation(allocation)
        
        # Step 6: Remaining goes to extra debt or discretionary
        if allocation.remaining_amount > 0:
            # Apply debt strategy for extra payments
            if self.settings.debt_strategy == DebtStrategy.AVALANCHE:
                debts.sort(key=lambda d: d.apr, reverse=True)  # Highest APR first
            else:  # SNOWBALL
                debts.sort(key=lambda d: d.balance)  # Smallest balance first
            
            for debt in debts:
                if allocation.remaining_amount <= 0:
                    break
                
                envelope = self.profile.get_envelope(debt.envelope_id)
                if not envelope:
                    continue
                
                # Allocate remaining to this debt
                allocation.allocations[debt.envelope_id] = allocation.allocations.get(debt.envelope_id, 0) + allocation.remaining_amount
                allocation.remaining_amount = 0
                break
            
            # If still remaining after debt, put in discretionary
            if allocation.remaining_amount > 0:
                discretionary_envelopes = [
                    e for e in self.profile.envelopes
                    if e.category == EnvelopeCategory.DISCRETIONARY
                ]
                if discretionary_envelopes:
                    # Put in first discretionary envelope
                    envelope = discretionary_envelopes[0]
                    allocation.allocations[envelope.id] = allocation.allocations.get(envelope.id, 0) + allocation.remaining_amount
                    allocation.remaining_amount = 0
        
        return self._finalize_allocation(allocation)
    
    def _calculate_next_payday(self, current_payday: date) -> date:
        """
        Calculate next payday based on typical schedule.
        Simplified - assumes biweekly for now.
        """
        return current_payday + timedelta(days=14)
    
    def _finalize_allocation(self, allocation: PaycheckAllocation) -> PaycheckAllocation:
        """Finalize allocation with rounding and validation."""
        # Round allocations to nearest specified amount
        round_to = self.settings.round_to_nearest
        if round_to > 0:
            rounded_allocations = {}
            total_rounded = 0.0
            
            for envelope_id, amount in allocation.allocations.items():
                rounded = self._round_to_nearest(amount, round_to)
                rounded_allocations[envelope_id] = rounded
                total_rounded += rounded
            
            # Adjust for rounding differences
            rounding_diff = sum(allocation.allocations.values()) - total_rounded
            if rounding_diff != 0 and rounded_allocations:
                # Add difference to first envelope
                first_id = next(iter(rounded_allocations))
                rounded_allocations[first_id] += rounding_diff
            
            allocation.allocations = rounded_allocations
        
        # Recalculate remaining amount
        allocated_total = sum(allocation.allocations.values())
        allocation.remaining_amount = allocation.net_amount - allocated_total
        
        # Ensure remaining amount is non-negative
        if allocation.remaining_amount < 0:
            # Reduce allocations proportionally
            scale = allocation.net_amount / allocated_total
            for envelope_id in allocation.allocations:
                allocation.allocations[envelope_id] *= scale
            allocation.remaining_amount = 0
        
        return allocation
    
    def _round_to_nearest(self, amount: float, nearest: float) -> float:
        """Round amount to nearest specified value."""
        if nearest == 0:
            return amount
        return round(amount / nearest) * nearest


class CashflowForecaster:
    """Forecasts day-by-day cashflow based on allocations and bills."""
    
    def __init__(self, profile: UserBudgetProfile):
        self.profile = profile
    
    def forecast_cashflow(
        self, 
        start_date: date, 
        end_date: date,
        starting_balance: float,
        paycheck_allocations: List[PaycheckAllocation]
    ) -> CashflowForecast:
        """
        Forecast cashflow day-by-day.
        
        Args:
            start_date: Start date for forecast
            end_date: End date for forecast
            starting_balance: Starting checking account balance
            paycheck_allocations: Planned paycheck allocations
            
        Returns:
            CashflowForecast with daily balances and alerts
        """
        forecast = CashflowForecast(
            start_date=start_date,
            end_date=end_date,
            starting_balance=starting_balance
        )
        
        # Initialize with starting balance
        current_balance = starting_balance
        current_date = start_date
        
        # Create dictionary of paycheck allocations by date
        paycheck_by_date = {alloc.date: alloc for alloc in paycheck_allocations}
        
        # Create list of bills sorted by due date
        bills = [bill for bill in self.profile.bills if not bill.paid]
        bills.sort(key=lambda b: b.due_date)
        
        # Track envelope balances (simplified - in reality would update as we go)
        envelope_balances = {
            envelope.id: envelope.current_balance
            for envelope in self.profile.envelopes
        }
        
        # Process each day
        while current_date <= end_date:
            # Add paycheck if received today
            if current_date in paycheck_by_date:
                paycheck = paycheck_by_date[current_date]
                current_balance += paycheck.net_amount
                
                # Update envelope balances with allocations
                for envelope_id, amount in paycheck.allocations.items():
                    if envelope_id in envelope_balances:
                        envelope_balances[envelope_id] += amount
                
                forecast.transactions.append({
                    "date": current_date,
                    "type": "paycheck",
                    "amount": paycheck.net_amount,
                    "description": f"Paycheck received"
                })
            
            # Pay bills due today
            today_bills = [b for b in bills if b.due_date == current_date]
            for bill in today_bills:
                envelope = self.profile.get_envelope(bill.envelope_id)
                if not envelope:
                    continue
                
                # Check if envelope has enough
                if envelope_balances.get(bill.envelope_id, 0) >= bill.amount:
                    # Pay from envelope
                    envelope_balances[bill.envelope_id] -= bill.amount
                    current_balance -= bill.amount  # Money leaves checking
                    
                    forecast.transactions.append({
                        "date": current_date,
                        "type": "bill_payment",
                        "amount": -bill.amount,
                        "description": f"Paid {bill.name}",
                        "envelope_id": bill.envelope_id
                    })
                else:
                    # Not enough in envelope - this is a problem
                    forecast.alerts.append(
                        f"Insufficient funds in envelope '{envelope.name}' "
                        f"to pay bill '{bill.name}' on {current_date}"
                    )
            
            # Record daily balance
            forecast.daily_balances[current_date] = current_balance
            
            # Check for negative balance alert
            if current_balance < self.profile.settings.checking_buffer:
                forecast.alerts.append(
                    f"Low balance warning: ${current_balance:.2f} on {current_date} "
                    f"(below buffer of ${self.profile.settings.checking_buffer:.2f})"
                )
            
            if current_balance < 0:
                forecast.alerts.append(
                    f"Negative balance: ${current_balance:.2f} on {current_date}"
                )
            
            # Move to next day
            current_date += timedelta(days=1)
        
        return forecast


class ReconciliationEngine:
    """Reconciles planned vs actual spending."""
    
    def reconcile(
        self,
        profile: UserBudgetProfile,
        start_date: date,
        end_date: date,
        actual_transactions: List[Dict[str, Any]]
    ) -> List[ReconciliationResult]:
        """
        Reconcile planned vs actual spending.
        
        Args:
            profile: User budget profile
            start_date: Start of reconciliation period
            end_date: End of reconciliation period
            actual_transactions: List of actual transactions with envelope_id and amount
            
        Returns:
            List of ReconciliationResult for each envelope
        """
        results = []
        
        # Group actual transactions by envelope
        actual_by_envelope: Dict[str, float] = {}
        for transaction in actual_transactions:
            envelope_id = transaction.get("envelope_id")
            amount = transaction.get("amount", 0)
            if envelope_id and amount != 0:
                actual_by_envelope[envelope_id] = actual_by_envelope.get(envelope_id, 0) + amount
        
        # Calculate planned amounts (from envelope targets and allocations)
        for envelope in profile.envelopes:
            # Simplified: planned amount is target amount for period
            # In reality, you'd track allocations to this envelope during the period
            planned_amount = envelope.target_amount
            
            actual_amount = abs(actual_by_envelope.get(envelope.id, 0))
            difference = actual_amount - planned_amount
            
            if difference > 0:
                over_under = "over"
            elif difference < 0:
                over_under = "under"
            else:
                over_under = "on"
            
            percentage = (actual_amount / planned_amount * 100) if planned_amount > 0 else 0
            
            results.append(ReconciliationResult(
                envelope_id=envelope.id,
                envelope_name=envelope.name,
                planned_amount=planned_amount,
                actual_amount=actual_amount,
                difference=abs(difference),
                over_under=over_under,
                percentage=percentage
            ))
        
        return results
    
    def adjust_allocation(
        self,
        profile: UserBudgetProfile,
        reconciliation_results: List[ReconciliationResult],
        adjustment_factor: float = 0.1
    ) -> UserBudgetProfile:
        """
        Adjust envelope targets based on reconciliation results.
        
        Args:
            profile: User budget profile
            reconciliation_results: Results from reconciliation
            adjustment_factor: How much to adjust (0.0 to 1.0)
            
        Returns:
            Updated UserBudgetProfile
        """
        # Create a copy of the profile
        updated_profile = profile.copy()
        
        for result in reconciliation_results:
            envelope = updated_profile.get_envelope(result.envelope_id)
            if not envelope:
                continue
            
            # Adjust target based on over/under spending
            if result.over_under == "over" and result.percentage > 110:
                # Consistently over budget - increase target
                adjustment = envelope.target_amount * adjustment_factor
                envelope.target_amount += adjustment
            
            elif result.over_under == "under" and result.percentage < 90:
                # Consistently under budget - decrease target
                adjustment = envelope.target_amount * adjustment_factor
                envelope.target_amount = max(0, envelope.target_amount - adjustment)
        
        return updated_profile