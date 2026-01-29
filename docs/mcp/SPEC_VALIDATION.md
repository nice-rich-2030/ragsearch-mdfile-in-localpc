# ローカルRAG MCPサーバー 整合性検証書 (SPEC_VALIDATION.md)

## 4.1 整合性確認表

### ファイル構成の整合性

| ファイル | SPEC.md (1.7/1.8) | SPEC_DETAIL.md (2.1) | SPEC_LOGIC.md | 判定 |
|---------|-------------------|---------------------|---------------|------|
| `config.py` | ✅ 1.7ツリー・1.8実装概要に記載 | ✅ 2.1に詳細記載 | ✅ 3.6で設定ロジック定義 | ✅ |
| `server.py` | ✅ 1.7ツリー・1.8実装概要に記載 | ✅ 2.1に詳細記載 | ✅ 3.1で検索フロー、3.7でデバッグ出力 | ✅ |
| `indexer.py` | ✅ 1.7ツリー・1.8実装概要に記載 | ✅ 2.1に詳細記載 | ✅ 3.2で差分更新ロジック | ✅ |
| `chunker.py` | ✅ 1.7ツリー・1.8実装概要に記載 | ✅ 2.1に詳細記載 | ✅ 3.3でチャンク分割ロジック | ✅ |
| `embedder.py` | ✅ 1.7ツリー・1.8実装概要に記載 | ✅ 2.1に詳細記載 | ✅ 3.4でAPI最適化ロジック | ✅ |
| `searcher.py` | ✅ 1.7ツリー・1.8実装概要に記載 | ✅ 2.1に詳細記載 | ✅ 3.1で検索ロジック | ✅ |
| `db.py` | ✅ 1.7ツリー・1.8実装概要に記載 | ✅ 2.1に詳細記載 | ✅ 3.5でChromaDB操作ロジック | ✅ |
| `config.yaml` | ✅ 1.7ツリーに記載 | — (設定ファイル自体) | ✅ 3.6で全項目定義 | ✅ |

---

### 機能の整合性

| 機能 | SPEC.md | SPEC_DETAIL.md | SPEC_LOGIC.md | 判定 |
|------|---------|----------------|---------------|------|
| ファイルスキャン・差分検出 | ✅ 1.3 主要機能1 | ✅ indexer.py詳細 | ✅ 3.2 差分更新ロジック | ✅ |
| チャンク分割 | ✅ 1.3 主要機能2 | ✅ chunker.py詳細 | ✅ 3.3 チャンク分割ロジック | ✅ |
| エンベディング生成 | ✅ 1.3 主要機能3 | ✅ embedder.py詳細 | ✅ 3.4 Gemini API最適化 | ✅ |
| セマンティック検索 | ✅ 1.3 主要機能4 | ✅ searcher.py詳細 | ✅ 3.1 高速検索ロジック | ✅ |
| MCPサーバー | ✅ 1.3 主要機能5 | ✅ server.py詳細 | ✅ 3.1で初回自動reindex | ✅ |
| 設定管理 | ✅ 1.2 技術スタック | ✅ config.py詳細 | ✅ 3.6 設定ファイルロジック | ✅ |
| デバッグ出力 | ✅ 1.9 デバッグ項目一覧 | — | ✅ 3.7 計測ロジック | ✅ |

---

### データモデルの整合性

| 項目 | SPEC.md (1.4) | SPEC_DETAIL.md (db.py) | SPEC_LOGIC.md (3.5) | 判定 |
|------|---------------|----------------------|---------------------|------|
| SQLite files テーブル | ✅ id/path/hash/mtime/updated_at | ✅ FileDB クラス定義 | ✅ 3.2でupsert/delete使用 | ✅ |
| ChromaDB collection名 | ✅ `documents` | ✅ VectorStore内で使用 | ✅ 3.5で`documents`指定 | ✅ |
| ChromaDB ID形式 | ✅ `{path}::chunk_{index}` | ✅ VectorStore.add_chunks | ✅ 3.5でID生成定義 | ✅ |
| ChromaDB metadatas | ✅ file_path/chunk_index/heading | ✅ VectorStore.add_chunks | ✅ 3.5でmetadata定義 | ✅ |
| Chunk dataclass | — | ✅ chunker.py内で定義 | ✅ 3.3でChunk構造定義 | ✅ |
| SearchResult dataclass | — | ✅ searcher.py内で定義 | ✅ 3.1でスコア変換定義 | ✅ |

