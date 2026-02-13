# Insane Finance App - Architecture & Data Model

## 🏗️ System Architecture

### Overview
The application follows a modular, layered architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit UI Layer                        │
├─────────────────────────────────────────────────────────────┤
│                  Business Logic Layer                        │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────┐    │
│  │   Tax       │  │   Budget    │  │   Data Import    │    │
│  │   Module    │  │   Engine    │  │   & Processing   │    │
│  └─────────────┘  └─────────────┘  └──────────────────┘    │
├─────────────────────────────────────────────────────────────┤
│                  Data Access Layer                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              SQLAlchemy ORM Models                   │   │
│  └──────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                  Storage Layer                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │               SQLite Database                        │   │
│  │               JSON Tax Tables                        │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 📊 Data Models

### Tax Module Models

#### `TaxBracket`
```python
class TaxBracket(BaseModel):
    threshold: float  # Income threshold for this bracket
    rate: float       # Marginal tax rate (0.0 to 1.0)
```

#### `JurisdictionTaxData`
```python
class JurisdictionTaxData(BaseModel):
    year: int
    jurisdiction: str  # 'federal' or province code
    brackets: List[TaxBracket]
    basic_personal_amount: float
    surtaxes: Optional[Dict[str, float]]
    credits: Optional[Dict[str, float]]
    metadata: Dict[str, Any]
```

#### `CPPEIData`
```python
class CPPEIData(BaseModel):
    year: int
    cpp_rate: float
    cpp_ympe: float  # Year's Maximum Pensionable Earnings
    cpp_basic_exemption: float
    cpp_max_contrib: float
    ei_rate: float
    ei_mie: float  # Maximum Insurable Earnings
    ei_max_contrib: float
    qpp_rate: Optional[float]  # Quebec only
    qpp_ympe: Optional[float]
    qpp_max_contrib: Optional[float]
    qpip_rate: Optional[float]  # Quebec only
    qpip_max_contrib: Optional[float]
```

#### `TaxTableSet`
```python
class TaxTableSet(BaseModel):
    year: int
    federal: JurisdictionTaxData
    provincial: Dict[str, JurisdictionTaxData]  # province_code -> data
    cpp_ei: CPPEIData
    metadata: Dict[str, Any]
```

#### `UserTaxProfile`
```python
class UserTaxProfile(BaseModel):
    province: Province
    tax_year: int
    pay_schedule: PaySchedule
    income_streams: List[IncomeStream]
    additional_claims: Dict[str, float] = Field(default_factory=dict)
    additional_tax_withheld: float = 0.0
```

### Budget Module Models

#### `Envelope`
```python
class Envelope(BaseModel):
    id: Optional[str]
    category: EnvelopeCategory  # bills, debt, sinking, savings, investing, discretionary
    name: str
    target_amount: float
    current_balance: float = 0.0
    priority: int  # 1=highest, 10=lowest
    due_date: Optional[date]
    recurrence: Optional[Recurrence]
    auto_pay: bool = False
```

#### `Bill`
```python
class Bill(BaseModel):
    id: Optional[str]
    name: str
    amount: float
    bill_type: BillType  # fixed, variable, subscription
    envelope_id: str
    due_date: date
    recurrence: Optional[Recurrence]
    paid: bool = False
    paid_date: Optional[date]
```

#### `Debt`
```python
class Debt(BaseModel):
    id: Optional[str]
    name: str
    balance: float
    apr: float  # 0.0 to 1.0
    minimum_payment: float
    due_date: date
    envelope_id: str
    strategy: DebtStrategy  # avalanche, snowball
    paid_off: bool = False
```

#### `SinkingFund`
```python
class SinkingFund(BaseModel):
    id: Optional[str]
    name: str
    target_amount: float
    current_balance: float = 0.0
    deadline: date
    monthly_contribution: Optional[float]
    envelope_id: str
    
    @property
    def months_remaining(self) -> int
    @property
    def recommended_contribution(self) -> float
```

#### `UserBudgetProfile`
```python
class UserBudgetProfile(BaseModel):
    user_id: Optional[str]
    envelopes: List[Envelope]
    bills: List[Bill]
    debts: List[Debt]
    sinking_funds: List[SinkingFund]
    savings_goals: List[SavingsGoal]
    settings: BudgetSettings
    last_reconciliation: Optional[date]
```

### Database Models (SQLAlchemy)

#### Core Entities
- `User`: User account with province, tax year, pay schedule
- `IncomeStream`: Income sources with type, amount, frequency
- `Envelope`: Budget envelopes (maps to Pydantic model)
- `Bill`: Bills and recurring expenses
- `Debt`: Debt accounts with APR and minimum payments
- `SinkingFund`: Future expense savings
- `SavingsGoal`: Long-term savings targets
- `Transaction`: Financial transactions with categorization
- `Paycheck`: Paycheck records with allocations
- `TaxTable`: Stored tax table data

