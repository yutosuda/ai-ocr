# AI-OCR API エンドポイント仕様

本文書では、AI-OCR システムが提供する API エンドポイントについて詳述します。すべてのエンドポイントは `/api/v1` プレフィックスの下に配置されています。

## 認証

すべての API リクエストには認証が必要です。認証は HTTP Authorization ヘッダーを使用します：

```
Authorization: Bearer <TOKEN>
```

認証トークンは既存の社内認証基盤から取得してください。

## エンドポイント一覧

### 文書管理

#### 文書のアップロード

```
POST /api/v1/documents
```

Excel 文書をアップロードし、処理ジョブを作成します。

**リクエスト**:

- Content-Type: `multipart/form-data`
- Body:
  - `file`: アップロードするファイル

**レスポンス**:

```json
{
  "document_id": "uuid",
  "status": "uploaded",
  "message": "Document uploaded successfully"
}
```

**ステータスコード**:

- `201 Created`: 文書が正常にアップロードされた
- `400 Bad Request`: 不正なリクエスト
- `413 Request Entity Too Large`: ファイルサイズが大きすぎる
- `500 Internal Server Error`: サーバーエラー

#### 文書情報の取得

```
GET /api/v1/documents/{document_id}
```

特定の文書の情報を取得します。

**パラメータ**:

- `document_id`: 文書 ID

**レスポンス**:

```json
{
  "id": "uuid",
  "filename": "example.xlsx",
  "file_type": "xlsx",
  "file_size": 12345,
  "status": "processed",
  "uploaded_at": "2023-01-01T12:00:00Z",
  "updated_at": "2023-01-01T12:05:00Z"
}
```

**ステータスコード**:

- `200 OK`: 成功
- `404 Not Found`: 文書が見つからない
- `500 Internal Server Error`: サーバーエラー

#### 文書一覧の取得

```
GET /api/v1/documents
```

文書の一覧を取得します。

**クエリパラメータ**:

- `skip`: スキップする文書数（デフォルト: 0）
- `limit`: 取得する最大文書数（デフォルト: 100）

**レスポンス**:

```json
[
  {
    "id": "uuid",
    "filename": "example1.xlsx",
    "file_type": "xlsx",
    "status": "processed",
    "uploaded_at": "2023-01-01T12:00:00Z"
  },
  {
    "id": "uuid",
    "filename": "example2.xlsx",
    "file_type": "xlsx",
    "status": "processing",
    "uploaded_at": "2023-01-01T12:30:00Z"
  }
]
```

**ステータスコード**:

- `200 OK`: 成功
- `500 Internal Server Error`: サーバーエラー

#### 文書の削除

```
DELETE /api/v1/documents/{document_id}
```

特定の文書を削除します。

**パラメータ**:

- `document_id`: 文書 ID

**レスポンス**:

なし（空のレスポンス）

**ステータスコード**:

- `204 No Content`: 成功
- `404 Not Found`: 文書が見つからない
- `500 Internal Server Error`: サーバーエラー

### ジョブ管理

#### 処理ジョブの作成

```
POST /api/v1/jobs
```

既存の文書に対して新しい処理ジョブを作成します。

**リクエスト**:

```json
{
  "document_id": "uuid"
}
```

**レスポンス**:

```json
{
  "job_id": "uuid",
  "document_id": "uuid",
  "status": "pending",
  "created_at": "2023-01-01T12:00:00Z"
}
```

**ステータスコード**:

- `201 Created`: ジョブが正常に作成された
- `400 Bad Request`: 不正なリクエスト
- `404 Not Found`: 文書が見つからない
- `500 Internal Server Error`: サーバーエラー

#### ジョブ情報の取得

```
GET /api/v1/jobs/{job_id}
```

特定のジョブの情報を取得します。

**パラメータ**:

- `job_id`: ジョブ ID

**レスポンス**:

```json
{
  "id": "uuid",
  "document_id": "uuid",
  "status": "processing",
  "progress": 45.0,
  "created_at": "2023-01-01T12:00:00Z",
  "updated_at": "2023-01-01T12:05:00Z",
  "completed_at": null,
  "error": null
}
```

**ステータスコード**:

- `200 OK`: 成功
- `404 Not Found`: ジョブが見つからない
- `500 Internal Server Error`: サーバーエラー

#### ジョブ一覧の取得

```
GET /api/v1/jobs
```

ジョブの一覧を取得します。

**クエリパラメータ**:

- `skip`: スキップするジョブ数（デフォルト: 0）
- `limit`: 取得する最大ジョブ数（デフォルト: 100）

**レスポンス**:

```json
[
  {
    "id": "uuid",
    "document_id": "uuid",
    "status": "completed",
    "progress": 100.0,
    "created_at": "2023-01-01T12:00:00Z",
    "updated_at": "2023-01-01T12:05:00Z"
  },
  {
    "id": "uuid",
    "document_id": "uuid",
    "status": "processing",
    "progress": 60.0,
    "created_at": "2023-01-01T12:30:00Z",
    "updated_at": "2023-01-01T12:32:00Z"
  }
]
```

**ステータスコード**:

- `200 OK`: 成功
- `500 Internal Server Error`: サーバーエラー

#### 文書に関連するジョブの取得

```
GET /api/v1/jobs/document/{document_id}
```

特定の文書に関連するジョブの一覧を取得します。

