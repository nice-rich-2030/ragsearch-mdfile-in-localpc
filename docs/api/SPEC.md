# ローカルRAG FastAPI Web API 仕様書

## 1.1 課題分析・機能提案

### ペインポイント
- **外部アプリケーションからのアクセス不可**: 既存のRAG機能はMCPプロトコル経由でのみ利用可能で、一般的なHTTPクライアントからアクセスできない
- **統合の制約**: Webアプリケーションやモバイルアプリ、他のサービスとの連携が困難
- **API標準化の欠如**: RESTful APIがないため、開発者にとって馴染みのないインターフェース

### 解決策
✅ **FastAPI Web API**: MCPと同じRAG機能をHTTP/RESTで提供
✅ **OpenAPI対応**: Swagger UIで自動ドキュメント生成、API探索が容易
✅ **データ共有**: MCPサーバーと同じデータディレクトリを使用し、一貫性を確保
✅ **シングルトン初期化**: アプリ起動時1回のみ初期化でパフォーマンス最適化

### 主要機能
1. **セマンティック検索API** - 自然言語クエリでドキュメント検索
2. **インデックス管理API** - インデックスの再構築・状態取得
3. **ヘルスチェックAPI** - サーバー状態監視

---

## 1.2 技術スタック選定

| カテゴリ | 技術 | バージョン | 選定根拠 |
|---------|------|-----------|---------|
| **Webフレームワーク** | FastAPI | ≥0.109.0 | 高速、自動ドキュメント生成、型安全 |
| **ASGIサーバー** | Uvicorn | ≥0.27.0 | FastAPI推奨、高性能 |
| **バリデーション** | Pydantic | v2 (FastAPI内蔵) | 型バリデーション、スキーマ自動生成 |
| **共有ロジック** | src/shared/ | - | 既存のRAGコアモジュールを再利用 |
| **環境変数** | python-dotenv | ≥1.0.0 | .envファイル読み込み |

### 共有モジュール（src/shared/）
- `config.py` - 設定管理
- `db.py` - FileDB + VectorStore
- `embedder.py` - Gemini Embedding API
- `searcher.py` - セマンティック検索
- `indexer.py` - インデックス管理
- `chunker.py` - テキストチャンク分割

---

## 1.3 機能詳細化

### 1. セマンティック検索API
**エンドポイント**: `POST /api/v1/search`

| サブ機能 | 説明 |
|---------|------|
| クエリバリデーション | Pydanticでリクエスト検証（query必須、top_k 1-100） |
| 自動インデックス構築 | インデックスが空の場合、自動的にreindex実行 |
| ベクトル検索 | Gemini Embedding + ChromaDBで類似度検索 |
| 結果フォーマット | file_path, heading, content, score, chunk_indexを返却 |
| 実行時間計測 | X-Process-Timeヘッダー + レスポンスにexecution_time_ms |

### 2. インデックス管理API
**エンドポイント**: `POST /api/v1/index/rebuild`, `GET /api/v1/index/status`

| サブ機能 | 説明 |
|---------|------|
| 差分更新 | 変更ファイルのみ再インデックス（mtime + hash比較） |
| 統計取得 | 追加/更新/削除/未変更ファイル数、総チャンク数 |
| 状態取得 | 現在のインデックスサイズ、ファイル数 |

### 3. ヘルスチェックAPI
**エンドポイント**: `GET /health`

| サブ機能 | 説明 |
|---------|------|
| サーバー状態 | status: "healthy" を返却 |
| インデックスサイズ | 現在のチャンク数を返却 |

---

## 1.4 データモデル定義

### リクエスト/レスポンススキーマ

