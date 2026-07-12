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
- 💾 **ディスクスプール** - Fluentd 断でもデータを失わない退避・再送機構
- 🐳 **コンテナ対応** - Docker および Kubernetes デプロイメント
- 🔍 **自動センサー検出** - 接続されたセンサーの自動認識と復帰 (Slack 通知付き)
- 💪 **高可用性** - ヘルスチェック機能とグレースフルシャットダウン
- ⚙️ **設定可能** - YAML ベース設定とスキーマ検証 (`--check-config` で事前検証可能)

## 🏗️ システム構成

```
センサー群 → sensing-py → Fluentd → データストレージ/処理
```

- **フレームワーク**: Python 3.11+
- **パッケージマネージャ**: uv
- **通信プロトコル**: I2C (smbus2), SPI (spidev), UART
- **データ送信**: Fluentd (fluent-logger)
- **デプロイ**: Docker + Kubernetes

## 📊 対応センサ

| センサー型式 | 種類           | メーカー          | インターフェース |
| ------------ | -------------- | ----------------- | ---------------- |
| SHT-35       | 温湿度センサ   | Sensirion         | I2C              |
| SCD4x        | CO2 センサ     | Sensirion         | I2C              |
| APDS-9250    | 周囲光センサ   | Broadcom          | I2C              |
| VEML7700     | 照度センサ     | Vishay            | I2C              |
| VEML6075     | 紫外線センサ   | Vishay            | I2C              |
| MAX31856     | 熱電対温度計   | Analog Devices    | SPI              |
| EZO RTD      | 水温センサ     | Atlas Scientific  | I2C              |
| EZO pH       | pH センサ      | Atlas Scientific  | I2C              |
| EZO DO       | 溶存酸素センサ | Atlas Scientific  | I2C              |
| Grove TDS    | TDS センサ     | Grove             | A/D (I2C)        |
| FD-Q10C      | 流量センサ     | KEYENCE           | IO-Link          |
| ADS1015/1115 | A/D 変換器     | Texas Instruments | I2C              |
| RG-15        | 雨量計         | Hydreon           | UART             |
| LPPYRA03     | 日射計         | Delta OHM         | A/D (I2C)        |
| SM9561       | 照度計         | SONBEST           | RS-485 (I2C)     |
| EchonetEnergy| スマートメータ | -                 | UART (Wi-SUN)    |

## 🚀 セットアップ

### 必要な環境

- Raspberry Pi (GPIO 制御が可能なモデル)
- Python 3.11+
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

# 設定内容の検証 (スキーマ + ドライバ名)
uv run sensing --check-config
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
uv run sensing
```

### コマンドラインオプション

```bash
# メインアプリケーション (常駐)
uv run sensing [-c CONFIG_FILE] [-D]

# 接続センサーの一覧と応答確認 (設置時の診断用)
uv run sensing --list

# 1 周期だけ計測して表示 (Fluentd へは送信しない)
uv run sensing --once

# 設定ファイルの検証
uv run sensing --check-config

# ヘルスチェック
uv run sensing-healthz [-c CONFIG_FILE] [-D]
```

オプション：

- `-c CONFIG_FILE`: 設定ファイル指定（デフォルト: `config.yaml`）
- `-D`: デバッグモード

## 🔧 設定

`config.yaml` の設定例（全体は [config.example.yaml](config.example.yaml) を参照）：

```yaml
fluentd:
    host: proxy.green-rabbit.net
    spool_file: data/spool.jsonl # Fluentd 断の際の退避先 (省略時は無効)

sensor:
    - name: sm9561
      field_prefix: outdoor_ # キー衝突回避用のプレフィックス
    - name: scd4x
      rename: # キー単位のリネームも可能
          temp: co2_temp
          humi: co2_humi
    - name: sht35
    - name: veml6075
      i2c_bus: VC # ARM (デフォルト) / VC

sensing:
    interval_sec: 20

liveness:
    file:
        sensing: /dev/shm/healthz
```

設定項目：

- **fluentd.host**: データ送信先 Fluentd ホスト（`port` / `tag` / `data_label` も指定可能）
- **fluentd.spool_file**: 送信失敗時にレコードを退避する JSON Lines ファイル（復旧時に自動再送）
- **sensor**: 使用するセンサーのリスト
    - `i2c_bus`: `ARM`（デフォルト）または `VC`
    - `dev_addr`: I2C デバイスアドレス
    - `field_prefix` / `rename`: 同種センサー併用時のキー衝突回避
    - `required`: `true` にすると起動時に応答がない場合エラー終了
- **sensing.interval_sec**: センシング間隔（最小1秒）
- **liveness.file**: ヘルスチェック用ファイルパス
- **slack**: エラー通知（`error`）と復帰通知（`info`、省略可）

計測データ (`<tag>.<data_label>`) とは別に、周期ごとの成否・所要時間・無効化中センサーなどのメタデータが `<tag>.meta` に送信されます。ダッシュボード側で「欠測」と「0 値」を区別できます。

## ☸️ Kubernetes デプロイ

[kubernetes/sensing.example.yaml](kubernetes/sensing.example.yaml) にマニフェスト例があります。
`sensing-healthz` を liveness probe として使うことで、センシングが止まった場合に自動再起動されます。
Docker 単体の場合も `HEALTHCHECK` が定義済みです。

## 🧪 テスト

ハードウェアなしで実行できるユニットテストを同梱しています（I2C/SPI はフェイクに差し替え）。

```bash
# テストの実行
uv run pytest tests/unit

# カバレッジレポートは tests/evidence/coverage に生成されます
```

## 📊 CI/CD

GitHub Actions ([.github/workflows/test.yaml](.github/workflows/test.yaml)) で push ごとに
ユニットテストと `--check-config` による設定検証を実行します。

## 📝 ライセンス

このプロジェクトは Apache License Version 2.0 のもとで公開されています。
