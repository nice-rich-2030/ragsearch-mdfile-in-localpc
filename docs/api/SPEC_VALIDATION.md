# ローカルRAG FastAPI Web API 整合性検証書

## 4.1 整合性確認表

### エンドポイント定義とルーター実装の整合性

| エンドポイント | SPEC.md | routers/*.py | 整合性 |
|--------------|---------|--------------|--------|
| POST /api/v1/search | ✅ 定義済み | ✅ search.py | ✅ 整合 |
| POST /api/v1/index/rebuild | ✅ 定義済み | ✅ index.py | ✅ 整合 |
| GET /api/v1/index/status | ✅ 定義済み | ✅ index.py | ✅ 整合 |
| GET /health | ✅ 定義済み | ✅ app.py | ✅ 整合 |

### Pydanticスキーマとレスポンス構造の整合性

| スキーマ | SPEC.md定義 | schemas/*.py | 整合性 |
|---------|------------|--------------|--------|
| SearchRequest | query, top_k | ✅ 一致 | ✅ 整合 |
| SearchResultItem | file_path, heading, content, score, chunk_index | ✅ 一致 | ✅ 整合 |
| SearchResponse | results, total_chunks, query, execution_time_ms | ✅ 一致 | ✅ 整合 |
| IndexRebuildRequest | (空) | ✅ 一致 | ✅ 整合 |
| IndexRebuildResponse | added, updated, deleted, unchanged, total_chunks, api_call_count, execution_time_ms | ✅ 一致 | ✅ 整合 |
| IndexStatusResponse | total_chunks, total_files | ✅ 一致 | ✅ 整合 |

---

## 4.2 MCP版との機能整合性

### search機能の対応確認

| 項目 | MCP版 | FastAPI版 | 整合性 |
|------|-------|----------|--------|
| クエリパラメータ | query (必須), top_k (任意) | query (必須), top_k (任意) | ✅ 整合 |
| デフォルトtop_k | 5 | 5 | ✅ 整合 |
| 空インデックス時の自動reindex | ✅ あり | ✅ あり | ✅ 整合 |
| 返却項目 | file_path, heading, content, score, chunk_index | file_path, heading, content, score, chunk_index | ✅ 整合 |
| total_chunks返却 | ✅ あり | ✅ あり | ✅ 整合 |

### reindex機能の対応確認

| 項目 | MCP版 | FastAPI版 | 整合性 |
|------|-------|----------|--------|
| 差分更新 | ✅ mtime + hash | ✅ mtime + hash | ✅ 整合 |
| 返却項目 | added, updated, deleted, unchanged, total_chunks, api_call_count | added, updated, deleted, unchanged, total_chunks, api_call_count | ✅ 整合 |
| execution_time_ms | ❌ なし | ✅ あり | ⚠️ FastAPI拡張 |

**注**: FastAPI版は `execution_time_ms` を追加で返却します。これはMCP版にはない機能ですが、互換性を損なうものではありません。

---

## 4.3 共有モジュールの互換性確認

### src/shared/モジュールの利用確認

| モジュール | MCP版 | FastAPI版 | 整合性 |
|-----------|-------|----------|--------|
| config.py | ✅ load_config() | ✅ load_config() | ✅ 整合 |
| db.py | ✅ FileDB, VectorStore | ✅ FileDB, VectorStore | ✅ 整合 |
| embedder.py | ✅ Embedder | ✅ Embedder | ✅ 整合 |
| searcher.py | ✅ Searcher | ✅ Searcher | ✅ 整合 |
| indexer.py | ✅ Indexer | ✅ Indexer | ✅ 整合 |
| chunker.py | ✅ (indexer経由) | ✅ (indexer経由) | ✅ 整合 |

### インポートパスの確認

| モジュール | MCP版 (src/mcp/server.py) | FastAPI版 (src/api/*.py) |
|-----------|--------------------------|-------------------------|
| config | `from ..shared.config import` | `from ..shared.config import` |
| db | `from ..shared.db import` | `from ..shared.db import` |
| embedder | `from ..shared.embedder import` | `from ..shared.embedder import` |
| searcher | `from ..shared.searcher import` | `from ..shared.searcher import` |
| indexer | `from ..shared.indexer import` | `from ..shared.indexer import` |

---

## 4.4 データディレクトリ整合性

### 共有データの確認

| データ | MCP版 | FastAPI版 | 共有方式 |
|--------|-------|----------|---------|
| files.db (SQLite) | data/files.db | data/files.db | ファイル共有 |
| chroma/ (ChromaDB) | data/chroma/ | data/chroma/ | ディレクトリ共有 |

### 環境変数の整合性

| 環境変数 | MCP版 | FastAPI版 | 備考 |
|---------|-------|----------|------|
| GEMINI_API_KEY | ✅ 必須 | ✅ 必須 | 同一キーを使用 |
| DOCS_DIR | コマンドライン引数 --docs-dir | ✅ 必須（環境変数） | 取得方法が異なる |
| DATA_DIR | コマンドライン引数 --data-dir | ✅ 任意（環境変数） | 取得方法が異なる |

---

## 4.5 技術スタック整合性

### 依存パッケージの確認

| パッケージ | MCP版 | FastAPI版 | 共有/専用 |
|-----------|-------|----------|----------|
| google-genai | ✅ | ✅ | 共有 |
| chromadb | ✅ | ✅ | 共有 |
| pyyaml | ✅ | ✅ | 共有 |
| python-dotenv | ✅ | ✅ | 共有 |
| mcp | ✅ | ❌ | MCP専用 |
| fastapi | ❌ | ✅ | FastAPI専用 |
| uvicorn | ❌ | ✅ | FastAPI専用 |
| httpx | ❌ | ✅ | FastAPIテスト専用 |

---

## 4.6 エラーハンドリング整合性

### エラー処理方式の比較

| エラー種別 | MCP版 | FastAPI版 |
|-----------|-------|----------|
| バリデーションエラー | ログ出力 + TextContent | 422 Unprocessable Entity |
| 検索エラー | ログ出力 + TextContent | 500 Internal Server Error |
| インデックスエラー | ログ出力 + TextContent | 500 Internal Server Error |
| 環境変数未設定 | ValueError | 500 Internal Server Error |

**注**: プロトコルの違い（MCP vs HTTP）により、エラー返却方式が異なるのは適切です。

---

## 4.7 検証結果サマリー

### 整合性判定

| カテゴリ | 結果 | 備考 |
|---------|------|------|
| エンドポイント定義 | ✅ 整合 | 全エンドポイントが仕様通り実装 |
| Pydanticスキーマ | ✅ 整合 | 全スキーマが仕様通り定義 |
| MCP版との機能整合性 | ✅ 整合 | search, reindexが同等機能 |
| 共有モジュール利用 | ✅ 整合 | src/shared/を正しく参照 |
| データディレクトリ共有 | ✅ 整合 | 同一ディレクトリを使用 |
| 依存パッケージ | ✅ 整合 | 適切に分離 |
| エラーハンドリング | ✅ 整合 | プロトコルに適した方式 |

### 修正不要

現時点で不整合は検出されませんでした。

---

## 4.8 テスト計画

### 単体テスト

| テスト対象 | テストファイル | テスト内容 |
|-----------|--------------|----------|
| SearchRequest | tests/api/test_search.py | バリデーション（query必須、top_k範囲） |
| SearchResponse | tests/api/test_search.py | レスポンス構造 |
| IndexRebuildResponse | tests/api/test_index.py | レスポンス構造 |
| IndexStatusResponse | tests/api/test_index.py | レスポンス構造 |

### 統合テスト

| テスト対象 | テストファイル | テスト内容 |
|-----------|--------------|----------|
| POST /api/v1/search | tests/api/test_search.py | 検索実行・結果取得 |
| POST /api/v1/index/rebuild | tests/api/test_index.py | インデックス更新 |
| GET /api/v1/index/status | tests/api/test_index.py | 状態取得 |
| GET /health | tests/api/test_search.py | ヘルスチェック |

### E2Eテスト（手動）

| テストシナリオ | 期待結果 |
|--------------|---------|
| FastAPIサーバー起動 | http://localhost:8000/docs でSwagger UI表示 |
| 検索API実行 | 検索結果がJSON形式で返却 |
| インデックス更新API実行 | 更新サマリーがJSON形式で返却 |
| MCP→FastAPIデータ共有 | MCPでreindex後、FastAPIで検索可能 |
| FastAPI→MCPデータ共有 | FastAPIでreindex後、MCPで検索可能 |
