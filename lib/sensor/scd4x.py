#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# SCD4x を使って CO2 濃度を取得するライブラリです．
#
# 作成時に使用したのは，Sensirion の SEK SCD41．
# https://www.sensirion.com/en/environmental-sensors/evaluation-kit-sek-environmental-sensing/evaluation-kit-sek-scd41/
# 明示的に start_periodic_measurement を呼ばなくても済むように少し工夫しています．

import time
import smbus


class SCD4X:
    NAME = "SCD4X"
    DEV_ADDR = 0x62  # 7bit
    RASP_I2C_BUS = 0x1  # Raspberry Pi の I2C のバス番号

    def __init__(self, bus=RASP_I2C_BUS, dev_addr=DEV_ADDR):
        self.bus = bus
        self.dev_addr = dev_addr
        self.i2cbus = smbus.SMBus(bus)
        self.is_init = False

    def ping(self):
        try:
            self.__get_data_ready()

            return True
        except:
            return False

    def __reset(self):
        # sto_periodic_measurement
        self.i2cbus.write_byte_data(self.dev_addr, 0x3F, 0x86)
        time.sleep(0.5)
        # reinit
        self.i2cbus.write_byte_data(self.dev_addr, 0x36, 0x46)
        time.sleep(0.02)

    def __crc(self, msg):
        poly = 0x31
        crc = 0xFF

        for data in bytearray(msg):
            crc ^= data
            for i in range(8):
                if crc & 0x80:
                    crc = (crc << 1) ^ poly
                else:
                    crc <<= 1
            crc &= 0xFF

        return crc

    def __decode_response(self, data):
        resp = []
        for word in zip(*[iter(data)] * 3):
            if self.__crc(word[0:2]) != word[2]:
                raise IOError("CRC unmatch")
            resp.extend(word[0:2])
        return resp

    def __get_data_ready(self):
        # get_data_ready_status
        self.i2cbus.write_byte_data(self.dev_addr, 0xE4, 0xB8)
        data = self.i2cbus.read_i2c_block_data(self.dev_addr, 3)
        resp = self.__decode_response(data)

        return (int.from_bytes(resp[0:2], byteorder="big") & 0x7F) != 0

    def __start_measurement(self):
        # NOTE: まず待ってみて，それでもデータが準備できないようだったら
        # 計測が始まっていないと判断する
        for i in range(10):
            if self.__get_data_ready():
                return
            time.sleep(0.5)

        # start_periodic_measurement
        self.i2cbus.write_byte_data(self.dev_addr, 0x21, 0xB1)

        for i in range(10):
            if self.__get_data_ready():
                return
            time.sleep(0.5)

    def get_value(self):
        self.__start_measurement()

        # read_measurement
        self.i2cbus.write_byte_data(self.dev_addr, 0xEC, 0x05)
        data = self.i2cbus.read_i2c_block_data(self.dev_addr, 0x00, 9)
        resp = self.__decode_response(data)

        co2 = int.from_bytes(resp[0:2], byteorder="big")
        temp = -45 + (175 * int.from_bytes(resp[2:4], byteorder="big")) / float(
            2 ** 16 - 1
        )
        humi = 100 * int.from_bytes(resp[4:6], byteorder="big") / float(2 ** 16 - 1)

        return [co2, round(temp, 4), round(humi, 1)]

    def get_value_map(self):
        value = self.get_value()

        return {"co2": value[0], "temp": value[1], "humi": value[2]}


if __name__ == "__main__":
    # TEST Code
    import os
    import sys
    import pprint

    sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir))

    import sensor.scd4x

    scd4x = sensor.scd4x.SCD4X()

    ping = scd4x.ping()
    print("PING: %s" % ping)

    if ping:
        pprint.pprint(scd4x.get_value_map())
