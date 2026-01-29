# ローカルRAG MCPサーバー ロジック・アルゴリズム詳細設計書 (SPEC_LOGIC.md)

本ドキュメントでは、検索時間の最小化を最優先目標として、各ロジックを設計する。

---

## 3.1 高速セマンティック検索ロジック

### 背景
MCPサーバーはClaude Codeの対話中にリアルタイムで呼び出されるため、検索レスポンスは高速でなければならない。ユーザー体験を損なわないために、検索クエリから結果返却まで1秒以内を目標とする。

### 提案するアルゴリズム

**検索フロー（search呼び出し時）**:

```
search(query, top_k=5)
  1. インデックス存在チェック
     → ChromaDB collection.count() == 0 なら自動 reindex
     （初回のみ遅延あり。2回目以降はスキップ）

  2. クエリエンベディング生成
     → client.models.embed_content(
           model="gemini-embedding-001",
           contents=query,
           config=EmbedContentConfig(
               task_type="RETRIEVAL_QUERY",
               output_dimensionality=768
           )
       )
     ※ task_type="RETRIEVAL_QUERY" で検索用途に最適化

  3. ChromaDB類似検索
     → collection.query(
           query_embeddings=[query_vector],
           n_results=top_k,
           include=["documents", "metadatas", "distances"]
       )
     ※ ChromaDBの内部HNSWインデックスで高速近似近傍探索

  4. 結果整形・返却
     → distances をスコア（1 - distance）に変換
     → SearchResult リストとして返却
```

### 特徴（洗練されたポイント）

1. **HNSWインデックスによるO(log N)検索**: ChromaDBは内部でHNSW（Hierarchical Navigable Small World）アルゴリズムを使用。全チャンクとの総当たり比較（O(N)）ではなく、近似最近傍探索でO(log N)の検索を実現。

2. **次元削減による高速化**: `gemini-embedding-001` はデフォルト3072次元だが、Matryoshka Representation Learning (MRL) により768次元に削減しても品質を維持。次元数を1/4にすることで：
   - メモリ使用量 1/4
   - ベクトル比較演算 1/4
   - ChromaDB格納サイズ 1/4

3. **task_type分離**: ドキュメント埋め込み時は `RETRIEVAL_DOCUMENT`、クエリ時は `RETRIEVAL_QUERY` を指定。Geminiが用途別に最適化したベクトルを生成し、検索精度を向上。

### パフォーマンス目標

| 指標 | 目標値 | 根拠 |
|------|--------|------|
| 検索レスポンス時間 | < 1秒 | Gemini API呼び出し(~500ms) + ChromaDB検索(~10ms) |
| 対応チャンク数 | 10,000件以上 | HNSW で O(log N)、768次元なら十分高速 |
| メモリ使用量 | < 200MB | 10,000チャンク × 768次元 × 4bytes ≈ 30MB |

---

## 3.2 差分インデックス更新ロジック

### 背景
ファイル数が増加すると、全ファイルのエンベディングを毎回再計算するコストが膨大になる。Gemini APIの呼び出し回数とレイテンシを最小化するため、変更のあったファイルのみを処理する。

### 提案するアルゴリズム

