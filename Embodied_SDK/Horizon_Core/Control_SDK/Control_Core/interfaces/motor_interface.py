# -*- coding: utf-8 -*-
"""
电机控制器抽象接口

所有电机驱动适配器必须实现此接口，确保不同厂家的驱动板
都能提供统一的API给上层应用使用。

扩展指南：
----------
如果要添加新的驱动板（如步科、汇川、台达等），请：

1. 继承 MotorControllerInterface
2. 实现所有抽象方法
3. 在 motor_factory.py 中注册新驱动
4. 创建对应的协议实现（如需要）

示例：
------
```python
class StepperDriverAdapter(MotorControllerInterface):
    def __init__(self, motor_id, protocol):
        self.motor_id = motor_id
        self.protocol = protocol
    
    def connect(self):
        # 步科驱动板的连接逻辑
        ...
    
    def enable(self):
        # 步科驱动板的使能逻辑
        ...
```
"""

from abc import ABC, abstractmethod
from typing import Optional


class MotorControllerInterface(ABC):
    """
    电机控制器抽象接口
    
    定义了所有电机控制器必须实现的标准方法。
    不同厂家的驱动板通过实现此接口来提供统一的API。
    """
    
    # ==================== 连接管理 ====================
    
    @abstractmethod
    def connect(self) -> None:
        """连接电机"""
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """断开连接"""
        pass
    
    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """检查是否已连接"""
        pass
    
    # ==================== 基本控制 ====================
    
    @abstractmethod
    def enable(self) -> None:
        """使能电机"""
        pass
    
    @abstractmethod
    def disable(self) -> None:
        """失能电机"""
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """立即停止"""
        pass
    
    # ==================== 运动控制 ====================
    
    @abstractmethod
    def move_to_position(self, position: float, speed: float, is_absolute: bool = True) -> None:
        """
        位置控制
        
        Args:
            position: 目标位置（度）
            speed: 运动速度（RPM）
            is_absolute: 是否绝对位置
        """
        pass
    
    @abstractmethod
    def move_to_position_trapezoid(self, position: float, max_speed: float, 
                                   acceleration: int, deceleration: int, 
                                   is_absolute: bool = True) -> None:
        """
        梯形曲线位置控制
        
        Args:
            position: 目标位置（度）
            max_speed: 最大速度（RPM）
            acceleration: 加速度（RPM/s）
            deceleration: 减速度（RPM/s）
            is_absolute: 是否绝对位置
        """
        pass
    
    @abstractmethod
    def set_speed(self, speed: float, acceleration: int = 1000) -> None:
        """
        速度控制
        
        Args:
            speed: 目标速度（RPM）
            acceleration: 加速度（RPM/s）
        """
        pass
    
    @abstractmethod
    def set_torque(self, current: float, slope: int = 100) -> None:
        """
        力矩控制
        
        Args:
            current: 目标电流（mA）
            slope: 电流斜率（mA/s）
        """
        pass
    
    # ==================== 状态读取 ====================
    
    @abstractmethod
    def get_position(self) -> float:
        """读取当前位置（度）"""
        pass
    
    @abstractmethod
    def get_speed(self) -> float:
        """读取当前速度（RPM）"""
        pass
    
    @abstractmethod
    def get_motor_status(self):
        """
        读取电机状态
        
        Returns:
            对象或字典，包含以下字段：
            - enabled: 使能状态
            - in_position: 到位状态
            - stalled: 堵转状态（可选）
            - 其他驱动板特定状态
        """
        pass
    
    @abstractmethod
    def get_temperature(self) -> float:
        """读取温度（°C）"""
        pass
    
    @abstractmethod
    def get_bus_voltage(self) -> float:
        """读取总线电压（V）"""
        pass
    
    @abstractmethod
    def get_current(self) -> float:
        """读取电流（A）"""
        pass
    
    @abstractmethod
    def get_version(self) -> dict:
        """
        读取版本信息
        
        Returns:
            dict: 版本信息字典，至少包含 'firmware' 字段
        """
        pass
    
    # ==================== 回零功能 ====================
    
    @abstractmethod
    def trigger_homing(self, mode: int = 4, **kwargs) -> None:
        """
        触发回零
        
        Args:
            mode: 回零模式（具体含义由驱动板定义）
            **kwargs: 其他参数（兼容性）
        """
        pass
    
    @abstractmethod
    def get_homing_status(self) -> dict:
        """读取回零状态"""
        pass
    
    def is_homing_complete(self) -> bool:
        """检查回零是否完成（可选实现）"""
        return not self.get_homing_status().get('homing_in_progress', False)
    
    # ==================== 其他功能 ====================
    
    @abstractmethod
    def set_zero_position(self, save_to_chip: bool = True) -> None:
        """设置当前位置为零点"""
        pass
    
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

