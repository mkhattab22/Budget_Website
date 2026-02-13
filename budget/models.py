"""
Budget models for paycheck allocation and envelope system.
"""
from typing import List, Dict, Optional, Any
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel, Field, validator


class EnvelopeCategory(str, Enum):
    """Categories for budget envelopes."""
    BILLS = "bills"
    DEBT = "debt"
    SINKING = "sinking"
    SAVINGS = "savings"
    INVESTING = "investing"
    DISCRETIONARY = "discretionary"


class BillType(str, Enum):
    """Types of bills."""
    FIXED = "fixed"  # Same amount each period
    VARIABLE = "variable"  # Amount varies
    SUBSCRIPTION = "subscription"  # Recurring subscription


class Recurrence(str, Enum):
    """Recurrence patterns for bills and income."""
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    SEMIMONTHLY = "semimonthly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUALLY = "annually"


class DebtStrategy(str, Enum):
    """Debt payoff strategies."""
    AVALANCHE = "avalanche"  # Highest interest first
    SNOWBALL = "snowball"  # Smallest balance first


class Envelope(BaseModel):
    """A budget envelope for allocating funds."""
    id: Optional[str] = None
    category: EnvelopeCategory
    name: str
    target_amount: float = Field(..., ge=0, description="Target amount for this envelope")
    current_balance: float = Field(0.0, description="Current balance in envelope")
    priority: int = Field(..., ge=1, le=10, description="Priority (1=highest, 10=lowest)")
    due_date: Optional[date] = Field(None, description="Due date for bills")
    recurrence: Optional[Recurrence] = Field(None, description="Recurrence pattern")
    auto_pay: bool = Field(False, description="Whether to auto-pay from this envelope")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('current_balance')
    def balance_not_negative(cls, v):
        if v < 0:
            raise ValueError('Envelope balance cannot be negative')
        return v


class Bill(BaseModel):
    """A bill or recurring expense."""
    id: Optional[str] = None
    name: str
    amount: float = Field(..., ge=0)
    bill_type: BillType
    envelope_id: str = Field(..., description="ID of envelope to pay from")
    due_date: date
    recurrence: Optional[Recurrence] = None
    paid: bool = Field(False)
    paid_date: Optional[date] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Debt(BaseModel):
    """A debt account."""
    id: Optional[str] = None
    name: str
    balance: float = Field(..., ge=0)
    apr: float = Field(..., ge=0, le=1, description="Annual percentage rate (0.0 to 1.0)")
    minimum_payment: float = Field(..., ge=0)
    due_date: date
    envelope_id: str = Field(..., description="ID of envelope for payments")
    strategy: DebtStrategy = Field(DebtStrategy.AVALANCHE)
    paid_off: bool = Field(False)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SinkingFund(BaseModel):
    """A sinking fund for future expenses."""
    id: Optional[str] = None
    name: str
    target_amount: float = Field(..., ge=0)
    current_balance: float = Field(0.0, ge=0)
    deadline: date
    monthly_contribution: Optional[float] = Field(None, ge=0)
    envelope_id: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @property
    def months_remaining(self) -> int:
        """Calculate months remaining until deadline."""
        today = date.today()
        if self.deadline <= today:
            return 0
        
        # Simple month difference
        months = (self.deadline.year - today.year) * 12 + (self.deadline.month - today.month)
        return max(0, months)
    
    @property
    def recommended_contribution(self) -> float:
        """Calculate recommended monthly contribution to meet target by deadline."""
        months = self.months_remaining
        if months == 0:
            return self.target_amount - self.current_balance
        
        remaining = self.target_amount - self.current_balance
        if remaining <= 0:
            return 0
        
        return remaining / months


class SavingsGoal(BaseModel):
    """A savings or investing goal."""
    id: Optional[str] = None
    name: str
    target_amount: float = Field(..., ge=0)
    current_balance: float = Field(0.0, ge=0)
    target_date: Optional[date] = None
    monthly_contribution: float = Field(0.0, ge=0)
    envelope_id: str
    investment_strategy: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PaycheckAllocation(BaseModel):
    """Allocation of a paycheck to various envelopes."""
    paycheck_id: Optional[str] = None
    date: date
    gross_amount: float
    net_amount: float
    allocations: Dict[str, float] = Field(
        default_factory=dict,
        description="Envelope ID -> amount allocated"
    )
    remaining_amount: float = Field(0.0, description="Amount not allocated (goes to discretionary)")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('allocations')
    def allocations_not_negative(cls, v):
        for amount in v.values():
            if amount < 0:
                raise ValueError('Allocation amount cannot be negative')
        return v


class CashflowForecast(BaseModel):
    """Day-by-day cashflow forecast."""
    start_date: date
    end_date: date
    starting_balance: float
    daily_balances: Dict[date, float] = Field(default_factory=dict)
    transactions: List[Dict[str, Any]] = Field(default_factory=list)
    alerts: List[str] = Field(default_factory=list)
    
    @property
    def min_balance(self) -> float:
        """Minimum balance during forecast period."""
        if not self.daily_balances:
            return self.starting_balance
        return min(self.daily_balances.values())
    
    @property
    def max_balance(self) -> float:
        """Maximum balance during forecast period."""
        if not self.daily_balances:
            return self.starting_balance
        return max(self.daily_balances.values())


class ReconciliationResult(BaseModel):
    """Result of reconciling planned vs actual spending."""
    envelope_id: str
    envelope_name: str
    planned_amount: float
    actual_amount: float
    difference: float
    over_under: str = Field(..., description="'over' or 'under' budget")
    percentage: float = Field(..., description="Percentage of budget used")


class BudgetSettings(BaseModel):
    """User budget settings."""
    checking_buffer: float = Field(500.0, ge=0, description="Minimum buffer in checking account")
    emergency_fund_target: float = Field(0.0, ge=0)
    debt_strategy: DebtStrategy = Field(DebtStrategy.AVALANCHE)
    savings_rate: float = Field(0.2, ge=0, le=1, description="Target savings rate")
    discretionary_percentage: float = Field(0.3, ge=0, le=1, description="Percentage of remaining for discretionary")
    round_to_nearest: float = Field(10.0, ge=0, description="Round allocations to nearest amount")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UserBudgetProfile(BaseModel):
    """Complete user budget profile."""
    user_id: Optional[str] = None
    envelopes: List[Envelope] = Field(default_factory=list)
    bills: List[Bill] = Field(default_factory=list)
    debts: List[Debt] = Field(default_factory=list)
    sinking_funds: List[SinkingFund] = Field(default_factory=list)
    savings_goals: List[SavingsGoal] = Field(default_factory=list)
    settings: BudgetSettings = Field(default_factory=BudgetSettings)
    last_reconciliation: Optional[date] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def get_envelope(self, envelope_id: str) -> Optional[Envelope]:
        """Get envelope by ID."""
        for envelope in self.envelopes:
            if envelope.id == envelope_id:
                return envelope
        return None
    
    def get_bills_due_before(self, cutoff_date: date) -> List[Bill]:
        """Get bills due before a specific date."""
        return [
            bill for bill in self.bills
            if not bill.paid and bill.due_date <= cutoff_date
        ]
    
    def get_active_debts(self) -> List[Debt]:
        """Get debts that are not paid off."""
        return [debt for debt in self.debts if not debt.paid_off]
    
    def get_urgent_sinking_funds(self) -> List[SinkingFund]:
        """Get sinking funds with approaching deadlines (<= 3 months)."""
        today = date.today()
        return [
            sf for sf in self.sinking_funds
            if sf.months_remaining <= 3 and sf.current_balance < sf.target_amount
        ]