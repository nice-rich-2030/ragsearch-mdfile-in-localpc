# Pythonインストールガイド

## 概要

このドキュメントでは、Pythonのインストール方法について説明します。

## Windowsでのインストール

### 1. インストーラーのダウンロード

1. [Python公式サイト](https://www.python.org/downloads/)にアクセス
2. 最新版のPython 3.11以上をダウンロード
3. インストーラーを実行

### 2. インストール手順

1. **"Add Python to PATH"にチェック**を入れる（重要！）
2. "Install Now"をクリック
3. インストール完了を待つ

### 3. インストール確認

コマンドプロンプトで以下を実行:

```bash
python --version
```

`Python 3.11.x`のように表示されればOK。

## Linuxでのインストール

### Ubuntu/Debian

```bash
sudo apt update
sudo apt install python3.11 python3-pip
```

### CentOS/RHEL

```bash
sudo yum install python3.11
```

## macOSでのインストール

### Homebrewを使用

```bash
brew install python@3.11
```

## 仮想環境の作成

プロジェクトごとに仮想環境を作成することを推奨します:

```bash
# 仮想環境作成
python -m venv venv

# 仮想環境有効化（Windows）
venv\Scripts\activate

# 仮想環境有効化（Linux/Mac）
source venv/bin/activate
```

## パッケージ管理

### pipのアップグレード

```bash
python -m pip install --upgrade pip
```

### パッケージのインストール

```bash
pip install package-name
```

## トラブルシューティング

### PATHが通っていない

Windowsの場合、環境変数を手動で設定:
1. システムのプロパティ → 環境変数
2. Path変数に`C:\Python311`と`C:\Python311\Scripts`を追加

### 複数バージョンの管理

`pyenv`を使用することを推奨:

```bash
# pyenvのインストール（Linux/Mac）
curl https://pyenv.run | bash

# Pythonバージョンのインストール
pyenv install 3.11.0
pyenv global 3.11.0
```
