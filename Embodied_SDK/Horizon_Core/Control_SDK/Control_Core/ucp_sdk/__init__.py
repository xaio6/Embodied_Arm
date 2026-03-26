#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Motor Control SDK - 基于 UCP (Universal Command Protocol) 的电机控制库

主要功能：
- UCP 客户端：与 OmniCAN 固件通信
- 数据解析：标准化 + 原生数据解析
- 常量定义：Opcode、TLV标签等

使用示例：
    from Control_Core.ucp_sdk import UcpClient, NativeMotorData, opcodes
    
    # 连接 OmniCAN
    client = UcpClient(port='COM13', baud=115200)
    client.connect()
    
    # 发送命令
    resp = client.request(motor_id=1, opcode=opcodes.READ_REALTIME_POSITION)
    
    # 解析数据
    parser = NativeMotorData(driver_type='ZDT')
    position = parser.parse_position(resp.data)
    print(f"位置: {position:.2f}°")
    
    client.disconnect()
"""

__version__ = '1.0.0'
__author__ = 'Motor Control Team'

from .ucp_client import UcpClient, UcpResponse
from .motor_data import StandardMotorData, NativeMotorData, create_parser
from . import opcodes
from . import constants

__all__ = [
    'UcpClient',
    'UcpResponse',
    'StandardMotorData',
    'NativeMotorData',
    'create_parser',
    'opcodes',
    'constants',
]