```
update()
  1. 現在のファイル一覧を収集
     → _collect_files(docs_dir)
     → {relative_path: actual_mtime} の辞書を構築

  2. SQLiteから既知ファイル一覧を取得
     → file_db.get_all_files()
     → {relative_path: FileRecord(hash, mtime)} の辞書を取得

  3. 差分分類（3つのセット演算）
     current_paths = set(現在のファイル)
     known_paths = set(既知ファイル)

     new_files     = current_paths - known_paths
     deleted_files = known_paths - current_paths
     existing_files = current_paths & known_paths

  4. 既存ファイルの更新判定（2段階フィルタ）
     updated_files = []
     for path in existing_files:
         if current_mtime[path] == known_mtime[path]:
             continue  # mtime同一 → 未変更（高速パス）
         current_hash = _compute_hash(path)
         if current_hash == known_hash[path]:
             continue  # 内容同一 → タイムスタンプだけ変わった
         updated_files.append(path)

  5. 削除処理（高速：API不要）
     for path in deleted_files:
         vector_store.delete_by_file(path)
         file_db.delete_file(path)

  6. 新規・更新ファイル処理
     files_to_process = new_files + updated_files
     for path in files_to_process:
         # 更新ファイルは旧データを先に削除
         if path in updated_files:
             vector_store.delete_by_file(path)

         content = read_file(path)
         chunks = chunk_file(path, content)

         # バッチエンベディング（ファイル単位でまとめて送信）
         texts = [c.content for c in chunks]
         embeddings = embedder.embed_texts(texts)

         # ChromaDBに一括登録
         vector_store.add_chunks(path, chunks, embeddings)

         # SQLite更新
         file_db.upsert_file(path, hash, mtime)

  7. サマリー返却
     → {added, updated, deleted, unchanged, total_chunks}
```

### 特徴（洗練されたポイント）

1. **2段階フィルタ（mtime → hash）**: まずmtimeを比較（O(1)の整数比較）し、変わっていなければハッシュ計算をスキップ。大量の未変更ファイルを高速に除外できる。mtimeが変わった場合のみSHA256を計算し、内容が実際に変更されたか確認する。

2. **ファイル単位バッチエンベディング**: チャンクを1件ずつAPI送信するのではなく、ファイル単位でまとめて `embed_content(contents=[...])` に渡す。API呼び出し回数を大幅に削減。

3. **全チャンク差し替え方式**: ファイル更新時、旧チャンクを全削除→新チャンクを全登録。チャンク単位の差分検出は複雑で、見出し変更などで全チャンクの位置がずれるため、ファイル単位の差し替えが合理的。

### パフォーマンス目標

| 指標 | 目標値 | 根拠 |
|------|--------|------|
| 未変更ファイルのスキップ判定 | < 1ms/ファイル | mtime比較のみ |
| 差分更新（1ファイル追加時） | < 3秒 | ハッシュ計算 + チャンク分割 + API 1回 + ChromaDB書込 |
| フルリインデックス（100ファイル） | < 5分 | バッチ処理 + API呼び出し最適化 |

---

## 3.3 Markdownチャンク分割ロジック

### 背景
チャンクの質が検索精度を直接左右する。Markdownの構造（見出し階層）を活用して意味的にまとまった単位で分割することで、検索結果の有用性を高める。

### 提案するアルゴリズム

```
chunk_markdown(content)
  1. 見出し行を検出（正規表現: ^#{1,3}\s+）
     → 見出し位置のリストを構築

  2. 見出し間のテキストをチャンクとして切り出し
     → 見出し行自体をチャンクの先頭に含める
     → 最初の見出しより前のテキスト（前文）も1チャンクとする

  3. 各チャンクのサイズチェック
     → 3000文字以下 → そのまま採用
     → 3000文字超 → _split_oversized() で再分割

  4. 空チャンク除去
     → strip() 後に空文字列のチャンクはスキップ

  5. Chunkオブジェクト生成
     → chunk_index を0から連番付与
     → heading にその時点の見出しテキストを設定

_split_oversized(text, max_chars=3000)
  1. 文境界で分割を試みる
     → 「。」「.」「\n\n」の位置を検出
     → max_chars 以内で最も後方の文境界で分割
  2. 文境界が見つからない場合
     → max_chars の位置で強制分割
  3. 再帰的に残りのテキストも処理

chunk_text(content)
  → 空行（\n\n）で段落分割
  → 各段落について chunk_markdown と同様のサイズチェック
  → heading は空文字列
```

### 特徴（洗練されたポイント）

1. **見出し階層の保持**: 各チャンクのmetadataに見出し情報を保持。検索結果に見出しが含まれることで、ユーザーが文脈を把握しやすい。

2. **前文の保持**: ファイル冒頭の見出し前テキスト（概要やメタ情報）も独立チャンクとして保持。見出しのないテキストも検索対象に。

