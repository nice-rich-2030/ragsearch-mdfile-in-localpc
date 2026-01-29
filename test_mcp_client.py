#!/usr/bin/env python3
"""
MCP Test Client

MCPサーバーをプログラム的に呼び出して動作確認するテストクライアント。

使い方:
    python test_mcp_client.py

環境変数:
    GEMINI_API_KEY: Gemini APIキー（必須）
"""

import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# MCP SDKのインポート
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    print("エラー: mcp パッケージがインストールされていません")
    print("インストール: pip install mcp")
    sys.exit(1)


async def test_mcp_server():
    """MCPサーバーのテスト"""
    
    # テスト用ドキュメントディレクトリ
    test_docs_dir = Path(__file__).parent / "test-docs"
    
    if not test_docs_dir.exists():
        print(f"エラー: テストドキュメントディレクトリが見つかりません: {test_docs_dir}")
        print("test-docs/ フォルダを作成してください")
        sys.exit(1)
    
    print("=" * 70)
    print("MCP Server Test Client")
    print("=" * 70)
    print(f"テストドキュメント: {test_docs_dir}")
    print()
    
    # サーバーパラメータ設定
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "src.mcp.server", "--docs-dir", str(test_docs_dir), "--verbose"],
        env={
            **os.environ,
            "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY", "")
        }
    )
    
    try:
        # MCPサーバーに接続
        print("MCPサーバーに接続中...")
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # 初期化
                await session.initialize()
                print("✓ サーバー接続成功\n")
                
                # ツール一覧取得
                print("利用可能なツール:")
                tools = await session.list_tools()
                for tool in tools.tools:
                    print(f"  - {tool.name}: {tool.description}")
                print()
                
                # Test 1: reindex ツール呼び出し
                print("-" * 70)
                print("Test 1: reindex ツール")
                print("-" * 70)
                print("インデックスを構築中... (初回は数分かかる場合があります)")
                print("詳細ログ: rag_server.log を確認してください")

                result = await session.call_tool("reindex", {})
                print("\n結果:")
                for content in result.content:
                    if hasattr(content, 'text'):
                        print(content.text)
                print()
                
                # Test 2: search ツール呼び出し
                print("-" * 70)
                print("Test 2: search ツール")
                print("-" * 70)
                
                test_queries = [
                    "Pythonのインストール方法",
                    "エラーハンドリング",
                    "テストの書き方"
                ]
                
                for query in test_queries:
                    print(f"\n検索クエリ: '{query}'")
                    print("-" * 50)
                    
                    result = await session.call_tool("search", {
                        "query": query,
                        "top_k": 3
                    })
                    
                    for content in result.content:
                        if hasattr(content, 'text'):
                            # 結果を整形して表示
                            lines = content.text.split('\n')
                            for line in lines[:20]:  # 最初の20行のみ表示
                                print(line)
                            if len(lines) > 20:
                                print("... (省略)")
                    print()
                
                print("=" * 70)
                print("テスト完了!")
                print("=" * 70)
    
    except FileNotFoundError:
        print("\nエラー: Pythonまたはサーバースクリプトが見つかりません")
        print("カレントディレクトリを確認してください")
        sys.exit(1)
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """メイン処理"""
    # APIキー確認
    if not os.getenv('GEMINI_API_KEY'):
        print("エラー: GEMINI_API_KEY環境変数を設定してください")
        print("\n設定方法:")
        print("  Windows: set GEMINI_API_KEY=your_api_key_here")
        print("  Linux/Mac: export GEMINI_API_KEY=your_api_key_here")
        sys.exit(1)
    
    # 非同期実行
    asyncio.run(test_mcp_server())


if __name__ == '__main__':
    main()
