# -*- coding: utf-8 -*-
"""
电机控制接口层

定义了通用的电机控制接口和通信协议接口，
为不同厂家的驱动板提供统一的抽象。
"""

from .motor_interface import MotorControllerInterface
from .protocol_interface import ProtocolInterface

__all__ = [
    'MotorControllerInterface',
    'ProtocolInterface',
]