3. **文境界分割**: 大きなチャンクの再分割は文の途中ではなく文末（句点や空行）で行い、意味の断絶を防ぐ。

### パフォーマンス目標

| 指標 | 目標値 |
|------|--------|
| チャンクサイズ | 100〜3000文字 |
| 分割処理時間 | < 10ms/ファイル |

---

## 3.4 エンベディング生成ロジック（Gemini API最適化）

### 背景
Gemini API呼び出しは検索時・インデックス構築時の両方で発生する。API呼び出し回数を最小化しつつ、用途に応じた最適なベクトルを生成する。

### 提案するアルゴリズム

```
embed_texts(texts, task_type="RETRIEVAL_DOCUMENT")
  1. バッチ分割
     → texts を最大100件ごとのバッチに分割
     （gemini-embedding-001のバッチ上限）

  2. 各バッチをAPI呼び出し
     → client.models.embed_content(
           model="gemini-embedding-001",
           contents=batch,
           config=types.EmbedContentConfig(
               task_type=task_type,
               output_dimensionality=768
           )
       )

  3. リトライ処理
     → API エラー時: 最大3回リトライ（exponential backoff: 1s, 2s, 4s）
     → レート制限エラー（429）: リトライ間隔を延長

  4. 結果結合
     → 各バッチの result.embeddings を結合
     → [e.values for e in embeddings] でリスト化して返却

embed_query(query)
  → embed_texts([query], task_type="RETRIEVAL_QUERY") を呼び出し
  → 結果の先頭要素を返却
```

### 特徴（洗練されたポイント）

1. **task_type の使い分け**:
   - ドキュメントチャンク → `RETRIEVAL_DOCUMENT`: 文書としての特徴を強調
   - 検索クエリ → `RETRIEVAL_QUERY`: 質問・検索意図を強調
   - 非対称検索（asymmetric retrieval）により、短いクエリでも関連文書を高精度にマッチ

2. **768次元への削減**: MRL学習により、3072→768次元でも検索品質をほぼ維持。ストレージとメモリを75%削減。

3. **バッチ処理**: 100チャンクを1回のAPI呼び出しで処理。10ファイル×10チャンクでもAPI呼び出しは1回で済む。

### パフォーマンス目標

| 指標 | 目標値 |
|------|--------|
| クエリエンベディング生成 | < 500ms（API 1回） |
| バッチエンベディング（100チャンク） | < 2秒（API 1回） |
| API呼び出し回数（100ファイルフルインデックス） | 10回程度 |

---

## 3.5 ChromaDB操作ロジック

### 背景
ChromaDBの最新API（v1.4.0）に準拠し、永続化・追加・削除・検索を正しく実装する。

### 提案するアルゴリズム

```
VectorStore.__init__(persist_dir)
  → client = chromadb.PersistentClient(path=str(persist_dir))
  → collection = client.get_or_create_collection(
        name="documents",
        metadata={"hnsw:space": "cosine"}
    )

add_chunks(file_path, chunks, embeddings)
  → ids = [f"{file_path}::chunk_{c.chunk_index}" for c in chunks]
  → documents = [c.content for c in chunks]
  → metadatas = [
        {"file_path": file_path, "chunk_index": c.chunk_index, "heading": c.heading}
        for c in chunks
    ]
  → collection.add(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas
    )
  ※ upsert ではなく add を使用（事前に delete_by_file 済み）

delete_by_file(file_path)
  → existing = collection.get(where={"file_path": file_path})
  → if existing["ids"]:
        collection.delete(ids=existing["ids"])
  ※ where条件で該当ファイルのチャンクIDを取得し、IDで削除

query(query_embedding, top_k)
  → results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )
  → 結果をSearchResultリストに変換
  → score = 1.0 - distance（cosine距離→類似度変換）
```

### 特徴（洗練されたポイント）

1. **PersistentClient**: `data/chroma/` に自動永続化。プロセス再起動後もインデックスが保持される。

2. **HNSW空間設定**: `metadata={"hnsw:space": "cosine"}` でコサイン類似度を指定。Geminiのエンベディングはコサイン類似度前提で学習されている。

