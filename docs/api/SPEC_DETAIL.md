# ローカルRAG FastAPI Web API 詳細設計書

## 2.1 ファイルごとの実装概要

### 2.1.1 src/api/app.py - FastAPIアプリケーション本体

**役割**: FastAPIアプリケーションの初期化と構成

**処理フロー**:
```
[アプリ起動]
    ↓
[ロギング設定] logging.basicConfig()
    ↓
[FastAPI初期化] FastAPI(title, description, version, docs_url, redoc_url)
    ↓
[CORS設定] CORSMiddleware追加
    ↓
[タイミングミドルウェア] timing_middleware登録
    ↓
[AppState初期化] get_app_state() → app.state.app_state
    ↓
[ルーター登録] search.router, index.router
    ↓
[ヘルスチェック] @app.get("/health")
    ↓
[起動完了] Uvicornがリクエスト受付開始
```

**主要コンポーネント**:
| コンポーネント | 説明 |
|--------------|------|
| `app` | FastAPIインスタンス |
| `CORSMiddleware` | CORS設定（allow_origins=["*"]） |
| `timing_middleware` | 処理時間計測 |
| `app.state.app_state` | アプリケーション状態（シングルトン） |

---

### 2.1.2 src/api/dependencies.py - 依存性注入

**役割**: アプリケーション状態の初期化と管理

**処理フロー**:
```
[get_app_state()]
    ↓
[.env読み込み] load_dotenv()
    ↓
[環境変数取得] DOCS_DIR, DATA_DIR, GEMINI_API_KEY
    ↓
[設定読込] load_config(docs_dir)
    ↓
[DB初期化] FileDB(data_dir/files.db)
    ↓
[VectorStore初期化] VectorStore(data_dir/chroma)
    ↓
[Embedder初期化] Embedder(embedding_config, retry_config)
    ↓
[Searcher初期化] Searcher(embedder, vector_store)
    ↓
[Indexer初期化] Indexer(docs_dir, file_db, vector_store, ...)
    ↓
[AppState返却]
```

**AppState構造**:
```python
@dataclass
class AppState:
    docs_dir: Path          # ドキュメントディレクトリ
    file_db: FileDB         # SQLiteメタデータDB
    vector_store: VectorStore  # ChromaDBベクトルストア
    embedder: Embedder      # Gemini Embedding API
    searcher: Searcher      # セマンティック検索
    indexer: Indexer        # インデックス管理
```

---

### 2.1.3 src/api/middleware.py - ミドルウェア

**役割**: リクエスト処理時間の計測とログ出力

**処理フロー**:
```
[リクエスト受信]
    ↓
[開始時刻記録] start_time = time.perf_counter()
    ↓
[次のミドルウェア/ルーター呼び出し] await call_next(request)
    ↓
[終了時刻記録] elapsed_ms = (perf_counter() - start_time) * 1000
    ↓
[ログ出力] logger.info(f"{method} {path} - {status} - {elapsed_ms}ms")
    ↓
[ヘッダー追加] response.headers["X-Process-Time"] = f"{elapsed_ms}ms"
    ↓
[レスポンス返却]
```

---

### 2.1.4 src/api/routers/search.py - 検索エンドポイント

**役割**: POST /api/v1/search の実装

**処理フロー**:
```
[POST /api/v1/search リクエスト受信]
    ↓
[Pydanticバリデーション] SearchRequest(query, top_k)
    ↓
[AppState取得] app_request.app.state.app_state
    ↓
[開始時刻記録]
    ↓
[インデックス空チェック]
    │
    ├── [空の場合] indexer.update() 実行
    │
    └── [空でない場合] スキップ
    ↓
[検索実行] searcher.search(query, top_k)
    ↓
[結果変換] SearchResult → SearchResultItem
    ↓
[レスポンス構築] SearchResponse
    ↓
[返却]
```

**エラーハンドリング**:
| エラー | HTTPステータス | 対応 |
|-------|---------------|------|
| バリデーションエラー | 422 | Pydanticが自動処理 |
| 検索エラー | 500 | HTTPException(500, detail) |

---

### 2.1.5 src/api/routers/index.py - インデックス管理エンドポイント

**役割**: インデックス管理APIの実装

**POST /api/v1/index/rebuild 処理フロー**:
```
[POST /api/v1/index/rebuild リクエスト受信]
    ↓
[AppState取得]
    ↓
[開始時刻記録]
    ↓
[インデックス更新] indexer.update()
    ↓
[サマリー取得] UpdateSummary
    ↓
[レスポンス構築] IndexRebuildResponse
    ↓
[返却]
```

**GET /api/v1/index/status 処理フロー**:
```
[GET /api/v1/index/status リクエスト受信]
    ↓
[AppState取得]
    ↓
[ファイル数取得] len(file_db.get_all_files())
    ↓
[チャンク数取得] vector_store.count()
    ↓
[レスポンス構築] IndexStatusResponse
    ↓
[返却]
```

---

### 2.1.6 src/api/schemas/search.py - 検索スキーマ

**役割**: 検索リクエスト/レスポンスの型定義

