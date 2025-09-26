#!/bin/bash

# 現在のディレクトリを探索対象とする
DIR_PATH="."

# 出力ファイル名
OUTPUT_FILE="code.txt"

# 既存の出力ファイルをクリアする（新しい内容で上書き）
> "$OUTPUT_FILE"

# find コマンドでサブディレクトリを含めた全ての .py ファイルを探索
# -type f はファイルのみを対象とします
# -name "*.py" は .py で終わるファイル名を検索します
# -print0 と while read は、スペースを含むファイル名を正しく処理するために使用します
find "$DIR_PATH" -type f -name "*.py" -print0 | while IFS= read -r -d $'\0' FILE; do
    # ファイルのパス全体をヘッダーとして追加
    echo "====$FILE ====" >> "$OUTPUT_FILE"
    
    # ファイルの内容を追加
    cat "$FILE" >> "$OUTPUT_FILE"
    
    # ファイルとファイルの間を空行で区切る
    echo "" >> "$OUTPUT_FILE"
done

echo "完了: 全ての.pyファイルの内容が $OUTPUT_FILE に出力されました。"