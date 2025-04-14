"""
Schema validator module for validating extracted data.
"""
import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import jsonschema
from jsonschema import Draft7Validator, FormatChecker

logger = logging.getLogger(__name__)


class SchemaValidator:
    """Validator for extracted data against predefined schemas."""

    def __init__(self):
        """Initialize schema validator."""
        self.schemas = {
            # Generic invoice schema
            "invoice": {
                "type": "object",
                "properties": {
                    "invoice_number": {"type": "string"},
                    "date": {"type": "string", "format": "date"},
                    "due_date": {"type": "string", "format": "date"},
                    "total_amount": {"type": "number"},
                    "currency": {"type": "string"},
                    "vendor": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "address": {"type": "string"},
                            "tax_id": {"type": "string"},
                        },
                        "required": ["name"],
                    },
                    "customer": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "address": {"type": "string"},
                        },
                        "required": ["name"],
                    },
                    "line_items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "description": {"type": "string"},
                                "quantity": {"type": "number"},
                                "unit_price": {"type": "number"},
                                "amount": {"type": "number"},
                            },
                            "required": ["description", "amount"],
                        },
                    },
                },
                "required": ["invoice_number", "date", "total_amount"],
            },
            
            # Generic report schema
            "report": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "date": {"type": "string", "format": "date"},
                    "author": {"type": "string"},
                    "sections": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "heading": {"type": "string"},
                                "content": {"type": "string"},
                            },
                            "required": ["heading"],
                        },
                    },
                    "data": {
                        "type": "object",
                        "additionalProperties": True,
                    },
                },
                "required": ["title", "date"],
            },
            
            # Generic form schema
            "form": {
                "type": "object",
                "properties": {
                    "form_type": {"type": "string"},
                    "submission_date": {"type": "string", "format": "date"},
                    "fields": {
                        "type": "object",
                        "additionalProperties": True,
                    },
                },
                "required": ["form_type", "fields"],
            },
        }
        
        # Initialize format checker with custom formats
        self.format_checker = FormatChecker()
        
        # Register custom format for date
        @self.format_checker.checks("date")
        def check_date_format(value):
            """Check if value is a valid date string."""
            # Allow common date formats
            date_patterns = [
                r"^\d{4}-\d{2}-\d{2}$",  # ISO format: YYYY-MM-DD
                r"^\d{2}/\d{2}/\d{4}$",  # US format: MM/DD/YYYY
                r"^\d{2}\.\d{2}\.\d{4}$",  # European format: DD.MM.YYYY
            ]
            
            for pattern in date_patterns:
                if re.match(pattern, value):
                    return True
            
            # Try to parse the date
            try:
                datetime.strptime(value, "%Y-%m-%d")
                return True
            except ValueError:
                try:
                    datetime.strptime(value, "%m/%d/%Y")
                    return True
                except ValueError:
                    try:
                        datetime.strptime(value, "%d.%m.%Y")
                        return True
                    except ValueError:
                        return False
        
        logger.info("Schema validator initialized")

    async def validate(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate extracted data against predefined schemas.

        Args:
            extracted_data: Extracted data to validate

        Returns:
            Dict[str, Any]: Validation results
        """
        try:
            # Determine the most appropriate schema
            schema_type = self._determine_schema_type(extracted_data)
            
            # Get the schema
            schema = self.schemas.get(schema_type)
            if not schema:
                logger.warning(f"No schema found for type: {schema_type}")
                return {
                    "valid": False,
                    "schema_type": "unknown",
                    "errors": [{"message": "No matching schema found"}],
                }
            
            # Create validator
            validator = Draft7Validator(schema, format_checker=self.format_checker)
            
            # Validate data
            errors = list(validator.iter_errors(extracted_data))
            
            # Prepare validation result
            validation_result = {
                "valid": len(errors) == 0,
                "schema_type": schema_type,
                "errors": [],
            }
            
            # Add error details
            for error in errors:
                validation_result["errors"].append({
                    "path": ".".join(str(path) for path in error.path) if error.path else "root",
                    "message": error.message,
                    "schema_path": ".".join(str(path) for path in error.schema_path),
                })
            
            # Add normalized data
            validation_result["normalized_data"] = self._normalize_data(extracted_data, schema_type)
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating data: {str(e)}")
            return {
                "valid": False,
                "schema_type": "error",
                "errors": [{"message": f"Validation error: {str(e)}"}],
            }

    def _determine_schema_type(self, data: Dict[str, Any]) -> str:
        """
        Determine the most appropriate schema type for the data.

        Args:
            data: Data to analyze

        Returns:
            str: Schema type
        """
        # Check for invoice-specific fields
        if "invoice_number" in data or "total_amount" in data:
            return "invoice"
        
        # Check for report-specific fields
        if "title" in data and ("sections" in data or "data" in data):
            return "report"
        
        # Check for form-specific fields
        if "form_type" in data and "fields" in data:
            return "form"
        
        # Default to generic form
        return "form"

    def _normalize_data(self, data: Dict[str, Any], schema_type: str) -> Dict[str, Any]:
        """
        Normalize data based on schema type.

        Args:
            data: Data to normalize
            schema_type: Schema type

        Returns:
            Dict[str, Any]: Normalized data
        """
        # Start with a copy of the original data
        normalized = data.copy()
        
        # Normalize based on schema type
        if schema_type == "invoice":
            # Ensure total_amount is a number
            if "total_amount" in normalized and not isinstance(normalized["total_amount"], (int, float)):
                try:
                    # Remove currency symbols and commas
                    clean_amount = re.sub(r'[^\d.\-]', '', str(normalized["total_amount"]))
                    normalized["total_amount"] = float(clean_amount)
                except (ValueError, TypeError):
                    pass
            
            # Normalize date format
            if "date" in normalized and not re.match(r'^\d{4}-\d{2}-\d{2}$', str(normalized["date"])):
                try:
                    # Try to parse and normalize to ISO format
                    for fmt in ["%m/%d/%Y", "%d.%m.%Y"]:
                        try:
                            date_obj = datetime.strptime(normalized["date"], fmt)
                            normalized["date"] = date_obj.strftime("%Y-%m-%d")
                            break
                        except ValueError:
                            continue
                except Exception:
                    pass
        
        return normalized 