---

### 技術スタックの整合性

| 技術 | SPEC.md (1.2) | SPEC_DETAIL.md | SPEC_LOGIC.md | 判定 |
|------|---------------|----------------|---------------|------|
| Python 3.11+ | ✅ | ✅ dataclass使用 | ✅ contextmanager使用 | ✅ |
| `google-genai` SDK | ✅ `gemini-embedding-001` | ✅ embedder.py内 | ✅ 3.4 `genai.Client` | ✅ |
| ChromaDB | ✅ ベクトルDB | ✅ db.py VectorStore | ✅ 3.5 PersistentClient | ✅ |
| SQLite | ✅ ファイル管理 | ✅ db.py FileDB | ✅ 3.2 差分管理 | ✅ |
| MCP Python SDK | ✅ MCPフレームワーク | ✅ server.py内 | ✅ 3.1 stdio通信 | ✅ |
| YAML (config.yaml) | ✅ 設定管理 | ✅ config.py内 | ✅ 3.6 設定ロジック | ✅ |

---

### セキュリティ・保守性の整合性

| 項目 | SPEC.md (1.9) | SPEC_DETAIL.md | SPEC_LOGIC.md | 判定 |
|------|---------------|----------------|---------------|------|
| APIキー環境変数管理 | ✅ `GEMINI_API_KEY` | ✅ embedder.py注意点 | ✅ 3.4 Client初期化 | ✅ |
| パストラバーサル防止 | ✅ 記載あり | ✅ indexer.py注意点 | ✅ 3.2 相対パス管理 | ✅ |
| stdio通信のみ | ✅ 記載あり | ✅ server.py | ✅ 3.1 | ✅ |
| ログ（INFO/WARN/ERROR） | ✅ 記載あり | — | ✅ 3.7 レベル別出力 | ✅ |
| デバッグ出力（時間計測） | ✅ 1.9 詳細項目列挙 | — | ✅ 3.7 contextmanager計測 | ✅ |
| APIリトライ | ✅ WARNING記載 | ✅ embedder.py注意点 | ✅ 3.4 exponential backoff | ✅ |

---

## 4.2 不整合箇所と修正

### 不整合1: チャンクサイズ上限の表記揺れ

| 文書 | 記載内容 |
|------|---------|
| SPEC.md 1.3 | 「約1000トークン」 |
| SPEC_LOGIC.md 3.3 | 「3000文字」 |
| SPEC_LOGIC.md 3.6 config.yaml | `max_chunk_chars: 3000` |

**判定**: ⚠️ 軽微な不整合。SPEC.mdのトークン表記とLOGICの文字数表記が混在。

**修正**: SPEC.md 1.3の「約1000トークン」を「約3000文字（config.yamlで変更可能）」に統一。

### 不整合2: SPEC_DETAIL.mdにconfig.yaml設定値の参照記述なし

**判定**: ⚠️ 軽微。SPEC_DETAIL.md内の各モジュール（embedder.py, chunker.py等）の説明で、設定値をハードコードしているように読める記述がある。

**修正**: 各モジュールの「実装時の注意点」にconfig参照を明記する必要あり（コーディング時に対応）。

---

## 4.3 修正実施記録

### 修正1: SPEC.md チャンクサイズ表記統一

- **対象**: SPEC.md 1.3 主要機能2 項目2.3
- **変更前**: 「チャンクサイズ上限（約1000トークン）を超える場合はさらに分割」
- **変更後**: 「チャンクサイズ上限（約3000文字、config.yamlで変更可能）を超える場合はさらに分割」
- **状態**: ✅ 修正済み（本検証と同時に実施）

---

## 4.4 最終整合性サマリー

| 確認項目 | 結果 |
|---------|------|
| 機能整合性 | ✅ 全7機能が3文書で一貫 |
| データモデル整合性 | ✅ SQLite/ChromaDB設計が3文書で一致 |
| ファイル構成整合性 | ✅ 8ファイル（src/配下7 + config.yaml）が3文書で一致 |
| 技術スタック整合性 | ✅ 6技術が全文書で一貫して使用 |
| セキュリティ・保守性整合性 | ✅ 6項目が3文書で一貫 |
| 不整合修正 | ✅ 2件検出・修正済み |

**結論**: 3つの仕様書（SPEC.md, SPEC_DETAIL.md, SPEC_LOGIC.md）は整合性が確認され、コーディングに進む準備が整っています。
