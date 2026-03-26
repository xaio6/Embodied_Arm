# -*- coding: utf-8 -*-
"""
电机控制器工厂 + 驱动管理器

功能：
1. DriverManager: 管理已注册的驱动适配器（沿用原有设计思想）
2. create_motor_controller: 工厂方法，根据配置创建对应驱动的控制器

扩展指南：
----------
添加新驱动（如步科、汇川）只需3步：

1. 创建驱动适配器（实现 MotorControllerInterface）
2. 创建通信协议（实现 ProtocolInterface，如需要）
3. 注册驱动：
   ```python
   from Control_Core import register_motor_driver
   from my_driver import StepperAdapter
   
   register_motor_driver(
       name="stepper",
       controller_cls=StepperAdapter,
       protocol_type="modbus"  # 或 "ucp"、"canopen" 等
   )
   ```

使用示例：
----------
```python
# 方式1：直接创建（默认ZDT+UCP）
motor = create_motor_controller(motor_id=1, port="COM31")

# 方式2：指定驱动类型
motor = create_motor_controller(
    motor_id=1, 
    port="COM31",
    driver_type="stepper",  # 切换到步科驱动
    protocol_type="modbus"   # 使用Modbus协议
)

# 方式3：使用gateway注册
from Horizon_Core import gateway
gateway.register_motor_driver("my_driver", MyDriverAdapter)
motor = gateway.create_motor_controller(motor_id=1, driver_type="my_driver")
```
"""

import logging
from typing import Dict, Type, Any, Optional

logger = logging.getLogger(__name__)


class DriverManager:
    """
    驱动管理器（沿用原有设计）
    
    功能：
    - 注册第三方驱动适配器
    - 管理驱动的协议类型
    - 提供驱动查询和默认驱动设置
    """
    
    # 已注册的驱动：{驱动名称: (控制器类, 协议类型)}
    _registered_drivers: Dict[str, tuple] = {}
    
    # 默认驱动
    _default_driver: str = "zdt"
    
    @classmethod
    def register_driver(cls, name: str, controller_cls: Type, protocol_type: str = "ucp") -> None:
        """
        注册驱动适配器
        
        Args:
            name: 驱动名称（如 "zdt", "stepper", "inovance"）
            controller_cls: 控制器类（必须实现 MotorControllerInterface）
            protocol_type: 协议类型（"ucp", "modbus", "canopen" 等）
        """
        from .interfaces.motor_interface import MotorControllerInterface
        
        # 检查是否实现接口
        if not issubclass(controller_cls, MotorControllerInterface):
            raise TypeError(f"驱动 {name} 的控制器类必须实现 MotorControllerInterface 接口")
        
        cls._registered_drivers[name] = (controller_cls, protocol_type)
        logger.info(f"✓ 已注册驱动: {name} (协议: {protocol_type})")
    
    @classmethod
    def get_driver(cls, name: str) -> Optional[tuple]:
        """
        获取已注册的驱动
        
        Returns:
            (controller_cls, protocol_type) 或 None
        """
        return cls._registered_drivers.get(name)
    
    @classmethod
    def set_default_driver(cls, name: str) -> None:
        """设置默认驱动"""
        if name not in cls._registered_drivers:
            raise ValueError(f"驱动 {name} 未注册，请先调用 register_driver()")
        cls._default_driver = name
        logger.info(f"✓ 默认驱动已设置为: {name}")
    
    @classmethod
    def get_default_driver(cls) -> str:
        """获取默认驱动名称"""
        return cls._default_driver
    
    @classmethod
    def list_drivers(cls) -> Dict[str, str]:
        """
        列出所有已注册的驱动
        
        Returns:
            {驱动名称: 协议类型}
        """
        return {name: protocol for name, (_, protocol) in cls._registered_drivers.items()}

    # -------------------- 向后兼容：命令构建器 --------------------
    @classmethod
    def get_builder(cls):
        """
        向后兼容接口：返回底层 ZDT 命令构建器。

        历史原因：
        - 旧版上层模块（如 embodied_func）会调用 DriverManager.get_builder()
          来构建 Y42 聚合子命令。
        - 新架构中命令构建器位于 command_builder_compat.py。
        """
        try:
            from .command_builder_compat import ZDTCommandBuilder
            return ZDTCommandBuilder
        except Exception:
            return None


