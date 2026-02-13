"""
Tests for the tax calculator module.
"""
import pytest
from datetime import date
from decimal import Decimal
from tax.models import (
    Province, PaySchedule, UserTaxProfile, IncomeStream,
    TaxBracket, JurisdictionTaxData, CPPEIData, TaxTableSet
)
from tax.calculator import TaxCalculator
from tax.loader import TaxTableLoader


def test_tax_bracket_model():
    """Test TaxBracket model validation."""
    # Valid bracket
    bracket = TaxBracket(threshold=0, rate=0.15)
    assert bracket.threshold == 0
    assert bracket.rate == 0.15
    
    # Invalid threshold
    with pytest.raises(ValueError):
        TaxBracket(threshold=-100, rate=0.15)
    
    # Invalid rate (too high)
    with pytest.raises(ValueError):
        TaxBracket(threshold=0, rate=1.5)
    
    # Invalid rate (negative)
    with pytest.raises(ValueError):
        TaxBracket(threshold=0, rate=-0.1)


def test_jurisdiction_tax_data_model():
    """Test JurisdictionTaxData model validation."""
    brackets = [
        TaxBracket(threshold=0, rate=0.15),
        TaxBracket(threshold=50000, rate=0.25),
        TaxBracket(threshold=100000, rate=0.30)
    ]
    
    # Valid data
    data = JurisdictionTaxData(
        year=2024,
        jurisdiction="ON",
        brackets=brackets,
        basic_personal_amount=15000
    )
    assert data.year == 2024
    assert data.jurisdiction == "ON"
    assert len(data.brackets) == 3
    
    # Unsorted brackets should raise error
    unsorted_brackets = [
        TaxBracket(threshold=100000, rate=0.30),
        TaxBracket(threshold=0, rate=0.15),
        TaxBracket(threshold=50000, rate=0.25)
    ]
    with pytest.raises(ValueError):
        JurisdictionTaxData(
            year=2024,
            jurisdiction="ON",
            brackets=unsorted_brackets,
            basic_personal_amount=15000
        )
    
    # Invalid jurisdiction
    with pytest.raises(ValueError):
        JurisdictionTaxData(
            year=2024,
            jurisdiction="INVALID",
            brackets=brackets,
            basic_personal_amount=15000
        )


def test_create_sample_tax_tables():
    """Test creating sample tax tables."""
    # Create federal data
    federal_brackets = [
        TaxBracket(threshold=0, rate=0.15),
        TaxBracket(threshold=53359, rate=0.205),
        TaxBracket(threshold=106717, rate=0.26),
        TaxBracket(threshold=165430, rate=0.29),
        TaxBracket(threshold=235675, rate=0.33)
    ]
    
    federal_data = JurisdictionTaxData(
        year=2024,
        jurisdiction="federal",
        brackets=federal_brackets,
        basic_personal_amount=15000
    )
    
    # Create Ontario data
    on_brackets = [
        TaxBracket(threshold=0, rate=0.0505),
        TaxBracket(threshold=49231, rate=0.0915),
        TaxBracket(threshold=98463, rate=0.1116),
        TaxBracket(threshold=150000, rate=0.1216),
        TaxBracket(threshold=220000, rate=0.1316)
    ]
    
    on_data = JurisdictionTaxData(
        year=2024,
        jurisdiction="ON",
        brackets=on_brackets,
        basic_personal_amount=11865
    )
    
    # Create CPP/EI data
    cpp_ei_data = CPPEIData(
        year=2024,
        cpp_rate=0.0595,
        cpp_ympe=68500,
        cpp_basic_exemption=3500,
        cpp_max_contrib=3867.50,
        ei_rate=0.0166,
        ei_mie=63100,
        ei_max_contrib=1047.46,
        qpp_rate=0.0615,
        qpp_ympe=68500,
        qpp_max_contrib=3997.50,
        qpip_rate=0.00494,
        qpip_max_contrib=449.74
    )
    
    # Create tax table set
    tax_tables = TaxTableSet(
        year=2024,
        federal=federal_data,
        provincial={"ON": on_data},
        cpp_ei=cpp_ei_data
    )
    
    assert tax_tables.year == 2024
    assert tax_tables.federal.jurisdiction == "federal"
    assert "ON" in tax_tables.provincial
    assert tax_tables.cpp_ei.cpp_rate == 0.0595