3. **ID設計**: `"{file_path}::chunk_{index}"` 形式で一意性を保証。ファイルパスベースなので、delete_by_fileでのフィルタリングも容易。

---

## 3.6 設定ファイル管理ロジック（config.yaml / config.py）

### 背景
ChromaDBのHNSWパラメータ、エンベディング次元数、チャンクサイズ等のパラメータは、環境やドキュメント特性に応じて調整が必要。開発者がコード変更なしでパラメータを変更できるよう、YAML設定ファイルで外部化する。

### config.yaml 構成

```yaml
# === エンベディング設定 ===
embedding:
  model: "gemini-embedding-001"           # Geminiモデル名
  output_dimensionality: 768              # 出力次元数（768 / 1536 / 3072）
  batch_size: 100                         # 1回のAPI呼び出しあたりの最大テキスト数
  task_type_document: "RETRIEVAL_DOCUMENT" # ドキュメント埋め込み時のtask_type
  task_type_query: "RETRIEVAL_QUERY"       # クエリ埋め込み時のtask_type

# === チャンク分割設定 ===
chunker:
  max_chunk_chars: 3000                   # チャンクサイズ上限（文字数）
  min_chunk_chars: 50                     # これ以下のチャンクは破棄
  heading_levels: [1, 2, 3]              # Markdown分割に使う見出しレベル

# === ChromaDB設定 ===
chromadb:
  collection_name: "documents"            # コレクション名
  hnsw_space: "cosine"                    # 距離関数（cosine / l2 / ip）
  hnsw_construction_ef: 200               # インデックス構築時の探索幅（精度↑ 構築速度↓）
  hnsw_search_ef: 100                     # 検索時の探索幅（精度↑ 検索速度↓）
  hnsw_M: 16                              # HNSWグラフの接続数（精度↑ メモリ↑）

# === 検索設定 ===
search:
  default_top_k: 5                        # デフォルトの返却件数

# === API リトライ設定 ===
retry:
  max_retries: 3                          # 最大リトライ回数
  base_delay: 1.0                         # 初回リトライ待機秒数
  backoff_factor: 2.0                     # 待機時間の倍率

# === ファイルスキャン設定 ===
scanner:
  file_extensions: [".md", ".txt"]        # スキャン対象拡張子
  exclude_dirs: [".rag-index", "data", ".git", "__pycache__", "node_modules"]
```

### 提案するアルゴリズム

```
load_config(config_path: Path | None) -> AppConfig
  1. config_path が指定されていれば読み込み
     → 指定なし: docs_dir/config.yaml → プロジェクトルート/config.yaml の順に探索
  2. YAMLパース → dict取得
  3. デフォルト値とマージ（YAML未指定項目はデフォルトを使用）
  4. AppConfig dataclass に変換して返却

AppConfig（dataclass）:
  embedding: EmbeddingConfig
  chunker: ChunkerConfig
  chromadb: ChromaDBConfig
  search: SearchConfig
  retry: RetryConfig
  scanner: ScannerConfig
```

### 特徴（洗練されたポイント）

1. **コード変更不要のパラメータ調整**: HNSW探索幅（ef）を変更して検索速度 vs 精度のトレードオフを調整可能。次元数を768↔3072で切り替えることも設定だけで可能。
2. **デフォルト値フォールバック**: config.yamlが存在しなくても全項目にデフォルト値があるため動作する。部分的なYAML記述も可能。
3. **ChromaDB HNSWチューニング**: `hnsw_construction_ef`, `hnsw_search_ef`, `hnsw_M` を外部化。大量データ時に検索速度を優先するか精度を優先するかを調整可能。

---

## 3.7 デバッグ出力・時間計測ロジック

### 背景
検索時間の最適化が本プロジェクトの最重要目標であるため、各処理ステップの所要時間を計測し、ボトルネックを特定可能にする。`--verbose` フラグで詳細出力を有効化する。

### 提案するアルゴリズム

