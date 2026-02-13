#!/usr/bin/env python3
"""
Test script to verify the Insane Finance App installation.
"""
import sys
import os
import json
from datetime import date

def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")
    
    try:
        # Test tax module imports
        from tax.models import Province, PaySchedule, TaxBracket, JurisdictionTaxData
        from tax.calculator import TaxCalculator
        from tax.loader import TaxTableLoader
        
        # Test budget module imports
        from budget.models import (
            UserBudgetProfile, Envelope, Bill, Debt, SinkingFund,
            EnvelopeCategory, DebtStrategy, BudgetSettings
        )
        from budget.allocator import PaycheckAllocator, CashflowForecaster
        
        # Test database imports
        from db.models import Database
        
        print("✅ All imports successful!")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're in the correct directory and have installed requirements.")
        return False

def test_tax_tables():
    """Test that tax tables can be loaded."""
    print("\nTesting tax table loading...")
    
    try:
        from tax.loader import TaxTableLoader
        loader = TaxTableLoader()
        tax_tables = loader.load_year(2024)
        
        if tax_tables:
            print(f"✅ Tax tables loaded for year {tax_tables.year}")
            print(f"   Federal jurisdiction: {tax_tables.federal.jurisdiction}")
            print(f"   Provinces loaded: {len(tax_tables.provincial)}")
            print(f"   CPP rate: {tax_tables.cpp_ei.cpp_rate}")
            return True
        else:
            print("❌ Could not load tax tables for 2024")
            print("   Make sure data/tax_tables_2024.json exists")
            return False
    except Exception as e:
        print(f"❌ Error loading tax tables: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_sample_calculation():
    """Test a sample tax calculation."""
    print("\nTesting sample tax calculation...")
    
    try:
        # Load tax tables
        from tax.loader import TaxTableLoader
        from tax.models import UserTaxProfile, IncomeStream, Province, PaySchedule
        from tax.calculator import TaxCalculator
        
        loader = TaxTableLoader()
        tax_tables = loader.load_year(2024)
        
        if not tax_tables:
            print("❌ Cannot test calculation without tax tables")
            return False
        
        # Create calculator
        calculator = TaxCalculator(tax_tables)
        
        # Create a simple user profile
        profile = UserTaxProfile(
            province=Province.ON,
            tax_year=2024,
            pay_schedule=PaySchedule.BIWEEKLY,
            income_streams=[
                IncomeStream(
                    name="Test Job",
                    type="salary",
                    gross_amount=75000,
                    frequency=PaySchedule.BIWEEKLY,
                    start_date=date(2024, 1, 1)
                )
            ]
        )
        
        # Calculate tax
        result = calculator.calculate_annual_tax(profile)
        
        print(f"✅ Tax calculation successful!")
        print(f"   Gross income: ${result.gross_income:,.2f}")
        print(f"   Federal tax: ${result.federal_tax:,.2f}")
        print(f"   Provincial tax: ${result.provincial_tax:,.2f}")
        print(f"   CPP contribution: ${result.cpp_contribution:,.2f}")
        print(f"   EI contribution: ${result.ei_contribution:,.2f}")
        print(f"   Total tax: ${result.total_tax:,.2f}")
        print(f"   Net income: ${result.net_income:,.2f}")
        print(f"   Effective tax rate: {result.effective_tax_rate*100:.1f}%")
        
        return True
    except Exception as e:
        print(f"❌ Error in tax calculation: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_budget_allocation():
    """Test a sample budget allocation."""
    print("\nTesting budget allocation...")
    
    try:
        from budget.models import (
            UserBudgetProfile, Envelope, Bill, Debt, SinkingFund,
            EnvelopeCategory, DebtStrategy, BudgetSettings
        )
        from budget.allocator import PaycheckAllocator
        
        # Create a sample budget profile
        profile = UserBudgetProfile(
            envelopes=[
                Envelope(
                    id="envelope_1",
                    category=EnvelopeCategory.BILLS,
                    name="Rent",
                    target_amount=1500.00,
                    current_balance=0.0,
                    priority=1
                ),
                Envelope(
                    id="envelope_2",
                    category=EnvelopeCategory.DEBT,
                    name="Credit Card",
                    target_amount=200.00,
                    current_balance=0.0,
                    priority=3
                ),
                Envelope(
                    id="envelope_3",
                    category=EnvelopeCategory.DISCRETIONARY,
                    name="Fun Money",
                    target_amount=400.00,
                    current_balance=0.0,
                    priority=10
                )
            ],
            bills=[
                Bill(
                    id="bill_1",
                    name="Rent",
                    amount=1500.00,
                    bill_type="fixed",
                    envelope_id="envelope_1",
                    due_date=date.today().replace(day=1),
                    paid=False
                )
            ],
            debts=[
                Debt(
                    id="debt_1",
                    name="Credit Card",
                    balance=5000.00,
                    apr=0.1999,
                    minimum_payment=200.00,
                    due_date=date.today(),
                    envelope_id="envelope_2",
                    strategy=DebtStrategy.AVALANCHE,
                    paid_off=False
                )
            ],
            settings=BudgetSettings(
                checking_buffer=500.00,
                emergency_fund_target=10000.00,
                debt_strategy=DebtStrategy.AVALANCHE,
                savings_rate=0.20,
                discretionary_percentage=0.30,
                round_to_nearest=10.00
            )
        )
        
        # Create allocator
        allocator = PaycheckAllocator(profile)
        
        # Allocate a paycheck
        allocation = allocator.allocate_paycheck(
            net_amount=2200.00,
            paycheck_date=date.today()
        )
        
        print(f"✅ Budget allocation successful!")
        print(f"   Net paycheck: ${allocation.net_amount:,.2f}")
        print(f"   Allocations: {len(allocation.allocations)} envelopes")
        print(f"   Remaining: ${allocation.remaining_amount:,.2f}")
        
        for envelope_id, amount in allocation.allocations.items():
            envelope = profile.get_envelope(envelope_id)
            if envelope:
                print(f"     - {envelope.name}: ${amount:,.2f}")
        
        return True
    except Exception as e:
        print(f"❌ Error in budget allocation: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database():
    """Test database initialization."""
    print("\nTesting database...")
    
    try:
        from db.models import Database
        
        # Create database instance
        db = Database("sqlite:///:memory:")  # Use in-memory database for testing
        db.init_db()
        
        print("✅ Database initialization successful!")
        
        # Test creating a session
        session = db.get_session()
        db.close_session(session)
        
        print("✅ Database session management successful!")
        return True
    except Exception as e:
        print(f"❌ Error with database: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("Insane Finance App - Installation Test")
    print("=" * 60)
    
    # Add current directory to Python path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    tests = [
        ("Module Imports", test_imports),
        ("Tax Table Loading", test_tax_tables),
        ("Tax Calculation", test_sample_calculation),
        ("Budget Allocation", test_budget_allocation),
        ("Database", test_database),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*40}")
        print(f"Test: {test_name}")
        print(f"{'='*40}")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ Test crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*60}")
    print("Test Summary")
    print(f"{'='*60}")
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
        if success:
            passed += 1
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! The application is ready to use.")
        print("\nTo run the application:")
        print("1. Activate your virtual environment")
        print("2. Run: streamlit run app/main.py")
        print("3. Open your browser to http://localhost:8501")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed.")
        print("Check the error messages above and ensure all requirements are installed.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)