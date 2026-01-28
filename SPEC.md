# ローカルRAG MCPサーバー 仕様書 (SPEC.md)

## 1.1 課題分析・機能提案

### 課題
- ローカルフォルダに蓄積された`.md`/`.txt`ファイル群から、目的の情報を素早く見つけられない
- キーワード検索では意味的に関連する文書を見逃す
- Claude Codeからローカルナレッジベースを直接参照する手段がない

### 解決策
- Gemini Embedding APIを用いたセマンティック検索をMCPサーバーとして提供
- Claude Codeから自然言語クエリでローカル文書を検索可能にする

### 潜在的課題の提案
- ファイル数増加時のエンベディング再計算コスト → **差分更新方式**で解決
- 大きなファイルのチャンク分割 → 適切なチャンキング戦略が必要
- APIキーの安全な管理 → 環境変数による管理

### 主要機能
| 区分 | 機能 |
|------|------|
| 入力 | ローカルフォルダパス、検索クエリ（自然言語） |
| 処理 | ファイルスキャン、差分検出、チャンク分割、エンベディング生成、類似度検索 |
| 出力 | 関連文書のチャンク（ファイル名・行番号付き）、類似度スコア |
| 外部連携 | Gemini Embedding API、Claude Code（MCP経由） |
| メンテナンス | インデックス再構築、キャッシュクリア |

---

## 1.2 技術スタック選定・選定根拠

| 項目 | 選定 | 根拠 |
|------|------|------|
| 言語 | Python 3.11+ | エコシステムの充実、Gemini SDK対応 |
| MCPフレームワーク | `mcp` (Python SDK) | Claude Code公式対応のMCPプロトコル実装 |
| Embedding API | Google Gemini `gemini-embedding-001` | 高品質な多言語埋め込み。`google-genai` SDK使用 |
| ベクトルDB | ChromaDB | 永続化対応のローカルベクトルDB、類似度検索内蔵 |
| ファイル管理 | SQLite | ファイルメタデータ・ハッシュの差分管理用 |
| チャンク分割 | 自前実装（段落ベース） | 外部依存を最小化、Markdown構造を考慮 |
| 設定管理 | YAML (`config.yaml`) | 開発者が各種パラメータを容易に変更可能 |

---

## 1.3 機能詳細化（ブレイクダウン）

### 主要機能1: ファイルスキャン・差分検出
- 1.1 指定フォルダの再帰スキャン（`*.md`, `*.txt`）
- 1.2 ファイルのハッシュ値（SHA256）と更新日時をSQLiteに記録
- 1.3 前回スキャン時との差分検出（新規・更新・削除）

### 主要機能2: チャンク分割
- 2.1 Markdownファイル: 見出し単位で分割（`#`, `##`, `###`）
- 2.2 テキストファイル: 空行区切りの段落単位で分割
- 2.3 チャンクサイズ上限（約3000文字、config.yamlで変更可能）を超える場合はさらに分割

### 主要機能3: エンベディング生成・保存
- 3.1 差分のあるファイルのチャンクのみエンベディングを計算
- 3.2 `google.genai.Client.models.embed_content()` でバッチ生成
- 3.3 エンベディングベクトルをChromaDBに保存
- 3.4 削除ファイルの古いエンベディングを削除

### 主要機能4: セマンティック検索
- 4.1 クエリ文字列をGemini APIでエンベディングに変換
- 4.2 ChromaDBの `collection.query()` で類似度検索
- 4.3 上位k件を返却（ファイルパス・チャンク内容・スコア付き）

### 主要機能5: MCPサーバー
- 5.1 MCPプロトコルによるツール公開（`search`ツール）
- 5.2 インデックス更新ツール（`reindex`ツール）
- 5.3 stdio通信（Claude Codeローカル接続）

---

## 1.4 データモデル・データ構造定義

### SQLite（ファイル管理用）

**files テーブル**
| カラム | 型 | 説明 |
|--------|------|------|
| id | INTEGER PK | 自動採番 |
| path | TEXT UNIQUE | ファイルの相対パス |
| hash | TEXT | SHA256ハッシュ |
| mtime | REAL | 最終更新日時 |
| updated_at | TEXT | レコード更新日時 |

### ChromaDB（ベクトル・チャンク管理用）

**collection: `documents`**
| 項目 | 内容 |
|------|------|
| id | `{relative_path}::chunk_{index}` 形式のユニークID |
| documents | チャンクテキスト本文 |
| embeddings | Gemini APIで生成したベクトル |
| metadatas | `file_path`, `chunk_index`, `heading` を格納 |

---

## 1.5 ユーザー操作シナリオ

### インストール
1. リポジトリをクローンまたはダウンロード
2. `pip install -r requirements.txt` で依存パッケージをインストール
3. 環境変数 `GEMINI_API_KEY` を設定
4. Claude Codeの `.claude.json` または MCPサーバー設定に本サーバーを登録