```
時間計測ユーティリティ（contextmanager方式）:

@contextmanager
def timer(label: str, logger):
    start = time.perf_counter()
    yield
    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.debug(f"[TIMER] {label}: {elapsed_ms:.1f}ms")

使用例:
  with timer("query_embedding", logger):
      query_vector = embedder.embed_query(query)
```

**search 時のデバッグ出力フロー**:

```
DEBUG [search] query="環境構築の方法", top_k=5
DEBUG [TIMER] query_embedding: 487.3ms
DEBUG [TIMER] chromadb_query: 8.2ms
DEBUG [search] results: 5 chunks returned
DEBUG [search]   [1] score=0.92 file=docs/setup.md heading="## インストール手順"
DEBUG [search]   [2] score=0.85 file=notes/memo.txt heading=""
DEBUG [search]   [3] score=0.78 file=docs/faq.md heading="## 環境設定"
DEBUG [search]   [4] score=0.71 file=docs/setup.md heading="## 前提条件"
DEBUG [search]   [5] score=0.65 file=notes/tips.txt heading=""
DEBUG [TIMER] search_total: 502.1ms
```

**reindex 時のデバッグ出力フロー**:

```
DEBUG [reindex] scanning docs_dir=/path/to/docs
DEBUG [reindex] scan result: 50 files (new=3, updated=1, deleted=0, unchanged=46)
DEBUG [TIMER] file_scan: 12.5ms
DEBUG [reindex] processing: docs/new-feature.md
DEBUG [TIMER]   hash_compute: 0.8ms
DEBUG [TIMER]   chunk_split: 2.1ms (8 chunks, chars=[245, 1200, 890, 320, 1500, 670, 1100, 450])
DEBUG [TIMER]   gemini_api: 1823.4ms (batch_size=8)
DEBUG [TIMER]   chromadb_write: 15.3ms
DEBUG [reindex] processing: docs/updated-guide.md
DEBUG [TIMER]   old_chunks_delete: 3.2ms
DEBUG [TIMER]   hash_compute: 0.5ms
DEBUG [TIMER]   chunk_split: 1.8ms (5 chunks, chars=[300, 980, 1100, 750, 420])
DEBUG [TIMER]   gemini_api: 1205.7ms (batch_size=5)
DEBUG [TIMER]   chromadb_write: 11.8ms
DEBUG [TIMER] reindex_total: 3091.2ms
DEBUG [reindex] summary: added=3, updated=1, deleted=0, unchanged=46, total_chunks=382
```

### 特徴（洗練されたポイント）

1. **contextmanager方式の計測**: `with timer(...)` でコードの可読性を維持したまま任意区間を計測。計測コード自体が処理ロジックを汚さない。
2. **検索時間の内訳可視化**: `query_embedding` と `chromadb_query` を分離計測。ボトルネックがAPI呼び出しか検索エンジンかを即座に判別可能。
3. **チャンク詳細の出力**: 各ファイルのチャンク数と文字数分布を出力。チャンクサイズ設定の妥当性を確認可能。
4. **INFOレベルとの使い分け**: 通常運用（INFO）ではサマリーのみ出力。DEBUGでは全計測値とチャンク詳細を出力。

---

## 洗練度チェックリスト

- [x] **検索高速化**: HNSWインデックス（O(log N)）、768次元削減、ChromaDB内蔵検索
- [x] **API呼び出し最小化**: バッチ処理、差分更新、task_type分離
- [x] **差分更新**: 2段階フィルタ（mtime→hash）、ファイル単位バッチ
- [x] **例外処理**: APIリトライ（exponential backoff）、空インデックス対応
- [x] **パフォーマンス目標**: 検索<1秒、差分更新<3秒/ファイル
- [x] **スケーラビリティ**: 10,000チャンク以上対応、HNSW対数オーダー
- [x] **監査対応ログ**: INFO/WARNING/ERRORレベルでの詳細ログ
- [x] **設定外部化**: config.yamlでChromaDB HNSW/エンベディング次元数/チャンクサイズ等を調整可能
- [x] **デバッグ計測**: contextmanager方式で各処理ステップの所要時間をms単位で計測・出力
