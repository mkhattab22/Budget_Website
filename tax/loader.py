"""
Tax tables loader for importing/exporting tax data from JSON/CSV files.
"""
import json
import csv
import os
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging
from .models import (
    TaxTableSet, JurisdictionTaxData, TaxBracket, CPPEIData,
    Province
)

logger = logging.getLogger(__name__)


class TaxTableLoader:
    """Loader for tax table data from various sources."""
    
    def __init__(self, data_dir: Optional[str] = None):
        """
        Initialize the loader.
        
        Args:
            data_dir: Directory containing tax table data files
        """
        self.data_dir = data_dir or os.path.join(os.path.dirname(__file__), "..", "data")
        self.data_dir = os.path.abspath(self.data_dir)
        
    def load_from_json(self, filepath: str) -> TaxTableSet:
        """
        Load tax tables from a JSON file.
        
        Args:
            filepath: Path to JSON file
            
        Returns:
            TaxTableSet parsed from JSON
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return self._parse_json_data(data)
    
    def load_year(self, year: int) -> Optional[TaxTableSet]:
        """
        Load tax tables for a specific year from the data directory.
        
        Args:
            year: Tax year to load
            
        Returns:
            TaxTableSet if found, None otherwise
        """
        # Try to find JSON file for the year
        json_path = os.path.join(self.data_dir, f"tax_tables_{year}.json")
        if os.path.exists(json_path):
            return self.load_from_json(json_path)
        
        # Try alternative naming
        json_path = os.path.join(self.data_dir, f"{year}_tax_tables.json")
        if os.path.exists(json_path):
            return self.load_from_json(json_path)
        
        logger.warning(f"No tax table file found for year {year}")
        return None
    
    def export_to_json(self, tax_tables: TaxTableSet, filepath: str) -> None:
        """
        Export tax tables to a JSON file.
        
        Args:
            tax_tables: TaxTableSet to export
            filepath: Path to save JSON file
        """
        data = self._serialize_to_dict(tax_tables)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def import_from_csv(self, filepath: str, year: int, jurisdiction: str) -> JurisdictionTaxData:
        """
        Import tax data from a CSV file.
        
        CSV format expected:
        threshold,rate,basic_personal_amount
        
        Args:
            filepath: Path to CSV file
            year: Tax year
            jurisdiction: 'federal' or province code
            
        Returns:
            JurisdictionTaxData parsed from CSV
        """
        brackets = []
        basic_personal_amount = 0.0
        
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'threshold' in row and 'rate' in row:
                    threshold = float(row['threshold'])
                    rate = float(row['rate'])
                    brackets.append(TaxBracket(threshold=threshold, rate=rate))
                
                if 'basic_personal_amount' in row:
                    basic_personal_amount = float(row['basic_personal_amount'])
        
        # Sort brackets by threshold
        brackets.sort(key=lambda b: b.threshold)
        
        return JurisdictionTaxData(
            year=year,
            jurisdiction=jurisdiction,
            brackets=brackets,
            basic_personal_amount=basic_personal_amount,
            metadata={"source": f"CSV import from {os.path.basename(filepath)}"}
        )
    
    def validate_tax_tables(self, tax_tables: TaxTableSet) -> List[str]:
        """
        Validate tax tables for consistency and completeness.
        
        Args:
            tax_tables: TaxTableSet to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check year consistency
        if tax_tables.year != tax_tables.federal.year:
            errors.append(f"Federal year {tax_tables.federal.year} doesn't match set year {tax_tables.year}")
        
        if tax_tables.year != tax_tables.cpp_ei.year:
            errors.append(f"CPP/EI year {tax_tables.cpp_ei.year} doesn't match set year {tax_tables.year}")
        
        # Check all provinces have data
        for province in Province:
            if province.value not in tax_tables.provincial:
                errors.append(f"Missing tax data for province {province.value}")
            else:
                prov_data = tax_tables.provincial[province.value]
                if prov_data.year != tax_tables.year:
                    errors.append(f"Province {province.value} year {prov_data.year} doesn't match set year {tax_tables.year}")
        
        # Check bracket ordering
        for jurisdiction, data in [("federal", tax_tables.federal)] + list(tax_tables.provincial.items()):
            thresholds = [b.threshold for b in data.brackets]
            if thresholds != sorted(thresholds):
                errors.append(f"Brackets not sorted for {jurisdiction}")
            
            # Check for negative thresholds
            if any(b.threshold < 0 for b in data.brackets):
                errors.append(f"Negative threshold found in {jurisdiction}")
            
            # Check rate bounds
            if any(b.rate < 0 or b.rate > 1 for b in data.brackets):
                errors.append(f"Invalid rate (not between 0 and 1) in {jurisdiction}")
        
        # Check CPP/EI data
        cpp_data = tax_tables.cpp_ei
        if cpp_data.cpp_rate < 0 or cpp_data.cpp_rate > 1:
            errors.append(f"Invalid CPP rate: {cpp_data.cpp_rate}")
        
        if cpp_data.ei_rate < 0 or cpp_data.ei_rate > 1:
            errors.append(f"Invalid EI rate: {cpp_data.ei_rate}")
        
        if cpp_data.qpp_rate and (cpp_data.qpp_rate < 0 or cpp_data.qpp_rate > 1):
            errors.append(f"Invalid QPP rate: {cpp_data.qpp_rate}")
        
        if cpp_data.qpip_rate and (cpp_data.qpip_rate < 0 or cpp_data.qpip_rate > 1):
            errors.append(f"Invalid QPIP rate: {cpp_data.qpip_rate}")
        
        return errors
    
    def _parse_json_data(self, data: Dict[str, Any]) -> TaxTableSet:
        """Parse JSON data into TaxTableSet."""
        year = data["year"]
        
        # Parse federal data
        federal_data = self._parse_jurisdiction_data(data["federal"], year, "federal")
        
        # Parse provincial data
        provincial_data = {}
        for province_code, prov_data in data["provincial"].items():
            provincial_data[province_code] = self._parse_jurisdiction_data(
                prov_data, year, province_code
            )
        
        # Parse CPP/EI data
        cpp_ei_data = self._parse_cpp_ei_data(data["cpp_ei"], year)
        
        # Get metadata
        metadata = data.get("metadata", {})
        
        return TaxTableSet(
            year=year,
            federal=federal_data,
            provincial=provincial_data,
            cpp_ei=cpp_ei_data,
            metadata=metadata
        )
    
    def _parse_jurisdiction_data(self, data: Dict[str, Any], year: int, jurisdiction: str) -> JurisdictionTaxData:
        """Parse jurisdiction tax data from JSON."""
        brackets = [
            TaxBracket(threshold=b["threshold"], rate=b["rate"])
            for b in data["brackets"]
        ]
        
        return JurisdictionTaxData(
            year=year,
            jurisdiction=jurisdiction,
            brackets=brackets,
            basic_personal_amount=data["basic_personal_amount"],
            surtaxes=data.get("surtaxes"),
            credits=data.get("credits"),
            metadata=data.get("metadata", {})
        )
    
    def _parse_cpp_ei_data(self, data: Dict[str, Any], year: int) -> CPPEIData:
        """Parse CPP/EI data from JSON."""
        return CPPEIData(
            year=year,
            cpp_rate=data["cpp_rate"],
            cpp_ympe=data["cpp_ympe"],
            cpp_basic_exemption=data["cpp_basic_exemption"],
            cpp_max_contrib=data["cpp_max_contrib"],
            ei_rate=data["ei_rate"],
            ei_mie=data["ei_mie"],
            ei_max_contrib=data["ei_max_contrib"],
            qpp_rate=data.get("qpp_rate"),
            qpp_ympe=data.get("qpp_ympe"),
            qpp_max_contrib=data.get("qpp_max_contrib"),
            qpip_rate=data.get("qpip_rate"),
            qpip_max_contrib=data.get("qpip_max_contrib")
        )
    
    def _serialize_to_dict(self, tax_tables: TaxTableSet) -> Dict[str, Any]:
        """Serialize TaxTableSet to dictionary for JSON export."""
        return {
            "year": tax_tables.year,
            "federal": {
                "year": tax_tables.federal.year,
                "jurisdiction": tax_tables.federal.jurisdiction,
                "brackets": [
                    {"threshold": b.threshold, "rate": b.rate}
                    for b in tax_tables.federal.brackets
                ],
                "basic_personal_amount": tax_tables.federal.basic_personal_amount,
                "surtaxes": tax_tables.federal.surtaxes,
                "credits": tax_tables.federal.credits,
                "metadata": tax_tables.federal.metadata
            },
            "provincial": {
                province_code: {
                    "year": data.year,
                    "jurisdiction": data.jurisdiction,
                    "brackets": [
                        {"threshold": b.threshold, "rate": b.rate}
                        for b in data.brackets
                    ],
                    "basic_personal_amount": data.basic_personal_amount,
                    "surtaxes": data.surtaxes,
                    "credits": data.credits,
                    "metadata": data.metadata
                }
                for province_code, data in tax_tables.provincial.items()
            },
            "cpp_ei": {
                "year": tax_tables.cpp_ei.year,
                "cpp_rate": tax_tables.cpp_ei.cpp_rate,
                "cpp_ympe": tax_tables.cpp_ei.cpp_ympe,
                "cpp_basic_exemption": tax_tables.cpp_ei.cpp_basic_exemption,
                "cpp_max_contrib": tax_tables.cpp_ei.cpp_max_contrib,
                "ei_rate": tax_tables.cpp_ei.ei_rate,
                "ei_mie": tax_tables.cpp_ei.ei_mie,
                "ei_max_contrib": tax_tables.cpp_ei.ei_max_contrib,
                "qpp_rate": tax_tables.cpp_ei.qpp_rate,
                "qpp_ympe": tax_tables.cpp_ei.qpp_ympe,
                "qpp_max_contrib": tax_tables.cpp_ei.qpp_max_contrib,
                "qpip_rate": tax_tables.cpp_ei.qpip_rate,
                "qpip_max_contrib": tax_tables.cpp_ei.qpip_max_contrib
            },
            "metadata": tax_tables.metadata
        }