## 🔧 Core Algorithms

### Tax Calculation Algorithm

```python
def calculate_jurisdiction_tax(income, jurisdiction_data):
    # 1. Apply basic personal amount deduction
    taxable_income = max(0, income - jurisdiction_data.basic_personal_amount)
    
    # 2. Apply additional TD1 claims
    for claim_amount in additional_claims.values():
        taxable_income = max(0, taxable_income - claim_amount)
    
    # 3. Progressive bracket calculation
    tax = 0.0
    for i in range(len(brackets)):
        current_bracket = brackets[i]
        next_threshold = brackets[i+1].threshold if i+1 < len(brackets) else float('inf')
        
        # Income in this bracket
        bracket_income = min(
            max(0, taxable_income - current_bracket.threshold),
            next_threshold - current_bracket.threshold
        )
        
        if bracket_income > 0:
            tax += bracket_income * current_bracket.rate
    
    # 4. Apply surtaxes if any
    if jurisdiction_data.surtaxes:
        for surtax_rate in jurisdiction_data.surtaxes.values():
            tax += tax * surtax_rate
    
    return round_to_cents(tax)
```

### CPP/EI Calculation
```python
def calculate_cpp_contribution(income, cpp_data):
    # Pensionable earnings = income - basic exemption, capped at YMPE
    pensionable_earnings = max(0, income - cpp_data.cpp_basic_exemption)
    pensionable_earnings = min(pensionable_earnings, cpp_data.cpp_ympe)
    
    cpp_contrib = pensionable_earnings * cpp_data.cpp_rate
    cpp_contrib = min(cpp_contrib, cpp_data.cpp_max_contrib)
    
    return round_to_cents(cpp_contrib)
```

### Paycheck Allocation Algorithm

**Priority Order:**
1. **Ensure minimum buffer** in checking account
2. **Fund bills due before next payday** (by due date priority)
3. **Fund minimum debt payments**
4. **Fund sinking funds by urgency** (time-to-deadline)
5. **Fund savings/investing per strategy** (fixed amount or %)
6. **Remaining goes to either:**
   - Extra debt payments (avalanche/snowball strategy)
   - Discretionary spending

```python
def allocate_paycheck(net_amount, paycheck_date, profile):
    allocation = PaycheckAllocation(...)
    
    # Step 1: Buffer (handled in cashflow forecast)
    
    # Step 2: Bills due before next payday
    next_payday = calculate_next_payday(paycheck_date)
    bills = profile.get_bills_due_before(next_payday)
    bills.sort(key=lambda b: b.due_date)
    
    for bill in bills:
        envelope = profile.get_envelope(bill.envelope_id)
        if envelope.current_balance < bill.amount:
            amount_needed = bill.amount - envelope.current_balance
            if amount_needed <= allocation.remaining_amount:
                allocate_to_envelope(allocation, envelope.id, amount_needed)
    
    # Steps 3-6 continue similarly...
    
    return allocation
```

### Cashflow Forecasting Algorithm
```python
def forecast_cashflow(start_date, end_date, starting_balance, paycheck_allocations):
    current_balance = starting_balance
    current_date = start_date
    
    while current_date <= end_date:
        # Add paycheck if received today
        if current_date in paycheck_by_date:
            paycheck = paycheck_by_date[current_date]
            current_balance += paycheck.net_amount
        
        # Pay bills due today
        today_bills = [b for b in bills if b.due_date == current_date]
        for bill in today_bills:
            if envelope_has_funds(bill.envelope_id, bill.amount):
                current_balance -= bill.amount
        
        # Record daily balance
        daily_balances[current_date] = current_balance
        
        # Check for alerts
        if current_balance < settings.checking_buffer:
            add_alert(f"Low balance: ${current_balance:.2f}")
        
        current_date += timedelta(days=1)
    
    return CashflowForecast(...)
```

## 📁 File Structure

```
insane-finance-app/
├── app/
│   └── main.py                    # Streamlit application entry point
├── tax/
│   ├── __init__.py
│   ├── models.py                  # Pydantic models for tax data
│   ├── calculator.py              # Tax calculation logic
│   └── loader.py                  # Tax table import/export
├── budget/
│   ├── __init__.py
│   ├── models.py                  # Pydantic models for budgeting
│   └── allocator.py               # Paycheck allocation engine
├── db/
│   ├── __init__.py
│   └── models.py                  # SQLAlchemy database models
├── data/
│   └── tax_tables_2024.json       # Sample tax tables
├── tests/
│   ├── __init__.py
│   ├── test_tax_calculator.py     # Tax module tests
│   └── test_budget_allocator.py   # Budget module tests
├── requirements.txt               # Python dependencies
├── README.md                      # User documentation
└── ARCHITECTURE.md               # This file
```

