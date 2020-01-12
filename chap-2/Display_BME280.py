# -*- coding: utf-8 -*-

import smbus2
import bme280

# バスの番号とアドレスを指定
bus_number = 1
i2c_address = 0x76

bus = smbus2.SMBus(bus_number)

# バスとI2Cアドレスで初期化
calibration_params = bme280.load_calibration_params(bus, i2c_address)

# BME280からデータを取得
data = bme280.sample(bus, i2c_address, calibration_params)

# データを出力
print(f"温度：{data.temperature:0.2f}度")
print(f"湿度：{data.humidity:0.2f}％")
print(f"気圧：{data.pressure:0.2f}hPa")
