#!/bin/bash
# FastAPIサーバー起動スクリプト

# .envファイルから環境変数を読み込み
if [ -f .env ]; then
  export $(cat .env | grep -v '^#' | xargs)
fi

# FastAPIサーバー起動
uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload
