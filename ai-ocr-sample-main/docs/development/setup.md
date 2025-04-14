# 開発環境セットアップガイド

このドキュメントでは、AI-OCR システムの開発環境のセットアップ方法について説明します。

## 前提条件

以下のソフトウェアがインストールされていることを確認してください：

- [Docker](https://docs.docker.com/get-docker/) および [Docker Compose](https://docs.docker.com/compose/install/)
- [Python 3.9](https://www.python.org/downloads/) 以上
- [Git](https://git-scm.com/downloads)
- コードエディタ（[Visual Studio Code](https://code.visualstudio.com/) 推奨）

## 開発環境のセットアップ

### 1. リポジトリのクローン

```bash
git clone <repository-url>
cd ai-ocr
```

### 2. 環境変数の設定

開発用の環境変数を設定します。

```bash
cp .env.local.example .env.local
```

`.env.local` ファイルを開き、必要な環境変数を設定します。特に以下の変数は重要です：

- `MODEL_API_KEY`: OpenAI API キー（GPT-4o へのアクセス用）
- `API_SECRET_KEY`: API のセキュリティキー（開発環境ではデフォルト値で問題ありません）

### 3. 仮想環境の作成（オプション）

ローカルでの開発のために仮想環境を作成することをお勧めします：

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# または
venv\Scripts\activate  # Windows
```

### 4. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 5. Docker 環境の構築と起動

```bash
docker-compose up --build -d
```

これにより、以下のサービスが起動します：

- API サービス: http://localhost:8000
- プロセッサーサービス (内部アクセスのみ)
- PostgreSQL データベース
- Redis キャッシュ/キュー
- MinIO オブジェクトストレージ: http://localhost:9000 (API), http://localhost:9001 (コンソール)

### 6. データベースの初期化

データベーススキーマは Docker 起動時に自動的に作成されますが、必要に応じて手動で初期化することもできます：

```bash
docker-compose exec db psql -U postgres -d ai_ocr -f /docker-entrypoint-initdb.d/01_schema.sql
```

## 開発ワークフロー

### コードの変更

- `src/api` ディレクトリには API サービスのコードがあります
- `src/processor` ディレクトリにはドキュメント処理サービスのコードがあります
- `src/db` ディレクトリにはデータベース初期化スクリプトがあります
- `src/tools` ディレクトリにはユーティリティスクリプトがあります

開発モードでは、コードの変更は自動的に反映されます。API サービスとプロセッサーサービスは、コードの変更が検出されると自動的に再起動します。

### API ドキュメントへのアクセス

FastAPI は自動的に OpenAPI ドキュメントを生成します：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### ログの確認

サービスのログを確認するには：

```bash
# API サービスのログ
docker-compose logs -f api

# プロセッサーサービスのログ
docker-compose logs -f processor

# すべてのサービスのログ
docker-compose logs -f
```

## テスト

AI-OCR システムには、様々なレベルのテストが用意されています。詳細なテスト実行方法については [テスト実行ガイド](testing.md) を参照してください。

### テスト用データの生成

テスト用の Excel ファイルを生成するには：

```bash
# サンプルファイルの生成（各種類1ファイルずつ）
python src/processor/create_test_data.py --output-dir test_data --num-files 1

# 複数のサンプルファイルを生成
python src/processor/create_test_data.py --output-dir test_data --num-files 5
```

### 抽出テストの実行

生成したファイルの処理をテストするには：

```bash
# テストファイルの生成と処理
python src/tools/generate_and_test.py --extract --api-url http://localhost:8000
```

### 単体テストの実行

```bash
# プロセッサーの単体テスト
cd src/processor
python run_tests.py --skip-ai  # AI テストをスキップ

# API の単体テスト
cd src/api
python -m pytest app/tests
```

## トラブルシューティング

### API サービスにアクセスできない

- Docker コンテナが実行中であることを確認してください：`docker-compose ps`
- API サービスのログを確認してください：`docker-compose logs -f api`
- ポート 8000 が他のアプリケーションで使用されていないことを確認してください

### データベース接続エラー

- PostgreSQL コンテナが実行中であることを確認してください
- 環境変数 `DATABASE_URL` が正しく設定されていることを確認してください
- データベースログを確認してください：`docker-compose logs -f db`

### MinIO 接続エラー

- MinIO コンテナが実行中であることを確認してください
- 環境変数 `MINIO_URL`, `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD` が正しく設定されていることを確認してください
- MinIO バケットが作成されていることを確認してください：`docker-compose exec api python -c "from app.services.storage_service import create_bucket; create_bucket()"`

### モデル API エラー

- 有効な API キーが `.env.local` ファイルに設定されていることを確認してください
- API キーに GPT-4o へのアクセス権があることを確認してください
- プロセッサーサービスのログを確認してください：`docker-compose logs -f processor`

## 開発のベストプラクティス

### 1. コードスタイル

このプロジェクトでは以下のコードスタイルツールを使用しています：

- [Black](https://black.readthedocs.io/) - コードフォーマッター
- [Flake8](https://flake8.pycqa.org/) - リンター
- [isort](https://pycqa.github.io/isort/) - インポートの整理
- [mypy](https://mypy.readthedocs.io/) - 型チェック

コードをコミットする前に以下のコマンドを実行してください：

```bash
black src/
flake8 src/
isort src/
mypy src/
```

### 2. コミットメッセージ

コミットメッセージには、変更内容を明確に記述してください。以下の形式を推奨します：

```
[コンポーネント] 変更の簡潔な説明

変更の詳細な説明（必要な場合）
```

### 3. ブランチ戦略

新機能の開発やバグ修正を行う場合は、`main` ブランチから新しいブランチを作成してください：

```bash
git checkout -b feature/new-feature  # 新機能の場合
git checkout -b fix/bug-description  # バグ修正の場合
```

## 環境クリーンアップ

開発環境をクリーンアップするには：

```bash
# コンテナとネットワークを停止および削除
docker-compose down

# コンテナ、ネットワーク、ボリュームを削除（すべてのデータが失われます）
docker-compose down -v
```

## 次のステップ

- [API 仕様](../api/endpoints.md)を確認する
- [アーキテクチャ概要](../architecture/server-architecture.md)を読む
- [設計思想](../architecture/design-philosophy.md)を理解する
