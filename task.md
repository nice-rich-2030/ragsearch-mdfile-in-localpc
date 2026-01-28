# ローカルRAG MCPサーバー 実装タスクリスト

## プロジェクト概要
Gemini Embedding APIとChromaDBを使用したローカル文書検索MCPサーバーの実装

## フェーズ1: プロジェクト基盤構築 ✅

### 1.1 プロジェクト構造作成
- [x] `src/` ディレクトリ作成
- [x] `data/` ディレクトリ作成（.gitignore追加）
- [x] `tests/` ディレクトリ作成
- [x] `requirements.txt` 作成
- [x] `.env.example` 作成
- [x] `config.yaml` 作成

### 1.2 依存パッケージ定義
- [x] `requirements.txt` に必要なパッケージを記載
  - `google-genai` (Gemini SDK)
  - `chromadb` (ベクトルDB)
  - `mcp` (MCPフレームワーク)
  - `pyyaml` (設定ファイル)
  - その他必要なパッケージ

---

## フェーズ2: コアモジュール実装 ✅

### 2.1 設定管理モジュール (`src/config.py`)
- [x] `EmbeddingConfig` dataclass 定義
- [x] `ChunkerConfig` dataclass 定義
- [x] `ChromaDBConfig` dataclass 定義
- [x] `SearchConfig` dataclass 定義
- [x] `RetryConfig` dataclass 定義
- [x] `ScannerConfig` dataclass 定義
- [x] `AppConfig` dataclass 定義
- [x] `load_config()` 関数実装
  - [x] YAML探索ロジック（引数 → docs_dir → プロジェクトルート）
  - [x] デフォルト値マージ
  - [x] dataclass変換

### 2.2 データベース層 (`src/db.py`)
- [x] `FileDB` クラス実装（SQLite）
  - [x] `__init__()`: DB接続・テーブル作成
  - [x] `get_all_files()`: 全ファイルレコード取得
  - [x] `upsert_file()`: ファイルレコード追加・更新
  - [x] `delete_file()`: ファイルレコード削除
- [x] `VectorStore` クラス実装（ChromaDB）
  - [x] `__init__()`: PersistentClient初期化・collection取得
  - [x] `add_chunks()`: チャンク＋ベクトル追加
  - [x] `delete_by_file()`: ファイル単位削除
  - [x] `query()`: 類似検索
  - [x] `count()`: 格納チャンク数取得

### 2.3 チャンク分割モジュール (`src/chunker.py`)
- [x] `Chunk` dataclass 定義
- [x] `chunk_file()` 関数実装
  - [x] 拡張子判定（.md / .txt）
  - [x] 適切な分割関数へ振り分け
- [x] `chunk_markdown()` 関数実装
  - [x] 見出し行検出（正規表現）
  - [x] 見出し間テキスト切り出し
  - [x] サイズチェック・再分割
- [x] `chunk_text()` 関数実装
  - [x] 空行区切り段落分割
  - [x] サイズチェック・再分割
- [x] `_split_oversized()` 関数実装
  - [x] 文境界検出（。、.、\n\n）
  - [x] 再帰的分割

### 2.4 エンベディング生成モジュール (`src/embedder.py`)
- [x] `Embedder` クラス実装
  - [x] `__init__()`: `genai.Client()` 初期化
  - [x] `embed_texts()`: バッチエンベディング生成
    - [x] バッチ分割（最大100件）
    - [x] API呼び出し（task_type指定）
    - [x] リトライ処理（exponential backoff）
    - [x] 結果結合
  - [x] `embed_query()`: クエリ用エンベディング

### 2.5 検索モジュール (`src/searcher.py`)
- [x] `SearchResult` dataclass 定義
- [x] `Searcher` クラス実装
  - [x] `__init__()`: 依存注入（embedder, vector_store）
  - [x] `search()`: セマンティック検索
    - [x] クエリエンベディング生成
    - [x] ChromaDB検索
    - [x] スコア変換（distance → similarity）
    - [x] 結果整形

