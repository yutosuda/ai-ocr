# AI-OCR テスト実行ガイド

このドキュメントでは、AI-OCR システムのテスト実行方法について説明します。

## テスト概要

AI-OCR システムのテストは以下のカテゴリに分類されます：

1. **単体テスト**: 個別のコンポーネントの機能をテスト
2. **統合テスト**: 複数のコンポーネントの連携をテスト
3. **機能テスト**: システム全体の機能をテスト
4. **抽出精度テスト**: AI による抽出精度をテスト

テストは pytest フレームワークを使用して実装されており、非同期コードのテストには pytest-asyncio を使用しています。

## テスト環境のセットアップ

### 前提条件

- Python 3.9 以上
- pytest と pytest-asyncio がインストールされていること
- OpenAI API キー（AI 抽出テスト用）

### テスト用依存関係のインストール

```bash
pip install pytest pytest-asyncio pytest-cov
```

## テストデータの生成

テスト用の Excel ファイルを生成するためのスクリプトが用意されています：

```bash
cd src/processor
python create_test_data.py --output-dir test_data --num-files 5
```

このスクリプトは以下の種類のテストファイルを生成します：

- **請求書 (invoice)**: 商品・サービスの項目リストと金額を含む請求書
- **売上レポート (sales_report)**: 複数シートにわたる売上データと地域情報を含むレポート
- **製品カタログ (product_catalog)**: 複数カテゴリの製品情報リスト

生成されたファイルは `test_data` ディレクトリに保存され、各テストで使用できます。

## テストの実行

### テストランナーの使用

プロセッサーサービスのテストを実行するには、専用のテストランナースクリプトを使用します：

```bash
cd src/processor
python run_tests.py
```

以下のオプションが利用可能です：

- `--test-path`: テストディレクトリのパス（デフォルト: app/tests）
- `--model-api-key`: OpenAI API キー
- `--skip-ai`: AI モデル使用のテストをスキップ
- `-v, --verbose`: 詳細な出力を表示
- `-k`: 特定のテスト名に一致するテストのみ実行
- `--no-capture`: 標準出力・標準エラー出力をキャプチャしない

#### AI テストの実行例

```bash
python run_tests.py --model-api-key "your-api-key" -v
```

#### AI を使用しないテストのみ実行

```bash
python run_tests.py --skip-ai -v
```

#### 特定のテストのみ実行

```bash
python run_tests.py -k "test_invoice"
```

### pytest の直接使用

pytest コマンドを直接使用してテストを実行することもできます：

```bash
# プロセッサーテストの実行
cd src/processor
python -m pytest app/tests -v

# API テストの実行
cd src/api
python -m pytest app/tests -v
```

## 抽出精度テスト

抽出精度テストでは、サンプルの Excel ファイルに対する AI 抽出処理の精度を検証します。

### テスト内容

- **請求書抽出テスト**: 請求書データの抽出精度を検証（請求番号、日付、金額、販売者情報など）
- **レポート抽出テスト**: レポートデータの抽出精度を検証（タイトル、期間、カテゴリ情報、地域データなど）
- **空ファイル処理テスト**: 空のファイルに対する処理の検証
- **エラー処理テスト**: エラーケースの適切な処理を検証

### テスト結果の評価

抽出精度テストでは、以下の基準で評価を行います：

1. **抽出成功率**: すべてのキーフィールドが正しく抽出されたファイルの割合
2. **フィールド抽出精度**: 個別フィールドごとの抽出精度
3. **信頼度スコア**: AI モデルが算出した信頼度スコアの分布
4. **データ構造の正確性**: 抽出された構造の正確性

## テストのカスタマイズ

### 新しいテストケースの追加

1. `src/processor/app/tests` または `src/api/app/tests` ディレクトリに新しいテストファイルを作成
2. ファイル名は `test_` で始まる必要があります（例: `test_new_feature.py`）
3. テストクラスとテスト関数を実装（関数名は `test_` で始まる必要があります）

### カスタムテストデータの作成

`create_test_data.py` スクリプトを拡張して、新しい種類のテストデータを生成することができます：

1. 新しいデータ生成関数を追加（例: `generate_new_document_type()`）
2. `main()` 関数内で新しい生成関数を呼び出す

## CI/CD パイプラインとの統合

GitHub Actions や Jenkins などの CI/CD パイプラインでテストを自動実行する場合は、以下の点に注意してください：

1. OpenAI API キーは環境変数またはシークレットとして設定
2. AI を使用するテストは、コスト削減のため `--skip-ai` オプションで必要な場合のみ実行
3. テストカバレッジレポートの生成には `pytest-cov` を使用

```yaml
# GitHub Actions 設定例
name: Run Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: "3.9"
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests without AI
        run: cd src/processor && python run_tests.py --skip-ai
      - name: Run tests with AI (only on main branch)
        if: github.ref == 'refs/heads/main'
        run: cd src/processor && python run_tests.py --model-api-key ${{ secrets.OPENAI_API_KEY }}
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

## トラブルシューティング

### テスト実行中のエラー

- **API キー関連のエラー**: OpenAI API キーが正しく設定されているか確認してください
- **依存関係エラー**: すべての依存関係がインストールされているか確認してください
- **タイムアウトエラー**: AI モデル呼び出しのタイムアウトは、通常ネットワーク遅延か OpenAI サービスの過負荷が原因です

### テスト結果の改善

- **抽出精度が低い場合**: テストデータの品質を確認し、より明確なレイアウトのファイルを使用してください
- **テストの遅延**: AI テストのバッチサイズを小さくし、並列実行を避けて OpenAI API の制限に引っかからないようにしてください

## 次のステップ

- [API 開発ガイド](../api/development.md)
- [プロセッサー開発ガイド](../processor/development.md)
- [プロジェクト仕様書](../specification.md)
