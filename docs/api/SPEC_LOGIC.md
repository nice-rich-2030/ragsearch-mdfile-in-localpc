# ローカルRAG FastAPI Web API ロジック・アルゴリズム設計書

## 3.1 検索APIロジック

### 3.1.1 リクエストバリデーション

**バリデーションルール**:
```
SearchRequest
├── query: str
│   ├── 必須チェック（422エラー）
│   ├── min_length=1（空文字禁止）
│   └── 文字列型チェック
└── top_k: Optional[int]
    ├── default=5（未指定時）
    ├── ge=1（最小1件）
    └── le=100（最大100件）
```

**Pydanticによる自動バリデーション**:
- リクエストボディをJSONパースし、SearchRequestに変換
- バリデーション失敗時: 422 Unprocessable Entity + 詳細エラーメッセージ

---

### 3.1.2 空インデックス検出・自動reindex

**ロジック**:
```python
if app_state.vector_store.count() == 0:
    # インデックスが空 → 自動構築
    app_state.indexer.update()
```

**目的**:
- ユーザーが初回アクセス時にreindexを明示的に呼び出す必要がない
- MCPサーバーと同じ挙動を維持

**注意点**:
- 初回検索は時間がかかる可能性（ファイルスキャン + Embedding API呼び出し）
- 2回目以降は高速（既存インデックスを使用）

---

### 3.1.3 セマンティック検索実行

**検索フロー**:
```
[クエリ文字列]
    ↓
[Embedder.embed_query(query)]
    │
    ├── task_type: "RETRIEVAL_QUERY"
    ├── Gemini Embedding API呼び出し
    └── 768次元ベクトル生成
    ↓
[VectorStore.query(embedding, top_k)]
    │
    ├── ChromaDB HNSWインデックス検索
    ├── コサイン類似度計算
    └── top_k件の結果取得
    ↓
[SearchResult構築]
    │
    ├── file_path: 元ファイルパス
    ├── heading: Markdown見出し
    ├── content: チャンク内容
    ├── score: 1 - distance（0〜1）
    └── chunk_index: チャンク番号
    ↓
[結果返却]
```

**パフォーマンス目標**:
- 検索時間: < 1秒（10,000チャンク規模）
- Embedding API呼び出し: ~300-500ms
- ChromaDB検索: ~10ms（HNSW O(log N)）

---

### 3.1.4 レスポンス構築

**変換ロジック**:
```python
# Searcher.SearchResult → API SearchResultItem
SearchResultItem(
    file_path=r.file_path,
    heading=r.heading,
    content=r.content,
    score=r.score,  # 0.0〜1.0
    chunk_index=r.chunk_index
)
```

**実行時間計測**:
```python
start_time = time.perf_counter()
# ... 検索処理 ...
elapsed_ms = (time.perf_counter() - start_time) * 1000
```

---

## 3.2 インデックス更新APIロジック

### 3.2.1 差分更新アルゴリズム

**2段階フィルタ**:
```
[ファイルスキャン]
    ↓
[Stage 1: mtime比較（高速）]
    │
    ├── 新規ファイル → new_files
    ├── mtime変更 → 候補リスト
    └── mtime未変更 → unchanged_files
    ↓
[Stage 2: hash計算（候補のみ）]
    │
    ├── hash変更 → updated_files
    └── hash未変更 → unchanged_files
    ↓
[差分リスト完成]
    ├── new_files: 新規追加
    ├── updated_files: 更新
    └── deleted_files: 削除（DBにあるがファイルなし）
```

**差分更新実行**:
```
[削除処理]
    ├── VectorStore.delete_by_file(path)
    └── FileDB.delete_file(path)
    ↓
[新規/更新処理]
    ├── ファイル読み込み
    ├── チャンク分割（chunker）
    ├── バッチEmbedding（100件/リクエスト）
    ├── VectorStore.add_chunks()
    └── FileDB.upsert_file()
    ↓
[サマリー返却]
```

---

### 3.2.2 UpdateSummary構造

**サマリー情報**:
```python
@dataclass
class UpdateSummary:
    added: int          # 新規追加ファイル数
    updated: int        # 更新ファイル数
    deleted: int        # 削除ファイル数
    unchanged: int      # 未変更ファイル数
    total_chunks: int   # 総チャンク数
    api_call_count: int # Embedding API呼び出し回数
```