**パラメータ**:

- `document_id`: 文書 ID

**レスポンス**:

```json
[
  {
    "id": "uuid",
    "status": "completed",
    "progress": 100.0,
    "created_at": "2023-01-01T12:00:00Z",
    "updated_at": "2023-01-01T12:05:00Z"
  },
  {
    "id": "uuid",
    "status": "failed",
    "progress": 30.0,
    "created_at": "2023-01-01T13:00:00Z",
    "updated_at": "2023-01-01T13:02:00Z"
  }
]
```

**ステータスコード**:

- `200 OK`: 成功
- `404 Not Found`: 文書が見つからない
- `500 Internal Server Error`: サーバーエラー

#### ジョブのキャンセル

```
POST /api/v1/jobs/{job_id}/cancel
```

処理中または保留中のジョブをキャンセルします。

**パラメータ**:

- `job_id`: ジョブ ID

**レスポンス**:

```json
{
  "id": "uuid",
  "status": "canceled",
  "message": "Job canceled successfully"
}
```

**ステータスコード**:

- `200 OK`: 成功
- `400 Bad Request`: キャンセルできないジョブ状態
- `404 Not Found`: ジョブが見つからない
- `500 Internal Server Error`: サーバーエラー

### 抽出データ管理

#### 抽出データの取得

```
GET /api/v1/extractions/{extraction_id}
```

特定の抽出結果の詳細を取得します。

**パラメータ**:

- `extraction_id`: 抽出 ID

**レスポンス**:

```json
{
  "id": "uuid",
  "job_id": "uuid",
  "document_id": "uuid",
  "extracted_data": {
    // 抽出されたデータの構造（文書による）
  },
  "confidence_score": 0.92,
  "format_type": "json",
  "validation_results": {
    "valid": true,
    "schema_type": "invoice",
    "errors": []
  },
  "extracted_at": "2023-01-01T12:05:00Z",
  "created_at": "2023-01-01T12:05:00Z"
}
```

**ステータスコード**:

- `200 OK`: 成功
- `404 Not Found`: 抽出結果が見つからない
- `500 Internal Server Error`: サーバーエラー

#### 抽出データ一覧の取得

```
GET /api/v1/extractions
```

抽出結果の一覧を取得します。

**クエリパラメータ**:

- `skip`: スキップする結果数（デフォルト: 0）
- `limit`: 取得する最大結果数（デフォルト: 100）

**レスポンス**:

```json
[
  {
    "id": "uuid",
    "job_id": "uuid",
    "document_id": "uuid",
    "confidence_score": 0.92,
    "format_type": "json",
    "extracted_at": "2023-01-01T12:05:00Z"
  },
  {
    "id": "uuid",
    "job_id": "uuid",
    "document_id": "uuid",
    "confidence_score": 0.85,
    "format_type": "json",
    "extracted_at": "2023-01-01T12:35:00Z"
  }
]
```

**ステータスコード**:

- `200 OK`: 成功
- `500 Internal Server Error`: サーバーエラー

#### 文書の抽出データ取得

```
GET /api/v1/extractions/document/{document_id}
```

特定の文書に関連する抽出結果の一覧を取得します。

**パラメータ**:

- `document_id`: 文書 ID

**レスポンス**:

```json
[
  {
    "id": "uuid",
    "job_id": "uuid",
    "confidence_score": 0.92,
    "format_type": "json",
    "extracted_at": "2023-01-01T12:05:00Z"
  },
  {
    "id": "uuid",
    "job_id": "uuid",
    "confidence_score": 0.78,
    "format_type": "json",
    "extracted_at": "2023-01-01T13:10:00Z"
  }
]
```

**ステータスコード**:

- `200 OK`: 成功
- `404 Not Found`: 文書が見つからない
- `500 Internal Server Error`: サーバーエラー

#### ジョブの抽出データ取得

```
GET /api/v1/extractions/job/{job_id}
```

特定のジョブに関連する抽出結果の一覧を取得します。

**パラメータ**:

- `job_id`: ジョブ ID

**レスポンス**:

```json
[
  {
    "id": "uuid",
    "document_id": "uuid",
    "confidence_score": 0.92,
    "format_type": "json",
    "extracted_at": "2023-01-01T12:05:00Z"
  }
]
```

**ステータスコード**:

- `200 OK`: 成功
- `404 Not Found`: ジョブが見つからない
- `500 Internal Server Error`: サーバーエラー

### システム管理

#### ヘルスチェック

```
GET /health
```

システムの健全性を確認します。

**レスポンス**:

```json
{
  "status": "healthy"
}
```

**ステータスコード**:

- `200 OK`: システムは正常に動作している
- `500 Internal Server Error`: システムに問題がある

## ステータスコード

- `200 OK`: リクエストが成功した
- `201 Created`: リソースが正常に作成された
- `204 No Content`: リクエストが成功し、返すコンテンツがない
- `400 Bad Request`: リクエストが不正
- `401 Unauthorized`: 認証が必要
- `403 Forbidden`: アクセス権限がない
- `404 Not Found`: リソースが見つからない
- `413 Request Entity Too Large`: リクエストエンティティが大きすぎる
- `500 Internal Server Error`: サーバーエラー

## エラーレスポンス形式

エラー発生時は以下のような JSON 形式でレスポンスが返ります：

```json
{
  "detail": "エラーメッセージ"
}
```