**スキーマ定義**:
```
SearchRequest
├── query: str
│   ├── 必須
│   ├── min_length=1
│   └── description="検索クエリ"
└── top_k: Optional[int]
    ├── default=5
    ├── ge=1, le=100
    └── description="返却件数"

SearchResultItem
├── file_path: str
├── heading: str
├── content: str
├── score: float (ge=0.0, le=1.0)
└── chunk_index: int

SearchResponse
├── results: List[SearchResultItem]
├── total_chunks: int
├── query: str
└── execution_time_ms: float
```

---

### 2.1.7 src/api/schemas/index.py - インデックススキーマ

**役割**: インデックス管理リクエスト/レスポンスの型定義

**スキーマ定義**:
```
IndexRebuildRequest
└── (空) # 将来的に force_full_rebuild などを追加可能

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
```

---

## 2.2 モジュール連携図

```
┌─────────────────────────────────────────────────────────────────┐
│                         FastAPI Layer                            │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ app.py                                                       ││
│  │  ├── FastAPI() インスタンス                                  ││
│  │  ├── CORSMiddleware                                          ││
│  │  ├── timing_middleware                                       ││
│  │  └── app.state.app_state ←── dependencies.get_app_state()   ││
│  └─────────────────────────────────────────────────────────────┘│
│                              │                                   │
│  ┌───────────────────────────┼───────────────────────────────┐  │
│  │ routers/                  │                               │  │
│  │  ├── search.py ──────────→ app.state.app_state           │  │
│  │  │   └── POST /api/v1/search                             │  │
│  │  └── index.py ───────────→ app.state.app_state           │  │
│  │      ├── POST /api/v1/index/rebuild                      │  │
│  │      └── GET /api/v1/index/status                        │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌───────────────────────────┼───────────────────────────────┐  │
│  │ schemas/                  │                               │  │
│  │  ├── search.py ──────────→ SearchRequest, SearchResponse │  │
│  │  └── index.py ───────────→ IndexRebuildResponse, etc.    │  │
│  └───────────────────────────────────────────────────────────┘  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               │ from ..shared.xxx import
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Shared Layer                             │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ src/shared/                                                  ││
│  │  ├── config.py ──────────→ load_config(), AppConfig         ││
│  │  ├── db.py ──────────────→ FileDB, VectorStore              ││
│  │  ├── embedder.py ────────→ Embedder                         ││
│  │  ├── searcher.py ────────→ Searcher, SearchResult           ││
│  │  ├── indexer.py ─────────→ Indexer, UpdateSummary           ││
│  │  └── chunker.py ─────────→ Chunk, chunk_file()              ││
│  └─────────────────────────────────────────────────────────────┘│
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Data Layer                               │
│  ┌───────────────────────┐  ┌───────────────────────────────┐  │
│  │ SQLite (files.db)     │  │ ChromaDB (chroma/)            │  │
│  │  └── ファイルメタデータ│  │  └── ベクトルインデックス    │  │
│  └───────────────────────┘  └───────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2.3 OpenAPI仕様

FastAPIは自動的にOpenAPI仕様を生成します。

**アクセス方法**:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

**生成される仕様**:
```yaml
openapi: 3.0.2
info:
  title: Local RAG API
  description: Semantic search API for local documents using Gemini Embedding and ChromaDB
  version: 1.0.0
paths:
  /api/v1/search:
    post:
      tags: [search]
      summary: Search
      operationId: search_api_v1_search_post
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/SearchRequest'
      responses:
        '200':
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SearchResponse'
  /api/v1/index/rebuild:
    post:
      tags: [index]
      summary: Rebuild Index
      operationId: rebuild_index_api_v1_index_rebuild_post
      responses:
        '200':
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/IndexRebuildResponse'
  /api/v1/index/status:
    get:
      tags: [index]
      summary: Index Status
      operationId: index_status_api_v1_index_status_get
      responses:
        '200':
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/IndexStatusResponse'
  /health:
    get:
      summary: Health
      operationId: health_health_get
      responses:
        '200':
          content:
            application/json:
              schema: {}
components:
  schemas:
    SearchRequest:
      type: object
      required: [query]
      properties:
        query:
          type: string
          minLength: 1
        top_k:
          type: integer
          default: 5
          minimum: 1
          maximum: 100
    SearchResultItem:
      type: object
      required: [file_path, heading, content, score, chunk_index]
      properties:
        file_path:
          type: string
        heading:
          type: string
        content:
          type: string
        score:
          type: number
          minimum: 0
          maximum: 1
        chunk_index:
          type: integer
    SearchResponse:
      type: object
      required: [results, total_chunks, query, execution_time_ms]
      properties:
        results:
          type: array
          items:
            $ref: '#/components/schemas/SearchResultItem'
        total_chunks:
          type: integer
        query:
          type: string
        execution_time_ms:
          type: number
    IndexRebuildResponse:
      type: object
      properties:
        added:
          type: integer
        updated:
          type: integer
        deleted:
          type: integer
        unchanged:
          type: integer
        total_chunks:
          type: integer
        api_call_count:
          type: integer
        execution_time_ms:
          type: number
    IndexStatusResponse:
      type: object
      properties:
        total_chunks:
          type: integer
        total_files:
          type: integer
```
