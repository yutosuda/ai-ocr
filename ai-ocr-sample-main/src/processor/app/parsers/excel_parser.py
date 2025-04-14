"""
Excel parser module for the document processor service.
"""
import json
import logging
import os
from typing import Dict, List, Optional, Union

import pandas as pd

logger = logging.getLogger(__name__)


class ExcelParser:
    """Parser for Excel files."""

    async def parse(self, file_path: str, file_type: str) -> Dict[str, Any]:
        """
        Parse Excel file and extract data.

        Args:
            file_path: Local file path
            file_type: File type (xlsx, xls, csv)

        Returns:
            Dict: Parsed data

        Raises:
            ValueError: If file type is not supported
        """
        try:
            if file_type not in ["xlsx", "xls", "csv"]:
                raise ValueError(f"Unsupported file type: {file_type}")

            logger.info(f"Parsing Excel file: {file_path}")

            if file_type == "csv":
                return await self._parse_csv(file_path)
            else:
                return await self._parse_excel(file_path)
        except Exception as e:
            logger.error(f"Error parsing Excel file {file_path}: {str(e)}")
            raise

    async def _parse_excel(self, file_path: str) -> Dict[str, Any]:
        """
        Parse Excel file (xlsx, xls).

        Args:
            file_path: Local file path

        Returns:
            Dict: Parsed data
        """
        try:
            # Read Excel file metadata
            xlsx = pd.ExcelFile(file_path)
            
            # Parse each sheet
            result = {
                "metadata": {
                    "filename": os.path.basename(file_path),
                    "sheet_names": xlsx.sheet_names,
                },
                "sheets": {},
            }
            
            # Process each sheet
            for sheet_name in xlsx.sheet_names:
                # Read the sheet
                df = pd.read_excel(xlsx, sheet_name=sheet_name)
                
                # Skip empty sheets
                if df.empty:
                    result["sheets"][sheet_name] = {
                        "empty": True,
                        "rows": 0,
                        "columns": 0,
                        "data": [],
                    }
                    continue
                
                # Convert to records
                records = df.to_dict(orient="records")
                
                # Extract column names
                columns = list(df.columns)
                
                # Add sheet data to result
                result["sheets"][sheet_name] = {
                    "empty": False,
                    "rows": len(df),
                    "columns": len(columns),
                    "column_names": columns,
                    "data": records,
                }
            
            return result
        except Exception as e:
            logger.error(f"Error parsing Excel file {file_path}: {str(e)}")
            raise

    async def _parse_csv(self, file_path: str) -> Dict[str, Any]:
        """
        Parse CSV file.

        Args:
            file_path: Local file path

        Returns:
            Dict: Parsed data
        """
        try:
            # Read CSV file
            df = pd.read_csv(file_path)
            
            # Create result
            result = {
                "metadata": {
                    "filename": os.path.basename(file_path),
                    "sheet_names": ["Sheet1"],  # Default sheet name for CSV
                },
                "sheets": {},
            }
            
            # Skip empty file
            if df.empty:
                result["sheets"]["Sheet1"] = {
                    "empty": True,
                    "rows": 0,
                    "columns": 0,
                    "data": [],
                }
                return result
            
            # Convert to records
            records = df.to_dict(orient="records")
            
            # Extract column names
            columns = list(df.columns)
            
            # Add sheet data to result
            result["sheets"]["Sheet1"] = {
                "empty": False,
                "rows": len(df),
                "columns": len(columns),
                "column_names": columns,
                "data": records,
            }
            
            return result
        except Exception as e:
            logger.error(f"Error parsing CSV file {file_path}: {str(e)}")
            raise 