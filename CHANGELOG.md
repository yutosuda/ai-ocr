# Changelog

## [0.2.0] - 2025-03-26

### Added

- 開発環境セットアップガイド (docs/development/setup.md)
- テスト実行ガイド (docs/development/testing.md)
- サンプル Excel ファイル生成スクリプト (src/processor/create_test_data.py)
  - 請求書 (invoice)
  - 売上レポート (sales_report)
  - 製品カタログ (product_catalog)
- 抽出精度テストフレームワーク (src/processor/app/tests/test_extraction.py)
  - 請求書抽出テスト
  - レポート抽出テスト
  - 空ファイル処理テスト
  - エラー処理テスト
- テストランナースクリプト (src/processor/run_tests.py)
- API テストフレームワーク (src/api/app/tests/test_document_api.py)
- 統合テストユーティリティ (src/tools/generate_and_test.py)
  - サンプルファイル生成
  - API エンドポイントを通じた処理
  - 抽出結果の収集と評価
- Dockerfile を改良し、開発環境と本番環境のビルドを分離

### Updated

- README を更新し、システムの機能と使用方法を詳細に説明
- ディレクトリ構造を整理し、明確なモジュール分割を実装

### Fixed

- ドキュメント間のリンク修正
- 設定パラメータの一貫性確保
- テスト環境と本番環境の分離を改善

## [0.1.0] - 2025-03-25

### Added

- 初期実装
  - API サービス (FastAPI)
  - プロセッサーサービス (LangChain/LangGraph)
  - データベース (PostgreSQL)
  - キャッシュ/キュー (Redis)
  - ドキュメントストレージ (MinIO)
- 基本的なドキュメント
  - サーバーアーキテクチャ (docs/architecture/server-architecture.md)
  - 設計思想 (docs/architecture/design-philosophy.md)
  - システム仕様 (docs/specification.md)
  - プロジェクト企画書 (docs/project-proposal.md)
- Docker 設定
- 基本的な API エンドポイント
  - ドキュメント管理
  - ジョブ管理
  - 抽出結果取得
