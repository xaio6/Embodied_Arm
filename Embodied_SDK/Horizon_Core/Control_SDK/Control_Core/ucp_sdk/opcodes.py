#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UCP Opcode 定义

所有 opcode 与 OmniCAN 固件对齐
"""

# ============================================================================
# 基础控制命令 (0x01-0x0F)
# ============================================================================

ENABLE = 0x01                   # 电机使能/失能
STOP = 0x02                     # 电机停止
SYNC_MOTION = 0x03              # 广播同步触发

# ============================================================================
# 运动控制命令 (0x10-0x1F)
# ============================================================================

SPEED_MODE = 0x10               # 速度模式
TORQUE_MODE = 0x11              # 力矩/电流模式
POSITION_DIRECT = 0x12          # 位置直通模式（限速位置）
POSITION_TRAPEZOID = 0x13       # 位置梯形曲线模式

# ============================================================================
# 读取命令 - 原生格式 (0x20-0x2F)
# ============================================================================

READ_REALTIME_POSITION = 0x20   # 读取实时位置（ZDT 原生格式）
READ_REALTIME_SPEED = 0x21      # 读取实时转速（ZDT 原生格式）
READ_TEMPERATURE = 0x22         # 读取温度（ZDT 原生格式）
READ_MOTOR_STATUS = 0x23        # 读取电机状态标志
READ_HOMING_STATUS = 0x24       # 读取回零状态标志
READ_BUS_VOLTAGE = 0x25         # 读取总线电压
READ_BUS_CURRENT = 0x26         # 读取总线电流
READ_PHASE_CURRENT = 0x27       # 读取相电流
READ_POSITION_ERROR = 0x28      # 读取位置误差
READ_TARGET_POSITION = 0x29     # 读取目标位置
READ_REALTIME_TARGET_POSITION = 0x2A  # 读取实时目标位置
READ_ENCODER_RAW = 0x2B         # 读取编码器原始值
READ_ENCODER_CALIBRATED = 0x2C  # 读取编码器校准值
READ_PULSE_COUNT = 0x2D         # 读取脉冲计数
READ_INPUT_PULSE = 0x2E         # 读取输入脉冲
READ_VERSION = 0x2F             # 读取版本信息

# ============================================================================
# 特殊命令 (0x30-0x3F)
# ============================================================================

Y42_MULTI_MOTOR = 0x30          # Y42 多电机聚合命令
READ_RESISTANCE_INDUCTANCE = 0x35  # 读取电阻电感
READ_PID_PARAMS = 0x36          # 读取 PID 参数
READ_HOMING_PARAMS = 0x37       # 读取回零参数
READ_DRIVE_PARAMETERS = 0x38    # 读取驱动参数
READ_SYSTEM_STATUS = 0x39       # 读取系统状态

# ============================================================================
# 设置命令 (0x40-0x4F)
# ============================================================================

SET_ZERO_POSITION = 0x40        # 设置零点位置
TRIGGER_HOMING = 0x41           # 触发回零
FORCE_STOP_HOMING = 0x42        # 强制停止回零
TRIGGER_ENCODER_CALIBRATION = 0x43  # 触发编码器校准
CLEAR_POSITION = 0x44           # 清零位置
RELEASE_STALL_PROTECTION = 0x45  # 解除堵转保护
FACTORY_RESET = 0x46            # 恢复出厂设置

# ============================================================================
# 修改参数命令 (0x50-0x5F)
# ============================================================================

MODIFY_HOMING_PARAMS = 0x50     # 修改回零参数
MODIFY_DRIVE_PARAMETERS = 0x51  # 修改驱动参数
MODIFY_MOTOR_ID = 0x52          # 修改电机 ID

# ============================================================================
# 读取命令 - 标准化格式 (0x60-0x6F)
# ============================================================================

READ_POSITION_STD = 0x60        # 读取位置（标准化 float32 度）
READ_SPEED_STD = 0x61           # 读取速度（标准化 float32 RPM）
READ_TEMPERATURE_STD = 0x62     # 读取温度（标准化 float32 °C）
READ_VOLTAGE_STD = 0x63         # 读取电压（标准化 float32 V）
READ_CURRENT_STD = 0x64         # 读取电流（标准化 float32 A）
READ_PHASE_CURRENT_STD = 0x65   # 读取相电流（标准化 float32 A）
READ_POSITION_ERROR_STD = 0x66  # 读取位置误差（标准化 float32 度）
READ_TARGET_POSITION_STD = 0x67  # 读取目标位置（标准化 float32 度）
READ_REALTIME_TARGET_POSITION_STD = 0x68  # 读取实时目标位置（标准化）
READ_PULSE_COUNT_STD = 0x69     # 读取脉冲计数（标准化 int32）

# ============================================================================
# 轨迹执行命令 (0x70-0x7F)
# ============================================================================

TRAJECTORY_UPLOAD = 0x70        # 批量上传轨迹点到 OmniCAN 缓存
TRAJECTORY_EXECUTE = 0x71       # 执行已上传的轨迹
TRAJECTORY_STOP = 0x72          # 停止轨迹执行
TRAJECTORY_STATUS = 0x73        # 查询轨迹执行状态

