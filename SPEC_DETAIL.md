# ローカルRAG MCPサーバー 詳細設計書 (SPEC_DETAIL.md)

## 2.1 ファイルごとの実装概要

---

### config.py（設定ファイル読み込み・デフォルト値管理）

- **役割**: `config.yaml` を読み込み、全モジュールで参照する設定値を `AppConfig` dataclass として提供する
- **処理フロー**:
  ```
  load_config(config_path)
    → config.yaml 探索（引数 → docs_dir → プロジェクトルート）
    → YAML読み込み → デフォルト値とマージ
    → AppConfig dataclass に変換して返却
  ```
- **主要な関数/メソッド**:
  | 関数名 | 引数 | 戻り値 | 説明 |
  |--------|------|--------|------|
  | `load_config(config_path)` | config_path: Path or None | AppConfig | 設定ファイル読み込み＋デフォルトマージ |
- **データ型**:
  ```
  @dataclass
  class EmbeddingConfig:
      model: str = "gemini-embedding-001"
      output_dimensionality: int = 768
      batch_size: int = 100
      task_type_document: str = "RETRIEVAL_DOCUMENT"
      task_type_query: str = "RETRIEVAL_QUERY"

  @dataclass
  class ChunkerConfig:
      max_chunk_chars: int = 3000
      min_chunk_chars: int = 50
      heading_levels: list[int] = field(default_factory=lambda: [1, 2, 3])

  @dataclass
  class ChromaDBConfig:
      collection_name: str = "documents"
      hnsw_space: str = "cosine"
      hnsw_construction_ef: int = 200
      hnsw_search_ef: int = 100
      hnsw_M: int = 16

  @dataclass
  class SearchConfig:
      default_top_k: int = 5

  @dataclass
  class RetryConfig:
      max_retries: int = 3
      base_delay: float = 1.0
      backoff_factor: float = 2.0

  @dataclass
  class ScannerConfig:
      file_extensions: list[str] = field(default_factory=lambda: [".md", ".txt"])
      exclude_dirs: list[str] = field(default_factory=lambda: [".rag-index", "data", ".git", "__pycache__", "node_modules"])

  @dataclass
  class AppConfig:
      embedding: EmbeddingConfig
      chunker: ChunkerConfig
      chromadb: ChromaDBConfig
      search: SearchConfig
      retry: RetryConfig
      scanner: ScannerConfig
  ```
- **他ファイルとの連携**:
  - `server.py` → 起動時に `load_config()` を呼び出し、各モジュールに注入
  - 全モジュール → `AppConfig` の該当セクションを参照
- **実装時の注意点**:
  - config.yaml が存在しない場合でも全デフォルト値で動作すること
  - YAML の部分記述を許容（未指定キーはデフォルト値）

---

### server.py（MCPサーバー本体・エントリポイント）

- **役割**: MCPプロトコルでツールを公開し、Claude Codeからのリクエストを処理する
- **処理フロー**:
  ```
  起動 → 設定読み込み（対象フォルダパス、データディレクトリ）
       → MCP Server初期化
       → ツール登録（search, reindex）
       → stdio通信でリクエスト待機
       → リクエスト受信 → 対応ハンドラ呼び出し → レスポンス返却
  ```
- **主要な関数/メソッド**:
  | 関数名 | 引数 | 戻り値 | 説明 |
  |--------|------|--------|------|
  | `main()` | なし | なし | エントリポイント。引数解析・サーバー起動 |
  | `handle_search(query, top_k)` | query: str, top_k: int | list[dict] | 検索リクエスト処理。必要時に自動reindex |
  | `handle_reindex()` | なし | dict | インデックス差分更新を実行、結果サマリー返却 |
  | `create_server(docs_dir, data_dir)` | docs_dir: str, data_dir: str | Server | MCPサーバーインスタンス生成・ツール登録 |
