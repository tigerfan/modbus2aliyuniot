# modbus2aliyuniot
组态软件访问modbus服务器以转发监控参数。
本程序作为modbus tcp客户端读取预定义的点表数据，发布到aliyun物联网平台。
监测数据变化时转发或者指定一个周期定时转发。
引用了：
    https://github.com/owagner/modbus2mqtt
    https://github.com/ljean/modbus-tk/
    https://github.com/yansongda/python-aliyun-iot-device