```
SearchRequest
├── query: str (必須, min_length=1)
└── top_k: int (任意, default=5, 1-100)

SearchResponse
├── results: List[SearchResultItem]
│   ├── file_path: str
│   ├── heading: str
│   ├── content: str
│   ├── score: float (0.0-1.0)
│   └── chunk_index: int
├── total_chunks: int
├── query: str
└── execution_time_ms: float

IndexRebuildResponse
├── added: int
├── updated: int
├── deleted: int
├── unchanged: int
├── total_chunks: int
├── api_call_count: int
└── execution_time_ms: float

IndexStatusResponse
├── total_chunks: int
└── total_files: int

HealthResponse
├── status: str
└── index_size: int
```

---

## 1.5 ユーザー操作シナリオ

### シナリオ1: 初回セットアップ

```
1. .envファイル作成
   GEMINI_API_KEY=your_key
   DOCS_DIR=/path/to/documents

2. 依存パッケージインストール
   pip install -r requirements.txt

3. FastAPIサーバー起動
   uvicorn src.api.app:app --reload

4. ブラウザでSwagger UIにアクセス
   http://localhost:8000/docs
```

### シナリオ2: 検索実行

```bash
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Pythonのインストール方法", "top_k": 3}'
```

### シナリオ3: インデックス更新

```bash
curl -X POST http://localhost:8000/api/v1/index/rebuild \
  -H "Content-Type: application/json" \
  -d '{}'
```

---

## 1.6 UI分析・提案

### OpenAPI（Swagger UI）
- **URL**: http://localhost:8000/docs
- **機能**:
  - エンドポイント一覧表示
  - リクエスト/レスポンススキーマ表示
  - Try it out（対話的API実行）

### ReDoc
- **URL**: http://localhost:8000/redoc
- **機能**: よりリッチなAPIドキュメント表示

---

## 1.7 フォルダ・ファイル構成

```
src/api/                        # FastAPI専用層
├── __init__.py                 # パッケージ初期化
├── app.py                      # FastAPIアプリケーション本体（~50行）
├── dependencies.py             # 依存性注入・AppState管理（~70行）
├── middleware.py               # ミドルウェア（~20行）
├── routers/                    # APIルーター
│   ├── __init__.py
│   ├── search.py               # 検索エンドポイント（~45行）
│   └── index.py                # インデックスエンドポイント（~50行）
└── schemas/                    # Pydanticスキーマ
    ├── __init__.py
    ├── search.py               # SearchRequest/Response（~30行）
    └── index.py                # IndexRequest/Response（~25行）
```

---

## 1.8 実装概要

| ファイル | 役割 | 主要処理 |
|---------|------|---------|
| `app.py` | アプリケーション本体 | FastAPI初期化、ミドルウェア設定、ルーター登録、ヘルスチェック |
| `dependencies.py` | 依存性注入 | 環境変数読み込み、AppState初期化、shared/モジュール接続 |
| `middleware.py` | ミドルウェア | リクエスト処理時間計測、X-Process-Timeヘッダー |
| `routers/search.py` | 検索API | POST /api/v1/search 実装 |
| `routers/index.py` | インデックスAPI | POST /api/v1/index/rebuild, GET /api/v1/index/status 実装 |
| `schemas/search.py` | 検索スキーマ | SearchRequest, SearchResultItem, SearchResponse定義 |
| `schemas/index.py` | インデックススキーマ | IndexRebuildRequest/Response, IndexStatusResponse定義 |

---

## 1.9 メンテナンス・セキュリティ

### ログ出力
- **ログレベル**: INFO（デフォルト）
- **ログ形式**: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
- **リクエストログ**: メソッド、パス、ステータスコード、処理時間

### CORS設定
- **開発環境**: `allow_origins=["*"]`（全オリジン許可）
- **本番環境**: 特定ドメインのみ許可に変更推奨

### エラーハンドリング
- **バリデーションエラー**: 422 Unprocessable Entity
- **内部エラー**: 500 Internal Server Error + detail メッセージ

### セキュリティ考慮事項
- **認証**: 現在は認証なし（将来的にJWT認証追加可能）
- **レート制限**: 現在はなし（将来的にSlowAPI等で追加可能）
- **入力検証**: Pydanticによる型・範囲チェック