def test_tax_calculator_basic():
    """Test basic tax calculation."""
    # Create simple tax tables
    federal_brackets = [
        TaxBracket(threshold=0, rate=0.15),
        TaxBracket(threshold=50000, rate=0.25),
        TaxBracket(threshold=100000, rate=0.30)
    ]
    
    federal_data = JurisdictionTaxData(
        year=2024,
        jurisdiction="federal",
        brackets=federal_brackets,
        basic_personal_amount=15000
    )
    
    provincial_brackets = [
        TaxBracket(threshold=0, rate=0.05),
        TaxBracket(threshold=50000, rate=0.10),
        TaxBracket(threshold=100000, rate=0.12)
    ]
    
    provincial_data = JurisdictionTaxData(
        year=2024,
        jurisdiction="ON",
        brackets=provincial_brackets,
        basic_personal_amount=10000
    )
    
    cpp_ei_data = CPPEIData(
        year=2024,
        cpp_rate=0.05,
        cpp_ympe=60000,
        cpp_basic_exemption=3500,
        cpp_max_contrib=2825,
        ei_rate=0.015,
        ei_mie=60000,
        ei_max_contrib=900
    )
    
    tax_tables = TaxTableSet(
        year=2024,
        federal=federal_data,
        provincial={"ON": provincial_data},
        cpp_ei=cpp_ei_data
    )
    
    calculator = TaxCalculator(tax_tables)
    
    # Create user profile
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
    
    # Basic assertions
    assert result.gross_income == 75000
    assert result.federal_tax > 0
    assert result.provincial_tax > 0
    assert result.cpp_contribution > 0
    assert result.ei_contribution > 0
    assert result.total_tax > 0
    assert result.net_income < result.gross_income
    assert 0 < result.effective_tax_rate < 1
    
    # Check per pay period breakdown
    assert "gross" in result.per_pay_period
    assert "net" in result.per_pay_period
    assert "federal_tax" in result.per_pay_period
    assert "provincial_tax" in result.per_pay_period
    
    # Check bracket breakdowns
    assert len(result.federal_breakdown) > 0
    assert len(result.provincial_breakdown) > 0


def test_tax_calculator_edge_cases():
    """Test tax calculator with edge cases."""
    # Create minimal tax tables
    federal_brackets = [TaxBracket(threshold=0, rate=0.15)]
    federal_data = JurisdictionTaxData(
        year=2024,
        jurisdiction="federal",
        brackets=federal_brackets,
        basic_personal_amount=15000
    )
    
    provincial_brackets = [TaxBracket(threshold=0, rate=0.05)]
    provincial_data = JurisdictionTaxData(
        year=2024,
        jurisdiction="ON",
        brackets=provincial_brackets,
        basic_personal_amount=10000
    )
    
    cpp_ei_data = CPPEIData(
        year=2024,
        cpp_rate=0.05,
        cpp_ympe=60000,
        cpp_basic_exemption=3500,
        cpp_max_contrib=2825,
        ei_rate=0.015,
        ei_mie=60000,
        ei_max_contrib=900
    )
    
    tax_tables = TaxTableSet(
        year=2024,
        federal=federal_data,
        provincial={"ON": provincial_data},
        cpp_ei=cpp_ei_data
    )
    
    calculator = TaxCalculator(tax_tables)
    
    # Test with zero income
    zero_income_profile = UserTaxProfile(
        province=Province.ON,
        tax_year=2024,
        pay_schedule=PaySchedule.BIWEEKLY,
        income_streams=[
            IncomeStream(
                name="No Income",
                type="salary",
                gross_amount=0,
                frequency=PaySchedule.BIWEEKLY,
                start_date=date(2024, 1, 1)
            )
        ]
    )
    
    zero_result = calculator.calculate_annual_tax(zero_income_profile)
    assert zero_result.gross_income == 0
    assert zero_result.total_tax == 0
    assert zero_result.net_income == 0
    assert zero_result.effective_tax_rate == 0
    
    # Test with income below basic personal amount
    low_income_profile = UserTaxProfile(
        province=Province.ON,
        tax_year=2024,
        pay_schedule=PaySchedule.BIWEEKLY,
        income_streams=[
            IncomeStream(
                name="Low Income",
                type="salary",
                gross_amount=10000,  # Below BPA
                frequency=PaySchedule.BIWEEKLY,
                start_date=date(2024, 1, 1)
            )
        ]
    )
    
    low_result = calculator.calculate_annual_tax(low_income_profile)
    assert low_result.gross_income == 10000
    # Should have little to no tax
    assert low_result.total_tax >= 0
    
    # Test with very high income
    high_income_profile = UserTaxProfile(
        province=Province.ON,
        tax_year=2024,
        pay_schedule=PaySchedule.BIWEEKLY,
        income_streams=[
            IncomeStream(
                name="High Income",
                type="salary",
                gross_amount=500000,
                frequency=PaySchedule.BIWEEKLY,
                start_date=date(2024, 1, 1)
            )
        ]
    )
    
    high_result = calculator.calculate_annual_tax(high_income_profile)
    assert high_result.gross_income == 500000
    assert high_result.total_tax > 0
    assert high_result.net_income < high_result.gross_income


