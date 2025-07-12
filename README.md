# 🌡️ sensing-py

## 📑 目次

- [📋 概要](#-概要)
    - [主な特徴](#主な特徴)
- [🏗️ システム構成](#️-システム構成)
- [📊 対応センサ](#-対応センサ)
- [🚀 セットアップ](#-セットアップ)
    - [必要な環境](#必要な環境)
    - [1. ハードウェア設定](#1-ハードウェア設定)
    - [2. 設定ファイルの準備](#2-設定ファイルの準備)
- [💻 実行方法](#-実行方法)
    - [Docker を使用する場合（推奨）](#docker-を使用する場合推奨)
    - [uv を使用する場合](#uv-を使用する場合)
    - [コマンドラインオプション](#コマンドラインオプション)
- [🔧 設定](#-設定)
- [☸️ Kubernetes デプロイ](#️-kubernetes-デプロイ)
- [🧪 テスト](#-テスト)
- [📊 CI/CD](#-cicd)
- [📝 ライセンス](#-ライセンス)

## 📋 概要

I2C/SPI/UART で接続されたセンサーで環境計測を行い、結果を Fluentd で送信する Raspberry Pi 向けセンシングアプリケーションです。

### 主な特徴

- 🔌 **マルチインターフェース対応** - I2C/SPI/UART による多様なセンサー接続
- 📡 **Fluentd 連携** - リアルタイムデータ送信とログ集約
- 🐳 **コンテナ対応** - Docker および Kubernetes デプロイメント
- 🔍 **自動センサー検出** - 接続されたセンサーの自動認識
- 💪 **高可用性** - ヘルスチェック機能とグレースフルシャットダウン
- ⚙️ **設定可能** - YAML ベース設定とスキーマ検証

## 🏗️ システム構成

```
センサー群 → sensing-py → Fluentd → データストレージ/処理
```

- **フレームワーク**: Python 3.10+
- **パッケージマネージャ**: uv
- **通信プロトコル**: I2C (smbus2), SPI (spidev), UART
- **データ送信**: Fluentd (fluent-logger)
- **デプロイ**: Docker + Kubernetes

## 📊 対応センサ

| センサー型式 | 種類         | メーカー          | インターフェース |
| ------------ | ------------ | ----------------- | ---------------- |
| SHT-35       | 温湿度センサ | Sensirion         | I2C              |
| SCD4x        | CO2 センサ   | Sensirion         | I2C              |
| APDS-9250    | 周囲光センサ | Broadcom          | I2C              |
| EZO RTD      | 水温センサ   | Atlas Scientific  | I2C              |
| EZO pH       | pH センサ    | Atlas Scientific  | I2C              |
| Grove TDS    | TDS センサ   | Grove             | A/D              |
| FD-Q10C      | 流量センサ   | KEYENCE           | A/D              |
| ADS1015      | A/D 変換器   | Texas Instruments | I2C              |
| RG-15        | 雨量計       | Hydreon           | UART             |
| LPPYRA03     | 日射計       | Delta OHM         | A/D              |
| SM9561       | 照度計       | SONBEST           | UART             |

## 🚀 セットアップ

### 必要な環境

- Raspberry Pi (GPIO 制御が可能なモデル)
- Python 3.10+
- Docker (オプション)

### 1. ハードウェア設定

Raspberry Pi の `/boot/firmware/config.txt` に以下を追加：

```text
dtparam=i2c_arm=on
dtparam=i2c_vc=on
dtparam=spi=on
dtoverlay=disable-bt
```

### 2. 設定ファイルの準備

```bash
cp config.example.yaml config.yaml
# config.yaml を環境に合わせて編集
```

## 💻 実行方法

### Docker を使用する場合（推奨）

```bash
# Dockerイメージのビルド
docker build -t sensing-py .

# コンテナの実行
docker run --rm --privileged \
  -v $(pwd)/config.yaml:/opt/sensing_py/config.yaml \
  sensing-py
```

### uv を使用する場合

```bash
# uv のインストール（未インストールの場合）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 依存関係のインストールと実行
uv sync
uv run python src/app.py
```

### コマンドラインオプション

```bash
# メインアプリケーション
./src/app.py [-c CONFIG_FILE] [-D]

# ヘルスチェック
./src/healthz.py [-c CONFIG_FILE] [-d]
```

オプション：

- `-c CONFIG_FILE`: 設定ファイル指定（デフォルト: `config.yaml`）
- `-D`: デバッグモード
- `-d`: ダミーモード（ヘルスチェック用）

## 🔧 設定

`config.yaml` の設定例：

```yaml
fluentd:
    host: proxy.green-rabbit.net

sensor:
    - name: sm9561
    - name: scd4x
    - name: max31856
    - name: sht35
    - name: apds9250
    - name: veml7700
    - name: veml6075
      bus: vc

sensing:
    interval_sec: 20

liveness:
    file:
        sensing: /dev/shm/healthz
```

設定項目：

- **fluentd.host**: データ送信先 Fluentd ホスト
- **sensor**: 使用するセンサーのリスト
- **sensing.interval_sec**: センシング間隔（最小1秒）
- **liveness.file**: ヘルスチェック用ファイルパス

## 🧪 テスト

```bash
# テストの実行
uv run pytest

# カバレッジ付きテスト
uv run pytest --cov
```

## 📝 ライセンス

このプロジェクトは Apache License Version 2.0 のもとで公開されています。
