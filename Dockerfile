# Python 3.12-slimをベースイメージとして使用
FROM python:3.12-slim

# OSのパッケージを更新し、必要なライブラリをインストール
# libzbar0: pyzbarの依存ライブラリ
# fonts-ipaexfont-gothic: fpdf2で日本語フォントを使用するためのパッケージ
# build-essential: pipが一部のパッケージをビルドするために必要
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    build-essential \
    tzdata \
    locales \
    libzbar0 \
    fonts-ipaexfont-gothic \
 && ln -snf /usr/share/zoneinfo/Asia/Tokyo /etc/localtime \
 && echo "Asia/Tokyo" > /etc/timezone \
 && dpkg-reconfigure -f noninteractive tzdata \
 && sed -i 's/# \(ja_JP.UTF-8 UTF-8\)/\1/' /etc/locale.gen \
 && locale-gen ja_JP.UTF-8 \
 && update-locale LANG=ja_JP.UTF-8 \
 && rm -rf /var/lib/apt/lists/*

# 日本語ロケールとタイムゾーンを設定
ENV LANG=ja_JP.UTF-8 \
    LC_ALL=ja_JP.UTF-8 \
    TZ=Asia/Tokyo \
    PYTHONUNBUFFERED=1

# コンテナ内の作業ディレクトリを設定
WORKDIR /app

# requirements.txtをコンテナにコピー
COPY requirements.txt .

# Pythonライブラリをインストール
# --no-cache-dirオプションでキャッシュを無効にし、イメージサイズを小さくする
RUN pip install --no-cache-dir -r requirements.txt

# プロジェクトの全ファイルをコンテナにコピー
COPY . .

# コンテナ起動時に実行するコマンド
# Streamlitは使っていないため、Pythonスクリプトを直接実行する
# src/QR/main.py に実行ファイルがあると仮定
CMD ["python3", "main.py"]