### 2.6 インデックス管理モジュール (`src/indexer.py`)
- [x] `ScanResult` dataclass 定義
- [x] `UpdateSummary` dataclass 定義
- [x] `Indexer` クラス実装
  - [x] `__init__()`: 依存注入
  - [x] `_collect_files()`: ファイル再帰収集
  - [x] `_compute_hash()`: SHA256計算
  - [x] `scan()`: 差分分類
    - [x] 現在のファイル一覧取得
    - [x] SQLiteから既知ファイル取得
    - [x] 新規/更新/削除/未変更の分類
    - [x] 2段階フィルタ（mtime → hash）
  - [x] `update()`: 差分更新実行
    - [x] 削除処理
    - [x] 新規・更新処理（チャンク分割→エンベディング→保存）
    - [x] サマリー返却

---

## フェーズ3: MCPサーバー実装 ✅

### 3.1 サーバー本体 (`src/server.py`)
- [x] `__init__.py` 作成（src/配下）
- [x] コマンドライン引数パーサー実装
  - [x] `--docs-dir` (必須)
  - [x] `--data-dir` (オプション)
  - [x] `--verbose` (オプション)
- [x] ロギング設定
  - [x] INFO/WARNING/ERROR レベル
  - [x] `--verbose` でDEBUG有効化
- [x] 時間計測ユーティリティ実装
  - [x] `timer()` contextmanager
- [x] `create_server()` 関数実装
  - [x] MCP Server インスタンス生成
  - [x] ツール登録（search, reindex）
- [x] `handle_search()` 関数実装
  - [x] インデックス存在チェック
  - [x] 初回自動reindex
  - [x] 検索実行
  - [x] デバッグ出力（時間計測）
- [x] `handle_reindex()` 関数実装
  - [x] インデックス更新実行
  - [x] デバッグ出力（時間計測）
- [x] `main()` 関数実装
  - [x] 設定読み込み
  - [x] DB初期化
  - [x] 各モジュール初期化
  - [x] サーバー起動

---

## フェーズ4: テスト・検証 🚧

### 4.1 ユニットテスト作成
- [x] `tests/test_chunker.py`
  - [x] Markdown分割テスト
  - [x] テキスト分割テスト
  - [x] サイズ超過再分割テスト
- [ ] `tests/test_indexer.py`
  - [ ] ファイルスキャンテスト
  - [ ] 差分検出テスト
- [ ] `tests/test_searcher.py`
  - [ ] 検索結果整形テスト

### 4.2 統合テスト
- [ ] テスト用ドキュメントフォルダ作成
- [ ] 初回インデックス構築テスト
- [ ] 検索機能テスト
- [ ] 差分更新テスト（ファイル追加・更新・削除）

### 4.3 パフォーマンス検証
- [ ] 検索レスポンス時間計測（目標: <1秒）
- [ ] 差分更新時間計測（目標: <3秒/ファイル）
- [ ] メモリ使用量確認（目標: <200MB for 10,000チャンク）

---

## フェーズ5: ドキュメント・デプロイ準備 🚧

### 5.1 ドキュメント整備
- [x] README.md 作成
  - [x] プロジェクト概要
  - [x] インストール手順
  - [x] 使用方法
  - [x] Claude Code設定例
- [x] .gitignore 作成
  - [x] `data/`
  - [x] `.env`
  - [x] `__pycache__/`
  - [x] `.rag-index/`

### 5.2 Claude Code連携設定
- [ ] `.claude.json` 設定例作成
- [ ] 実際のClaude Codeでの動作確認

---

## 実装優先順位

### 高優先度（Phase 1-2）
1. プロジェクト構造・依存関係
2. config.py（全モジュールの基盤）
3. db.py（データ永続化層）
4. chunker.py（データ前処理）
5. embedder.py（外部API連携）

### 中優先度（Phase 3）
6. searcher.py（検索機能）
7. indexer.py（インデックス管理）
8. server.py（MCPサーバー）

### 低優先度（Phase 4-5）
9. テスト作成
10. ドキュメント整備

---

## 進捗管理

- ✅ 完了
- 🚧 作業中
- ⏸️ 保留
- ❌ ブロック

## メモ・課題

### 技術的注意点
- Gemini API Key は環境変数 `GEMINI_API_KEY` から取得
- ChromaDB は `data/chroma/` に永続化
- SQLite は `data/files.db` に保存
- 検索時間最小化が最優先目標（<1秒）

### 依存関係
- embedder.py → config.py
- searcher.py → embedder.py, db.py
- indexer.py → chunker.py, embedder.py, db.py
- server.py → 全モジュール