## 🔄 Data Flow

### Tax Calculation Flow
```
User Input → TaxTableLoader → TaxCalculator → Results Display
    │            │                  │              │
    │            │                  │              └──► Streamlit UI
    │            │                  │
    │            └──► JSON/CSV      └──► Progressive
    │                 Files             Bracket Math
    │
    └──► Province, Year,
        Income, Deductions
```

### Budget Allocation Flow
```
User Profile → PaycheckAllocator → Allocation Plan → Cashflow Forecast
     │               │                  │                  │
     │               │                  │                  └──► Alerts & Warnings
     │               │                  │
     │               └──► Priority      └──► Envelope Updates
     │                    Rules
     │
     └──► Envelopes, Bills,
         Debts, Settings
```

## 🧮 Mathematical Formulas

### Effective Tax Rate
```
Effective Tax Rate = Total Tax ÷ Gross Income
```

### CPP Contribution
```
Pensionable Earnings = min(max(0, Income - Basic Exemption), YMPE)
CPP Contribution = min(Pensionable Earnings × CPP Rate, Max Contribution)
```

### Sinking Fund Monthly Contribution
```
Months Remaining = max(0, (Deadline - Today).months)
Remaining Amount = Target Amount - Current Balance
Monthly Contribution = Remaining Amount ÷ Months Remaining
```

### Debt Payoff Timeline (Simplified)
```
Monthly Payment = Minimum Payment + Extra Payment
Monthly Interest = Remaining Balance × APR ÷ 12
Principal Payment = Monthly Payment - Monthly Interest
Months to Payoff = Remaining Balance ÷ Principal Payment
```

## 🔐 Security Considerations

### Data Protection
- **Local Storage**: SQLite database remains on user's machine
- **Sensitive Data**: No transmission of financial data to external servers
- **Input Validation**: Comprehensive Pydantic validation on all models
- **Error Handling**: Graceful degradation with user-friendly messages

### Privacy
- **No Analytics**: No tracking or analytics collection
- **User Control**: Full control over data import/export
- **Transparency**: Open source with clear data flow documentation

## 📈 Performance Considerations

### Database Optimization
- **Indexing**: Strategic indexes on frequently queried fields
- **Connection Pooling**: SQLAlchemy connection management
- **Lazy Loading**: Relationship loading optimized for common use cases

### Memory Management
- **Streaming**: Large CSV imports processed in chunks
- **Caching**: Tax tables cached in memory after loading
- **Cleanup**: Regular cleanup of temporary data

## 🔧 Extension Points

### Adding New Features
1. **New Tax Jurisdiction**: Add to `Province` enum and update tax table loader
2. **New Budget Category**: Add to `EnvelopeCategory` enum and update allocation logic
3. **New Report Type**: Add to reports page with new data visualization
4. **New Import Format**: Extend `TaxTableLoader` with new parser

### Integration Points
1. **Bank APIs**: Implement adapter for Plaid, Yodlee, or direct bank APIs
2. **Investment Tracking**: Connect to brokerage APIs or CSV exports
3. **Tax Filing**: Export data to tax preparation software formats
4. **Mobile Sync**: Add REST API for mobile app synchronization

## 🧪 Testing Strategy

### Unit Tests
- **Tax Calculations**: Verify bracket math with known inputs/outputs
- **Budget Allocation**: Test priority rules with various scenarios
- **Data Models**: Validate constraints and business rules

### Integration Tests
- **End-to-End Workflows**: Complete user journeys
- **Database Operations**: CRUD operations with SQLite
- **File Import/Export**: JSON/CSV round-trip testing

### Performance Tests
- **Large Datasets**: Test with thousands of transactions
- **Concurrent Access**: Simulate multiple users (future)
- **Memory Usage**: Profile memory consumption

## 🚀 Deployment Considerations

### Local Deployment
- **Virtual Environment**: Isolated Python environment
- **Database Migration**: Alembic for schema changes (future)
- **Configuration**: Environment variables for settings

### Cloud Deployment (Future)
- **Containerization**: Docker for consistent environments
- **Database**: PostgreSQL for production use
- **Scaling**: Horizontal scaling for multi-user support

---

*This architecture provides a solid foundation for a comprehensive personal finance application while maintaining flexibility for future enhancements.*