### 利用
1. Claude Codeで会話中に「このフォルダからXXXに関する情報を検索して」と指示
2. MCPサーバーが `search` ツールを実行 → インデックス未構築なら自動構築
3. 関連チャンクがClaude Codeに返却され、回答に活用される

### メンテナンス
- `reindex` ツールでインデックスを手動再構築可能
- `data/` ディレクトリ削除で完全リセット（SQLite + ChromaDB）

---

## 1.6 UI分析・提案

本プロジェクトはCLI/MCPサーバーのため、GUIは不要。

### MCPツール定義

**search ツール**
```
名前: search
説明: ローカルドキュメントからセマンティック検索を実行
パラメータ:
  - query: string (必須) - 検索クエリ
  - top_k: integer (任意, デフォルト5) - 返却件数
戻り値: 関連チャンクのリスト（ファイルパス、内容、スコア）
```

**reindex ツール**
```
名前: reindex
説明: ドキュメントインデックスを再構築（差分更新）
パラメータ: なし
戻り値: 更新結果サマリー（追加/更新/削除件数）
```

---

## 1.7 フォルダ・ファイル構成

```
rag-tst1/
├── SPEC.md                  # 本仕様書
├── SPEC_DETAIL.md           # 詳細設計書
├── SPEC_LOGIC.md            # ロジック・アルゴリズム設計書
├── SPEC_VALIDATION.md       # 整合性検証書
├── requirements.txt         # Python依存パッケージ
├── config.yaml              # 開発者向け設定ファイル（パラメータ調整用）
├── .env.example             # 環境変数テンプレート（APIキー等）
├── src/
│   ├── __init__.py
│   ├── server.py            # MCPサーバー本体（エントリポイント）
│   ├── config.py            # 設定ファイル読み込み・デフォルト値管理
│   ├── indexer.py           # ファイルスキャン・差分検出・インデックス管理
│   ├── chunker.py           # チャンク分割ロジック
│   ├── embedder.py          # Gemini Embedding API呼び出し
│   ├── searcher.py          # ChromaDB検索ロジック
│   └── db.py                # SQLite（ファイル管理）＋ ChromaDB操作
├── data/                    # 自動生成ディレクトリ
│   ├── files.db             # SQLite（ファイルメタデータ）
│   └── chroma/              # ChromaDB永続化ディレクトリ
└── tests/
    ├── test_indexer.py
    ├── test_chunker.py
    └── test_searcher.py
```

各ファイルは200〜400行程度を想定（800行制約内）。

---

## 1.8 実装概要

| ファイル | 役割 | 主要関数/クラス |
|---------|------|----------------|
| `config.py` | 設定ファイル読み込み、デフォルト値管理 | `load_config()`, `AppConfig` |
| `server.py` | MCPサーバー起動、ツール登録、リクエストハンドリング | `main()`, `handle_search()`, `handle_reindex()` |
| `indexer.py` | ファイル走査、差分検出、インデックス更新のオーケストレーション | `Indexer.scan()`, `Indexer.update()` |
| `chunker.py` | ファイル内容をチャンクに分割 | `chunk_markdown()`, `chunk_text()` |
| `embedder.py` | `google.genai.Client`でエンベディング生成 | `Embedder.embed_texts()`, `Embedder.embed_query()` |
| `searcher.py` | ChromaDBによる類似度検索 | `Searcher.search()` |
| `db.py` | SQLite（ファイル管理）＋ ChromaDB操作 | `FileDB`, `VectorStore` |

---

## 1.9 メンテナンス・セキュリティ

### ログ
- Python標準 `logging` モジュールを使用
- INFO: ファイルスキャン結果、インデックス更新件数
- WARNING: APIエラー時のリトライ
- ERROR: 致命的エラー

### セキュリティ
- `GEMINI_API_KEY` は環境変数で管理（コードにハードコードしない）
- 指定フォルダ外へのパストラバーサルを防止
- MCPサーバーはstdio通信のみ（ネットワーク非公開）

### デバッグ（`--verbose` フラグでDEBUGレベル有効化）

**検索時（search）のデバッグ出力**:
- クエリ文字列
- クエリエンベディング生成時間（ms）
- ChromaDB検索時間（ms）
- 検索トータル時間（ms）
- 返却チャンク数、各チャンクのスコアとファイルパス

**インデックス更新時（reindex）のデバッグ出力**:
- スキャンファイル総数
- 差分分類結果（新規/更新/削除/未変更の件数）
- 各ファイルのハッシュ計算時間（ms）
- 各ファイルのチャンク分割結果（チャンク数、各チャンク文字数）
- Gemini API呼び出し時間（ms）、バッチサイズ
- ChromaDB書き込み時間（ms）
- リインデックストータル時間（ms）

**データ参照**:
- SQLite（ファイル管理）・ChromaDB（ベクトル）ともに直接参照可能