def create_motor_controller(
    motor_id: int,
    port: str = "COM31",
    baudrate: int = 115200,
    driver_type: Optional[str] = None,
    protocol_type: Optional[str] = None,
    **kwargs
) -> Any:
    """
    工厂方法：创建电机控制器实例
    
    Args:
        motor_id: 电机ID (1-255)
        port: 串口号
        baudrate: 波特率
        driver_type: 驱动类型（None则使用默认驱动）
        protocol_type: 协议类型（None则使用驱动的默认协议）
        **kwargs: 传递给控制器构造函数的其他参数
    
    Returns:
        MotorControllerInterface: 电机控制器实例
    
    Raises:
        ValueError: 驱动未注册或协议不支持
    """
    # 确定使用哪个驱动
    if driver_type is None:
        driver_type = DriverManager.get_default_driver()
    
    # 获取驱动信息
    driver_info = DriverManager.get_driver(driver_type)
    if driver_info is None:
        available = ", ".join(DriverManager.list_drivers().keys())
        raise ValueError(
            f"驱动 '{driver_type}' 未注册。\n"
            f"可用驱动: {available}\n"
            f"提示：使用 register_motor_driver() 注册新驱动"
        )
    
    controller_cls, default_protocol = driver_info
    
    # 确定使用哪个协议
    if protocol_type is None:
        protocol_type = default_protocol
    
    # 创建协议实例
    protocol = _create_protocol(protocol_type, port, baudrate)
    
    # 创建控制器实例
    logger.info(f"创建控制器: driver={driver_type}, protocol={protocol_type}, motor_id={motor_id}")
    return controller_cls(motor_id=motor_id, protocol=protocol, **kwargs)


def _create_protocol(protocol_type: str, port: str, baudrate: int) -> Any:
    """
    内部方法：创建协议实例
    
    Args:
        protocol_type: 协议类型（"ucp", "modbus", "canopen" 等）
        port: 串口号
        baudrate: 波特率
    
    Returns:
        ProtocolInterface: 协议实例
    """
    if protocol_type == "ucp":
        from .protocols.ucp_protocol import UcpProtocol
        return UcpProtocol(port=port, baudrate=baudrate)
    
    elif protocol_type == "modbus":
        # 预留：未来可扩展Modbus协议
        # from .protocols.modbus_protocol import ModbusProtocol
        # return ModbusProtocol(port=port, baudrate=baudrate)
        raise NotImplementedError("Modbus协议尚未实现，敬请期待")
    
    elif protocol_type == "canopen":
        # 预留：未来可扩展CANopen协议
        raise NotImplementedError("CANopen协议尚未实现，敬请期待")
    
    else:
        raise ValueError(
            f"不支持的协议类型: {protocol_type}\n"
            f"当前支持: ucp\n"
            f"即将支持: modbus, canopen"
        )


def register_motor_driver(name: str, controller_cls: Type, protocol_type: str = "ucp") -> None:
    """
    注册第三方电机驱动（便捷函数）
    
    Args:
        name: 驱动名称
        controller_cls: 控制器类
        protocol_type: 默认协议类型
    
    示例：
        from Control_Core import register_motor_driver
        from my_package import MyDriverAdapter
        
        register_motor_driver("my_driver", MyDriverAdapter, "modbus")
    """
    DriverManager.register_driver(name, controller_cls, protocol_type)


def set_default_motor_driver(name: str) -> None:
    """
    设置默认驱动（便捷函数）
    
    Args:
        name: 驱动名称
    """
    DriverManager.set_default_driver(name)


# ==================== 在模块加载时注册内置驱动 ====================

def _register_builtin_drivers():
    """注册内置驱动（ZDT）"""
    try:
        from .drivers.zdt_driver import ZDTDriverAdapter
        DriverManager.register_driver("zdt", ZDTDriverAdapter, "ucp")
        logger.debug("✓ 内置驱动已注册: ZDT (UCP)")
    except ImportError as e:
        logger.error(f"✗ ZDT驱动注册失败: {e}")


# 自动注册内置驱动
_register_builtin_drivers()

