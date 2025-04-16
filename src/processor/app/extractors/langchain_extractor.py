"""
LangChain extractor module for structured data extraction.

This module provides an extractor that uses LangChain and LangGraph with LLMs
to extract structured data from documents. It supports multiple languages including
Japanese and uses few-shot learning to improve extraction accuracy.
"""
import json
import os
from typing import Any, Dict, List, Optional, Tuple, Union
from enum import Enum

import langchain
from langchain.chains import LLMChain
from langchain.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, SystemMessagePromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph
from pydantic import BaseModel, Field

from app.logger import get_logger

# Initialize logger
logger = get_logger("langchain_extractor")

# Define extraction modes for different use cases
class ExtractionMode(str, Enum):
    """Extraction modes for different document types."""
    STANDARD = "standard"  # Standard extraction for general documents
    JAPANESE = "japanese"  # Optimized for Japanese documents
    DETAILED = "detailed"  # Detailed extraction with higher precision
    FAST = "fast"          # Faster extraction with lower precision


class ExtractionOptions(BaseModel):
    """Options for controlling extraction behavior."""
    mode: ExtractionMode = Field(default=ExtractionMode.STANDARD, description="Extraction mode")
    use_few_shot: bool = Field(default=True, description="Whether to use few-shot examples")
    language: str = Field(default="auto", description="Document language (auto, en, ja, etc.)")
    max_tokens: int = Field(default=4096, description="Maximum tokens for LLM responses")
    extraction_depth: str = Field(default="standard", description="Extraction depth (basic, standard, deep)")


