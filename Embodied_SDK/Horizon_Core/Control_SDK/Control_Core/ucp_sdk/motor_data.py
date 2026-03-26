#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UCP 电机数据解析库（标准模式 + 原生模式）

包含两个解析类：
1. StandardMotorData：标准化数据解析（opcode 0x60-0x69）
   - 统一格式：float32/uint32 小端序
   - 统一单位：度/RPM/V/A/°C
   - 适用于所有厂商

2. NativeMotorData：原生数据解析（opcode 0x20-0x39）
   - 厂商特定格式（目前支持 ZDT）
   - 需要理解厂商协议
   - 可扩展支持其他厂商

使用示例：
    from Control_Core.ucp_sdk import StandardMotorData, NativeMotorData
    
    # 标准模式（推荐，适用于所有厂商）
    std_parser = StandardMotorData()
    resp = ucp.call(motor_id, opcode=0x60)
    position = std_parser.parse_float32(resp.data)  # 直接得到度数
    
    # 原生模式（需要理解厂商协议）
    native_parser = NativeMotorData(driver_type='ZDT')
    resp = ucp.call(motor_id, opcode=0x20)
    position = native_parser.parse_position(resp.data)  # ZDT 格式解析
"""

import struct
import math
from typing import Optional, Dict, Any, Literal


class StandardMotorData:
    """UCP 标准化电机数据解析器（适用于所有厂商）"""
    
    # 标准化 Opcode 定义
    OP_READ_POSITION_STD = 0x60
    OP_READ_SPEED_STD = 0x61
    OP_READ_TEMPERATURE_STD = 0x62
    OP_READ_VOLTAGE_STD = 0x63
    OP_READ_CURRENT_STD = 0x64
    OP_READ_PHASE_CURRENT_STD = 0x65
    OP_READ_POSITION_ERROR_STD = 0x66
    OP_READ_TARGET_POSITION_STD = 0x67
    OP_READ_STATUS_FLAGS_STD = 0x69
    
    # 状态标志位定义
    FLAG_MOTOR_ENABLED = 1 << 0
    FLAG_IN_POSITION = 1 << 1
    FLAG_STALL_DETECTED = 1 << 2
    FLAG_STALL_PROTECTION = 1 << 3
    FLAG_HOMING_IN_PROGRESS = 1 << 4
    FLAG_HOMING_COMPLETE = 1 << 5
    FLAG_HOMING_FAILED = 1 << 6
    FLAG_ENCODER_READY = 1 << 7
    FLAG_ENCODER_CALIBRATED = 1 << 8
    FLAG_ERROR_STATE = 1 << 9
    
    @staticmethod
    def parse_float32(data: bytes) -> Optional[float]:
        """
        解析 float32（IEEE 754 单精度，小端序）
        
        Args:
            data: 响应数据（至少 4 字节）
        
        Returns:
            float: 解析后的浮点数，失败返回 None
        """
        if not data or len(data) < 4:
            return None
        
        try:
            value = struct.unpack("<f", data[:4])[0]
            # 检查是否为 NaN（表示固件解析失败）
            if math.isnan(value):
                return None
            return value
        except struct.error:
            return None
    
    @staticmethod
    def parse_uint32(data: bytes) -> Optional[int]:
        """
        解析 uint32（小端序）
        
        Args:
            data: 响应数据（至少 4 字节）
        
        Returns:
            int: 解析后的整数，失败返回 None
        """
        if not data or len(data) < 4:
            return None
        
        try:
            return struct.unpack("<I", data[:4])[0]
        except struct.error:
            return None
    
    @classmethod
    def parse_status_flags(cls, data: bytes) -> Optional[Dict[str, bool]]:
        """
        解析标准化状态标志位
        
        Args:
            data: 响应数据（uint32 小端序）
        
        Returns:
            dict: 状态标志字典，失败返回 None
            
        示例返回：
            {
                'motor_enabled': True,
                'in_position': False,
                'stall_detected': False,
                'stall_protection': False,
                'homing_in_progress': False,
                'homing_complete': True,
                'homing_failed': False,
                'encoder_ready': True,
                'encoder_calibrated': True,
                'error_state': False
            }
        """
        flags = cls.parse_uint32(data)
        if flags is None:
            return None
        
        return {
            'motor_enabled': bool(flags & cls.FLAG_MOTOR_ENABLED),
            'in_position': bool(flags & cls.FLAG_IN_POSITION),
            'stall_detected': bool(flags & cls.FLAG_STALL_DETECTED),
            'stall_protection': bool(flags & cls.FLAG_STALL_PROTECTION),
            'homing_in_progress': bool(flags & cls.FLAG_HOMING_IN_PROGRESS),
            'homing_complete': bool(flags & cls.FLAG_HOMING_COMPLETE),
            'homing_failed': bool(flags & cls.FLAG_HOMING_FAILED),
            'encoder_ready': bool(flags & cls.FLAG_ENCODER_READY),
            'encoder_calibrated': bool(flags & cls.FLAG_ENCODER_CALIBRATED),
            'error_state': bool(flags & cls.FLAG_ERROR_STATE),
        }
    
    @classmethod
    def format_status(cls, status: Dict[str, bool]) -> str:
        """
        格式化状态标志为可读字符串
        
        Args:
            status: parse_status_flags() 返回的状态字典
        
        Returns:
            str: 格式化的状态字符串
        """
        if not status:
            return "Unknown"
        
        parts = []
        if status['motor_enabled']:
            parts.append("[OK]使能")
        else:
            parts.append("[X]失能")
        
        if status['in_position']:
            parts.append("[OK]到位")
        
        if status['stall_detected']:
            parts.append("[!]堵转")
        
        if status['stall_protection']:
            parts.append("[!]堵转保护")
        
        if status['homing_in_progress']:
            parts.append("[~]回零中")
        elif status['homing_complete']:
            parts.append("[OK]回零完成")
        elif status['homing_failed']:
            parts.append("[X]回零失败")
        
        if status['error_state']:
            parts.append("[X]错误")
        
        return " | ".join(parts) if parts else "正常"


# ============================================================================
# 原生数据解析类（厂商特定格式）
# ============================================================================

class NativeMotorData:
    """
    UCP 原生电机数据解析器（厂商特定格式）
    
    当前支持的厂商：
    - ZDT：张大头闭环步进驱动板
    
    使用方法：
        parser = NativeMotorData(driver_type='ZDT')
        
        # 解析位置（ZDT 格式：sign(1B) + pos(4B BE) * 0.1度）
        resp = ucp.call(motor_id, opcode=0x20)
        position = parser.parse_position(resp.data)
    """
    
    def __init__(self, driver_type: Literal['ZDT'] = 'ZDT'):
        """
        初始化原生数据解析器
        
        Args:
            driver_type: 驱动板类型，当前支持 'ZDT'
        """
        self.driver_type = driver_type
        
        # 根据驱动板类型选择解析函数
        if driver_type == 'ZDT':
            self._parse_position_impl = self._parse_zdt_position
            self._parse_speed_impl = self._parse_zdt_speed
            self._parse_temperature_impl = self._parse_zdt_temperature
            self._parse_voltage_impl = self._parse_zdt_voltage
            self._parse_current_impl = self._parse_zdt_current
            self._parse_status_impl = self._parse_zdt_status
            self._parse_homing_status_impl = self._parse_zdt_homing_status
            self._parse_version_impl = self._parse_zdt_version
        else:
            raise ValueError(f"不支持的驱动板类型: {driver_type}")
    
    # ========================================================================
    # 通用接口（自动路由到对应厂商的实现）
    # ========================================================================
    
    def parse_position(self, data: bytes) -> Optional[float]:
        """解析实时位置（度）"""
        return self._parse_position_impl(data)
    
    def parse_speed(self, data: bytes) -> Optional[float]:
        """解析实时转速（RPM）"""
        return self._parse_speed_impl(data)
    
    def parse_temperature(self, data: bytes) -> Optional[float]:
        """解析温度（°C）"""
        return self._parse_temperature_impl(data)
    
    def parse_voltage(self, data: bytes) -> Optional[float]:
        """解析电压（V）"""
        return self._parse_voltage_impl(data)
    
    def parse_current(self, data: bytes) -> Optional[float]:
        """解析电流（A）"""
        return self._parse_current_impl(data)
    
    def parse_status(self, data: bytes) -> Optional[Dict[str, bool]]:
        """解析电机状态标志"""
        return self._parse_status_impl(data)
    
    def parse_homing_status(self, data: bytes) -> Optional[Dict[str, bool]]:
        """解析回零状态标志"""
        return self._parse_homing_status_impl(data)
    
    def parse_version(self, data: bytes) -> Optional[Dict[str, str]]:
        """解析版本信息"""
        return self._parse_version_impl(data)
    
    # ========================================================================
    # ZDT 厂商特定实现
    # ========================================================================
    
    @staticmethod
    def _parse_zdt_position(data: bytes) -> Optional[float]:
        """
        解析 ZDT 位置数据
        
        格式：sign(1B) + pos(4B big-endian) * 0.1度
        
        Args:
            data: ZDT 原始响应数据
        
        Returns:
            float: 位置（度），失败返回 None
        """
        if not data or len(data) < 5:
            return None
        
        try:
            sign = data[0]
            pos_raw = struct.unpack(">I", data[1:5])[0]  # 大端序
            position = pos_raw * 0.1
            
            if sign == 1:
                position = -position
            
            return position
        except struct.error:
            return None
    
    @staticmethod
    def _parse_zdt_speed(data: bytes) -> Optional[float]:
        """
        解析 ZDT 速度数据
        
        格式：sign(1B) + speed(2B big-endian) * 0.1RPM
        
        Args:
            data: ZDT 原始响应数据
        
        Returns:
            float: 速度（RPM），失败返回 None
        """
        if not data or len(data) < 3:
            return None
        
        try:
            sign = data[0]
            speed_raw = struct.unpack(">H", data[1:3])[0]  # 大端序
            speed = speed_raw * 0.1
            
            if sign == 1:
                speed = -speed
            
            return speed
        except struct.error:
            return None
    
    @staticmethod
    def _parse_zdt_temperature(data: bytes) -> Optional[float]:
        """
        解析 ZDT 温度数据
        
        格式：sign(1B) + temp(1B 摄氏度)
        
        Args:
            data: ZDT 原始响应数据
        
        Returns:
            float: 温度（°C），失败返回 None
        """
        if not data or len(data) < 2:
            return None
        
        sign = data[0]
        temp = float(data[1])
        
        if sign == 1:
            temp = -temp
        
        return temp
    
    @staticmethod
    def _parse_zdt_voltage(data: bytes) -> Optional[float]:
        """
        解析 ZDT 电压数据
        
        格式：voltage(2B big-endian) 单位 mV
        
        Args:
            data: ZDT 原始响应数据
        
        Returns:
            float: 电压（V），失败返回 None
        """
        if not data or len(data) < 2:
            return None
        
        try:
            mv = struct.unpack(">H", data[:2])[0]  # 大端序
            return mv / 1000.0
        except struct.error:
            return None
    
    @staticmethod
    def _parse_zdt_current(data: bytes) -> Optional[float]:
        """
        解析 ZDT 电流数据
        
        格式：current(2B big-endian) 单位 mA
        
        Args:
            data: ZDT 原始响应数据
        
        Returns:
            float: 电流（A），失败返回 None
        """
        if not data or len(data) < 2:
            return None
        
        try:
            ma = struct.unpack(">H", data[:2])[0]  # 大端序
            return ma / 1000.0
        except struct.error:
            return None
    
    @staticmethod
    def _parse_zdt_status(data: bytes) -> Optional[Dict[str, bool]]:
        """
        解析 ZDT 电机状态标志
        
        格式：flags(1B)
        bit 0: enabled（使能）
        bit 1: in_position（到位）
        bit 2: stall_detected（检测到堵转）
        bit 3: stall_protection（堵转保护触发）
        
        Args:
            data: ZDT 原始响应数据
        
        Returns:
            dict: 状态标志字典，失败返回 None
        """
        if not data or len(data) < 1:
            return None
        
        flags = data[0]
        return {
            'enabled': bool(flags & 0x01),
            'in_position': bool(flags & 0x02),
            'stall_detected': bool(flags & 0x04),
            'stall_protection': bool(flags & 0x08),
        }
    
    @staticmethod
    def _parse_zdt_homing_status(data: bytes) -> Optional[Dict[str, bool]]:
        """
        解析 ZDT 回零状态标志
        
        格式：flags(1B)
        bit 0: encoder_ready（编码器就绪）
        bit 1: encoder_calibrated（编码器已校准）
        bit 2: homing_in_progress（回零进行中）
        bit 3: homing_failed（回零失败）
        bit 7: high_precision（高精度模式）
        
        Args:
            data: ZDT 原始响应数据
        
        Returns:
            dict: 回零状态字典，失败返回 None
        """
        if not data or len(data) < 1:
            return None
        
        flags = data[0]
        return {
            'encoder_ready': bool(flags & 0x01),
            'encoder_calibrated': bool(flags & 0x02),
            'homing_in_progress': bool(flags & 0x04),
            'homing_failed': bool(flags & 0x08),
            'high_precision': bool(flags & 0x80),
        }
    
    @staticmethod
    def _parse_zdt_version(data: bytes) -> Optional[Dict[str, str]]:
        """
        解析 ZDT 版本信息
        
        格式：fw_ver(2B BE) + hw_ver(2B BE)
        
        Args:
            data: ZDT 原始响应数据
        
        Returns:
            dict: {'firmware': 'x.y', 'hardware': 'x.y'}，失败返回 None
        """
        if not data or len(data) < 4:
            return None
        
        try:
            fw_ver = struct.unpack(">H", data[0:2])[0]
            hw_ver = struct.unpack(">H", data[2:4])[0]
            
            return {
                'firmware': f"{fw_ver // 100}.{fw_ver % 100:02d}",
                'hardware': f"{hw_ver // 100}.{hw_ver % 100:02d}",
            }
        except struct.error:
            return None


# ============================================================================
# 便捷工具函数
# ============================================================================

def hex_bytes(data: bytes) -> str:
    """将字节数组格式化为十六进制字符串（用于调试）"""
    return ' '.join(f'{b:02X}' for b in data)


def create_parser(mode: Literal['standard', 'native'] = 'standard', 
                  driver_type: str = 'ZDT'):
    """
    工厂函数：创建解析器实例
    
    Args:
        mode: 'standard' 或 'native'
        driver_type: 仅在 native 模式时需要，指定驱动板类型
    
    Returns:
        StandardMotorData 或 NativeMotorData 实例
    
    使用示例：
        # 标准模式（推荐）
        parser = create_parser('standard')
        position = parser.parse_float32(resp.data)
        
        # 原生模式
        parser = create_parser('native', driver_type='ZDT')
        position = parser.parse_position(resp.data)
    """
    if mode == 'standard':
        return StandardMotorData()
    elif mode == 'native':
        return NativeMotorData(driver_type=driver_type)
    else:
        raise ValueError(f"不支持的模式: {mode}，请使用 'standard' 或 'native'")