def test_cpp_ei_calculations():
    """Test CPP and EI contribution calculations."""
    cpp_ei_data = CPPEIData(
        year=2024,
        cpp_rate=0.0595,
        cpp_ympe=68500,
        cpp_basic_exemption=3500,
        cpp_max_contrib=3867.50,
        ei_rate=0.0166,
        ei_mie=63100,
        ei_max_contrib=1047.46
    )
    
    # Create simple tax tables for testing
    federal_brackets = [TaxBracket(threshold=0, rate=0.15)]
    federal_data = JurisdictionTaxData(
        year=2024,
        jurisdiction="federal",
        brackets=federal_brackets,
        basic_personal_amount=15000
    )
    
    provincial_brackets = [TaxBracket(threshold=0, rate=0.05)]
    provincial_data = JurisdictionTaxData(
        year=2024,
        jurisdiction="ON",
        brackets=provincial_brackets,
        basic_personal_amount=10000
    )
    
    tax_tables = TaxTableSet(
        year=2024,
        federal=federal_data,
        provincial={"ON": provincial_data},
        cpp_ei=cpp_ei_data
    )
    
    calculator = TaxCalculator(tax_tables)
    
    # Test CPP calculation below YMPE
    profile_below_ympe = UserTaxProfile(
        province=Province.ON,
        tax_year=2024,
        pay_schedule=PaySchedule.BIWEEKLY,
        income_streams=[
            IncomeStream(
                name="Below YMPE",
                type="salary",
                gross_amount=50000,
                frequency=PaySchedule.BIWEEKLY,
                start_date=date(2024, 1, 1)
            )
        ]
    )
    
    result_below = calculator.calculate_annual_tax(profile_below_ympe)
    expected_cpp = (50000 - 3500) * 0.0595  # Below YMPE
    expected_cpp = min(expected_cpp, 3867.50)
    assert abs(result_below.cpp_contribution - expected_cpp) < 0.01
    
    # Test CPP calculation above YMPE (should be capped)
    profile_above_ympe = UserTaxProfile(
        province=Province.ON,
        tax_year=2024,
        pay_schedule=PaySchedule.BIWEEKLY,
        income_streams=[
            IncomeStream(
                name="Above YMPE",
                type="salary",
                gross_amount=100000,
                frequency=PaySchedule.BIWEEKLY,
                start_date=date(2024, 1, 1)
            )
        ]
    )
    
    result_above = calculator.calculate_annual_tax(profile_above_ympe)
    # Should be at max contribution
    assert abs(result_above.cpp_contribution - 3867.50) < 0.01
    
    # Test EI calculation
    expected_ei = min(50000, 63100) * 0.0166
    expected_ei = min(expected_ei, 1047.46)
    assert abs(result_below.ei_contribution - expected_ei) < 0.01


def test_tax_loader():
    """Test tax table loader."""
    loader = TaxTableLoader()
    
    # Test loading from JSON
    import os
    json_path = os.path.join(os.path.dirname(__file__), "..", "data", "tax_tables_2024.json")
    
    if os.path.exists(json_path):
        tax_tables = loader.load_from_json(json_path)
        
        assert tax_tables.year == 2024
        assert tax_tables.federal.jurisdiction == "federal"
        assert "ON" in tax_tables.provincial
        assert "QC" in tax_tables.provincial
        assert "AB" in tax_tables.provincial
        assert tax_tables.cpp_ei.cpp_rate == 0.0595
        
        # Test validation
        errors = loader.validate_tax_tables(tax_tables)
        assert len(errors) == 0, f"Validation errors: {errors}"
    
    # Test load_year method
    tax_tables_2024 = loader.load_year(2024)
    if tax_tables_2024:
        assert tax_tables_2024.year == 2024


def test_quebec_specific_calculations():
    """Test Quebec-specific calculations (QPP, QPIP)."""
    # Create tax tables with Quebec data
    federal_brackets = [TaxBracket(threshold=0, rate=0.15)]
    federal_data = JurisdictionTaxData(
        year=2024,
        jurisdiction="federal",
        brackets=federal_brackets,
        basic_personal_amount=15000
    )
    
    qc_brackets = [TaxBracket(threshold=0, rate=0.14)]
    qc_data = JurisdictionTaxData(
        year=2024,
        jurisdiction="QC",
        brackets=qc_brackets,
        basic_personal_amount=17783
    )
    
    cpp_ei_data = CPPEIData(
        year=2024,
        cpp_rate=0.0595,
        cpp_ympe=68500,
        cpp_basic_exemption=3500,
        cpp_max_contrib=3867.50,
        ei_rate=0.0166,
        ei_mie=63100,
        ei_max_contrib=1047.46,
        qpp_rate=0.0615,
        qpp_ympe=68500,
        qpp_max_contrib=3997.50,
        qpip_rate=0.00494,
        qpip_max_contrib=449.74
    )
    
    tax_tables = TaxTableSet(
        year=2024,
        federal=federal_data,
        provincial={"QC": qc_data},
        cpp_ei=cpp_ei_data
    )
    
    calculator = TaxCalculator(tax_tables)
    
    # Quebec resident profile
    qc_profile = UserTaxProfile(
        province=Province.QC,
        tax_year=2024,
        pay_schedule=PaySchedule.BIWEEKLY,
        income_streams=[
            IncomeStream(
                name="QC Job",
                type="salary",
                gross_amount=75000,
                frequency=PaySchedule.BIWEEKLY,
                start_date=date(2024, 1, 1)
            )
        ]
    )
    
    result = calculator.calculate_annual_tax(qc_profile)
    
    # Should have QPP and QPIP contributions
   