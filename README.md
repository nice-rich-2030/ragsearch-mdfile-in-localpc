# ローカルRAG MCP & FastAPI

<div align="center">

**Claude CodeからもHTTP APIからもローカル文書を自然言語で検索**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![MCP](https://img.shields.io/badge/MCP-Compatible-purple.svg)](https://modelcontextprotocol.io/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688.svg)](https://fastapi.tiangolo.com/)

Gemini Embedding APIとChromaDBを使用した、高速・高精度なセマンティック検索サーバー

[特徴](#-特徴) • [インストール](#-インストール) • [使い方](#-使い方) • [設定](#-設定)

</div>

---

## 📖 概要

ローカルRAGは、あなたのローカルに蓄積されたMarkdown/テキストファイルを自然言語で検索できるようにするツールです。

**2つのインターフェースを提供:**
- **MCPサーバー**: Claude Codeから直接利用
- **FastAPI Web API**: HTTP経由で任意のアプリケーションから利用

### 💡 解決する課題

#### 課題
- **情報の発見困難**: ローカルフォルダに蓄積された`.md`/`.txt`ファイル群から、目的の情報を素早く見つけられない
- **キーワード検索の限界**: 従来のキーワード検索では、意味的に関連する文書を見逃してしまう
- **Claude Codeとの断絶**: Claude Codeからローカルナレッジベースを直接参照する手段がない

#### 解決策
✅ **セマンティック検索**: Gemini Embedding APIを用いた意味理解による高精度な検索  
✅ **MCP統合**: Claude Codeから自然言語クエリでローカル文書を直接検索可能  
✅ **差分更新**: ファイル数増加時のエンベディング再計算コストを最小化  
✅ **適切なチャンキング**: 大きなファイルも見出し・段落単位で最適に分割  
✅ **セキュアな管理**: APIキーは環境変数で安全に管理

---

## ✨ 特徴

### 🚀 高速検索（目標: <1秒）
- **HNSWインデックス**: O(log N)の近似最近傍探索で10,000件以上のチャンクに対応
- **次元削減**: 768次元エンベディング（MRL活用で75%削減）
- **非対称検索**: task_type分離により短いクエリでも高精度マッチング

### 🔄 差分更新（目標: <3秒/ファイル）
- **2段階フィルタ**: mtime比較（高速）→ hash計算（確実）で未変更ファイルを効率的にスキップ
- **バッチ処理**: 最大100件/リクエストでAPI呼び出しを最小化
- **ファイル単位更新**: 変更のあったファイルのみを再インデックス化

### 🎯 高精度
- **Gemini Embedding API**: 高品質な多言語埋め込み（日本語・英語対応）
- **見出し保持**: Markdownの構造を活用した意味的なチャンク分割
- **スコアリング**: コサイン類似度による関連度の可視化

### 💾 永続化
- **ChromaDB**: ベクトルインデックスの永続化
- **SQLite**: ファイルメタデータの管理
- **自動復元**: プロセス再起動後もインデックスを保持

### 🔧 設定可能
- **config.yaml**: 全パラメータを外部ファイルで管理
- **チューニング**: HNSW探索幅、チャンクサイズ、次元数などを調整可能
- **デバッグモード**: 詳細ログと時間計測（ms単位）

---

## 🏗️ アーキテクチャ

```
┌──────────────┐
│ Claude Code  │  自然言語クエリ
│  (MCP Client)│  「環境構築の方法を教えて」
└──────┬───────┘
       │ MCP Protocol (stdio)
┌──────▼───────┐
│  MCPサーバー  │  search / reindex ツール
└──┬───────┬───┘
   │       │
   ▼       ▼
┌────────┐ ┌─────────┐
│Searcher│ │ Indexer  │  差分検出・更新
│        │ │          │
│Gemini  │ │Chunker   │  見出し・段落分割
│API     │ │Embedder  │  バッチエンベディング
└──┬─────┘ └─────┬───┘
   │             │
   ▼             ▼
┌─────────────────┐
│  VectorStore    │  HNSW検索（O(log N)）
│  (ChromaDB)     │  768次元ベクトル
└─────────────────┘
```

---

## 📦 インストール

### 前提条件
- Python 3.10以上
- Gemini API Key（[取得はこちら](https://aistudio.google.com/app/apikey)）

### 1. リポジトリのクローン

```bash
git clone https://github.com/nice-rich-2030/ragsearch-mdfile-in-localpc.git
cd ragsearch-mdfile-in-localpc
```

### 2. 依存パッケージのインストール

```bash
# 本番用パッケージのみ
pip install -e .

# 開発用パッケージも含める（テスト実行など）
pip install -e ".[dev]"
```

### 3. 環境変数の設定

```bash
# .envファイルを作成
cp .env.example .env

# .envファイルを編集してAPIキーを設定
# GEMINI_API_KEY=your_api_key_here
```

---

## 🚀 使い方

### 方法1: FastAPI Web API（HTTP経由）

#### 1. 環境変数設定

`.env`ファイルを作成または編集:

```env
GEMINI_API_KEY=your_api_key_here
DOCS_DIR=/path/to/your/documents
DATA_DIR=/path/to/data  # Optional
```

#### 2. FastAPIサーバー起動

```bash
# Windows
scripts\start_api.bat

# Linux/Mac
./scripts/start_api.sh

# または直接Uvicornで起動
uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload
```

#### 3. Swagger UIでテスト

ブラウザで http://localhost:8000/docs を開く

#### 4. curlで検索実行

```bash
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Pythonのインストール方法", "top_k": 3}'
```

#### 5. インデックス更新

```bash
curl -X POST http://localhost:8000/api/v1/index/rebuild \
  -H "Content-Type: application/json" \
  -d '{}'
```

---

### 方法2: MCPサーバー（Claude Codeから）

#### 動作テスト１　スタンドアロン実行

下記では、MCPサーバーを起動を確認：
　MCPサーバープロセスが起動
　stdio（標準入出力）経由で通信待機状態になる
　直接ユーザーが対話することはできない、データベースもファイルを作成するが中身は空。

```bash
# 基本的な使い方
python -m src.mcp.server --docs-dir /path/to/documents

# デバッグモード（詳細ログ・時間計測）
python -m src.mcp.server --docs-dir /path/to/documents --verbose

# データディレクトリを指定
python -m src.mcp.server --docs-dir /path/to/documents --data-dir /path/to/data
```

### 動作テスト２　PythonからMCPサーバーをテスト

MCPサーバーをプログラム的に呼び出して動作確認できます。

#### テストクライアントの実行

```bash
# テストクライアント実行
python test_mcp_client.py
```

#### 期待される出力

```
======================================================================
MCP Server Test Client
======================================================================
テストドキュメント: d:\rag-tst1\test-docs

MCPサーバーに接続中...
✓ サーバー接続成功

利用可能なツール:
  - search: Search local documents using semantic search
  - reindex: Rebuild document index (differential update)

----------------------------------------------------------------------
Test 1: reindex ツール
----------------------------------------------------------------------
結果:
Index update complete:
  Added: 3
  Updated: 0
  Deleted: 0
  Unchanged: 0
  Total chunks: 15

----------------------------------------------------------------------
Test 2: search ツール
----------------------------------------------------------------------

検索クエリ: 'Pythonのインストール方法'
--------------------------------------------------
Found 3 results for query: 'Pythonのインストール方法'
Total chunks in index: 15

--- Result 1 (score: 0.923) ---
File: test-docs\python-install.md
Heading: ## Windowsでのインストール

### 1. インストーラーのダウンロード

1. [Python公式サイト](https://www.python.org/downloads/)にアクセス
2. 最新版のPython 3.11以上をダウンロード
...

======================================================================
テスト完了!
======================================================================
```

#### テストドキュメント

`test-docs/` フォルダには以下のサンプルドキュメントが含まれています:
- `python-install.md` - Pythonインストール手順
- `error-handling.md` - エラーハンドリングのベストプラクティス
- `testing-guide.txt` - テストの書き方

---



### Claude Codeとの連携

#### 設定ファイルの編集

`.claude.json`または`claude_desktop_config.json`に以下を追加:

```json
{
  "mcpServers": {
    "local-rag": {
      "command": "python",
      "args": [
        "-m", "src.mcp.server",
        "--docs-dir", "/absolute/path/to/your/documents"
      ],
      "cwd": "/absolute/path/to/rag-tst1",
      "env": {
        "GEMINI_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

#### Claude Codeでの使用例

```
ユーザー: 「このプロジェクトのREADMEから、インストール手順を教えて」

Claude: [searchツールを使用]
→ 関連する文書チャンクを取得
→ インストール手順を回答

ユーザー: 「Pythonのエラーハンドリングのベストプラクティスは?」

Claude: [searchツールを使用]
→ ローカルドキュメントから関連情報を検索
→ ベストプラクティスを説明
```


## 🛠️ 利用可能なツール

### `search` - セマンティック検索

ローカルドキュメントから自然言語クエリで検索します。

**パラメータ:**
| 名前 | 型 | 必須 | 説明 |
|------|-----|------|------|
| `query` | string | ✅ | 検索クエリ（自然言語） |
| `top_k` | integer | ❌ | 返却件数（デフォルト: 5） |

**レスポンス:**
- ファイルパス
- 見出し（Markdownの場合）
- チャンク内容
- 類似度スコア（0〜1）
- チャンクインデックス

### `reindex` - インデックス再構築

ドキュメントインデックスを差分更新します。

**パラメータ:** なし

**レスポンス:**
- 追加ファイル数
- 更新ファイル数
- 削除ファイル数
- 未変更ファイル数
- 総チャンク数

---

## ⚙️ 設定

`config.yaml`で各種パラメータを調整できます:

```yaml
# エンベディング設定
embedding:
  model: "gemini-embedding-001"
  output_dimensionality: 768      # 768 / 1536 / 3072
  batch_size: 100
  task_type_document: "RETRIEVAL_DOCUMENT"
  task_type_query: "RETRIEVAL_QUERY"

# チャンク分割設定
chunker:
  max_chunk_chars: 3000           # チャンクサイズ上限
  min_chunk_chars: 50             # 最小サイズ
  heading_levels: [1, 2, 3]      # Markdown見出しレベル

# ChromaDB設定
chromadb:
  collection_name: "documents"
  hnsw_space: "cosine"            # 距離関数
  hnsw_search_ef: 100             # 検索精度（↑精度 ↓速度）
  hnsw_M: 16                      # グラフ接続数

# 検索設定
search:
  default_top_k: 5

# リトライ設定
retry:
  max_retries: 3
  base_delay: 1.0
  backoff_factor: 2.0

# スキャン設定
scanner:
  file_extensions: [".md", ".txt"]
  exclude_dirs: [".rag-index", "data", ".git", "__pycache__"]
```

---

## 📊 パフォーマンス

| 指標 | 目標値 | 実装方式 |
|------|--------|----------|
| 検索レスポンス時間 | **< 1秒** | HNSW O(log N)、768次元 |
| 差分更新（1ファイル） | **< 3秒** | 2段階フィルタ、バッチAPI |
| 対応チャンク数 | **10,000件以上** | HNSW対数オーダー |
| メモリ使用量 | **< 200MB** | 10,000チャンク時 |

---

## 🔧 トラブルシューティング

### APIキーエラー

```
ValueError: GEMINI_API_KEY or GOOGLE_API_KEY environment variable must be set
```

**解決策**: 環境変数`GEMINI_API_KEY`を設定してください。

### インデックスが空

初回検索時、インデックスが空の場合は**自動的にインデックス構築**が実行されます。

手動で構築する場合:
```bash
# Claude Codeから
reindexツールを実行

# MCPサーバーから
python -m src.mcp.server --docs-dir /path/to/docs --verbose
# → 初回起動時に自動構築

# FastAPI経由
curl -X POST http://localhost:8000/api/v1/index/rebuild -H "Content-Type: application/json" -d '{}'
```

### 検索結果が0件

1. ドキュメントディレクトリに`.md`または`.txt`ファイルが存在するか確認
2. `--verbose`フラグでログを確認
3. `config.yaml`の`scanner.file_extensions`と`scanner.exclude_dirs`を確認

### パフォーマンスが遅い

`config.yaml`で調整:
```yaml
chromadb:
  hnsw_search_ef: 50  # 100 → 50（速度優先）
embedding:
  output_dimensionality: 768  # 3072 → 768（推奨）
```

---

## 📂 プロジェクト構造

```
rag-tst1/
├── docs/
│   ├── mcp/                # MCP向け仕様書
│   └── api/                # FastAPI向け仕様書
├── src/
│   ├── shared/             # 共有ビジネスロジック
│   ├── mcp/                # MCPサーバー
│   └── api/                # FastAPI Web API
├── tests/
│   ├── shared/             # 共有モジュールテスト
│   ├── mcp/                # MCPテスト
│   ├── api/                # FastAPIテスト
│   └── debug/              # デバッグツール
├── scripts/                # 起動スクリプト
└── config.yaml             # 共通設定
```

---

## 📚 ドキュメント

### MCP向け
- **[docs/mcp/SPEC.md](docs/mcp/SPEC.md)**: 仕様書
- **[docs/mcp/SPEC_DETAIL.md](docs/mcp/SPEC_DETAIL.md)**: 詳細設計書
- **[docs/mcp/SPEC_LOGIC.md](docs/mcp/SPEC_LOGIC.md)**: ロジック設計書
- **[docs/mcp/SPEC_VALIDATION.md](docs/mcp/SPEC_VALIDATION.md)**: 整合性検証書

### FastAPI向け
- **[docs/api/SPEC.md](docs/api/SPEC.md)**: 仕様書
- **[docs/api/SPEC_DETAIL.md](docs/api/SPEC_DETAIL.md)**: 詳細設計書
- **[docs/api/SPEC_LOGIC.md](docs/api/SPEC_LOGIC.md)**: ロジック設計書
- **[docs/api/SPEC_VALIDATION.md](docs/api/SPEC_VALIDATION.md)**: 整合性検証書

---

## 🧪 開発者向け

### テスト実行

```bash
pytest tests/
```

### デバッグモード

```bash
# MCPサーバー
python -m src.mcp.server --docs-dir /path/to/documents --verbose

# FastAPIサーバー（自動リロード有効）
uvicorn src.api.app:app --reload
```

詳細なタイミング情報とデバッグログが出力されます:

```
[TIMER] query_embedding: 487.3ms
[TIMER] chromadb_query: 8.2ms
[TIMER] search_total: 502.1ms
```

### デバッグツール

インデックスの状態確認やチャンク分割のデバッグに使用できるツールを提供しています。

#### 1. ChromaDBダンプツール

インデックスに登録されている全ドキュメントを表示します。

```bash
python tests/debug/dump_chromadb.py ./test-docs
```

**出力例:**
```
File: error-handling.md (14 chunks)
--- Chunk 1/14 ---
  heading: # エラーハンドリングのベストプラクティス1
  content: (49 chars)
  [FOUND] Contains search text!
```

#### 2. チャンク分割デバッグツール

ファイルがどのようにチャンクに分割されるかを確認します。

```bash
python tests/debug/debug_chunker.py ./test-docs/error-handling.md
```

**出力例:**
```
Generated 14 chunks:
Chunk 0 (index=0):
  Heading: # エラーハンドリングのベストプラクティス1
  Length: 49 chars
  Coverage: 100.0%
```

#### 3. 詳細チャンク分割デバッグツール

チャンク分割の詳細なステップを確認します。どのセクションが`min_chunk_chars`でフィルタリングされたかを表示します。

```bash
python tests/debug/debug_chunker_verbose.py ./test-docs/error-handling.md
```

**出力例:**
```
Section 1: heading='## 基本原則'
  Content length: 49 chars
  [PASS] Size check OK
```

#### 4. test-docs再インデックスツール

test-docsフォルダの再インデックスを実行します。設定変更後の動作確認に便利です。

```bash
python tests/debug/reindex_test_docs.py
```

**出力例:**
```
================================================================================
Reindex Test Docs
================================================================================
Docs dir: D:\src\rag-tst1\test-docs
Data dir: D:\src\rag-tst1\test-docs\.rag-index

Config loaded:
  min_chunk_chars: 10
  max_chunk_chars: 3000

Running indexer...

================================================================================
Reindex complete!
================================================================================
Added: 4
Updated: 0
Deleted: 0
Unchanged: 0
Total chunks: 75
API calls: 4
```

**デバッグツール一覧:**
- **[tests/debug/dump_chromadb.py](tests/debug/dump_chromadb.py)**: ChromaDB内の全ドキュメント表示
- **[tests/debug/debug_chunker.py](tests/debug/debug_chunker.py)**: チャンク分割の確認
- **[tests/debug/debug_chunker_verbose.py](tests/debug/debug_chunker_verbose.py)**: チャンク分割の詳細分析
- **[tests/debug/reindex_test_docs.py](tests/debug/reindex_test_docs.py)**: test-docs再インデックス

### データのリセット

```bash
# インデックスデータを削除
rm -rf /path/to/documents/.rag-index

# または
rm -rf /path/to/custom/data-dir
```

次回起動時に再構築されます。

---

## 🤝 コントリビューション

Issue・Pull Requestを歓迎します！

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 ライセンス

MIT License - 詳細は[LICENSE](LICENSE)を参照してください。

---

## 🙏 謝辞

- [Google Gemini API](https://ai.google.dev/) - 高品質な埋め込みAPI
- [ChromaDB](https://www.trychroma.com/) - オープンソースベクトルDB
- [Model Context Protocol](https://modelcontextprotocol.io/) - Claude Code統合

---

<div align="center">

**Made with ❤️ by Antigravity AI**

⭐ このプロジェクトが役に立ったら、スターをお願いします！

</div>
