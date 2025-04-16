"""
Excel data validator for the API service.

This module provides a validator for data extracted from Excel files.
It validates the structure and content of the extracted data to ensure
it meets the expected format and quality standards.
"""
import json
import re
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import jsonschema
from jsonschema import ValidationError

from app.validators.base_validator import BaseValidator
from app.utils.logger import get_logger

# Initialize logger
logger = get_logger("excel_validator")


class ValidationLevel(str, Enum):
    """Validation levels for controlling validation strictness."""
    BASIC = "basic"        # Minimal validation
    STANDARD = "standard"  # Standard validation with schema
    STRICT = "strict"      # Strict validation with additional checks
    CUSTOM = "custom"      # Custom validation with user-provided rules


class ExcelValidator(BaseValidator):
    """
    Validator for data extracted from Excel files.
    
    This validator ensures that data extracted from Excel files meets
    the expected structure and quality standards. It supports multiple
    validation levels and custom validation rules.
    """
    
    SUPPORTED_DATA_TYPES = [
        "excel_table",      # Table-like data with headers and rows
        "excel_form",       # Form-like data with field-value pairs
        "excel_report",     # Report with sections and tables
        "excel_financial",  # Financial data with numeric validations
        "excel_inventory",  # Inventory data with stock validations
        "excel_timesheet"   # Timesheet data with time validations
    ]
    
    def __init__(self):
        """Initialize the Excel validator with custom validation rules."""
        # Define custom validation rules
        self.custom_rules = {
            "excel_table": self._validate_excel_table,
            "excel_form": self._validate_excel_form,
            "excel_report": self._validate_excel_report,
            "excel_financial": self._validate_excel_financial,
            "excel_inventory": self._validate_excel_inventory,
            "excel_timesheet": self._validate_excel_timesheet
        }
        
        # Define data type patterns for auto-detection
        self.data_type_patterns = {
            "excel_table": {
                "headers": ["id", "name", "code", "category", "amount", "quantity", "date", "status"],
                "sheet_names": ["data", "table", "list", "records", "items"]
            },
            "excel_form": {
                "headers": ["field", "value", "label", "input", "form"],
                "sheet_names": ["form", "input", "entry", "fields"]
            },
            "excel_financial": {
                "headers": ["account", "amount", "balance", "credit", "debit", "revenue", "expense"],
                "sheet_names": ["finance", "financial", "accounts", "ledger", "balance", "p&l"]
            },
            "excel_inventory": {
                "headers": ["sku", "inventory", "stock", "quantity", "location", "warehouse"],
                "sheet_names": ["inventory", "stock", "products", "items", "warehouse"]
            },
            "excel_timesheet": {
                "headers": ["hours", "date", "day", "time", "project", "task", "employee"],
                "sheet_names": ["timesheet", "hours", "time", "attendance", "schedule"]
            }
        }
    
    async def validate(
        self,
        data: Dict[str, Any],
        schema: Optional[Dict[str, Any]] = None,
        validation_level: str = "standard",
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate extracted Excel data.
        
        Args:
            data: The data to validate
            schema: Optional schema to validate against (if None, uses default schema)
            validation_level: Validation level (basic, standard, strict, custom)
            
        Returns:
            Tuple containing:
                - Boolean indicating if validation passed
                - Dict with validation results including errors
        """
        try:
            # Normalize validation level
            try:
                level = ValidationLevel(validation_level.lower())
            except ValueError:
                level = ValidationLevel.STANDARD
                logger.warning("Unknown validation level, using standard", requested_level=validation_level, used_level=level.value)
                
            # Auto-detect data type if not specified
            metadata = data.get("metadata", {})
            data_type = metadata.get("document_type")
            if not data_type or data_type not in self.SUPPORTED_DATA_TYPES:
                data_type = self._detect_data_type(data)
                # Update metadata with detected data type
                if "metadata" not in data:
                    data["metadata"] = {}
                data["metadata"]["document_type"] = data_type
                logger.info("Auto-detected data type", data_type=data_type)
                
            # Get schema if not provided
            if schema is None:
                schema = await self.get_default_schema(data_type)
            
            # Initialize validation results
            validation_results = {
                "valid": False,
                "level": level.value,
                "data_type": data_type,
                "errors": [],
                "warnings": [],
                "details": {
                    "basic": {"valid": False, "checks": []},
                    "schema": {"valid": False, "checks": []},
                    "custom": {"valid": False, "checks": []}
                }
            }
            
            # Execute validation based on level
            basic_valid = await self._run_basic_validation(data, validation_results)
            
            # Stop if basic validation fails and we're not in STRICT mode
            if not basic_valid and level != ValidationLevel.STRICT:
                validation_results["valid"] = False
                return False, validation_results
                
            # Run schema validation for standard and above
            schema_valid = True
            if level.value in [ValidationLevel.STANDARD.value, ValidationLevel.STRICT.value, ValidationLevel.CUSTOM.value]:
                schema_valid = await self._run_schema_validation(data, schema, validation_results)
            
            # Run custom validation for strict and custom levels
            custom_valid = True
            if level.value in [ValidationLevel.STRICT.value, ValidationLevel.CUSTOM.value]:
                custom_valid = await self._run_custom_validation(data, data_type, validation_results)
            
            # Determine overall validation result
            is_valid = basic_valid
            if level.value in [ValidationLevel.STANDARD.value, ValidationLevel.STRICT.value, ValidationLevel.CUSTOM.value]:
                is_valid = is_valid and schema_valid
            if level.value in [ValidationLevel.STRICT.value, ValidationLevel.CUSTOM.value]:
                is_valid = is_valid and custom_valid
            
            # Update validation result
            validation_results["valid"] = is_valid
            
            # Return validation result
            return is_valid, validation_results
            
        except Exception as e:
            logger.error("Error validating data", error=str(e))
            return False, {
                "valid": False,
                "level": validation_level,
                "errors": [f"Validation error: {str(e)}"],
                "warnings": [],
                "details": {"error": str(e)}
            }
            
    async def _run_basic_validation(self, data: Dict[str, Any], validation_results: Dict[str, Any]) -> bool:
        """
        Run basic validation checks.
        
        Args:
            data: The data to validate
            validation_results: Dictionary to store validation results
            
        Returns:
            Boolean indicating if basic validation passed
        """
        basic_results = validation_results["details"]["basic"]
        basic_results["checks"] = []
        
        # Check 1: Data must be a dictionary
        check = {"name": "data_structure", "passed": isinstance(data, dict)}
        if not check["passed"]:
            check["message"] = "Data must be a dictionary"
            validation_results["errors"].append(check["message"])
        basic_results["checks"].append(check)
        
        # Check 2: Check for tables field
        has_tables = "tables" in data and isinstance(data["tables"], list)
        check = {"name": "has_tables", "passed": has_tables}
        if not check["passed"]:
            check["message"] = "Missing or invalid 'tables' field (must be a list)"
            validation_results["errors"].append(check["message"])
        basic_results["checks"].append(check)
        
        # Check 3: Check for metadata
        has_metadata = "metadata" in data and isinstance(data["metadata"], dict)
        check = {"name": "has_metadata", "passed": has_metadata}
        if not check["passed"]:
            check["message"] = "Missing or invalid 'metadata' field (must be a dictionary)"
            validation_results["errors"].append(check["message"])
        basic_results["checks"].append(check)
        
        # Check 4: At least one table for table data types
        data_type = validation_results.get("data_type", "excel_table")
        if data_type == "excel_table" and has_tables:
            has_some_tables = len(data["tables"]) > 0
            check = {"name": "has_some_tables", "passed": has_some_tables}
            if not check["passed"]:
                check["message"] = "No tables found in data"
                validation_results["warnings"].append(check["message"])
            basic_results["checks"].append(check)
            
        # Check 5: Check for fields in form data type
        if data_type == "excel_form":
            has_fields = "fields" in data and isinstance(data["fields"], list)
            check = {"name": "has_fields", "passed": has_fields}
            if not check["passed"] and data_type == "excel_form":
                check["message"] = "Missing or invalid 'fields' field for form data (must be a list)"
                validation_results["errors"].append(check["message"])
            basic_results["checks"].append(check)
        
        # Set basic validation result
        passed_checks = [c for c in basic_results["checks"] if c["passed"]]
        basic_results["valid"] = len(passed_checks) == len(basic_results["checks"])
        
        return basic_results["valid"]
        
    async def _run_schema_validation(self, data: Dict[str, Any], schema: Dict[str, Any], validation_results: Dict[str, Any]) -> bool:
        """
        Run schema validation checks.
        
        Args:
            data: The data to validate
            schema: The JSON schema to validate against
            validation_results: Dictionary to store validation results
            
        Returns:
            Boolean indicating if schema validation passed
        """
        schema_results = validation_results["details"]["schema"]
        schema_results["checks"] = []
        
        try:
            # Validate data against schema
            jsonschema.validate(instance=data, schema=schema)
            check = {"name": "schema_validation", "passed": True}
            schema_results["checks"].append(check)
            schema_results["valid"] = True
            return True
            
        except ValidationError as e:
            # Extract validation error details
            check = {
                "name": "schema_validation", 
                "passed": False,
                "message": f"Schema validation error: {e.message}",
                "path": ".".join(str(p) for p in e.path) if e.path else "root",
                "schema_path": ".".join(str(p) for p in e.schema_path) if e.schema_path else "root"
            }
            schema_results["checks"].append(check)
            validation_results["errors"].append(check["message"])
            schema_results["valid"] = False
            return False
            
    async def _run_custom_validation(self, data: Dict[str, Any], data_type: str, validation_results: Dict[str, Any]) -> bool:
        """
        Run custom validation checks based on data type.
        
        Args:
            data: The data to validate
            data_type: Type of data to validate
            validation_results: Dictionary to store validation results
            
        Returns:
            Boolean indicating if custom validation passed
        """
        custom_results = validation_results["details"]["custom"]
        custom_results["checks"] = []
        
        # Get appropriate validator function
        validator_func = self.custom_rules.get(data_type)
        if not validator_func:
            # No custom validator for this data type
            check = {
                "name": "custom_validation", 
                "passed": True,
                "message": f"No custom validator available for data type: {data_type}"
            }
            custom_results["checks"].append(check)
            validation_results["warnings"].append(check["message"])
            custom_results["valid"] = True
            return True
            
        # Run custom validation
        is_valid, custom_checks = await validator_func(data)
        custom_results["checks"].extend(custom_checks)
        
        # Add errors and warnings to main results
        for check in custom_checks:
            if not check.get("passed", True):
                if check.get("severity", "error") == "error":
                    validation_results["errors"].append(check.get("message", "Custom validation error"))
                else:
                    validation_results["warnings"].append(check.get("message", "Custom validation warning"))
        
        # Set custom validation result
        custom_results["valid"] = is_valid
        return is_valid
        
    def _detect_data_type(self, data: Dict[str, Any]) -> str:
        """
        Detect the data type from its content.
        
        Args:
            data: The data to analyze
            
        Returns:
            Detected data type
        """
        # Extract sheet names
        tables = data.get("tables", [])
        sheet_names = [table.get("sheet_name", "").lower() for table in tables]
        
        # Extract headers
        headers = []
        for table in tables:
            headers.extend([h.lower() for h in table.get("headers", [])])
        
        # Check if form data
        if "fields" in data and isinstance(data["fields"], list):
            return "excel_form"
            
        # Check if report data
        if "sections" in data and isinstance(data["sections"], list):
            return "excel_report"
            
        # Match against patterns
        type_scores = {}
        for data_type, patterns in self.data_type_patterns.items():
            score = 0
            
            # Score based on sheet names
            for sheet_name in sheet_names:
                for pattern in patterns["sheet_names"]:
                    if pattern in sheet_name:
                        score += 2
                        
            # Score based on headers
            for header in headers:
                for pattern in patterns["headers"]:
                    if pattern in header:
                        score += 1
            
            type_scores[data_type] = score
            
        # Get data type with highest score
        if type_scores:
            max_score = max(type_scores.values())
            if max_score > 0:
                for data_type, score in type_scores.items():
                    if score == max_score:
                        return data_type
            
        # Default to excel_table
        return "excel_table"
    
    async def get_default_schema(self, data_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get the default schema for validating extracted Excel data.
        
        Args:
            data_type: Optional data type to get specific schema
            
        Returns:
            Dict containing the default validation schema
        """
        # Default schema for excel_table type
        default_schema = {
            "type": "object",
            "properties": {
                "tables": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "sheet_name": {"type": "string"},
                            "table_name": {"type": "string"},
                            "headers": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "data": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "additionalProperties": True,
                                },
                            },
                        },
                        "required": ["sheet_name", "headers", "data"],
                    },
                },
                "metadata": {
                    "type": "object",
                    "properties": {
                        "document_type": {"type": "string"},
                        "extraction_mode": {"type": "string"},
                        "confidence_score": {"type": "number"},
                    },
                },
            },
            "required": ["tables", "metadata"],
        }
        
        # Return schema based on data type
        doc_type = data_type or "excel_table"
        if doc_type not in self.SUPPORTED_DATA_TYPES:
            raise ValueError(f"Unsupported data type: {doc_type}")
        
        # Different schemas for different data types
        if doc_type == "excel_form":
            # Form schema has fields instead of tables
            form_schema = default_schema.copy()
            form_schema["properties"]["fields"] = {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "value": {"type": ["string", "number", "boolean", "null"]},
                        "confidence": {"type": "number"},
                    },
                    "required": ["name", "value"],
                },
            }
            form_schema["required"] = ["fields", "metadata"]
            return form_schema
            
        elif doc_type == "excel_report":
            # Report schema has sections
            report_schema = default_schema.copy()
            report_schema["properties"]["sections"] = {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "content": {"type": "string"},
                        "tables": {
                            "type": "array",
                            "items": default_schema["properties"]["tables"]["items"],
                        },
                    },
                    "required": ["title"],
                },
            }
            report_schema["required"].append("sections")
            return report_schema
        
        # Default to excel_table schema
        return default_schema
    
    def get_supported_data_types(self) -> List[str]:
        """
        Get the list of data types supported by this validator.
        
        Returns:
            List of supported data types
        """
        return self.SUPPORTED_DATA_TYPES 

    async def _validate_excel_table(self, data: Dict[str, Any]) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Custom validation for excel_table data type.
        
        Args:
            data: The data to validate
            
        Returns:
            Tuple containing:
                - Boolean indicating if validation passed
                - List of validation check results
        """
        checks = []
        
        # Check table structure
        tables = data.get("tables", [])
        for i, table in enumerate(tables):
            # Check headers exist and are non-empty
            headers = table.get("headers", [])
            check = {
                "name": f"table_{i}_headers",
                "passed": bool(headers),
                "message": f"Table {i}: Missing or empty headers",
                "severity": "error"
            }
            checks.append(check)
            
            # Check data rows are present
            rows = table.get("data", [])
            check = {
                "name": f"table_{i}_data",
                "passed": bool(rows),
                "message": f"Table {i}: No data rows found",
                "severity": "warning"
            }
            checks.append(check)
            
            # Check for data consistency (all rows have the same fields)
            if headers and rows:
                field_sets = [set(row.keys()) for row in rows]
                if field_sets:
                    consistent = all(fs == field_sets[0] for fs in field_sets)
                    check = {
                        "name": f"table_{i}_consistency",
                        "passed": consistent,
                        "message": f"Table {i}: Inconsistent row fields",
                        "severity": "warning"
                    }
                    checks.append(check)
        
        # Check that at least one table has data
        has_data = any(bool(table.get("data", [])) for table in tables)
        check = {
            "name": "has_table_data",
            "passed": has_data,
            "message": "No data found in any table",
            "severity": "error"
        }
        checks.append(check)
        
        # Determine validation result
        errors = [c for c in checks if not c["passed"] and c["severity"] == "error"]
        is_valid = not errors
        
        return is_valid, checks
    
    async def _validate_excel_form(self, data: Dict[str, Any]) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Custom validation for excel_form data type.
        
        Args:
            data: The data to validate
            
        Returns:
            Tuple containing:
                - Boolean indicating if validation passed
                - List of validation check results
        """
        checks = []
        
        # Check fields exist
        fields = data.get("fields", [])
        check = {
            "name": "has_fields",
            "passed": bool(fields),
            "message": "No fields found in form data",
            "severity": "error"
        }
        checks.append(check)
        
        # Check each field has name and value
        if fields:
            for i, field in enumerate(fields):
                has_name = "name" in field and bool(field["name"])
                check = {
                    "name": f"field_{i}_name",
                    "passed": has_name,
                    "message": f"Field {i}: Missing name",
                    "severity": "error"
                }
                checks.append(check)
                
                has_value = "value" in field
                check = {
                    "name": f"field_{i}_value",
                    "passed": has_value,
                    "message": f"Field {i}: Missing value",
                    "severity": "error"
                }
                checks.append(check)
        
        # Determine validation result
        errors = [c for c in checks if not c["passed"] and c["severity"] == "error"]
        is_valid = not errors
        
        return is_valid, checks
    
    async def _validate_excel_report(self, data: Dict[str, Any]) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Custom validation for excel_report data type.
        
        Args:
            data: The data to validate
            
        Returns:
            Tuple containing:
                - Boolean indicating if validation passed
                - List of validation check results
        """
        checks = []
        
        # Check sections exist
        sections = data.get("sections", [])
        check = {
            "name": "has_sections",
            "passed": bool(sections),
            "message": "No sections found in report data",
            "severity": "error"
        }
        checks.append(check)
        
        # Check each section has title
        if sections:
            for i, section in enumerate(sections):
                has_title = "title" in section and bool(section["title"])
                check = {
                    "name": f"section_{i}_title",
                    "passed": has_title,
                    "message": f"Section {i}: Missing title",
                    "severity": "error"
                }
                checks.append(check)
                
                # Check if section has content or tables
                has_content = ("content" in section and bool(section["content"])) or \
                             ("tables" in section and bool(section["tables"]))
                check = {
                    "name": f"section_{i}_content",
                    "passed": has_content,
                    "message": f"Section {i}: Missing content and tables",
                    "severity": "warning"
                }
                checks.append(check)
        
        # Determine validation result
        errors = [c for c in checks if not c["passed"] and c["severity"] == "error"]
        is_valid = not errors
        
        return is_valid, checks
    
    async def _validate_excel_financial(self, data: Dict[str, Any]) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Custom validation for excel_financial data type.
        
        Args:
            data: The data to validate
            
        Returns:
            Tuple containing:
                - Boolean indicating if validation passed
                - List of validation check results
        """
        checks = []
        
        # Check tables exist
        tables = data.get("tables", [])
        check = {
            "name": "has_tables",
            "passed": bool(tables),
            "message": "No tables found in financial data",
            "severity": "error"
        }
        checks.append(check)
        
        # Check for financial data characteristics
        if tables:
            # Financial tables typically have numeric columns
            for i, table in enumerate(tables):
                headers = table.get("headers", [])
                rows = table.get("data", [])
                
                # Check for numeric columns (amount, balance, etc.)
                numeric_headers = [h for h in headers if any(term in h.lower() for term in 
                                  ["amount", "balance", "total", "sum", "credit", "debit", "value", "price"])]
                check = {
                    "name": f"table_{i}_financial_columns",
                    "passed": bool(numeric_headers),
                    "message": f"Table {i}: No financial columns detected",
                    "severity": "warning"
                }
                checks.append(check)
                
                # Check numeric values in financial columns
                if numeric_headers and rows:
                    for j, header in enumerate(numeric_headers):
                        if header in rows[0]:
                            # Check if values are numeric or can be converted to numeric
                            numeric_values = []
                            for row in rows:
                                value = row.get(header)
                                try:
                                    if value is not None:
                                        float(str(value).replace(',', ''))
                                        numeric_values.append(True)
                                    else:
                                        numeric_values.append(False)
                                except (ValueError, TypeError):
                                    numeric_values.append(False)
                            
                            all_numeric = all(numeric_values)
                            check = {
                                "name": f"table_{i}_column_{header}_numeric",
                                "passed": all_numeric,
                                "message": f"Table {i}: Column '{header}' contains non-numeric values",
                                "severity": "warning"
                            }
                            checks.append(check)
        
        # Determine validation result
        errors = [c for c in checks if not c["passed"] and c["severity"] == "error"]
        is_valid = not errors
        
        return is_valid, checks
    
    async def _validate_excel_inventory(self, data: Dict[str, Any]) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Custom validation for excel_inventory data type.
        
        Args:
            data: The data to validate
            
        Returns:
            Tuple containing:
                - Boolean indicating if validation passed
                - List of validation check results
        """
        checks = []
        
        # Check tables exist
        tables = data.get("tables", [])
        check = {
            "name": "has_tables",
            "passed": bool(tables),
            "message": "No tables found in inventory data",
            "severity": "error"
        }
        checks.append(check)
        
        # Check for inventory data characteristics
        if tables:
            for i, table in enumerate(tables):
                headers = table.get("headers", [])
                rows = table.get("data", [])
                
                # Check for inventory columns (sku, quantity, etc.)
                inventory_headers = [h for h in headers if any(term in h.lower() for term in 
                                    ["sku", "product", "item", "quantity", "stock", "inventory", "warehouse", "location"])]
                check = {
                    "name": f"table_{i}_inventory_columns",
                    "passed": bool(inventory_headers),
                    "message": f"Table {i}: No inventory columns detected",
                    "severity": "warning"
                }
                checks.append(check)
                
                # Check for quantity columns and verify they are numeric
                quantity_headers = [h for h in headers if any(term in h.lower() for term in 
                                   ["quantity", "stock", "count", "units", "qty"])]
                if quantity_headers and rows:
                    for header in quantity_headers:
                        if header in rows[0]:
                            # Check if quantities are numeric and non-negative
                            valid_quantities = []
                            for row in rows:
                                value = row.get(header)
                                try:
                                    if value is not None:
                                        qty = float(str(value).replace(',', ''))
                                        valid_quantities.append(qty >= 0)
                                    else:
                                        valid_quantities.append(False)
                                except (ValueError, TypeError):
                                    valid_quantities.append(False)
                            
                            all_valid = all(valid_quantities)
                            check = {
                                "name": f"table_{i}_column_{header}_valid_quantity",
                                "passed": all_valid,
                                "message": f"Table {i}: Column '{header}' contains invalid quantities (must be numeric and non-negative)",
                                "severity": "warning"
                            }
                            checks.append(check)
        
        # Determine validation result
        errors = [c for c in checks if not c["passed"] and c["severity"] == "error"]
        is_valid = not errors
        
        return is_valid, checks
    
    async def _validate_excel_timesheet(self, data: Dict[str, Any]) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Custom validation for excel_timesheet data type.
        
        Args:
            data: The data to validate
            
        Returns:
            Tuple containing:
                - Boolean indicating if validation passed
                - List of validation check results
        """
        checks = []
        
        # Check tables exist
        tables = data.get("tables", [])
        check = {
            "name": "has_tables",
            "passed": bool(tables),
            "message": "No tables found in timesheet data",
            "severity": "error"
        }
        checks.append(check)
        
        # Check for timesheet data characteristics
        if tables:
            for i, table in enumerate(tables):
                headers = table.get("headers", [])
                rows = table.get("data", [])
                
                # Check for timesheet columns (date, hours, etc.)
                timesheet_headers = [h for h in headers if any(term in h.lower() for term in 
                                    ["date", "day", "time", "hours", "project", "task", "employee", "activity"])]
                check = {
                    "name": f"table_{i}_timesheet_columns",
                    "passed": bool(timesheet_headers),
                    "message": f"Table {i}: No timesheet columns detected",
                    "severity": "warning"
                }
                checks.append(check)
                
                # Check for date columns and verify they are valid dates
                date_headers = [h for h in headers if any(term in h.lower() for term in 
                               ["date", "day", "when"])]
                if date_headers and rows:
                    for header in date_headers:
                        if header in rows[0]:
                            # Simple check for date-like strings
                            valid_dates = []
                            for row in rows:
                                value = row.get(header)
                                if value is not None:
                                    # Simple pattern matching for common date formats
                                    date_str = str(value)
                                    is_date = bool(re.match(r'^\d{4}-\d{1,2}-\d{1,2}$', date_str) or  # YYYY-MM-DD
                                                 re.match(r'^\d{1,2}/\d{1,2}/\d{2,4}$', date_str) or  # MM/DD/YYYY
                                                 re.match(r'^\d{1,2}-\d{1,2}-\d{2,4}$', date_str))     # DD-MM-YYYY
                                    valid_dates.append(is_date)
                                else:
                                    valid_dates.append(False)
                            
                            all_valid = all(valid_dates)
                            check = {
                                "name": f"table_{i}_column_{header}_valid_date",
                                "passed": all_valid,
                                "message": f"Table {i}: Column '{header}' contains invalid date values",
                                "severity": "warning"
                            }
                            checks.append(check)
                
                # Check for hour columns and verify they are numeric
                hour_headers = [h for h in headers if any(term in h.lower() for term in 
                               ["hours", "time", "duration"])]
                if hour_headers and rows:
                    for header in hour_headers:
                        if header in rows[0]:
                            # Check if hours are numeric and reasonable
                            valid_hours = []
                            for row in rows:
                                value = row.get(header)
                                try:
                                    if value is not None:
                                        hours = float(str(value).replace(',', ''))
                                        valid_hours.append(0 <= hours <= 24)  # Hours in a day
                                    else:
                                        valid_hours.append(False)
                                except (ValueError, TypeError):
                                    valid_hours.append(False)
                            
                            all_valid = all(valid_hours)
                            check = {
                                "name": f"table_{i}_column_{header}_valid_hours",
                                "passed": all_valid,
                                "message": f"Table {i}: Column '{header}' contains invalid hour values (must be between 0 and 24)",
                                "severity": "warning"
                            }
                            checks.append(check)
        
        # Determine validation result
        errors = [c for c in checks if not c["passed"] and c["severity"] == "error"]
        is_valid = not errors
        
        return is_valid, checks 