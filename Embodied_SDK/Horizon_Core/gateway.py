#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Horizon_Core 网关（统一出口）
================================

设计目的：
- 为核心功能提供统一的访问入口；
- 其他模块（UI、小工具等）可以通过这里调用核心功能。

当前对三块核心能力做统一出口：
- 运动控制：Control_SDK
- 具身智能：core.embodied_core
- AI 大模型：AI_SDK
"""

from __future__ import annotations

from typing import Any


# ==================== 运动控制相关（Control_SDK） ====================

def get_control_core() -> Any:
    """
    获取运动控制核心模块 `Horizon_Core.Control_SDK.Control_Core`

    用法示例：
        from Horizon_Core import gateway
        Control_Core = gateway.get_control_core()
        controller = Control_Core.MotorController(...)
    """
    from Horizon_Core.Control_SDK import Control_Core  # 延迟导入避免循环
    return Control_Core


def create_motor_controller(*args, **kwargs) -> Any:
    """
    创建 ZDTMotorController 实例（UCP硬件保护模式）
    
    Args:
        motor_id: 电机ID (1-255)
        port: OmniCAN 串口端口（如 COM31）
        baudrate: 波特率（默认115200）
        **kwargs: 其他参数（旧的SLCAN参数会被自动忽略）
    
    Returns:
        ZDTMotorController: 电机控制器实例
    
    注意：现在使用UCP硬件保护模式，旧的SLCAN参数（interface_type, shared_interface等）会被自动忽略
    """
    from Horizon_Core.Control_SDK.Control_Core import create_motor_controller as _create
    return _create(*args, **kwargs)


def register_motor_driver(name: str, controller_cls: Any, 
                          protocol_type: str = "ucp", **kwargs) -> None:
    """
    注册第三方电机驱动
    
    Args:
        name: 驱动名称（如 "stepper", "inovance"）
        controller_cls: 控制器类（必须实现MotorControllerInterface）
        protocol_type: 默认协议类型（"ucp", "modbus", "canopen" 等）
        **kwargs: 兼容旧参数（builder_cls, parser_cls会被忽略）
    
    示例：
    ```python
    from Horizon_Core import gateway
    from my_package import MyDriverAdapter
    
    gateway.register_motor_driver("my_driver", MyDriverAdapter, protocol_type="ucp")
    motor = gateway.create_motor_controller(motor_id=1, port="COM31", driver_type="my_driver")
    ```
    """
    from Horizon_Core.Control_SDK.Control_Core import register_motor_driver as _register
    return _register(name=name, controller_cls=controller_cls, protocol_type=protocol_type)


def set_default_motor_driver(name: str) -> None:
    """
    设置默认电机驱动
    
    Args:
        name: 驱动名称
    
    示例：
    ```python
    from Horizon_Core import gateway
    gateway.set_default_motor_driver("zdt")
    ```
    """
    from Horizon_Core.Control_SDK.Control_Core import set_default_motor_driver as _set_default
    return _set_default(name=name)


# ==================== 具身智能相关（embodied_core） ====================

def get_embodied_module() -> Any:
    """
    获取具身智能功能函数模块 `Horizon_Core.core.embodied_core.embodied_func`

    用法示例：
        from Horizon_Core import gateway
        embodied = gateway.get_embodied_module()
        ok = embodied.c_a_j([...])
    """
    from Horizon_Core.core.embodied_core import embodied_func  # 延迟导入
    return embodied_func


def get_embodied_internal_module() -> Any:
    """
    获取具身智能内部工具模块 `Horizon_Core.core.embodied_core.embodied_internal`
    """
    from Horizon_Core.core.embodied_core import embodied_internal  # 延迟导入
    return embodied_internal


def get_hierarchical_decision_system_class() -> Any:
    """
    获取层级决策系统类 `HierarchicalDecisionSystem`

    用法示例：
        from Horizon_Core import gateway
        HDS = gateway.get_hierarchical_decision_system_class()
        hds = HDS(config)
    """
    from Horizon_Core.core.embodied_core.hierarchical_decision_system import HierarchicalDecisionSystem
    return HierarchicalDecisionSystem


# ==================== AI 大模型相关（AI_SDK） ====================

def create_aisdk(*args, **kwargs) -> Any:
    """
    构造 AI SDK 主类 `AISDK`

    用法示例：
        from Horizon_Core import gateway
        sdk = gateway.create_aisdk()              # 使用默认配置
        resp = sdk.chat("alibaba", "qwen-turbo", "你好")
    """
    from Horizon_Core.AI_SDK import AISDK  # 延迟导入
    return AISDK(*args, **kwargs)


def create_depth_estimation_sdk(*args, **kwargs) -> Any:
    """
    构造深度估计 SDK (StereoDepthEstimator)
    """
    # 优先尝试从 AI_SDK 导入（如果是别名）
    try:
        from Horizon_Core.AI_SDK import DepthEstimationSDK
        return DepthEstimationSDK(*args, **kwargs)
    except ImportError:
        # 回退到底层类
        from Horizon_Core.core.arm_core.Depth_Estimation import StereoDepthEstimator
        return StereoDepthEstimator(*args, **kwargs)


__all__ = [
    "get_control_core",
    "create_motor_controller",
    "register_motor_driver",
    "set_default_motor_driver",
    "get_embodied_module",
    "get_embodied_internal_module",
    "get_hierarchical_decision_system_class",
    "create_aisdk",
    "create_depth_estimation_sdk",
]
