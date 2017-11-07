#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json
import websocket
import requests
import logging
from datetime import datetime
from threading import Lock

logging.basicConfig(format="%(asctime)s:%(levelname)s:%(message)s", level=logging.DEBUG)

setting = json.load(open("./setting.json", "r"))
waker_url = "http://{waker_host}:{waker_port}/api/schedules".format(**setting)
zaif_api = setting["zaif_api"]

class ZaifWebsocket:
    def __init__(self):
        websocket.enableTrace(True)
        ws = websocket.WebSocketApp(zaif_api, on_open=self.on_open, on_message=self.on_message, on_error=self.on_error, on_close=self.on_close)
        self.zw = ZaifWatcher(setting["minute_range"])
        self._lock = Lock()

        try:
            ws.run_forever()
        except KeyboardInterrupt:
            ws.close()

    def on_error(self, ws, message):
        logging.error(message)

    def on_close(self, ws):
        logging.info("disconncted from Zaif server.")

    def on_message(self, ws, message):
        self._lock.acquire()
        data = json.loads(message)
        nowtime = datetime.now().replace(second=0, microsecond=0)
        self.zw.update(data["last_price"]["price"], nowtime)
        if self.zw.max()/self.zw.min() > setting["ratio"]:
            params = {
                "sound_id": setting["sound_id"],
                "level": setting["level"],
                "repeat": setting["repeat"]
            }
            requests.post(waker_url, data=json.dumps(params))
        self._lock.release()

    def on_open(self, ws):
        logging.info("connected to Zaif server.")

# minute_range間の値動きを保存しておくやつ
class ZaifWatcher:
    def __init__(self, minute_range):
        self._minute_range = minute_range
        self._last_time = None
        self.prices = []
    
    def update(self, price, time):
        # 初回
        if self._last_time == None:
            self.prices.append({
                "max":price,
                "min":price,
                "open":price,
                "close":price
            })

        # 1分経ったとき
        if self._last_time != None and self._last_time < time:
            self.prices.append({
                "max":price,
                "min":price,
                "open":price,
                "close":price
            })

            # 前回の値を1分前の終値として登録
            self.prices[-2]["close"] = self.last_price
            
            # 保存する分数より大きければ一番古いデータを消す.
            if self._minute_range < len(self.prices):
                self.prices.pop(0)
        
        else:
            self.prices[-1].update({
                "max": max([self.prices[-1]["max"], price]),
                "min": min([self.prices[-1]["min"], price]),
                "close": price
            })

        self._last_time = time
        self.last_price = price
    
    # minute_rangeで指定した分数だけデータを持っているか?
    def is_available(self):
        return self._minute_range == len(self.prices)

    def max(self):
        return max(self.prices, key=lambda x:x["max"])["max"]

    def min(self):
        return min(self.prices, key=lambda x:x["min"])["min"]

def main():
    z = ZaifWebsocket()

if __name__ == "__main__":
    main()
