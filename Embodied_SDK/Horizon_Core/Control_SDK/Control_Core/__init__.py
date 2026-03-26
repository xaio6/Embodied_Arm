# -*- coding: utf-8 -*-
"""
ZDT闭环驱动板 Python SDK - UCP硬件保护模式

通过 OmniCAN 进行电机控制，实现硬件级防火墙保护。

核心优势：
- 🔒 硬件防火墙：ZDT协议细节封装在 OmniCAN 固件中
- 🚀 高效通信：通过UCP协议与 OmniCAN 通信
- 🎯 Y42同步：硬件级多电机同步控制
- 💎 知识产权保护：别人无法通过SDK代码直接控制电机

使用示例：
```python
from Control_Core import ZDTMotorController

# 单电机控制
motor = ZDTMotorController(motor_id=1, port="COM31")
motor.connect()
motor.enable()
motor.move_to_position(90, speed=500)
motor.disconnect()

# 多电机同步（Y42聚合模式）
motor1 = ZDTMotorController(motor_id=1, port="COM31")
motor2 = ZDTMotorController(motor_id=2, port="COM31")
motor1.connect()
motor2.connect()

controllers = {1: motor1, 2: motor2}
targets = {1: 90.0, 2: 180.0}

# 一次通信完成多电机同步
ZDTMotorController.y42_sync_enable(controllers, enabled=True)
ZDTMotorController.y42_sync_position(controllers, targets, speed=500)
```
"""

import logging

__version__ = "2.0.0"  # UCP硬件保护版本
__author__ = "Horizon Arm Team"

# ==================== 向后兼容层（旧API） ====================
# 保留现有的ZDTMotorController，确保旧代码仍然可用
from .motor_controller_ucp_simple import ZDTMotorController

# 导入命令构建器（供Embodied_SDK等高层SDK使用）
from .command_builder_compat import ZDTCommandBuilder

# ==================== 新架构层（接口+工厂） ====================
# 导入接口定义
from .interfaces import MotorControllerInterface, ProtocolInterface

# 导入协议实现
from .protocols import UcpProtocol

# 导入驱动适配器
from .drivers import ZDTDriverAdapter

# 导入工厂和管理器
from .motor_factory import (
    DriverManager,
    create_motor_controller as _create_motor_controller_new,
    register_motor_driver,
    set_default_motor_driver,
)

# ==================== UCP SDK组件 ====================
from .ucp_sdk import (
    UcpClient,
    UcpResponse,
    StandardMotorData,
    NativeMotorData,
    opcodes,
    constants
)

# ==================== 错误处理模块 ====================
from .error_handler import MotorLogger, MotorError, analyze_serial_exception, format_error_for_ui

# ==================== 连接池 ====================
from .ucp_connection_pool import UcpConnectionPool

# ==================== 定义导出的公共接口 ====================
__all__ = [
    # 向后兼容（旧API）
    "ZDTMotorController",
    "ZDTCommandBuilder",  # 供Embodied_SDK使用
    
    # 新架构（接口）
    "MotorControllerInterface",
    "ProtocolInterface",
    
    # 新架构（协议）
    "UcpProtocol",
    
    # 新架构（驱动）
    "ZDTDriverAdapter",
    
    # 新架构（工厂和管理器）
    "DriverManager",
    "register_motor_driver",
    "set_default_motor_driver",
    
    # UCP SDK组件
    "UcpClient",
    "UcpResponse",
    "StandardMotorData",
    "NativeMotorData",
    "opcodes",
    "constants",
    
    # 错误处理
    "MotorLogger",
    "MotorError",
    "analyze_serial_exception",
    "format_error_for_ui",
    
    # 连接池
    "UcpConnectionPool",
    
    # 便捷函数
    "create_motor_controller",
    "setup_logging",
    "get_version",
]


def create_motor_controller(motor_id: int, port: str = "COM31", baudrate: int = 115200, 
                           driver_type: str = None, protocol_type: str = None, **kwargs):
    """
    创建电机控制器的便捷函数（支持新旧两种模式）
    
    **智能兼容模式：**
    - 如果不指定driver_type：使用旧的ZDTMotorController（向后兼容）
    - 如果指定driver_type：使用新的工厂模式（支持多驱动）
    
    Args:
        motor_id: 电机ID (1-255)
        port: 串口端口（如 COM31）
        baudrate: 波特率（默认115200）
        driver_type: 驱动类型（None=向后兼容模式, "zdt"=工厂模式）
        protocol_type: 协议类型（None=使用驱动默认协议）
        **kwargs: 其他参数
        
    Returns:
        MotorControllerInterface: 电机控制器实例
        
    示例：
    ------
    旧代码（仍然支持）：
    ```python
    motor = create_motor_controller(motor_id=1, port="COM31")
    motor.connect()
    motor.enable()
    ```
    
    新代码（扩展性更好）：
    ```python
    # 明确指定驱动类型
    motor = create_motor_controller(motor_id=1, port="COM31", driver_type="zdt")
    
    # 切换到其他驱动（未来支持）
    motor = create_motor_controller(motor_id=1, port="COM31", driver_type="stepper", protocol_type="modbus")
    ```
    """
    # 智能兼容：如果指定了driver_type，使用新工厂模式
    if driver_type is not None:
        return _create_motor_controller_new(
            motor_id=motor_id,
            port=port,
            baudrate=baudrate,
            driver_type=driver_type,
            protocol_type=protocol_type,
            **kwargs
        )
    
    # 否则使用旧模式（向后兼容）
    kwargs.pop('interface_type', None)  # 忽略旧的SLCAN参数
    kwargs.pop('shared_interface', None)
    return ZDTMotorController(motor_id=motor_id, port=port, baudrate=baudrate, **kwargs)


def setup_logging(level=logging.INFO):
    """
    设置日志配置
    
    Args:
        level: 日志级别（logging.INFO, logging.DEBUG等）
    """
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def get_version() -> str:
    """获取SDK版本号"""
    return __version__


def print_welcome():
    """打印SDK欢迎信息"""
    print(f"""
    ========================================
    ZDT闭环驱动板 Python SDK v{__version__}
    硬件防火墙保护版（UCP模式）
    ========================================
    
    核心优势：
    🔒 硬件防火墙：ZDT协议封装在 OmniCAN 固件中
    🚀 Y42同步：硬件级多电机同步控制
    💎 知识产权保护：SDK不暴露底层协议细节
    
    快速开始:
    1. 连接 OmniCAN 到PC
    2. 创建控制器: 
       motor = create_motor_controller(motor_id=1, port="COM31")
    3. 控制电机:
       motor.connect()
       motor.enable()
       motor.move_to_position(90, speed=500)
    
    多电机同步（Y42聚合模式⭐）:
       controllers = {1: motor1, 2: motor2}
       targets = {1: 90.0, 2: 180.0}
       ZDTMotorController.y42_sync_position(controllers, targets, 500)
    
    文档和示例请查看项目根目录
    ========================================
    """)


def check_dependencies():
    """检查依赖包是否安装"""
    try:
        import serial
        print(f"✓ pyserial 已安装 (版本: {serial.__version__})")
    except ImportError:
        print("✗ pyserial 未安装，请运行: pip install pyserial")
    
    print("\n✓ UCP模式不需要python-can库")
    print("✓ 所有依赖检查完成")