- **他ファイルとの連携**:
  - `indexer.py` → `handle_reindex()` から `Indexer.update()` を呼び出し
  - `searcher.py` → `handle_search()` から `Searcher.search()` を呼び出し
  - `db.py` → 初期化時に `FileDB`, `VectorStore` を生成して各モジュールに注入
- **実装時の注意点**:
  - コマンドライン引数で `--docs-dir`（対象フォルダ）を必須とする
  - `--data-dir` はオプション（デフォルト: `対象フォルダ/.rag-index/`）
  - 初回 `search` 時にインデックスが空なら自動で `reindex` を実行

---

### indexer.py（ファイルスキャン・差分検出・インデックス更新）

- **役割**: 対象フォルダを走査し、変更のあったファイルだけを検出してインデックスを差分更新する
- **処理フロー**:
  ```
  scan()
    → 対象フォルダを再帰走査（*.md, *.txt）
    → 各ファイルのSHA256ハッシュを計算
    → SQLiteの既存レコードと比較
    → 分類: 新規 / 更新 / 削除 / 未変更

  update()
    → scan()で差分取得
    → 新規・更新ファイル: chunker→embedder→VectorStoreに保存
    → 削除ファイル: VectorStore・SQLiteから削除
    → SQLiteのファイルレコードを更新
    → サマリー返却（added, updated, deleted, unchanged件数）
  ```
