@echo off
REM FastAPIサーバー起動スクリプト

REM FastAPIサーバー起動
uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload
