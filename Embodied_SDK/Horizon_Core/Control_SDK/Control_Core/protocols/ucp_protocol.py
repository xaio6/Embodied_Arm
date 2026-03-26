# -*- coding: utf-8 -*-
"""
UCP (Universal Command Protocol) 协议实现

UCP是通过 OmniCAN 与电机驱动器通信的协议。
OmniCAN 内部封装了具体的驱动板协议（如ZDT的CAN协议），
Python端只需要通过UCP发送高层命令。
"""

import logging
from typing import Optional
from ..interfaces.protocol_interface import ProtocolInterface
from ..ucp_sdk import UcpClient, UcpResponse
from ..ucp_connection_pool import UcpConnectionPool


class UcpProtocol(ProtocolInterface):
    """
    UCP协议实现（通过 OmniCAN）
    
    特点：
    - 串口通信（Serial）
    - OmniCAN 作为中间层，处理CAN总线通信
    - 支持多电机共享同一个串口（通过motor_id区分）
    """
    
    def __init__(self, port: str, baudrate: int = 115200):
        """
        初始化UCP协议
        
        Args:
            port: 串口号（如 COM31）
            baudrate: 波特率（默认115200）
        """
        self.port = port
        self.baudrate = baudrate
        self.client: Optional[UcpClient] = None
        self.logger = logging.getLogger(f"UcpProtocol[{port}]")
        self._connected = False
        self._pool = UcpConnectionPool.instance()
    
    def connect(self) -> None:
        """建立连接"""
        if self._connected and self.client is not None:
            return

        # 关键：使用连接池，避免“每个电机对象都重复打开同一个COM口”导致冲突/不稳定
        self.client = self._pool.connect(self.port, self.baudrate)
        self._connected = True
        try:
            ref = self._pool.get_ref_count(self.port, self.baudrate)
            self.logger.info(f"UCP连接已建立: {self.port}@{self.baudrate} (pool_ref={ref})")
        except Exception:
            self.logger.info(f"UCP连接已建立: {self.port}@{self.baudrate}")
    
    def disconnect(self) -> None:
        """断开连接"""
        if not self._connected:
            self.client = None
            return

        # 使用连接池：减少引用计数，最后一个释放者会真正关闭串口
        try:
            self._pool.release(self.port, self.baudrate)
        finally:
            self.client = None
            self._connected = False
        self.logger.info(f"UCP连接已断开: {self.port} (released)")
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected and self.client is not None
    
    def request(self, motor_id: int, command: int, args: bytes = b"", 
                timeout_ms: int = 1500) -> UcpResponse:
        """
        发送UCP请求
        
        Args:
            motor_id: 电机ID (1-255, 0为广播)
            command: UCP opcode
            args: 参数（字节串）
            timeout_ms: 超时时间（毫秒）
            
        Returns:
            UcpResponse: UCP响应对象
        """
        if not self.is_connected():
            raise RuntimeError("UCP未连接，请先调用 connect()")
        
        return self.client.request(
            motor_id=motor_id,
            opcode=command,
            args=args,
            timeout_ms=timeout_ms
        )

