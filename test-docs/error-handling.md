# エラーハンドリングのベストプラクティス

## 基本原則

Pythonでのエラーハンドリングは、プログラムの堅牢性を高める重要な要素です。

## try-except の基本

### 基本的な使い方

```python
try:
    # エラーが発生する可能性のあるコード
    result = 10 / 0
except ZeroDivisionError:
    # エラー処理
    print("ゼロ除算エラー")
```

### 複数の例外をキャッチ

```python
try:
    # 処理
    value = int(input("数値を入力: "))
    result = 100 / value
except ValueError:
    print("数値ではありません")
except ZeroDivisionError:
    print("ゼロで割ることはできません")
```

## ベストプラクティス

### 1. 具体的な例外をキャッチする

❌ **悪い例:**
```python
try:
    # 処理
    do_something()
except Exception:  # 広すぎる
    pass
```

✅ **良い例:**
```python
try:
    # 処理
    do_something()
except FileNotFoundError:
    print("ファイルが見つかりません")
except PermissionError:
    print("権限がありません")
```

### 2. エラーメッセージを記録する

```python
import logging

try:
    # 処理
    process_data()
except Exception as e:
    logging.error(f"処理中にエラーが発生: {e}", exc_info=True)
    raise
```

### 3. finally で後処理

```python
file = None
try:
    file = open("data.txt", "r")
    data = file.read()
except FileNotFoundError:
    print("ファイルが見つかりません")
finally:
    if file:
        file.close()
```

### 4. コンテキストマネージャーを使用

```python
# with文を使うと自動的にクローズされる
try:
    with open("data.txt", "r") as file:
        data = file.read()
except FileNotFoundError:
    print("ファイルが見つかりません")
```

## カスタム例外

### 独自の例外クラス

```python
class ValidationError(Exception):
    """バリデーションエラー"""
    pass

def validate_age(age):
    if age < 0:
        raise ValidationError("年齢は0以上である必要があります")
    if age > 150:
        raise ValidationError("年齢が不正です")
    return True

try:
    validate_age(-5)
except ValidationError as e:
    print(f"バリデーションエラー: {e}")
```

## エラーの再送出

```python
def process_file(filename):
    try:
        with open(filename) as f:
            return f.read()
    except FileNotFoundError:
        logging.error(f"ファイルが見つかりません: {filename}")
        raise  # エラーを再送出
```

## まとめ

- 具体的な例外をキャッチする
- エラーメッセージをログに記録する
- `finally`や`with`で確実にリソースを解放する
- 必要に応じてカスタム例外を定義する
- エラーを握りつぶさない
