"""
Tax data models for Canadian federal and provincial tax calculations.
"""
from typing import List, Dict, Optional, Any
from datetime import date
from pydantic import BaseModel, Field, validator
from enum import Enum


class Province(str, Enum):
    """Canadian provinces and territories."""
    AB = "AB"  # Alberta
    BC = "BC"  # British Columbia
    MB = "MB"  # Manitoba
    NB = "NB"  # New Brunswick
    NL = "NL"  # Newfoundland and Labrador
    NS = "NS"  # Nova Scotia
    NT = "NT"  # Northwest Territories
    NU = "NU"  # Nunavut
    ON = "ON"  # Ontario
    PE = "PE"  # Prince Edward Island
    QC = "QC"  # Quebec
    SK = "SK"  # Saskatchewan
    YT = "YT"  # Yukon


class PaySchedule(str, Enum):
    """Pay schedule frequencies."""
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    SEMIMONTHLY = "semimonthly"
    MONTHLY = "monthly"


class TaxBracket(BaseModel):
    """A single tax bracket with threshold and marginal rate."""
    threshold: float = Field(..., description="Income threshold for this bracket")
    rate: float = Field(..., ge=0, le=1, description="Marginal tax rate (0.0 to 1.0)")
    
    @validator('threshold')
    def threshold_must_be_positive(cls, v):
        if v < 0:
            raise ValueError('Threshold must be non-negative')
        return v


class CPPEIData(BaseModel):
    """CPP/QPP and EI contribution data for a specific year."""
    year: int
    cpp_rate: float = Field(..., ge=0, le=1, description="CPP contribution rate")
    cpp_ympe: float = Field(..., description="Yearly Maximum Pensionable Earnings")
    cpp_basic_exemption: float = Field(..., description="Basic exemption amount")
    cpp_max_contrib: float = Field(..., description="Maximum CPP contribution")
    
    ei_rate: float = Field(..., ge=0, le=1, description="EI contribution rate")
    ei_mie: float = Field(..., description="Maximum Insurable Earnings")
    ei_max_contrib: float = Field(..., description="Maximum EI contribution")
    
    qpp_rate: Optional[float] = Field(None, ge=0, le=1, description="QPP rate (Quebec only)")
    qpp_ympe: Optional[float] = Field(None, description="QPP YMPE (Quebec only)")
    qpp_max_contrib: Optional[float] = Field(None, description="Maximum QPP contribution")
    
    qpip_rate: Optional[float] = Field(None, ge=0, le=1, description="QPIP rate (Quebec only)")
    qpip_max_contrib: Optional[float] = Field(None, description="Maximum QPIP contribution")


class JurisdictionTaxData(BaseModel):
    """Tax data for a specific jurisdiction (federal or provincial) in a specific year."""
    year: int
    jurisdiction: str = Field(..., description="'federal' or province code like 'ON', 'QC'")
    brackets: List[TaxBracket] = Field(..., description="Tax brackets sorted by threshold")
    basic_personal_amount: float = Field(..., description="Basic personal amount")
    surtaxes: Optional[Dict[str, float]] = Field(None, description="Surtax rates by bracket")
    credits: Optional[Dict[str, float]] = Field(None, description="Tax credits available")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Source, citation, notes")
    
    @validator('brackets')
    def brackets_must_be_sorted(cls, v):
        thresholds = [b.threshold for b in v]
        if thresholds != sorted(thresholds):
            raise ValueError('Brackets must be sorted by threshold')
        return v
    
    @validator('jurisdiction')
    def jurisdiction_must_be_valid(cls, v):
        valid = ['federal'] + [p.value for p in Province]
        if v not in valid:
            raise ValueError(f'Jurisdiction must be one of: {valid}')
        return v


class TaxTableSet(BaseModel):
    """Complete set of tax tables for a specific year."""
    year: int
    federal: JurisdictionTaxData
    provincial: Dict[str, JurisdictionTaxData]  # province code -> data
    cpp_ei: CPPEIData
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaxCalculationResult(BaseModel):
    """Result of a tax calculation."""
    gross_income: float
    federal_tax: float
    provincial_tax: float
    cpp_contribution: float
    ei_contribution: float
    qpp_contribution: Optional[float] = None
    qpip_contribution: Optional[float] = None
    total_tax: float
    net_income: float
    effective_tax_rate: float
    
    # Per pay period breakdown
    per_pay_period: Dict[str, float] = Field(default_factory=dict)
    
    # Detailed bracket breakdown
    federal_breakdown: List[Dict[str, float]] = Field(default_factory=list)
    provincial_breakdown: List[Dict[str, float]] = Field(default_factory=list)


class IncomeStream(BaseModel):
    """A single source of income."""
    name: str
    type: str = Field(..., description="salary, overtime, bonus, irregular, reimbursement")
    gross_amount: float
    frequency: PaySchedule
    start_date: date
    end_date: Optional[date] = None
    deductions: Dict[str, float] = Field(default_factory=dict, description="RRSP, union, benefits, etc.")


class UserTaxProfile(BaseModel):
    """User profile for tax calculations."""
    province: Province
    tax_year: int
    pay_schedule: PaySchedule
    income_streams: List[IncomeStream] = Field(default_factory=list)
    additional_claims: Dict[str, float] = Field(default_factory=dict, description="TD1 adjustments")
    additional_tax_withheld: float = Field(0.0, description="Additional tax requested to be withheld")