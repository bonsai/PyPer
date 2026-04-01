#!/bin/bash
# Phase 1の動作確認用スクリプト

echo "🔍 Project Mirai-Yokai Phase 1 テスト"
echo "====================================="

# 仮想環境の作成（必要な場合）
if [ ! -d "venv" ]; then
    echo "📦 仮想環境を作成中..."
    python3 -m venv venv
fi

# 仮想環境のアクティベート
source venv/bin/activate

# 依存関係のインストール
echo "📦 依存関係をインストール中..."
pip install -q -r requirements.txt

# テスト実行
echo "🚀 Phase 1 実行中..."
python src/main.py

# 結果表示
echo ""
echo "📊 データファイルの状態:"
if [ -f "data/seen_urls.txt" ]; then
    echo "   ✓ seen_urls.txt が作成されました"
    echo "   内容: $(cat data/seen_urls.txt | wc -l) 件のURL"
    head -3 data/seen_urls.txt | while read line; do
        echo "   - $line"
    done
    if [ $(cat data/seen_urls.txt | wc -l) -gt 3 ]; then
        echo "   ..."
    fi
else
    echo "   ✗ seen_urls.txt が見つかりません"
fi

echo "====================================="
echo "✅ Phase 1 テスト完了"

# 仮想環境の終了
deactivate