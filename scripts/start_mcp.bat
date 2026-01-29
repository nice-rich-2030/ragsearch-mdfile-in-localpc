@echo off
REM MCPサーバー起動スクリプト

REM MCPサーバー起動
python -m src.mcp.server --docs-dir "%DOCS_DIR%" --verbose
