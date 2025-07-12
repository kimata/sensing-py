# 環境センシングアプリ

## 概要

I2C/SPI/UART で接続されたセンサーで計測を行い，結果を Fluentd で送信するアプリです．

## 対応センサ

| 種類           | センサー型式                 | センサメーカ      |
| -------------- | ---------------------------- | ----------------- |
| 温湿度センサ   | SHT-35                       | Sensirion         |
| CO2 センサ     | SCD4x                        | Sensirion         |
| 周囲光センサ   | APDS-9250                    | Broadcom          |
| UV光センサ     | VEML6075                     | Vishay            |
| 照度センサ     | VEML7700                     | Vishay            |
| 水温 センサ    | EZO RTD Temperature Circuit  | Atlas Scientific  |
| 溶存酸素センサ | EZO Dissolved Oxygen Circuit | Atlas Scientific  |
| PH センサ      | EZO pH Circuit               | Atlas Scientific  |
| TDS センサ     | Grove - TDS Sensor           | Grove             |
| 流量センサ     | FD-Q10C                      | KEYENCE           |
| A/D 変換器     | ADS1015                      | Texas Instruments |
| 熱電対アンプ   | MAX31856                     | Analog Devices    |
| 雨量計         | RG-15                        | Hydreon           |
| 日射計         | LPPYRA03                     | Delta OHM         |
| 照度計         | SM9561                       | SONBEST           |

## 設定

Raspberry Pi の場合， `/boot/firmware/config.txt` に以下の設定を行っておきます．

```text
dtparam=i2c_arm=on
dtparam=i2c_vc=on
dtparam=spi=on
dtoverlay=disable-bt
dtparam=spi=on
```