- **主要な関数/メソッド**:
  | 関数名 | 引数 | 戻り値 | 説明 |
  |--------|------|--------|------|
  | `Indexer.__init__(docs_dir, file_db, vector_store, embedder)` | 各依存 | なし | 依存注入 |
  | `Indexer.scan()` | なし | ScanResult | 差分分類結果を返す |
  | `Indexer.update()` | なし | UpdateSummary | 差分更新を実行 |
  | `_compute_hash(path)` | path: Path | str | ファイルSHA256計算 |
  | `_collect_files(docs_dir)` | docs_dir: Path | list[Path] | *.md/*.txt再帰収集 |
- **他ファイルとの連携**:
  - `db.py (FileDB)` → ファイルメタデータの読み書き
  - `db.py (VectorStore)` → チャンク・ベクトルの追加・削除
  - `chunker.py` → ファイル内容のチャンク分割
  - `embedder.py` → チャンクのエンベディング生成
- **実装時の注意点**:
  - ファイルパスは対象フォルダからの相対パスで管理
  - `data/` ディレクトリ自体や `.rag-index/` はスキャン対象から除外
  - 更新ファイルは旧チャンクを全削除→新チャンクを再登録（部分更新は複雑すぎる）

---

### chunker.py（チャンク分割ロジック）

- **役割**: ファイル内容を検索に適したチャンクに分割する
- **処理フロー**:
  ```
  chunk_file(path, content)
    → 拡張子判定
    → .md → chunk_markdown(content)
    → .txt → chunk_text(content)
    → 各チャンクにメタデータ付与（heading, chunk_index）
  ```
- **主要な関数/メソッド**:
  | 関数名 | 引数 | 戻り値 | 説明 |
  |--------|------|--------|------|
  | `chunk_file(path, content)` | path: Path, content: str | list[Chunk] | 拡張子に応じた分割 |
  | `chunk_markdown(content)` | content: str | list[Chunk] | 見出し単位で分割 |
  | `chunk_text(content)` | content: str | list[Chunk] | 空行区切りで段落分割 |
  | `_split_oversized(text, max_chars)` | text: str, max_chars: int | list[str] | 大きすぎるチャンクを再分割 |
- **データ型**:
  ```
  @dataclass
  class Chunk:
      content: str          # チャンクテキスト
      chunk_index: int      # ファイル内順序
      heading: str = ""     # 所属見出し（mdのみ）
  ```
- **他ファイルとの連携**:
  - `indexer.py` から呼び出される（入力: ファイルパス＋内容、出力: Chunkリスト）
- **実装時の注意点**:
  - `chunk_markdown`: 見出し行（`# `, `## `, `### `）を分割ポイントとする。見出し自体はチャンク先頭に含める
  - チャンクサイズ上限: 約3000文字。超えた場合は文境界（`。`や`.`の後）で再分割
  - 空チャンク（空白のみ）はスキップ

---

### embedder.py（Gemini Embedding API呼び出し）

- **役割**: テキストをGemini APIでベクトル化する
- **処理フロー**:
  ```
  embed_texts(texts)
    → テキストリストをバッチ分割（API制限考慮）
    → client.models.embed_content(model="gemini-embedding-001", contents=batch)
    → 結果のembeddingsを結合して返却

  embed_query(query)
    → 単一テキストをembed_texts()で処理
  ```
- **主要な関数/メソッド**:
  | 関数名 | 引数 | 戻り値 | 説明 |
  |--------|------|--------|------|
  | `Embedder.__init__()` | なし | なし | `genai.Client()` 初期化 |
  | `Embedder.embed_texts(texts)` | texts: list[str] | list[list[float]] | バッチエンベディング生成 |
  | `Embedder.embed_query(query)` | query: str | list[float] | クエリ用エンベディング |
- **他ファイルとの連携**:
  - `indexer.py` → チャンクテキストのバッチエンベディング
  - `searcher.py` → クエリのエンベディング
- **実装時の注意点**:
  - `GEMINI_API_KEY` は環境変数 or `GOOGLE_API_KEY` から取得（`google-genai` SDKのデフォルト）
  - バッチサイズ: 最大100テキスト/リクエスト（API制限に合わせる）
  - API呼び出しエラー時はリトライ（最大3回、exponential backoff）

---

### searcher.py（ChromaDB検索ロジック）

- **役割**: クエリに類似するチャンクをChromaDBから検索して返す
- **処理フロー**:
  ```
  search(query, top_k)
    → embedder.embed_query(query) でクエリベクトル生成
    → vector_store.query(query_embedding, top_k) でChromaDB検索
    → 結果を整形して返却
  ```
- **主要な関数/メソッド**:
  | 関数名 | 引数 | 戻り値 | 説明 |
  |--------|------|--------|------|
  | `Searcher.__init__(embedder, vector_store)` | 依存注入 | なし | 初期化 |
  | `Searcher.search(query, top_k=5)` | query: str, top_k: int | list[SearchResult] | 類似チャンク検索 |
- **データ型**:
  ```
  @dataclass
  class SearchResult:
      file_path: str       # ファイルの相対パス
      content: str         # チャンク内容
      heading: str         # 所属見出し
      score: float         # 類似度スコア（0〜1、高いほど類似）
      chunk_index: int     # ファイル内順序
  ```
- **他ファイルとの連携**:
  - `embedder.py` → クエリのベクトル化
  - `db.py (VectorStore)` → ChromaDBへのクエリ実行
- **実装時の注意点**:
  - ChromaDBはデフォルトでコサイン類似度を使用（設定不要）
  - インデックスが空の場合は空リストを返す（エラーにしない）

---

### db.py（SQLite＋ChromaDB操作）

- **役割**: データ永続化層。ファイル管理（SQLite）とベクトル管理（ChromaDB）を統合
- **処理フロー**:
  ```
  FileDB: SQLiteでファイルメタデータ（パス、ハッシュ、更新日時）を管理
  VectorStore: ChromaDBでチャンクテキスト＋エンベディングを管理
  ```
- **主要な関数/メソッド**:

  **FileDB クラス（SQLite）**:
  | 関数名 | 引数 | 戻り値 | 説明 |
  |--------|------|--------|------|
  | `__init__(db_path)` | db_path: Path | なし | DB接続・テーブル作成 |
  | `get_all_files()` | なし | dict[str, FileRecord] | 全ファイルレコード取得 |
  | `upsert_file(path, hash, mtime)` | 各値 | なし | ファイルレコード追加・更新 |
  | `delete_file(path)` | path: str | なし | ファイルレコード削除 |

  **VectorStore クラス（ChromaDB）**:
  | 関数名 | 引数 | 戻り値 | 説明 |
  |--------|------|--------|------|
  | `__init__(persist_dir)` | persist_dir: Path | なし | ChromaDB初期化・collection取得 |
  | `add_chunks(file_path, chunks, embeddings)` | 各値 | なし | チャンク＋ベクトルを追加 |
  | `delete_by_file(file_path)` | file_path: str | なし | 指定ファイルの全チャンク削除 |
  | `query(query_embedding, top_k)` | embedding: list[float], top_k: int | QueryResult | 類似検索 |
  | `count()` | なし | int | 格納チャンク数 |
- **他ファイルとの連携**:
  - `indexer.py` → ファイル管理＋ベクトル追加/削除
  - `searcher.py` → ベクトル検索
  - `server.py` → 初期化時にインスタンス生成
- **実装時の注意点**:
  - ChromaDB collection名: `"documents"`（固定）
  - ChromaDBのID形式: `"{relative_path}::chunk_{index}"`
  - `delete_by_file` は `where={"file_path": path}` でフィルタして一括削除
  - SQLiteは `data/files.db`、ChromaDBは `data/chroma/` に永続化

---

## 2.2 ソフトウェア画面構成の概要

本プロジェクトはMCPサーバー（CLI）のため、GUI画面はない。
Claude Codeとの対話インターフェースはMCPプロトコルで自動処理される。

### MCPツール応答フォーマット

**search ツール応答例**:
```json
{
  "results": [
    {
      "file_path": "docs/setup.md",
      "heading": "## インストール手順",
      "content": "Python 3.11以上をインストールし...",
      "score": 0.92,
      "chunk_index": 2
    },
    {
      "file_path": "notes/memo.txt",
      "heading": "",
      "content": "環境構築の際には...",
      "score": 0.85,
      "chunk_index": 0
    }
  ],
  "total_chunks": 150,
  "query": "環境構築の方法"
}
```

**reindex ツール応答例**:
```json
{
  "added": 3,
  "updated": 1,
  "deleted": 0,
  "unchanged": 45,
  "total_chunks": 150
}
```

### コマンドライン起動

```
python -m src.server --docs-dir /path/to/documents [--data-dir /path/to/data] [--verbose]
```

### Claude Code MCP設定例（.claude.json）

```json
{
  "mcpServers": {
    "local-rag": {
      "command": "python",
      "args": ["-m", "src.server", "--docs-dir", "/path/to/documents"],
      "cwd": "/path/to/rag-tst1"
    }
  }
}
```

---

## 2.3 モジュール連携図

```
┌──────────────┐
│ Claude Code  │
│  (MCP Client)│
└──────┬───────┘
       │ stdio (MCP Protocol)
┌──────▼───────┐
│  server.py   │  ← エントリポイント
│  (MCP Server)│
└──┬───────┬───┘
   │       │
   ▼       ▼
┌──────┐ ┌────────┐
│search│ │reindex │
└──┬───┘ └───┬────┘
   │         │
   ▼         ▼
┌────────┐ ┌─────────┐
│searcher│ │ indexer  │
│  .py   │ │  .py    │
└──┬─────┘ └┬──┬──┬──┘
   │        │  │  │
   │        │  │  ▼
   │        │  │ ┌────────┐
   │        │  │ │chunker │
   │        │  │ │  .py   │
   │        │  │ └────────┘
   │        │  ▼
   │        │ ┌─────────┐
   ▼        ▼ │embedder │
┌─────────┐  │  .py    │
│  db.py   │  └─────────┘
│ FileDB   │
│VectorStore│
└──┬────┬──┘
   │    │
   ▼    ▼
SQLite ChromaDB
```