class TableUpdater:
    """Utility for updating tax tables from official sources."""
    
    def __init__(self, loader: TaxTableLoader):
        self.loader = loader
    
    def update_from_official_sources(self, year: int) -> Optional[TaxTableSet]:
        """
        Attempt to fetch tax tables from official government sources.
        
        Note: This is a placeholder implementation. In a real app,
        this would fetch from CRA and provincial revenue websites.
        
        Args:
            year: Tax year to update
            
        Returns:
            Updated TaxTableSet if successful, None otherwise
        """
        logger.info(f"Attempting to fetch tax tables for {year} from official sources")
        
        # This is a placeholder - in reality you would:
        # 1. Fetch federal brackets from CRA website
        # 2. Fetch provincial brackets from each province's revenue website
        # 3. Fetch CPP/EI rates from Service Canada
        
        # For now, return None to indicate manual import is required
        logger.warning("Official source fetching not implemented. Please import tables manually.")
        return None
    
    def merge_updates(self, existing: TaxTableSet, updates: Dict[str, Any]) -> TaxTableSet:
        """
        Merge updates into existing tax tables.
        
        Args:
            existing: Existing TaxTableSet
            updates: Dictionary with updates to apply
            
        Returns:
            Updated TaxTableSet
        """
        # Create a deep copy of the existing data
        # (simplified - in reality you'd use copy.deepcopy or reconstruct)
        updated_data = self.loader._serialize_to_dict(existing)
        
        # Apply updates
        for key, value in updates.items():
            if key in updated_data:
                if isinstance(updated_data[key], dict) and isinstance(value, dict):
                    updated_data[key].update(value)
                else:
                    updated_data[key] = value
        
        # Parse back to TaxTableSet
        return self.loader._parse_json_data(updated_data)