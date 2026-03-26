# -*- coding: utf-8 -*-
"""
ZDT命令构建器兼容层（严格参照ESP_can_firmware实现）

为Embodied_SDK和UI提供兼容的ZDTCommandBuilder接口。
在UCP模式下，这些命令构建器主要用于Y42聚合模式的子命令构建。

⚠️ 关键：所有命令格式必须与ESP_can_firmware/test_multi_motor_ucp.py保持一致！
"""

import struct


class ZDTCommandBuilder:
    """
    ZDT命令构建器（兼容层）
    
    严格参照 ESP_can_firmware 实现，确保与板子固件一致。
    用于构建ZDT原生命令字节（用于Y42聚合等场景）。
    注意：这些方法返回的是ZDT命令体（bytes），不包含motor_id前缀。
    """
    
    @staticmethod
    def position_mode_direct(position: float, speed: float, is_absolute: bool = True, multi_sync: bool = False) -> bytes:
        """
        构建位置控制命令（直通模式）
        
        ⚠️ 参照 ESP_can_firmware/test_multi_motor_ucp.py:315-319
        
        ZDT 0xFB 位置直通命令（大端序）：
        FB + Dir(1B) + Speed(2B BE) + Position(4B BE) + Abs/Rel(1B) + Sync(1B) + 6B
        
        Args:
            position: 目标位置（度）
            speed: 速度（RPM）
            is_absolute: 是否绝对位置
            multi_sync: 是否多机同步（Y42模式下始终False）
            
        Returns:
            bytes: ZDT命令体（10字节，不包含motor_id）
        """
        # 参数转换（与ESP_can_firmware一致）
        direction = 1 if position < 0 else 0
        pos_val = int(round(abs(position) * 10.0))  # 度 → 0.1度单位
        spd_val = int(round(abs(speed) * 10.0))     # RPM → 0.1RPM单位
        
        # ZDT 0xFB 命令（大端序）
        sub_body = struct.pack(">BBHI", 0xFB, direction, spd_val, pos_val) + \
                   struct.pack(">BB", 1 if is_absolute else 0, 0) + \
                   b"\x6B"
        
        return sub_body
    
    @staticmethod
    def position_mode_trapezoid(position: float, max_speed: float,
                               acceleration: int, deceleration: int,
                               is_absolute: bool = True, multi_sync: bool = False) -> bytes:
        """
        构建位置控制命令（梯形曲线模式）
        
        ✅ 对齐 ESP 固件 `zdt_commands.cpp::position_trapezoid`：
        ZDT 0xFD 梯形曲线位置模式（大端序）：
        FD + Dir(1B) + Accel(2B BE) + Decel(2B BE) + Speed(2B BE) + Position(4B BE) + Abs/Rel(1B) + Sync(1B) + 6B
        
        Args:
            position: 目标位置（度）
            max_speed: 最大速度（RPM）
            acceleration: 加速度（RPM/s）
            deceleration: 减速度（RPM/s）
            is_absolute: 是否绝对位置
            multi_sync: 是否多机同步
            
        Returns:
            bytes: ZDT命令体
        """
        # 参数转换（与固件一致）
        direction = 1 if position < 0 else 0
        pos_val = int(round(abs(position) * 10.0))        # 度 → 0.1度单位（u32）
        spd_val = int(round(abs(max_speed) * 10.0))       # RPM → 0.1RPM单位（u16）
        acc_val = int(acceleration) if acceleration is not None else 0
        dec_val = int(deceleration) if deceleration is not None else 0
        # 夹逼到 u16
        if acc_val < 0: acc_val = 0
        if dec_val < 0: dec_val = 0
        if acc_val > 0xFFFF: acc_val = 0xFFFF
        if dec_val > 0xFFFF: dec_val = 0xFFFF
        if spd_val < 0: spd_val = 0
        if spd_val > 0xFFFF: spd_val = 0xFFFF
        
        sub_body = (
            struct.pack(">BBHHH", 0xFD, direction, acc_val, dec_val, spd_val) +
            struct.pack(">I", pos_val) +
            struct.pack(">BB", 1 if is_absolute else 0, 0) +
            b"\x6B"
        )
        return sub_body
    
    @staticmethod
    def speed_mode(speed: float, acceleration: int = 1000, multi_sync: bool = False) -> bytes:
        """
        构建速度控制命令
        
        ⚠️ 参照 ESP_can_firmware/test_multi_motor_ucp.py:343-345
        
        ZDT 0xF6 速度模式（大端序）：
        F6 + Dir(1B) + Accel(2B BE) + Speed(2B BE) + Sync(1B) + 6B
        
        Args:
            speed: 目标速度（RPM）
            acceleration: 加速度（RPM/s）
            multi_sync: 是否多机同步
            
        Returns:
            bytes: ZDT命令体（8字节）
        """
        # 参数转换
        direction = 1 if speed < 0 else 0
        spd_val = int(round(abs(speed) * 10.0))  # RPM → 0.1RPM单位
        acc_val = acceleration  # 直接使用RPM/s
        
        # ZDT 0xF6 命令（大端序）⚠️ 注意：加速度在前，速度在后！
        sub_body = struct.pack(">BBHH B", 0xF6, direction, acc_val, spd_val, 0) + b"\x6B"
        
        return sub_body
    
    @staticmethod
    def homing_mode(mode: int = 4, **kwargs) -> bytes:
        """
        构建回零命令
        
        ⚠️ 参照 ESP_can_firmware/test_multi_motor_ucp.py:423-424
        
        ZDT 0x9A 回零（大端序）：
        9A + Mode(1B) + Sync(1B) + 6B
        
        Args:
            mode: 回零模式（0-5）
            **kwargs: 其他参数
            
        Returns:
            bytes: ZDT命令体（4字节）
        """
        # ZDT 0x9A 命令（大端序）
        sub_body = struct.pack(">BB B", 0x9A, mode, 0) + b"\x6B"
        
        return sub_body
    
    @staticmethod
    def build_single_command_bytes(motor_id: int, function_body: bytes) -> bytes:
        """
        构建单个Y42子命令：motor_id + function_body
        
        Args:
            motor_id: 电机ID
            function_body: 功能体（来自position_mode_direct等方法）
            
        Returns:
            bytes: 完整的Y42子命令
        """
        if isinstance(function_body, bytes):
            return bytes([motor_id]) + function_body
        else:
            # 兼容list输入
            return bytes([motor_id]) + bytes(function_body)

