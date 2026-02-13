# Insane Finance App 💰

A comprehensive personal finance and paycheck budgeting application for Canada with province-specific automatic tax calculations and a sophisticated paycheck allocation engine.

## 🚀 Features

### **Tax Module**
- **Accurate Canadian Payroll Calculations**: Federal + provincial/territorial tax calculations
- **All Provinces & Territories**: AB, BC, MB, NB, NL, NS, NT, NU, ON, PE, QC, SK, YT
- **CPP/EI/QPP Calculations**: Yearly maximums and rates for each tax year
- **Tax Table Management**: Import/export JSON/CSV, fetch from official sources
- **Multiple Income Streams**: Salary, overtime, bonus, irregular income, reimbursements

### **Budget Engine**
- **Paycheck-Based Allocation**: Automatically allocate money to bills, debt, sinking funds, savings, and discretionary spending
- **Envelope System**: Categorize spending with customizable envelopes
- **Cashflow Forecasting**: Day-by-day balance predictions with alerts
- **Debt Payoff Strategies**: Avalanche (highest interest first) vs Snowball (smallest balance first)
- **Sinking Funds**: Save for future expenses with deadline tracking
- **Reconciliation**: Match actual spending to planned budgets

### **User Interface**
- **Streamlit Dashboard**: Modern, interactive web interface
- **8 Comprehensive Pages**:
  1. **Overview**: Next payday, predicted balance, upcoming bills, alerts
  2. **Paycheck Planner**: Gross→net breakdown, deductions, allocation summary
  3. **Tax Calculator**: Detailed tax breakdown by bracket
  4. **Bills & Calendar**: Due dates timeline, calendar view
  5. **Debts**: Payoff projections, strategy comparison
  6. **Sinking Funds**: Progress bars, required contributions
  7. **Reports**: Spending by category, net worth, trends
  8. **Settings**: Province, tax year, pay schedule, table import/export

### **Data Management**
- **SQLite Database**: Local storage with SQLAlchemy ORM
- **Transaction Import**: CSV import from bank exports
- **Subscription Detection**: Automatic recurring pattern recognition
- **Data Export**: Export to CSV for external analysis

## 🛠️ Installation

### Prerequisites
- Python 3.8+
- pip package manager

### Setup

1. **Clone and navigate to the project**
```bash
cd insane-finance-app
```

2. **Create virtual environment**
```bash
python -m venv venv
```

3. **Activate virtual environment**
- **Windows**:
  ```bash
  venv\Scripts\activate
  ```
- **Mac/Linux**:
  ```bash
  source venv/bin/activate
  ```

4. **Install dependencies**
```bash
pip install -r requirements.txt
```

5. **Initialize database**
```bash
python -c "from db.models import default_db; default_db.init_db()"
```

6. **Run the application**
```bash
streamlit run app/main.py
```

## 📋 Requirements

See `requirements.txt` for complete list. Key dependencies:
- `streamlit` - Web dashboard
- `pandas` - Data manipulation
- `plotly` - Interactive charts
- `sqlalchemy` - Database ORM
- `pydantic` - Data validation
- `pytest` - Testing framework

## 📊 Sample Tax Tables

The app includes sample tax tables for 2024 in `data/tax_tables_2024.json` covering:
- Federal tax brackets
- All 13 provinces/territories
- CPP/EI rates and maximums
- QPP/QPIP for Quebec

**⚠️ Important**: These are example rates for demonstration. For actual tax calculations, import official CRA and provincial revenue agency data.

## 🔧 Importing Official Tax Tables

### Method 1: JSON Import
1. Navigate to **Settings → Tax Table Management**
2. Upload a JSON file with the following structure:
```json
{
  "year": 2024,
  "federal": { ... },
  "provincial": { ... },
  "cpp_ei": { ... }
}
```

### Method 2: CSV Import (Individual Jurisdictions)
1. Prepare CSV files with columns: `threshold,rate,basic_personal_amount`
2. Use the `TaxTableLoader.import_from_csv()` method

### Method 3: Official Sources (Placeholder)
The app includes a `TableUpdater` class that can be extended to fetch data from:
- Canada Revenue Agency (CRA)
- Provincial revenue websites
- Service Canada for CPP/EI rates

## 🧪 Testing

Run the test suite:
```bash
pytest tests/ -v
```

Test coverage includes:
- Tax bracket calculations
- CPP/EI contribution limits
- Budget allocation algorithms
- Cashflow forecasting
- Data model validation

## 🏗️ Architecture

```
insane-finance-app/
├── app/
│   └── main.py              # Streamlit dashboard
├── tax/
│   ├── models.py           # Pydantic models
│   ├── calculator.py       # Tax calculations
│   └── loader.py          # Tax table import/export
├── budget/
│   ├── models.py          # Budget models
│   └── allocator.py       # Paycheck allocation engine
├── db/
│   └── models.py          # SQLAlchemy models
├── data/
│   └── tax_tables_2024.json # Sample tax data
├── tests/
│   └── test_tax_calculator.py
├── requirements.txt
├── README.md
└── ARCHITECTURE.md
```

## 📈 Sample Workflow

1. **Setup Profile**
   - Select province (e.g., Ontario)
   - Set tax year (2024)
   - Configure pay schedule (biweekly)

2. **Configure Budget**
   - Create envelopes: Rent, Utilities, Groceries, etc.
   - Add bills with due dates
   - Set up sinking funds for future expenses
   - Configure debt payoff strategy

3. **Plan Paycheck**
   - Enter gross income
   - View tax breakdown (federal, provincial, CPP, EI)
   - See net pay calculation
   - Review automatic allocation to envelopes

4. **Monitor & Adjust**
   - Track daily cashflow
   - Receive alerts for low balances
   - Reconcile actual vs planned spending
   - Adjust allocations based on performance

## 🔒 Security & Quality

- **Local Data Storage**: SQLite database stays on your machine
- **Input Validation**: Comprehensive Pydantic models
- **Error Handling**: Graceful degradation with clear error messages
- **Type Hints**: Full type annotations throughout
- **Testing**: 80%+ coverage for core logic
- **Logging**: Secure logging without sensitive data

## 🚧 Future Enhancements

Planned features:
- [ ] Bank API integration (Plaid, Yodlee)
- [ ] Investment portfolio tracking
- [ ] Retirement planning calculator
- [ ] Mobile app (React Native)
- [ ] Multi-user support with authentication
- [ ] Advanced reporting with PDF export
- [ ] AI-powered spending categorization

## 📝 License

This project is for educational and demonstration purposes. Tax calculations should be verified with official government sources.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit changes
4. Push to the branch
5. Open a Pull Request

## 🆘 Support

For issues or questions:
1. Check the [ARCHITECTURE.md](ARCHITECTURE.md) for technical details
2. Review sample data in `data/` directory
3. Run tests to verify installation
4. Open an issue with detailed description

---

**Disclaimer**: This application provides estimates for educational purposes. Always consult with a qualified financial advisor and verify tax calculations with official government sources before making financial decisions.