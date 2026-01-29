#!/bin/bash
# MCPサーバー起動スクリプト

# .envファイルから環境変数を読み込み
if [ -f .env ]; then
  export $(cat .env | grep -v '^#' | xargs)
fi

# MCPサーバー起動
python -m src.mcp.server --docs-dir "$DOCS_DIR" --verbose
