# -*- coding: utf-8 -*-
'''
组态软件访问modbus服务器以转发监控参数。
本程序作为modbus tcp客户端读取预定义的点表数据，发布到aliyun物联网平台。
监测数据变化时转发或者指定一个周期定时转发。
引用了：
    https://github.com/owagner/modbus2mqtt
    https://github.com/ljean/modbus-tk/
    https://github.com/yansongda/python-aliyun-iot-device
by tigerfan
'''

import argparse
import logging
import logging.handlers
import time
import socket
import io
import sys
import csv
import signal
import json
import context
import random

import modbus_tk
import modbus_tk.defines as cst
from modbus_tk import modbus_rtu
from modbus_tk import modbus_tcp
from aliyun_iot_device.mqtt import Client as IOT

def on_connect(client, userdata, flags, rc):
    print('连接阿里云物联网平台')
    client.subscribe(qos=1)

def on_message(client, userdata, msg):
    print('接收消息')
    print(str(msg.payload))

# Custom MQTT message callback
def customCallback(client, userdata, message):
    print("Received a new message: ")
    print(message.payload)
    print("from topic: ")
    print(message.topic)
    print("--------------\n\n")

#阿里云物联网平台设备参数
PRODUCE_KEY = "xxx"
DEVICE_NAME = "xxx"
DEVICE_SECRET = "xxx"

#MODBUS服务器地址端口
MODBUS_HOST = "localhost"
MODBUS_PORT = 502
CONFIG_FILE = "D:\MyCode\modbus2aliyuniot\examples\mqtt\config.csv"
FORCE_TIME = 60        #10分钟

#传参格式定义
loopCount = 0

sendmsg = {}
params = {}
paranum = 0
parakey = []
paraval = []
sendmsg['id'] = ''
sendmsg['version'] = '1.0'
sendmsg['method'] = 'thing.event.property.post'

SendTopic = "/sys/" + PRODUCE_KEY + "/" + DEVICE_NAME + "/thing/event/property/post"

class Register:
    def __init__(self,topic,frequency,slaveid,functioncode,register,size,format):
        self.topic = topic
        self.frequency = int(frequency)
        self.slaveid = int(slaveid)
        self.functioncode = int(functioncode)
        self.register = int(register)
        self.size = int(size)
        self.format = format.split(":",2)
        self.next_due = 0
        self.lastval = None
        self.last = None

    def checkpoll(self):
        if self.next_due < time.time():
            self.poll()
            self.next_due = time.time() + self.frequency

    def poll(self):
        try:
            res = master.execute(self.slaveid,self.functioncode,self.register,self.size,data_format=self.format[0])
            r = res[0] + random.random()
            if self.format[1]:
                r = self.format[1] % r
            #if r != self.lastval or ((time.time() - self.last) > FORCE_TIME):
            self.lastval = r
            parakey.append(self.topic)
            paraval.append(float(self.lastval))
            print(self.topic)
            print(self.lastval)

            self.last = time.time()

        except modbus_tk.modbus.ModbusError as exc:
            logging.error("Error reading "+self.topic+": Slave returned %s - %s", exc, exc.get_exception_code())
        except Exception as exc:
            logging.error("Error reading "+self.topic+": %s", exc)

registers = []

# 读取点表定义
with open(CONFIG_FILE,"r") as csvfile:
    dialect = csv.Sniffer().sniff(csvfile.read(8192))
    csvfile.seek(0)
    defaultrow = {"Size":1,"Format":">H","Frequency":60,"Slave":1,"FunctionCode":4}
    reader = csv.DictReader(csvfile,fieldnames = ["Topic","Register","Size","Format","Frequency","Slave","FunctionCode"],dialect=dialect)
    for row in reader:
        # Skip header row
        if row["Frequency"] == "Frequency":
            continue
        # Comment?
        if row["Topic"][0] == "#":
            continue
        if row["Topic"] == "DEFAULT":
            temp = dict((k,v) for k,v in row.items() if v is not None and v!="")
            defaultrow.update(temp)
            continue
        freq = row["Frequency"]
        if freq is None or freq == "":
            freq = defaultrow["Frequency"]
        slave = row["Slave"]
        if slave is None or slave == "":
            slave = defaultrow["Slave"]
        fc=row["FunctionCode"]
        if fc is None or fc == "":
            fc=defaultrow["FunctionCode"]
        fmt = row["Format"]
        if fmt is None or fmt == "":
            fmt = defaultrow["Format"]
        size = row["Size"]
        if size is None or size == "":
            size = defaultrow["Size"]
        r = Register(row["Topic"],freq,slave,fc,row["Register"],size,fmt)
        registers.append(r)
    paranum = len(registers)
logging.info('Read %u valid register definitions from \"%s\"' %(paranum, CONFIG_FILE))

master = modbus_tcp.TcpMaster(MODBUS_HOST, MODBUS_PORT)
master.set_verbose(True)
master.set_timeout(5.0)

iot = IOT((PRODUCE_KEY, DEVICE_NAME, DEVICE_SECRET))
iot.on_connect = on_connect
iot.on_message = on_message
iot.connect()
iot.loop_start()
    
while True:
    for r in registers:
        r.checkpoll()
        loopCount += 1

        if len(parakey) >= paranum :
            sendmsg.update(params = dict(zip(parakey, paraval)))
            SendJson = json.dumps(sendmsg)
            iot.publish(payload = SendJson, qos = 1, topic = SendTopic)

            del parakey[:]
            del paraval[:]
            print(SendJson)
            print(SendTopic)
            print(time.time())
            print(loopCount)
            loopCount = 0

    #time.sleep(30)
