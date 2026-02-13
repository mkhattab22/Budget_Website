"""
Tax calculator for Canadian federal and provincial income tax, CPP, EI, QPP, QPIP.
"""
import math
from typing import Dict, List, Optional, Tuple
from decimal import Decimal, ROUND_HALF_UP
from .models import (
    TaxTableSet, TaxCalculationResult, UserTaxProfile, 
    Province, PaySchedule, JurisdictionTaxData, CPPEIData
)


class TaxCalculator:
    """Calculator for Canadian income tax and deductions."""
    
    def __init__(self, tax_tables: TaxTableSet):
        self.tax_tables = tax_tables
        self.year = tax_tables.year
        
    def calculate_annual_tax(self, profile: UserTaxProfile) -> TaxCalculationResult:
        """
        Calculate annual tax and deductions for a user profile.
        
        Args:
            profile: User tax profile with income streams and province
            
        Returns:
            TaxCalculationResult with detailed breakdown
        """
        # Calculate total gross income from all streams
        total_gross = sum(stream.gross_amount for stream in profile.income_streams)
        
        # Calculate deductions
        federal_tax = self._calculate_jurisdiction_tax(
            total_gross, self.tax_tables.federal, profile
        )
        
        provincial_data = self.tax_tables.provincial.get(profile.province.value)
        if not provincial_data:
            raise ValueError(f"No tax data for province {profile.province.value} in year {self.year}")
        
        provincial_tax = self._calculate_jurisdiction_tax(
            total_gross, provincial_data, profile
        )
        
        # Calculate CPP/EI/QPP contributions
        cpp_contrib = self._calculate_cpp_contribution(total_gross)
        ei_contrib = self._calculate_ei_contribution(total_gross)
        
        # Quebec-specific calculations
        qpp_contrib = None
        qpip_contrib = None
        if profile.province == Province.QC:
            qpp_contrib = self._calculate_qpp_contribution(total_gross)
            qpip_contrib = self._calculate_qpip_contribution(total_gross)
        
        # Calculate total tax and net income
        total_tax = federal_tax + provincial_tax + cpp_contrib + ei_contrib
        if qpp_contrib:
            total_tax += qpp_contrib
        if qpip_contrib:
            total_tax += qpip_contrib
        
        net_income = total_gross - total_tax
        effective_tax_rate = total_tax / total_gross if total_gross > 0 else 0
        
        # Calculate per pay period amounts
        pay_periods = self._get_pay_periods_per_year(profile.pay_schedule)
        per_pay_period = {
            "gross": total_gross / pay_periods,
            "federal_tax": federal_tax / pay_periods,
            "provincial_tax": provincial_tax / pay_periods,
            "cpp": cpp_contrib / pay_periods,
            "ei": ei_contrib / pay_periods,
            "total_tax": total_tax / pay_periods,
            "net": net_income / pay_periods,
        }
        
        if qpp_contrib:
            per_pay_period["qpp"] = qpp_contrib / pay_periods
        if qpip_contrib:
            per_pay_period["qpip"] = qpip_contrib / pay_periods
        
        # Get detailed bracket breakdowns
        federal_breakdown = self._get_bracket_breakdown(total_gross, self.tax_tables.federal)
        provincial_breakdown = self._get_bracket_breakdown(total_gross, provincial_data)
        
        return TaxCalculationResult(
            gross_income=total_gross,
            federal_tax=federal_tax,
            provincial_tax=provincial_tax,
            cpp_contribution=cpp_contrib,
            ei_contribution=ei_contrib,
            qpp_contribution=qpp_contrib,
            qpip_contribution=qpip_contrib,
            total_tax=total_tax,
            net_income=net_income,
            effective_tax_rate=effective_tax_rate,
            per_pay_period=per_pay_period,
            federal_breakdown=federal_breakdown,
            provincial_breakdown=provincial_breakdown
        )
    
    def _calculate_jurisdiction_tax(
        self, income: float, jurisdiction_data: JurisdictionTaxData, profile: UserTaxProfile
    ) -> float:
        """
        Calculate tax for a specific jurisdiction using progressive brackets.
        
        Args:
            income: Annual gross income
            jurisdiction_data: Tax data for the jurisdiction
            profile: User tax profile
            
        Returns:
            Annual tax amount
        """
        # Apply basic personal amount as a deduction
        taxable_income = max(0, income - jurisdiction_data.basic_personal_amount)
        
        # Apply additional claims from TD1
        for claim_amount in profile.additional_claims.values():
            taxable_income = max(0, taxable_income - claim_amount)
        
        # Calculate tax using progressive brackets
        tax = 0.0
        brackets = jurisdiction_data.brackets
        
        for i in range(len(brackets)):
            current_bracket = brackets[i]
            next_threshold = brackets[i + 1].threshold if i + 1 < len(brackets) else float('inf')
            
            # Income in this bracket
            bracket_income = min(
                max(0, taxable_income - current_bracket.threshold),
                next_threshold - current_bracket.threshold
            )
            
            if bracket_income > 0:
                tax += bracket_income * current_bracket.rate
        
        # Apply surtaxes if any
        if jurisdiction_data.surtaxes:
            for surtax_name, surtax_rate in jurisdiction_data.surtaxes.items():
                tax += tax * surtax_rate
        
        # Add additional tax withheld if requested
        tax += profile.additional_tax_withheld
        
        return self._round_to_cents(tax)
    
    def _calculate_cpp_contribution(self, income: float) -> float:
        """Calculate CPP contribution for the year."""
        cpp_data = self.tax_tables.cpp_ei
        
        # Pensionable earnings = income - basic exemption, capped at YMPE
        pensionable_earnings = max(0, income - cpp_data.cpp_basic_exemption)
        pensionable_earnings = min(pensionable_earnings, cpp_data.cpp_ympe)
        
        cpp_contrib = pensionable_earnings * cpp_data.cpp_rate
        cpp_contrib = min(cpp_contrib, cpp_data.cpp_max_contrib)
        
        return self._round_to_cents(cpp_contrib)
    
    def _calculate_ei_contribution(self, income: float) -> float:
        """Calculate EI contribution for the year."""
        ei_data = self.tax_tables.cpp_ei
        
        # Insurable earnings capped at MIE
        insurable_earnings = min(income, ei_data.ei_mie)
        ei_contrib = insurable_earnings * ei_data.ei_rate
        ei_contrib = min(ei_contrib, ei_data.ei_max_contrib)
        
        return self._round_to_cents(ei_contrib)
    
    def _calculate_qpp_contribution(self, income: float) -> float:
        """Calculate QPP contribution for Quebec residents."""
        cpp_data = self.tax_tables.cpp_ei
        
        if not cpp_data.qpp_rate or not cpp_data.qpp_ympe:
            return 0.0
        
        # Similar to CPP but with Quebec-specific rates and limits
        pensionable_earnings = max(0, income - cpp_data.cpp_basic_exemption)
        pensionable_earnings = min(pensionable_earnings, cpp_data.qpp_ympe)
        
        qpp_contrib = pensionable_earnings * cpp_data.qpp_rate
        if cpp_data.qpp_max_contrib:
            qpp_contrib = min(qpp_contrib, cpp_data.qpp_max_contrib)
        
        return self._round_to_cents(qpp_contrib)
    
    def _calculate_qpip_contribution(self, income: float) -> float:
        """Calculate QPIP contribution for Quebec residents."""
        cpp_data = self.tax_tables.cpp_ei
        
        if not cpp_data.qpip_rate:
            return 0.0
        
        # QPIP uses the same maximum as EI for Quebec
        insurable_earnings = min(income, cpp_data.ei_mie)
        qpip_contrib = insurable_earnings * cpp_data.qpip_rate
        
        if cpp_data.qpip_max_contrib:
            qpip_contrib = min(qpip_contrib, cpp_data.qpip_max_contrib)
        
        return self._round_to_cents(qpip_contrib)
    
    def _get_bracket_breakdown(self, income: float, jurisdiction_data: JurisdictionTaxData) -> List[Dict[str, float]]:
        """Get detailed breakdown of tax by bracket."""
        taxable_income = max(0, income - jurisdiction_data.basic_personal_amount)
        brackets = jurisdiction_data.brackets
        breakdown = []
        
        for i in range(len(brackets)):
            current_bracket = brackets[i]
            next_threshold = brackets[i + 1].threshold if i + 1 < len(brackets) else float('inf')
            
            # Income in this bracket
            bracket_income = min(
                max(0, taxable_income - current_bracket.threshold),
                next_threshold - current_bracket.threshold
            )
            
            if bracket_income > 0:
                tax_in_bracket = bracket_income * current_bracket.rate
                breakdown.append({
                    "bracket_min": current_bracket.threshold,
                    "bracket_max": next_threshold if next_threshold != float('inf') else None,
                    "income_in_bracket": bracket_income,
                    "marginal_rate": current_bracket.rate,
                    "tax_in_bracket": tax_in_bracket
                })
        
        return breakdown
    
    def _get_pay_periods_per_year(self, pay_schedule: PaySchedule) -> int:
        """Get number of pay periods per year based on schedule."""
        periods = {
            PaySchedule.WEEKLY: 52,
            PaySchedule.BIWEEKLY: 26,
            PaySchedule.SEMIMONTHLY: 24,
            PaySchedule.MONTHLY: 12
        }
        return periods[pay_schedule]
    
    def _round_to_cents(self, amount: float) -> float:
        """Round amount to nearest cent using banker's rounding."""
        return float(Decimal(str(amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
    
    def calculate_paycheck_tax(self, profile: UserTaxProfile, paycheck_gross: float) -> Dict[str, float]:
        """
        Calculate tax for a single paycheck (not annualized).
        
        Args:
            profile: User tax profile
            paycheck_gross: Gross amount for this paycheck
            
        Returns:
            Dictionary with tax breakdown for this paycheck
        """
        # First calculate annual tax
        # For simplicity, we'll assume this paycheck represents a typical pay period
        # In a real implementation, you would track YTD amounts
        
        annual_result = self.calculate_annual_tax(profile)
        pay_period_result = annual_result.per_pay_period
        
        # Scale based on this paycheck's proportion of annual income
        pay_periods = self._get_pay_periods_per_year(profile.pay_schedule)
        estimated_annual_from_paycheck = paycheck_gross * pay_periods
        
        # If this paycheck differs from typical, adjust proportions
        typical_paycheck_gross = annual_result.gross_income / pay_periods
        if typical_paycheck_gross > 0:
            scale_factor = paycheck_gross / typical_paycheck_gross
        else:
            scale_factor = 1.0
        
        paycheck_result = {}
        for key, value in pay_period_result.items():
            paycheck_result[key] = self._round_to_cents(value * scale_factor)
        
        return paycheck_result