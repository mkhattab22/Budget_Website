"""
Supabase client for the finance application.
"""
import os
from typing import Optional, Dict, Any, List
from datetime import date, datetime
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SupabaseClient:
    """Supabase client wrapper."""
    
    def __init__(self):
        self.url: str = os.getenv("SUPABASE_URL")
        self.key: str = os.getenv("SUPABASE_KEY")
        self.service_key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not self.url or not self.key:
            raise ValueError("Supabase URL and key must be set in environment variables")
        
        self.client: Client = create_client(self.url, self.key)
    
    # User operations
    def create_user(self, email: str) -> Dict[str, Any]:
        """Create a new user."""
        return self.client.table("users").insert({"email": email}).execute()
    
    def get_user(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email."""
        response = self.client.table("users").select("*").eq("email", email).execute()
        return response.data[0] if response.data else None
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        response = self.client.table("users").select("*").eq("id", user_id).execute()
        return response.data[0] if response.data else None
    
    # Budget profile operations
    def create_budget_profile(self, user_id: str, name: str = "Default") -> Dict[str, Any]:
        """Create a new budget profile."""
        return self.client.table("budget_profiles").insert({
            "user_id": user_id,
            "name": name
        }).execute()
    
    def get_budget_profile(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """Get budget profile by ID."""
        response = self.client.table("budget_profiles").select("*").eq("id", profile_id).execute()
        return response.data[0] if response.data else None
    
    def get_user_budget_profiles(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all budget profiles for a user."""
        response = self.client.table("budget_profiles").select("*").eq("user_id", user_id).execute()
        return response.data
    
    def update_budget_profile(self, profile_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a budget profile."""
        return self.client.table("budget_profiles").update(data).eq("id", profile_id).execute()
    
    def delete_budget_profile(self, profile_id: str) -> Dict[str, Any]:
        """Delete a budget profile."""
        return self.client.table("budget_profiles").delete().eq("id", profile_id).execute()
    
    # Envelope operations
    def create_envelope(self, profile_id: str, envelope_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new envelope."""
        data = {
            "profile_id": profile_id,
            "category": envelope_data.get("category"),
            "name": envelope_data.get("name"),
            "target_amount": float(envelope_data.get("target_amount", 0)),
            "current_balance": float(envelope_data.get("current_balance", 0)),
            "priority": envelope_data.get("priority", 10)
        }
        return self.client.table("envelopes").insert(data).execute()
    
    def get_envelopes(self, profile_id: str) -> List[Dict[str, Any]]:
        """Get all envelopes for a profile."""
        response = self.client.table("envelopes").select("*").eq("profile_id", profile_id).execute()
        return response.data
    
    def get_envelope(self, envelope_id: str) -> Optional[Dict[str, Any]]:
        """Get envelope by ID."""
        response = self.client.table("envelopes").select("*").eq("id", envelope_id).execute()
        return response.data[0] if response.data else None
    
    def update_envelope(self, envelope_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an envelope."""
        return self.client.table("envelopes").update(data).eq("id", envelope_id).execute()
    
    def delete_envelope(self, envelope_id: str) -> Dict[str, Any]:
        """Delete an envelope."""
        return self.client.table("envelopes").delete().eq("id", envelope_id).execute()
    
    # Bill operations
    def create_bill(self, profile_id: str, bill_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new bill."""
        due_date = bill_data.get("due_date")
        if isinstance(due_date, date):
            due_date = due_date.isoformat()
        
        data = {
            "profile_id": profile_id,
            "envelope_id": bill_data.get("envelope_id"),
            "name": bill_data.get("name"),
            "amount": float(bill_data.get("amount", 0)),
            "bill_type": bill_data.get("bill_type"),
            "due_date": due_date,
            "paid": bill_data.get("paid", False)
        }
        return self.client.table("bills").insert(data).execute()
    
    def get_bills(self, profile_id: str, paid: bool = None) -> List[Dict[str, Any]]:
        """Get bills for a profile."""
        query = self.client.table("bills").select("*").eq("profile_id", profile_id)
        if paid is not None:
            query = query.eq("paid", paid)
        response = query.execute()
        return response.data
    
    def get_upcoming_bills(self, profile_id: str, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Get bills due between start_date and end_date."""
        response = self.client.table("bills").select("*").eq("profile_id", profile_id).eq("paid", False).gte("due_date", start_date.isoformat()).lte("due_date", end_date.isoformat()).execute()
        return response.data
    
    def update_bill(self, bill_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a bill."""
        return self.client.table("bills").update(data).eq("id", bill_id).execute()
    
    def delete_bill(self, bill_id: str) -> Dict[str, Any]:
        """Delete a bill."""
        return self.client.table("bills").delete().eq("id", bill_id).execute()
    
    # Debt operations
    def create_debt(self, profile_id: str, debt_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new debt."""
        due_date = debt_data.get("due_date")
        if isinstance(due_date, date):
            due_date = due_date.isoformat()
        
        data = {
            "profile_id": profile_id,
            "envelope_id": debt_data.get("envelope_id"),
            "name": debt_data.get("name"),
            "balance": float(debt_data.get("balance", 0)),
            "apr": float(debt_data.get("apr", 0)),
            "minimum_payment": float(debt_data.get("minimum_payment", 0)),
            "due_date": due_date,
            "strategy": debt_data.get("strategy"),
            "paid_off": debt_data.get("paid_off", False)
        }
        return self.client.table("debts").insert(data).execute()
    
    def get_debts(self, profile_id: str, paid_off: bool = False) -> List[Dict[str, Any]]:
        """Get debts for a profile."""
        response = self.client.table("debts").select("*").eq("profile_id", profile_id).eq("paid_off", paid_off).execute()
        return response.data
    
    def update_debt(self, debt_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a debt."""
        return self.client.table("debts").update(data).eq("id", debt_id).execute()
    
    def delete_debt(self, debt_id: str) -> Dict[str, Any]:
        """Delete a debt."""
        return self.client.table("debts").delete().eq("id", debt_id).execute()
    
    # Sinking fund operations
    def create_sinking_fund(self, profile_id: str, fund_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new sinking fund."""
        deadline = fund_data.get("deadline")
        if isinstance(deadline, date):
            deadline = deadline.isoformat()
        
        data = {
            "profile_id": profile_id,
            "envelope_id": fund_data.get("envelope_id"),
            "name": fund_data.get("name"),
            "target_amount": float(fund_data.get("target_amount", 0)),
            "current_balance": float(fund_data.get("current_balance", 0)),
            "deadline": deadline
        }
        return self.client.table("sinking_funds").insert(data).execute()
    
    def get_sinking_funds(self, profile_id: str) -> List[Dict[str, Any]]:
        """Get sinking funds for a profile."""
        response = self.client.table("sinking_funds").select("*").eq("profile_id", profile_id).execute()
        return response.data
    
    def update_sinking_fund(self, fund_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a sinking fund."""
        return self.client.table("sinking_funds").update(data).eq("id", fund_id).execute()
    
    def delete_sinking_fund(self, fund_id: str) -> Dict[str, Any]:
        """Delete a sinking fund."""
        return self.client.table("sinking_funds").delete().eq("id", fund_id).execute()
    
    # Savings goal operations
    def create_savings_goal(self, profile_id: str, goal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new savings goal."""
        target_date = goal_data.get("target_date")
        if isinstance(target_date, date):
            target_date = target_date.isoformat()
        
        data = {
            "profile_id": profile_id,
            "envelope_id": goal_data.get("envelope_id"),
            "name": goal_data.get("name"),
            "target_amount": float(goal_data.get("target_amount", 0)),
            "current_balance": float(goal_data.get("current_balance", 0)),
            "target_date": target_date,
            "monthly_contribution": float(goal_data.get("monthly_contribution", 0))
        }
        return self.client.table("savings_goals").insert(data).execute()
    
    def get_savings_goals(self, profile_id: str) -> List[Dict[str, Any]]:
        """Get savings goals for a profile."""
        response = self.client.table("savings_goals").select("*").eq("profile_id", profile_id).execute()
        return response.data
    
    def update_savings_goal(self, goal_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a savings goal."""
        return self.client.table("savings_goals").update(data).eq("id", goal_id).execute()
    
    def delete_savings_goal(self, goal_id: str) -> Dict[str, Any]:
        """Delete a savings goal."""
        return self.client.table("savings_goals").delete().eq("id", goal_id).execute()
    
    # Settings operations
    def create_budget_settings(self, profile_id: str, settings_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create budget settings for a profile."""
        data = {
            "profile_id": profile_id,
            "checking_buffer": float(settings_data.get("checking_buffer", 500.00)),
            "emergency_fund_target": float(settings_data.get("emergency_fund_target", 10000.00)),
            "debt_strategy": settings_data.get("debt_strategy", "AVALANCHE"),
            "savings_rate": float(settings_data.get("savings_rate", 0.20)),
            "discretionary_percentage": float(settings_data.get("discretionary_percentage", 0.30)),
            "round_to_nearest": float(settings_data.get("round_to_nearest", 10.00))
        }
        return self.client.table("budget_settings").insert(data).execute()
    
    def get_budget_settings(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """Get budget settings for a profile."""
        response = self.client.table("budget_settings").select("*").eq("profile_id", profile_id).execute()
        return response.data[0] if response.data else None
    
    def update_budget_settings(self, profile_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update budget settings for a profile."""
        return self.client.table("budget_settings").update(data).eq("profile_id", profile_id).execute()
    
    # Helper methods
    def delete_item(self, table_name: str, item_id: str) -> Dict[str, Any]:
        """Delete an item from any table."""
        return self.client.table(table_name).delete().eq("id", item_id).execute()
    
    def test_connection(self) -> bool:
        """Test the Supabase connection."""
        try:
            response = self.client.table("users").select("*").limit(1).execute()
            return True
        except Exception as e:
            print(f"Supabase connection test failed: {str(e)}")
            return False

# Singleton instance
try:
    supabase_client = SupabaseClient()
except Exception as e:
    print(f"Failed to initialize Supabase client: {str(e)}")
    supabase_client = None