class LangChainExtractor:
    """Extractor using LangChain and LangGraph with LLMs."""

    # Few-shot examples for different document types
    FEW_SHOT_EXAMPLES = {
        "excel_table": [
            {
                "document": {
                    "file_name": "sales_data.xlsx",
                    "file_type": "xlsx",
                    "sheets": {
                        "Sales": {
                            "columns": [
                                {"name": "Date", "type": "datetime64[ns]"},
                                {"name": "Product", "type": "object"},
                                {"name": "Region", "type": "object"},
                                {"name": "Units", "type": "int64"},
                                {"name": "Revenue", "type": "float64"}
                            ],
                            "data": [
                                {"Date": "2023-01-15", "Product": "Widget A", "Region": "North", "Units": 120, "Revenue": 1200.00},
                                {"Date": "2023-01-16", "Product": "Widget B", "Region": "South", "Units": 85, "Revenue": 1020.00}
                            ]
                        }
                    }
                },
                "extraction": {
                    "document_type": "Sales Report",
                    "date_range": {"start": "2023-01-15", "end": "2023-01-16"},
                    "total_revenue": 2220.00,
                    "total_units": 205,
                    "products": ["Widget A", "Widget B"],
                    "regions": ["North", "South"],
                    "sales_by_product": {
                        "Widget A": {"units": 120, "revenue": 1200.00},
                        "Widget B": {"units": 85, "revenue": 1020.00}
                    }
                }
            }
        ],
        "japanese_excel": [
            {
                "document": {
                    "file_name": "売上データ.xlsx",
                    "file_type": "xlsx",
                    "sheets": {
                        "売上": {
                            "columns": [
                                {"name": "日付", "type": "datetime64[ns]"},
                                {"name": "商品", "type": "object"},
                                {"name": "地域", "type": "object"},
                                {"name": "数量", "type": "int64"},
                                {"name": "売上", "type": "float64"}
                            ],
                            "data": [
                                {"日付": "2023-01-15", "商品": "製品A", "地域": "東京", "数量": 120, "売上": 12000.00},
                                {"日付": "2023-01-16", "商品": "製品B", "地域": "大阪", "数量": 85, "売上": 10200.00}
                            ]
                        }
                    }
                },
                "extraction": {
                    "document_type": "売上レポート",
                    "date_range": {"start": "2023-01-15", "end": "2023-01-16"},
                    "total_revenue": 22200.00,
                    "total_units": 205,
                    "products": ["製品A", "製品B"],
                    "regions": ["東京", "大阪"],
                    "sales_by_product": {
                        "製品A": {"units": 120, "revenue": 12000.00},
                        "製品B": {"units": 85, "revenue": 10200.00}
                    }
                }
            }
        ]
    }

    def __init__(self, model_name: str, model_temperature: float, api_key: str):
        """
        Initialize LangChain extractor.

        Args:
            model_name: LLM model name
            model_temperature: LLM temperature
            api_key: API key for LLM
        """
        self.model_name = model_name
        self.model_temperature = model_temperature
        self.api_key = api_key
        self.llm = None
        self._models = {}  # Cache for different model configurations
        
        # Initialize default LLM
        try:
            self.llm = self._get_llm()
            logger.info(f"Initialized LLM", model=self.model_name)
        except Exception as e:
            logger.error(f"Error initializing LLM", error=str(e))
            raise

    def _get_llm(self, 
                max_tokens: int = 4096, 
                json_mode: bool = False, 
                model_name: Optional[str] = None) -> ChatOpenAI:
        """
        Get LLM instance with specific configuration.
        
        Args:
            max_tokens: Maximum tokens for response
            json_mode: Whether to force JSON output format
            model_name: Override model name
            
        Returns:
            ChatOpenAI: Configured LLM instance
        """
        # Create a cache key based on parameters
        cache_key = f"{model_name or self.model_name}_{max_tokens}_{json_mode}"
        
        # Return cached instance if available
        if cache_key in self._models:
            return self._models[cache_key]
        
        # Create model kwargs
        model_kwargs = {}
        if json_mode:
            model_kwargs["response_format"] = {"type": "json_object"}
        
        # Create new LLM instance
        llm = ChatOpenAI(
            model=model_name or self.model_name,
            temperature=self.model_temperature,
            api_key=self.api_key,
            max_tokens=max_tokens,
            model_kwargs=model_kwargs
        )
        
        # Cache the instance
        self._models[cache_key] = llm
        return llm

    async def extract(self, parsed_data: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], float]:
        """
        Extract structured data from parsed document.

        Args:
            parsed_data: Parsed document data
            options: Optional extraction options

        Returns:
            Tuple[Dict[str, Any], float]: Extracted data and confidence score
        """
        try:
            # Check if LLM is initialized
            if not self.llm:
                raise ValueError("LLM not initialized")
            
            # Process options
            processed_options = self._process_options(options or {})
            
            # Detect language if set to auto
            if processed_options.language == "auto":
                processed_options.language = self._detect_language(parsed_data)
                logger.info(f"Detected document language", language=processed_options.language)
                
                # Set japanese mode if Japanese is detected
                if processed_options.language == "ja":
                    processed_options.mode = ExtractionMode.JAPANESE
            
            # Extract data using LangGraph
            extraction_result = await self._run_extraction_graph(parsed_data, processed_options)
            
            # Calculate confidence score
            confidence_score = extraction_result.get("confidence_score", 0.7)
            
            # Return extracted data and confidence score
            return extraction_result.get("extracted_data", {}), confidence_score
            
        except Exception as e:
            logger.error(f"Error extracting data", error=str(e))
            raise

    def _process_options(self, options: Dict[str, Any]) -> ExtractionOptions:
        """
        Process and validate extraction options.
        
        Args:
            options: Raw options dictionary
            
        Returns:
            ExtractionOptions: Processed options
        """
        # Handle string mode
        if "mode" in options and isinstance(options["mode"], str):
            try:
                options["mode"] = ExtractionMode(options["mode"])
            except ValueError:
                logger.warning(f"Invalid extraction mode", mode=options["mode"], fallback=ExtractionMode.STANDARD)
                options["mode"] = ExtractionMode.STANDARD
        
        # Create options object
        return ExtractionOptions(**options)
    
    def _detect_language(self, parsed_data: Dict[str, Any]) -> str:
        """
        Detect document language from parsed data.
        
        Args:
            parsed_data: Parsed document data
            
        Returns:
            str: Detected language code (en, ja, etc.)
        """
        # Extract text samples for language detection
        text_samples = []
        
        # Get file name
        file_name = parsed_data.get("file_name", "")
        if file_name:
            text_samples.append(file_name)
        
        # Get sheet names
        sheet_names = parsed_data.get("sheet_names", [])
        text_samples.extend(sheet_names)
        
        # Get column names from sheets
        sheets = parsed_data.get("sheets", {})
        for sheet_name, sheet_data in sheets.items():
            columns = []
            for col in sheet_data.get("columns", []):
                col_name = col.get("name", "")
                if col_name:
                    columns.append(col_name)
            text_samples.extend(columns)
            
            # Get sample data
            for row in sheet_data.get("data", [])[:3]:  # First 3 rows
                for key, value in row.items():
                    if isinstance(value, str) and len(value) > 2:
                        text_samples.append(value)
        
        # Combine samples
        combined_text = " ".join(text_samples)
        
        # Check for Japanese characters
        japanese_chars = any(ord(c) >= 0x3040 and ord(c) <= 0x30FF for c in combined_text) or \
                         any(ord(c) >= 0x4E00 and ord(c) <= 0x9FFF for c in combined_text)
        
        if japanese_chars:
            return "ja"
        
        # Default to English
        return "en"
    
    def _get_few_shot_examples(self, document_type: str, language: str) -> List[Dict[str, Any]]:
        """
        Get appropriate few-shot examples based on document type and language.
        
        Args:
            document_type: Document type
            language: Document language
            
        Returns:
            List[Dict[str, Any]]: List of few-shot examples
        """
        # Try to get examples for specific document type and language
        if language == "ja":
            examples = self.FEW_SHOT_EXAMPLES.get("japanese_excel", [])
            if examples:
                return examples
        
        # Fall back to generic examples
        return self.FEW_SHOT_EXAMPLES.get(document_type, self.FEW_SHOT_EXAMPLES.get("excel_table", []))
    
    async def _run_extraction_graph(self, parsed_data: Dict[str, Any], options: ExtractionOptions) -> Dict[str, Any]:
        """
        Run extraction graph using LangGraph.

        Args:
            parsed_data: Parsed document data
            options: Extraction options

        Returns:
            Dict[str, Any]: Extraction result
        """
        # Create extraction state
        extraction_state = {
            "document": parsed_data,
            "metadata": parsed_data.get("metadata", {}),
            "options": options.dict(),
            "extracted_data": {},
            "context": {},
            "confidence_score": 0.0,
        }
        
        # Define LangGraph nodes
        def identify_document_type(state):
            """Identify document type from the parsed data."""
            # Extract sheet names and column names
            sheet_names = state["document"].get("sheet_names", [])
            
            # Prepare input for LLM
            sheet_info = []
            for sheet_name in sheet_names:
                if sheet_name in state["document"].get("sheets", {}):
                    sheet_data = state["document"]["sheets"][sheet_name]
                    # Get columns
                    columns = [col.get("name", "") for col in sheet_data.get("columns", [])]
                    if columns:
                        sheet_info.append(f"Sheet: {sheet_name}, Columns: {', '.join(columns)}")
            
            # Get language-specific system template
            language = state["options"].get("language", "en")
            if language == "ja":
                system_template = """
                あなたはドキュメント分析の専門家です。シート名と列名に基づいてドキュメントのタイプを識別してください。
                以下の構造化された応答を提供してください：
                1. ドキュメントタイプ：ドキュメントタイプの説明的な名前
                2. 目的：このドキュメントの目的
                3. 重要フィールド：抽出すべき最も重要なフィールド
                """
            else:
                system_template = """
                You are a document analysis expert. Identify the type of document based on the sheet names and column names.
                Provide a structured response with:
                1. Document Type: A descriptive name for the document type
                2. Purpose: The likely purpose of this document
                3. Key Fields: The most important fields to extract
                """
            
            # Create prompt for LLM
            prompt = ChatPromptTemplate.from_messages([
                SystemMessagePromptTemplate.from_template(system_template),
                HumanMessagePromptTemplate.from_template("Document metadata:\n{metadata}\n\nSheet information:\n{sheet_info}")
            ])
            
            # Run LLM chain
            chain = LLMChain(llm=self.llm, prompt=prompt)
            response = chain.run(metadata=state["metadata"], sheet_info="\n".join(sheet_info))
            
            # Update state
            state["context"]["document_type_analysis"] = response
            
            # Try to determine document type from analysis
            document_type = "excel_table"  # Default
            if "sales" in response.lower() or "売上" in response:
                document_type = "sales_report"
            elif "invoice" in response.lower() or "請求書" in response:
                document_type = "invoice"
            elif "inventory" in response.lower() or "在庫" in response:
                document_type = "inventory"
                
            state["context"]["document_type"] = document_type
            return state
        
        def extract_table_structure(state):
            """Extract table structure from sheets."""
            # Extract sheets data
            sheets = state["document"].get("sheets", {})
            
            # For each sheet, extract structure
            table_structures = {}
            for sheet_name, sheet_data in sheets.items():
                # Get column information
                columns = sheet_data.get("columns", [])
                
                # Analyze first few rows
                data = sheet_data.get("data", [])
                sample_rows = data[:min(5, len(data))]
                
                # Extract statistical information if available
                stats = sheet_data.get("statistical_summary", {})
                
                # Create table structure
                table_structures[sheet_name] = {
                    "columns": columns,
                    "sample_rows": sample_rows,
                    "row_count": sheet_data.get("shape", {}).get("rows", len(data)),
                    "stats": stats,
                }
            
            # Update state
            state["context"]["table_structures"] = table_structures
            return state
        
        def prepare_few_shot_examples(state):
            """Prepare few-shot examples for extraction."""
            # Get document type and language
            document_type = state["context"].get("document_type", "excel_table")
            language = state["options"].get("language", "en")
            
            # Determine if we should use few-shot examples
            use_few_shot = state["options"].get("use_few_shot", True)
            if not use_few_shot:
                state["context"]["few_shot_examples"] = []
                return state
            
            # Get examples
            examples = self._get_few_shot_examples(document_type, language)
            
            # Update state
            state["context"]["few_shot_examples"] = examples
            return state
        
        def extract_data_with_llm(state):
            """Extract structured data using LLM."""
            # Get document type analysis and table structures
            doc_type_analysis = state["context"].get("document_type_analysis", "")
            table_structures = state["context"].get("table_structures", {})
            few_shot_examples = state["context"].get("few_shot_examples", [])
            
            # Get extraction options
            language = state["options"].get("language", "en")
            extraction_mode = state["options"].get("mode", ExtractionMode.STANDARD)
            extraction_depth = state["options"].get("extraction_depth", "standard")
            
            # Prepare sample data
            sample_data = {}
            for sheet_name, structure in table_structures.items():
                sample_data[sheet_name] = {
                    "columns": structure["columns"],
                    "sample_rows": structure["sample_rows"][:min(5, len(structure["sample_rows"]))],
                }
            
            # Create language-specific system template
            if language == "ja":
                system_template = """
                あなたはデータ抽出の専門家です。与えられたドキュメントから構造化された情報を抽出してください。
                ドキュメント分析とテーブル構造に基づいて、適切に構造化されたJSONデータを提供してください。
                
                以下に重点を置いて抽出してください：
                1. 主要なエンティティ情報（企業、人物など）
                2. 主要な指標や値
                3. 日付や期間
                4. カテゴリーや分類
                5. エンティティ間の関係
                
                出力は適切なネスト構造を持つ有効なJSONである必要があります。
                """
            else:
                system_template = """
                You are a data extraction expert. Extract structured information from the given document.
                Based on the document analysis and table structures, provide a well-structured JSON output with the key information.
                
                Focus on extracting:
                1. Main entity information (company, person, etc.)
                2. Key metrics or values
                3. Dates and time periods
                4. Categories and classifications
                5. Relationships between entities
                
                Your output should be valid JSON with nested structures as appropriate.
                """
            
            # Add few-shot examples if available
            human_messages = []
            if few_shot_examples:
                for example in few_shot_examples:
                    human_messages.extend([
                        HumanMessagePromptTemplate.from_template(
                            "Document:\n{example_document}\n\nExtract structured data from this document."
                        ),
                        SystemMessagePromptTemplate.from_template(
                            "{example_extraction}"
                        )
                    ])
            
            # Add current document for extraction
            if language == "ja":
                human_template = """
                ドキュメント分析:
                {doc_analysis}
                
                テーブル構造:
                {table_structures}
                
                このドキュメントから主要情報を抽出し、構造化されたJSONデータとして返してください。
                """
            else:
                human_template = """
                Document Analysis:
                {doc_analysis}
                
                Table Structures:
                {table_structures}
                
                Extract the key information from this document and return it as structured JSON data.
                """
            
            # Create prompt based on whether we have few-shot examples
            if few_shot_examples:
                few_shot_prompt = ChatPromptTemplate.from_messages([
                    SystemMessagePromptTemplate.from_template(system_template),
                    *human_messages,
                    HumanMessagePromptTemplate.from_template(human_template)
                ])
                prompt = few_shot_prompt
            else:
                prompt = ChatPromptTemplate.from_messages([
                    SystemMessagePromptTemplate.from_template(system_template),
                    HumanMessagePromptTemplate.from_template(human_template)
                ])
            
            # Get extraction LLM with JSON output format
            extraction_llm = self._get_llm(
                max_tokens=4096,
                json_mode=True,
                model_name="gpt-4o" if extraction_mode == ExtractionMode.DETAILED else None
            )
            
            # Run LLM chain
            chain = LLMChain(llm=extraction_llm, prompt=prompt)
            
            # Prepare example data if we have few-shot examples
            example_vars = {}
            if few_shot_examples:
                for i, example in enumerate(few_shot_examples):
                    example_vars[f"example_document_{i}"] = json.dumps(example["document"], indent=2)
                    example_vars[f"example_extraction_{i}"] = json.dumps(example["extraction"], indent=2)
            
            # Run the chain
            response = chain.run(
                doc_analysis=doc_type_analysis,
                table_structures=json.dumps(sample_data, indent=2),
                **({"example_document": json.dumps(few_shot_examples[0]["document"], indent=2),
                    "example_extraction": json.dumps(few_shot_examples[0]["extraction"], indent=2)} 
                   if few_shot_examples else {})
            )
            
            # Parse LLM response
            try:
                extracted_data = json.loads(response) if isinstance(response, str) else response
            except json.JSONDecodeError:
                logger.warning("Could not parse LLM response as JSON, using raw response")
                extracted_data = {"raw_extraction": response}
            
            # Update state
            state["extracted_data"] = extracted_data
            return state
        
        def assess_confidence(state):
            """Assess confidence of extraction."""
            # Calculate confidence score based on extraction completeness
            extracted_data = state["extracted_data"]
            
            # If extraction failed completely, return low confidence
            if not extracted_data:
                state["confidence_score"] = 0.2
                return state
            
            # Get language-specific system template
            language = state["options"].get("language", "en")
            if language == "ja":
                system_template = """
                あなたはデータ品質の専門家です。ドキュメントから抽出されたデータの信頼度レベルを評価してください。
                
                以下に基づいて抽出を評価してください：
                1. 完全性：期待されるフィールドがすべて存在するか？
                2. 一貫性：値が全体として意味をなすか？
                3. データ型：値が期待される型（数値、日付、テキスト）か？
                4. 異常値：疑わしい、または予期しない値はあるか？
                
                0.0から1.0の間の信頼スコアを返してください：
                - 0.9-1.0：非常に高い信頼度、すべてのデータが正確
                - 0.7-0.9：高い信頼度、軽微な問題の可能性あり
                - 0.5-0.7：中程度の信頼度、いくつかの問題あり
                - 0.3-0.5：低い信頼度、重大な問題あり
                - 0.0-0.3：非常に低い信頼度、大きな問題または欠落データ
                
                'confidence_score'（浮動小数点数）と'assessment'（文字列）を含むJSONオブジェクトを返してください。
                """
            else:
                system_template = """
                You are a data quality expert. Assess the confidence level of the extracted data from a document.
                
                Evaluate the extraction based on:
                1. Completeness: Are all expected fields present?
                2. Coherence: Do the values make sense together?
                3. Data types: Are values of the expected type (numbers, dates, text)?
                4. Unusual values: Are there any suspicious or unexpected values?
                
                Return a confidence score between 0.0 and 1.0 where:
                - 0.9-1.0: Very high confidence, all data looks correct
                - 0.7-0.9: High confidence, minor issues possible
                - 0.5-0.7: Medium confidence, some issues present
                - 0.3-0.5: Low confidence, significant issues present
                - 0.0-0.3: Very low confidence, major issues or missing data
                
                Your response should be a JSON object with 'confidence_score' (float) and 'assessment' (string).
                """
            
            # Create prompt
            prompt = ChatPromptTemplate.from_messages([
                SystemMessagePromptTemplate.from_template(system_template),
                HumanMessagePromptTemplate.from_template("Document metadata:\n{metadata}\n\nExtracted data:\n{extracted_data}")
            ])
            
            # Get confidence LLM with JSON output format
            confidence_llm = self._get_llm(
                max_tokens=2048,
                json_mode=True
            )
            
            # Run LLM chain
            chain = LLMChain(llm=confidence_llm, prompt=prompt)
            response = chain.run(
                metadata=json.dumps(state["metadata"], indent=2),
                extracted_data=json.dumps(state["extracted_data"], indent=2)
            )
            
            # Parse LLM response
            try:
                confidence_result = json.loads(response) if isinstance(response, str) else response
                confidence_score = float(confidence_result.get("confidence_score", 0.7))
                # Ensure score is in valid range
                confidence_score = max(0.0, min(1.0, confidence_score))
            except (json.JSONDecodeError, ValueError):
                logger.warning("Could not parse confidence assessment, using default value")
                confidence_score = 0.7
            
            # Update state
            state["confidence_score"] = confidence_score
            state["context"]["confidence_assessment"] = confidence_result if isinstance(confidence_result, dict) else {"assessment": "Confidence assessment failed"}
            return state
        
        # Create LangGraph
        extraction_graph = StateGraph(extraction_state)
        
        # Add nodes
        extraction_graph.add_node("identify_document_type", identify_document_type)
        extraction_graph.add_node("extract_table_structure", extract_table_structure)
        extraction_graph.add_node("prepare_few_shot_examples", prepare_few_shot_examples)
        extraction_graph.add_node("extract_data_with_llm", extract_data_with_llm)
        extraction_graph.add_node("assess_confidence", assess_confidence)
        
        # Add edges
        extraction_graph.add_edge("identify_document_type", "extract_table_structure")
        extraction_graph.add_edge("extract_table_structure", "prepare_few_shot_examples")
        extraction_graph.add_edge("prepare_few_shot_examples", "extract_data_with_llm")
        extraction_graph.add_edge("extract_data_with_llm", "assess_confidence")
        
        # Set entry and exit points
        extraction_graph.set_entry_point("identify_document_type")
        extraction_graph.set_finish_point("assess_confidence")
        
        # Compile graph
        extraction_app = extraction_graph.compile()
        
        # Run the graph
        result = extraction_app.invoke(extraction_state)
        
        return {
            "extracted_data": result.get("extracted_data", {}),
            "confidence_score": result.get("confidence_score", 0.7),
            "context": result.get("context", {})
        } 