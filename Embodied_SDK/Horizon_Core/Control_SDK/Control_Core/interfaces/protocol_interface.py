# -*- coding: utf-8 -*-
"""
通信协议抽象接口

定义了通用的通信协议接口，允许使用不同的通信方式（UCP、Modbus、CANopen等）
来与驱动板通信。

扩展指南：
----------
如果要添加新的通信协议（如Modbus RTU、EtherCAT等），请：

1. 继承 ProtocolInterface
2. 实现所有抽象方法
3. 在驱动适配器中使用新协议

示例：
------
```python
class ModbusProtocol(ProtocolInterface):
    def __init__(self, port, baudrate):
        self.client = ModbusClient(port=port, baudrate=baudrate)
    
    def connect(self):
        self.client.connect()
    
    def request(self, command, args):
        # Modbus读写寄存器
        return self.client.read_holding_registers(command, args)
```
"""

from abc import ABC, abstractmethod
from typing import Any, Optional


class ProtocolInterface(ABC):
    """
    通信协议抽象接口
    
    定义了与驱动板通信的基本操作，
    不同的协议（UCP、Modbus、CANopen等）都实现此接口。
    """
    
    @abstractmethod
    def connect(self) -> None:
        """建立连接"""
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """断开连接"""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """检查是否已连接"""
        pass
    
    @abstractmethod
    def request(self, motor_id: int, command: Any, args: bytes = b"", 
                timeout_ms: int = 1500) -> Any:
        """
        发送请求并接收响应
        
        Args:
            motor_id: 电机ID
            command: 命令码（具体类型由协议决定）
            args: 命令参数（字节串）
            timeout_ms: 超时时间（毫秒）
            
        Returns:
            响应对象（具体类型由协议决定）
        """
        pass