**パフォーマンス目標**:
- 差分更新: < 3秒/ファイル
- バッチ処理: 最大100チャンク/API呼び出し

---

## 3.3 エラーハンドリング

### 3.3.1 HTTPExceptionパターン

**エラー分類**:
| 状況 | HTTPステータス | 対応 |
|------|---------------|------|
| リクエストバリデーション失敗 | 422 | Pydantic自動処理 |
| 環境変数未設定 | 500 | ValueError → HTTPException |
| Embedding API失敗 | 500 | リトライ後 → HTTPException |
| ChromaDB接続失敗 | 500 | HTTPException |
| ファイル読み込み失敗 | 500 | ログ出力 + スキップ |

**例外処理パターン**:
```python
try:
    results = app_state.searcher.search(request.query, request.top_k)
except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))
```

---

### 3.3.2 リトライロジック（Embedding API）

**Exponential Backoff**:
```
[API呼び出し]
    ↓
[失敗した場合]
    │
    ├── 1回目リトライ: 1秒待機
    ├── 2回目リトライ: 2秒待機
    ├── 3回目リトライ: 4秒待機
    └── 全て失敗: 例外送出
```

**設定（config.yaml）**:
```yaml
retry:
  max_retries: 3
  base_delay: 1.0
  backoff_factor: 2.0
```

---

## 3.4 パフォーマンス最適化

### 3.4.1 AppStateシングルトンパターン

**目的**:
- アプリ起動時に1回だけ初期化
- リクエストごとの初期化オーバーヘッドを排除

**実装**:
```python
# app.py（起動時1回）
app.state.app_state = get_app_state()

# routers/search.py（リクエストごと）
app_state = app_request.app.state.app_state  # 既存インスタンスを参照
```

**MCP版との違い**:
| 項目 | MCP版 | FastAPI版 |
|------|-------|----------|
| 初期化タイミング | リクエストごと | アプリ起動時1回 |
| メモリ使用 | リクエストごとに確保 | 共有 |
| ChromaDB接続 | 毎回接続 | 永続接続 |

---

### 3.4.2 検索時間目標

**目標**: < 1秒（検索完了まで）

**内訳**:
| 処理 | 目標時間 | 実装方式 |
|------|---------|---------|
| Embedding生成 | 300-500ms | Gemini API（RETRIEVAL_QUERY） |
| ChromaDB検索 | 10-50ms | HNSW O(log N) |
| レスポンス構築 | < 10ms | Python辞書構築 |
| ネットワーク | 可変 | ローカルなら数ms |

---

## 3.5 CORS設定

### 3.5.1 開発環境設定

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # 全オリジン許可
    allow_credentials=True,
    allow_methods=["*"],      # 全メソッド許可
    allow_headers=["*"],      # 全ヘッダー許可
)
```

**用途**:
- ローカル開発時のフロントエンド連携
- Swagger UIからのAPI呼び出し

---

### 3.5.2 本番環境設定（推奨）

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://yourdomain.com",
        "https://app.yourdomain.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)
```

**注意点**:
- 本番環境では特定ドメインのみ許可
- 環境変数で設定可能にすることを推奨

---

## 3.6 データ共有ロジック

### 3.6.1 MCPとFastAPIのデータ共有

**共有リソース**:
```
data/
├── files.db     # SQLite（MCPとFastAPIで共有）
└── chroma/      # ChromaDB（MCPとFastAPIで共有）
```

**同時アクセス考慮**:
- SQLite: ファイルロック機構により整合性確保
- ChromaDB: 読み取り専用操作は並行可能

**使用シナリオ**:
```
[MCP] reindex実行 → data/ 更新
    ↓
[FastAPI] 検索実行 → 更新されたインデックスを参照
```

---

### 3.6.2 環境変数による設定

**必須環境変数**:
```env
GEMINI_API_KEY=your_api_key_here
DOCS_DIR=/path/to/documents
```

**オプション環境変数**:
```env
DATA_DIR=/path/to/data  # 未指定時: DOCS_DIR/.rag-index
```

**読み込みロジック**:
```python
docs_dir = Path(os.getenv("DOCS_DIR")).resolve()
data_dir = Path(os.getenv("DATA_DIR")).resolve() if os.getenv("DATA_DIR") else docs_dir / ".rag-index"
```
