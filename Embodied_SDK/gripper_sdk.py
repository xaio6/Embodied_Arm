#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
夹爪 SDK（UCP/OmniCAN 硬件保护模式）
=================================

说明
----
当前主版本已将电机控制底层下沉到 OmniCAN（UCP 协议）。因此夹爪应当像普通电机一样控制：
- 固定电机 ID = 7
- 力矩模式（本质电流控制）：通过 `ZDTMotorController.set_torque()` 下发

对外只提供两个动作：
- clamp(): 夹紧（持续夹持）
- open():  张开（固定流程：反向运行 1 秒）

安全限制（软件硬限制）
--------------------
- 默认电流 1200mA
- 电流硬限幅：不超过 2000mA（任何入口都不会发送超过该值的电流）
- open() 反向运行 1 秒：固定（经测试验证）
"""

from __future__ import annotations

from typing import Dict, Optional, Any
import time

from Horizon_Core import gateway as horizon_gateway
import logging

# ----------------------------
# 安全参数（强约束）
# ----------------------------
DEFAULT_CURRENT_MA = 1200
MAX_SAFE_CURRENT_MA = 2000


def _clamp_safe_current_ma(value: int) -> int:
    """将电流限制在安全范围内（0..MAX_SAFE_CURRENT_MA），超限强制限幅。"""
    try:
        v = abs(int(value))
    except Exception:
        v = DEFAULT_CURRENT_MA
    return min(MAX_SAFE_CURRENT_MA, v)


class ZDTGripperSDK:
    """
    夹爪控制 SDK（内部电机ID=7，UCP 硬件保护模式）。

    推荐用法：直接传入已连接的电机实例（来自“连接电机”逻辑）：
        gripper = ZDTGripperSDK(motor=motors[7])

    也支持独立创建（不推荐用于 GUI 主流程，仅供脚本/测试兜底）：
        gripper = ZDTGripperSDK(port="COM31", baudrate=115200)
    """

    def __init__(
        self,
        *,
        motor: Optional[Any] = None,
        port: Optional[str] = None,
        baudrate: int = 115200,
        motor_id: int = 7,
    ) -> None:
        self.motor_id = int(motor_id)
        self._owns_motor = False
        self._silence_motor_logs = (self.motor_id == 7)

        if motor is not None:
            self._motor = motor
            self._owns_motor = False
        else:
            if not port:
                raise ValueError("未提供 motor 时必须提供 port（OmniCAN 串口）")
            self._motor = horizon_gateway.create_motor_controller(
                motor_id=self.motor_id,
                port=str(port),
                baudrate=int(baudrate),
            )
            self._owns_motor = True

        # 对外禁止暴露夹爪内部电机 ID：静默 7 号电机的底层日志
        self._maybe_silence_motor_logger()

    def _maybe_silence_motor_logger(self) -> None:
        if not self._silence_motor_logs:
            return
        try:
            lg = logging.getLogger(f"ZDTMotorController[ID:{self.motor_id}]")
            lg.disabled = True
            lg.propagate = False
            lg.setLevel(logging.CRITICAL)
        except Exception:
            pass

    def _release_stall_protection(self) -> None:
        """尽量清除堵转保护，提升张开/闭合的鲁棒性（尤其在用户手动干预时）。"""
        try:
            if hasattr(self._motor, "release_stall_protection"):
                self._motor.release_stall_protection()
            elif hasattr(self._motor, "trigger_actions") and hasattr(self._motor.trigger_actions, "release_stall_protection"):
                self._motor.trigger_actions.release_stall_protection()
        except Exception:
            pass

    # ----------------- 连接 -----------------
    def connect(self) -> None:
        """连接夹爪电机（仅当本实例自行创建 motor 时才会连接）。"""
        if self._owns_motor and hasattr(self._motor, "connect"):
            self._motor.connect()

    def disconnect(self) -> None:
        """断开夹爪电机（仅当本实例自行创建 motor 时才会断开）。"""
        if self._owns_motor and hasattr(self._motor, "disconnect"):
            self._motor.disconnect()

    def is_connected(self) -> bool:
        # UCP 控制器内部用 _connected 标志；同时有 client 连接池
        try:
            if hasattr(self._motor, "_connected"):
                return bool(getattr(self._motor, "_connected"))
            if hasattr(self._motor, "client"):
                return getattr(self._motor, "client", None) is not None
        except Exception:
            return False
        return True

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.disconnect()

    # ----------------- 遥测 -----------------
    def read_telemetry(self) -> Dict[str, float]:
        """
        Returns:
            dict: {"voltage_v": float, "current_a": float, "temperature_c": float}
        """
        voltage_v = float("nan")
        current_a = float("nan")
        temperature_c = float("nan")

        try:
            if hasattr(self._motor, "get_bus_voltage"):
                voltage_v = float(self._motor.get_bus_voltage())
        except Exception:
            pass
        try:
            if hasattr(self._motor, "get_current"):
                current_a = float(self._motor.get_current())
        except Exception:
            pass
        try:
            if hasattr(self._motor, "get_temperature"):
                temperature_c = float(self._motor.get_temperature())
        except Exception:
            pass

        return {"voltage_v": voltage_v, "current_a": current_a, "temperature_c": temperature_c}

    # ----------------- 对外动作接口（只保留两个） -----------------
    def clamp(self, current_ma: int = DEFAULT_CURRENT_MA, *, slope_ma_s: int = 1000) -> None:
        """
        夹紧（力矩/电流模式，持续夹持）。
        """
        cur = _clamp_safe_current_ma(current_ma)
        self._maybe_silence_motor_logger()
        self._release_stall_protection()
        try:
            self._motor.enable()
        except Exception:
            # 某些上层可能用 control_actions.enable()
            if hasattr(self._motor, "control_actions"):
                self._motor.control_actions.enable()
        time.sleep(0.05)
        self._motor.set_torque(int(+cur), slope=int(slope_ma_s))

    def close(self, current_ma: int = DEFAULT_CURRENT_MA) -> None:
        """兼容旧接口：close() 等同于 clamp()。"""
        self.clamp(current_ma=current_ma)

    def open(
        self,
        current_ma: int = DEFAULT_CURRENT_MA,
        *,
        slope_ma_s: int = 1000,
        settle_s: float = 0.0,
    ) -> None:
        """
        张开（固定流程：反向运行 1 秒）。
        """
        cur = _clamp_safe_current_ma(current_ma)
        self._maybe_silence_motor_logger()
        self._release_stall_protection()

        # stop -> enable -> reverse torque 1s -> stop -> disable -> enable
        try:
            self._motor.stop()
        except Exception:
            if hasattr(self._motor, "control_actions"):
                self._motor.control_actions.stop()
        # 起始等待尽量缩短：避免出现“刚点张开瞬间没力→用户手动掰动→触发保护”的窗口
        time.sleep(max(0.0, float(settle_s)))

        try:
            self._motor.enable()
        except Exception:
            if hasattr(self._motor, "control_actions"):
                self._motor.control_actions.enable()
        time.sleep(0.02)

        # 固定反向 1 秒（按你测试验证的流程保留“双下发”）
        self._motor.set_torque(int(-cur), slope=int(slope_ma_s))
        time.sleep(0.05)
        self._motor.set_torque(int(-cur), slope=int(slope_ma_s))
        time.sleep(1.0)

        try:
            self._motor.stop()
        except Exception:
            if hasattr(self._motor, "control_actions"):
                self._motor.control_actions.stop()
        time.sleep(max(0.0, float(settle_s)))

        try:
            self._motor.disable()
        except Exception:
            if hasattr(self._motor, "control_actions"):
                self._motor.control_actions.disable()
        time.sleep(max(0.0, float(settle_s)))
        try:
            self._motor.enable()
        except Exception:
            if hasattr(self._motor, "control_actions"):
                self._motor.control_actions.enable()
        time.sleep(max(0.0, float(settle_s)))
        # 再次尝试清除堵转保护（若用户在张开过程中手动反向掰动）
        self._release_stall_protection()

