# AI-OCR: Excel データ抽出 AI システム

AI-OCR は、Microsoft Office Excel 文書から AI を用いて構造化データを抽出するシステムです。LangChain、LangGraph、GPT-4o などの最新の AI 技術を活用し、高精度なデータ抽出を実現します。

![AI-OCR System](https://via.placeholder.com/800x400?text=AI-OCR+System+Architecture)

## 概要

企業内には多くの Excel ファイルが蓄積されており、それらから有用な情報を抽出することは大きな課題です。AI-OCR は Excel ファイル（.xlsx, .xls, .csv）に焦点を当て、AI による高度な文書理解と構造化データの抽出を提供します。

### 主な特徴

- **高精度データ抽出**: GPT-4o を活用した高性能な文書理解と情報抽出
- **スマート構造認識**: 表形式データの構造を正確に認識し維持
- **フレキシブルな処理**: 様々な形式の Excel ファイルに対応
- **コンテキスト理解**: データの意味を理解した抽出
- **信頼度評価**: 抽出結果の確実性の評価
- **RESTful API**: 簡単に他システムと連携可能
- **非同期処理**: 大量のドキュメントを効率的に処理

## システムアーキテクチャ

AI-OCR システムは、マイクロサービスアーキテクチャに基づいて設計されており、Docker コンテナとして実装されています。

### コアコンポーネント

- **API サービス (FastAPI)**:

  - 外部システムとのインターフェース
  - ドキュメント管理 API
  - ジョブ管理 API
  - データ抽出結果 API

- **プロセッサーサービス**:

  - Excel ファイルの解析
  - LangChain/LangGraph を用いた抽出パイプライン
  - GPT-4o との連携
  - データ検証と正規化

- **データベース (PostgreSQL)**:

  - 文書メタデータの保存
  - ジョブステータスの管理
  - 抽出結果の永続化

- **キャッシュ/キュー (Redis)**:

  - 処理ジョブのキューイング
  - 一時データのキャッシュ

- **文書ストレージ (MinIO)**:
  - 文書ファイルの保存
  - S3 互換 API

詳細なアーキテクチャ情報は [docs/architecture/server-architecture.md](docs/architecture/server-architecture.md) を参照してください。

## 処理フロー

1. **文書アップロード**: API を通じて Excel 文書をアップロード
2. **文書解析**: ファイル形式に応じたパーサーによる解析
3. **構造認識**: シート構造とデータレイアウトの分析
4. **AI 抽出**: GPT-4o を用いたデータ抽出
5. **データ検証**: スキーマに基づく抽出データの検証
6. **結果保存**: 構造化データとして保存
7. **結果取得**: API を通じた抽出結果の取得

![Processing Flow](https://via.placeholder.com/800x300?text=AI-OCR+Processing+Flow)

## 開始方法

### 前提条件

- [Docker](https://docs.docker.com/get-docker/) と [Docker Compose](https://docs.docker.com/compose/install/)
- [OpenAI API キー](https://platform.openai.com/) (GPT-4o アクセス用)

### クイックスタート

1. リポジトリをクローン:

   ```bash
   git clone <repository-url>
   cd ai-ocr
   ```

2. 環境変数を設定:

   ```bash
   cp .env.local.example .env.local
   # .env.local を編集して API キーなどを設定
   ```

3. Docker で起動:

   ```bash
   docker-compose up --build -d
   ```

4. API サービスにアクセス:
   - API エンドポイント: http://localhost:8000
   - Swagger UI ドキュメント: http://localhost:8000/docs
   - MinIO コンソール: http://localhost:9001 (minioadmin / minioadmin)

詳細なセットアップ手順は [docs/development/setup.md](docs/development/setup.md) を参照してください。

## API の使用例

### 文書のアップロード

```bash
curl -X POST "http://localhost:8000/api/v1/documents" \
  -F "file=@/path/to/document.xlsx"
```

レスポンス:

```json
{
  "document_id": "12345678-1234-5678-1234-567812345678",
  "status": "uploaded",
  "message": "Document uploaded successfully"
}
```

### 処理ジョブの作成

```bash
curl -X POST "http://localhost:8000/api/v1/jobs" \
  -H "Content-Type: application/json" \
  -d '{"document_id": "12345678-1234-5678-1234-567812345678"}'
```

レスポンス:

```json
{
  "job_id": "87654321-8765-4321-8765-432187654321",
  "document_id": "12345678-1234-5678-1234-567812345678",
  "status": "pending",
  "created_at": "2025-03-26T12:00:00.000Z"
}
```

### ジョブステータスの確認

```bash
curl -X GET "http://localhost:8000/api/v1/jobs/87654321-8765-4321-8765-432187654321"
```

レスポンス:

```json
{
  "id": "87654321-8765-4321-8765-432187654321",
  "document_id": "12345678-1234-5678-1234-567812345678",
  "status": "completed",
  "progress": 100.0,
  "created_at": "2025-03-26T12:00:00.000Z",
  "updated_at": "2025-03-26T12:01:30.000Z",
  "completed_at": "2025-03-26T12:01:30.000Z",
  "error": null
}
```

### 抽出データの取得

```bash
curl -X GET "http://localhost:8000/api/v1/extractions/job/87654321-8765-4321-8765-432187654321"
```

レスポンス:

```json
{
  "id": "abcdef12-abcd-ef12-abcd-ef12abcdef12",
  "job_id": "87654321-8765-4321-8765-432187654321",
  "document_id": "12345678-1234-5678-1234-567812345678",
  "extracted_data": {
    "invoice_number": "INV-2025-001",
    "date": "2025-03-26",
    "total_amount": 12345.67,
    "vendor": {
      "name": "Example Vendor Inc.",
      "address": "123 Vendor Street, Vendor City"
    },
    "line_items": [
      {
        "description": "Product A",
        "quantity": 10,
        "unit_price": 100.0,
        "amount": 1000.0
      },
      {
        "description": "Service B",
        "quantity": 5,
        "unit_price": 200.0,
        "amount": 1000.0
      }
    ]
  },
  "confidence_score": 0.95,
  "format_type": "json",
  "extracted_at": "2025-03-26T12:01:30.000Z"
}
```

## カスタマイズと拡張

AI-OCR システムは拡張性を考慮して設計されており、以下の点でカスタマイズが可能です：

- **新しい文書タイプ**: 新しいパーサーを実装することで対応
- **抽出ルール**: 特定のフォーマットに特化した抽出ロジックの追加
- **検証スキーマ**: 業務要件に合わせたバリデーションスキーマの定義
- **出力フォーマット**: 異なる出力形式のサポート

詳細は [docs/architecture/design-philosophy.md](docs/architecture/design-philosophy.md) を参照してください。

## プロジェクト仕様

完全な仕様については、以下のドキュメントを参照してください：

- [システム仕様書](docs/specification.md)
- [API 仕様](docs/api/endpoints.md)
- [プロジェクト企画書](docs/project-proposal.md)

## 開発情報

- **言語**: Python 3.9+
- **主要ライブラリ**:
  - FastAPI: Web API フレームワーク
  - LangChain/LangGraph: AI オーケストレーション
  - SQLAlchemy: データベース ORM
  - pandas/openpyxl: Excel ファイル処理

開発者向け情報は [docs/development/setup.md](docs/development/setup.md) を参照してください。

## ライセンス

このプロジェクトは社内利用を目的として開発されています。

## File Processing Components

### Parsers

Parsers are responsible for converting document files into structured data formats that can be processed. The system includes:

- **BaseParser**: Abstract base class for all parsers
- **ExcelParser**: Handles Excel files (xlsx, xls, csv)
- **ParserFactory**: Creates appropriate parser instances based on file type

Example usage:

```python
from app.parsers import ParserFactory

# Get parser for a specific file type
parser = ParserFactory.get_parser("xlsx")

# Parse a document
parsed_data = await parser.parse("path/to/document.xlsx")
```

### Extractors

Extractors convert parsed document data into structured, normalized data. The system includes:

- **BaseExtractor**: Abstract base class for all extractors
- **ExcelExtractor**: Extracts data from Excel-based parsed data
- **ExtractorFactory**: Creates extractor instances based on document type

Example usage:

```python
from app.extractors import ExtractorFactory

# Get extractor for document type
extractor_factory = ExtractorFactory()
extractor = extractor_factory.get_extractor("excel")

# Extract structured data
extracted_data, confidence = await extractor.extract(parsed_data)
```

### Validators

Validators ensure the quality and consistency of extracted data. The system includes:

- **BaseValidator**: Abstract base class for all validators
- **ExcelValidator**: Validates Excel-derived data
- **ValidatorFactory**: Creates validator instances based on data type

Example usage:

```python
from app.validators import ValidatorFactory

# Get validator for data type
validator_factory = ValidatorFactory()
validator = validator_factory.get_validator("excel")

# Validate extracted data
is_valid, validation_results = await validator.validate(extracted_data)
```

## API Endpoints

### Document Management

- `POST /api/v1/documents/`: Upload a new document
- `GET /api/v1/documents/{document_id}`: Get document information
- `GET /api/v1/documents/`: List all documents
- `DELETE /api/v1/documents/{document_id}`: Delete a document

### Document Processing

- `POST /api/v1/documents/parse`: Parse a document without storing it
- `POST /api/v1/documents/{document_id}/process`: Process a stored document

### Job Management

- `POST /api/v1/jobs/`: Create a processing job
- `GET /api/v1/jobs/{job_id}`: Get job information
- `GET /api/v1/jobs/`: List all jobs
- `POST /api/v1/jobs/{job_id}/cancel`: Cancel a job

### Extraction Results

- `GET /api/v1/extractions/{extraction_id}`: Get extraction data
- `GET /api/v1/extractions/`: List all extractions
- `GET /api/v1/extractions/document/{document_id}`: Get extractions for a document
- `GET /api/v1/extractions/job/{job_id}`: Get extractions for a job

## Setup and Installation

### Prerequisites

- Docker
- Docker Compose
- Python 3.9+

### Installation

1. Clone this repository
2. Create a `.env.local` file based on `.env.local.example`
3. Build and start the containers:

```bash
docker-compose up -d
```

### Configuration

The system can be configured through environment variables, which can be set in the `.env.local` file.

## Development

### Running Tests

```bash
# Run API service tests
docker-compose exec api pytest

# Run processor service tests
docker-compose exec processor python -m run_tests
```

### Adding New Document Types

1. Create a new parser class that inherits from `BaseParser`
2. Create a new extractor class that inherits from `BaseExtractor`
3. Create a new validator class that inherits from `BaseValidator`
4. Register the new classes with their respective factories
5. Update API endpoints to support the new document type

## License

[MIT License](LICENSE)
