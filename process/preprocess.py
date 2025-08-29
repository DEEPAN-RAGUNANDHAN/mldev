import re
from datetime import datetime
from typing import Dict, Any, List, Union

# List of keys to remove from the input data
REMOVE_KEYS = ["created_at", "updated_at", "completion_date", "certificate_type"]

# Keys you expect to be in ISO 8601 format and need date formatting
DATE_KEYS = ["start_date", "end_date"]

def format_iso_date(date_str: str) -> str:
    """
    Convert ISO 8601 date to "Month Year" format.
    Example: "2025-07-02T04:40:44.5Z" → "July 2025"
    """
    try:
        # Remove fractional seconds and timezone if present
        clean_str = re.sub(r"\.\d+Z?$", "", date_str)
        dt = datetime.fromisoformat(clean_str.replace("Z", ""))
        return dt.strftime("%B %Y")
    except (ValueError, TypeError):
        return date_str  # Return original if parsing fails

def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Clean and transform input data:
    - Remove unwanted keys
    - Convert date strings to "Month Year"
    """
    def process_dict(d: Dict[str, Any]) -> Dict[str, Any]:
        result = {}
        for key, value in d.items():
            if key in REMOVE_KEYS:
                continue
            if isinstance(value, dict):
                result[key] = process_dict(value)
            elif isinstance(value, list):
                result[key] = [process_dict(item) if isinstance(item, dict) else format_iso_date(item) if key in DATE_KEYS else item for item in value]
            elif key in DATE_KEYS:
                if value in [None, "null"]:
                    result[key] = "Present"
                elif isinstance(value, str):
                    result[key] = format_iso_date(value)
            else:
                result[key] = value
        return result

    return process_dict(data)
