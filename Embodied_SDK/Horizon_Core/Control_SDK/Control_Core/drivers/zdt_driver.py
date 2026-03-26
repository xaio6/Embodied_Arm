# -*- coding: utf-8 -*-
"""
ZDT驱动适配器

将现有的ZDTMotorController包装成符合MotorControllerInterface的适配器，
支持通过ProtocolInterface进行通信。

特点：
- 完全兼容现有ZDTMotorController的所有功能
- 支持通过protocol参数注入不同的通信协议
- 保持向后兼容性
"""

import logging
from typing import Optional
from ..interfaces.motor_interface import MotorControllerInterface
from ..interfaces.protocol_interface import ProtocolInterface
from ..motor_controller_ucp_simple import ZDTMotorController as _ZDTMotorControllerImpl


class ZDTDriverAdapter(MotorControllerInterface):
    """
    ZDT驱动适配器
    
    功能：
    - 实现MotorControllerInterface接口
    - 内部委托给ZDTMotorController实现
    - 支持ProtocolInterface注入
    
    使用示例：
    ----------
    方式1：通过工厂创建（推荐）
    ```python
    from Control_Core import create_motor_controller
    motor = create_motor_controller(motor_id=1, port="COM31", driver_type="zdt")
    ```
    
    方式2：直接创建
    ```python
    from Control_Core.protocols import UcpProtocol
    from Control_Core.drivers import ZDTDriverAdapter
    
    protocol = UcpProtocol(port="COM31", baudrate=115200)
    motor = ZDTDriverAdapter(motor_id=1, protocol=protocol)
    motor.connect()
    ```
    
    方式3：向后兼容（旧代码仍然可用）
    ```python
    from Control_Core import ZDTMotorController
    motor = ZDTMotorController(motor_id=1, port="COM31")  # 仍然支持
    ```
    """
    
    def __init__(self, motor_id: int, protocol: ProtocolInterface, **kwargs):
        """
        初始化ZDT驱动适配器
        
        Args:
            motor_id: 电机ID (1-255)
            protocol: 通信协议实例（如UcpProtocol）
            **kwargs: 其他参数（传递给底层实现）
        """
        self.motor_id = motor_id
        self.protocol = protocol
        self.logger = logging.getLogger(f"ZDTDriverAdapter[ID:{motor_id}]")
        
        # 创建底层实现（注入protocol的client）
        self._impl: Optional[_ZDTMotorControllerImpl] = None
        self._impl_kwargs = kwargs
    
    def _ensure_impl(self):
        """延迟初始化底层实现（避免connect前创建client）"""
        if self._impl is None:
            # 创建ZDTMotorController，但不自动连接
            self._impl = _ZDTMotorControllerImpl(
                motor_id=self.motor_id,
                port=getattr(self.protocol, 'port', 'N/A'),
                baudrate=getattr(self.protocol, 'baudrate', 115200),
                auto_connect=False,  # 不自动连接，由我们控制
                **self._impl_kwargs
            )
            
            # 注入protocol的client（如果protocol已连接）
            if hasattr(self.protocol, 'client') and self.protocol.is_connected():
                self._impl.client = self.protocol.client
                self._impl._connected = True
    
    # ==================== 连接管理 ====================
    
    def connect(self) -> None:
        """连接电机"""
        self._ensure_impl()
        
        # 先连接protocol
        if not self.protocol.is_connected():
            self.protocol.connect()
        
        # 将protocol的client注入到实现中
        if hasattr(self.protocol, 'client'):
            self._impl.client = self.protocol.client
            self._impl._connected = True
            self.logger.info(f"ZDT驱动适配器已连接 (motor_id={self.motor_id})")
        else:
            raise RuntimeError(f"协议 {type(self.protocol).__name__} 不支持client注入")
    
    def disconnect(self) -> None:
        """断开连接"""
        if self._impl:
            # 注意：不断开protocol，因为可能被其他电机共享
            self._impl._connected = False
            self.logger.info(f"ZDT驱动适配器已断开 (motor_id={self.motor_id})")
    
    @property
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._impl is not None and self._impl._connected and self.protocol.is_connected()
    
    # ==================== 基本控制 ====================
    
    def enable(self) -> None:
        """使能电机"""
        self._ensure_impl()
        self._impl.enable()
    
    def disable(self) -> None:
        """失能电机"""
        self._ensure_impl()
        self._impl.disable()
    
    def stop(self) -> None:
        """立即停止"""
        self._ensure_impl()
        self._impl.stop()
    
    # ==================== 运动控制 ====================
    
    def move_to_position(self, position: float, speed: float, is_absolute: bool = True) -> None:
        """位置控制"""
        self._ensure_impl()
        self._impl.move_to_position(position=position, speed=speed, is_absolute=is_absolute)
    
    def move_to_position_trapezoid(self, position: float, max_speed: float, 
                                   acceleration: int, deceleration: int, 
                                   is_absolute: bool = True) -> None:
        """梯形曲线位置控制"""
        self._ensure_impl()
        self._impl.move_to_position_trapezoid(
            position=position,
            max_speed=max_speed,
            acceleration=acceleration,
            deceleration=deceleration,
            is_absolute=is_absolute
        )
    
    def set_speed(self, speed: float, acceleration: int = 1000) -> None:
        """速度控制"""
        self._ensure_impl()
        self._impl.set_speed(speed=speed, acceleration=acceleration)
    
    def set_torque(self, current: float, slope: int = 100) -> None:
        """力矩控制"""
        self._ensure_impl()
        self._impl.set_torque(current=current, slope=slope)
    
    # ==================== 状态读取 ====================
    
    def get_position(self) -> float:
        """读取当前位置（度）"""
        self._ensure_impl()
        return self._impl.get_position()
    
    def get_speed(self) -> float:
        """读取当前速度（RPM）"""
        self._ensure_impl()
        return self._impl.get_speed()
    
    def get_motor_status(self):
        """读取电机状态"""
        self._ensure_impl()
        return self._impl.get_motor_status()
    
    def get_temperature(self) -> float:
        """读取温度（°C）"""
        self._ensure_impl()
        return self._impl.get_temperature()
    
    def get_bus_voltage(self) -> float:
        """读取总线电压（V）"""
        self._ensure_impl()
        return self._impl.get_bus_voltage()
    
    def get_current(self) -> float:
        """读取电流（A）"""
        self._ensure_impl()
        return self._impl.get_current()
    
    def get_version(self) -> dict:
        """读取版本信息"""
        self._ensure_impl()
        return self._impl.get_version()
    
    # ==================== 回零功能 ====================
    
    def trigger_homing(self, mode: int = 4, **kwargs) -> None:
        """触发回零"""
        self._ensure_impl()
        # 兼容旧API的homing_mode参数
        if 'homing_mode' in kwargs:
            mode = kwargs.pop('homing_mode')
        self._impl.trigger_homing(mode=mode, **kwargs)
    
    def get_homing_status(self) -> dict:
        """读取回零状态"""
        self._ensure_impl()
        return self._impl.get_homing_status()
    
    def is_homing_complete(self) -> bool:
        """检查回零是否完成"""
        self._ensure_impl()
        return self._impl.is_homing_complete()
    
    # ==================== 其他功能 ====================
    
    def set_zero_position(self, save_to_chip: bool = True) -> None:
        """设置当前位置为零点"""
        self._ensure_impl()
        self._impl.set_zero_position(save_to_chip=save_to_chip)
    
    # ==================== 兼容性属性（GUI需要）====================
    
    @property
    def control_actions(self):
        """兼容旧API：motor.control_actions.enable()"""
        return self
    
    @property
    def read_parameters(self):
        """兼容旧API：motor.read_parameters.get_position()"""
        return self
    
    @property
    def homing_commands(self):
        """兼容旧API：motor.homing_commands.trigger_homing()"""
        return self

    @property
    def trigger_actions(self):
        """兼容旧API：motor.trigger_actions.clear_position()/release_stall_protection()"""
        return self

    @property
    def modify_parameters(self):
        """兼容旧API：motor.modify_parameters.set_motor_id()/modify_drive_parameters()"""
        return self

    @property
    def can_interface(self):
        """兼容旧API占位：UCP模式下不参与通信"""
        self._ensure_impl()
        return getattr(self._impl, "can_interface", None)

    @can_interface.setter
    def can_interface(self, value):
        self._ensure_impl()
        try:
            self._impl.can_interface = value
        except Exception:
            # 兜底：不阻塞上层
            pass
    
    @property
    def command_builder(self):
        """兼容旧API：motor.command_builder.position_mode_direct()"""
        self._ensure_impl()
        return self._impl.command_builder
    
    def multi_motor_command(self, *args, **kwargs):
        """多机聚合命令（委托给实现）"""
        self._ensure_impl()
        return self._impl.multi_motor_command(*args, **kwargs)
    
    # ==================== 扩展方法（委托给实现）====================
    
    def __getattr__(self, name: str):
        """
        代理其他方法调用到底层实现
        
        这确保了即使接口中未定义的方法（如wait_for_position等）
        也能正常工作，完全向后兼容。
        """
        self._ensure_impl()
        if hasattr(self._impl, name):
            return getattr(self._impl, name)
        raise AttributeError(f"'{type(self).__name__}' 和 '{type(self._impl).__name__}' 都没有属性 '{name}'")

