# -*- coding: utf-8 -*-
"""
UCP连接池管理模块

用于多电机共享同一个串口连接，避免重复占用串口
"""

import logging
from typing import Dict, Optional
from threading import Lock


class UcpConnectionPool:
    """
    UCP串口连接池（单例模式）
    
    多个电机控制器可以共享同一个UCP客户端连接
    """
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._connections: Dict[str, 'UcpClient'] = {}  # key: "port:baudrate"
        self._ref_counts: Dict[str, int] = {}  # 引用计数
        self._connection_lock = Lock()
        self.logger = logging.getLogger("UcpConnectionPool")
        self._initialized = True
    
    @classmethod
    def instance(cls):
        """获取连接池单例实例"""
        return cls()
    
    def get_connection_key(self, port: str, baudrate: int) -> str:
        """生成连接键"""
        return f"{port}:{baudrate}"
    
    def get_or_create(self, port: str, baudrate: int) -> 'UcpClient':
        """
        获取或创建UCP客户端连接
        
        Args:
            port: 串口号
            baudrate: 波特率
            
        Returns:
            共享的UcpClient实例
        """
        key = self.get_connection_key(port, baudrate)
        
        with self._connection_lock:
            if key not in self._connections:
                # 导入并创建UcpClient
                from .ucp_sdk import UcpClient
                client = UcpClient(port=port, baud=baudrate)
                
                self._connections[key] = client
                self._ref_counts[key] = 0
                # 连接池内部细节默认不刷屏；需要排查连接复用/串口问题时再开 DEBUG。
                self.logger.debug(f"创建新的UCP连接: {key}")
            
            # 增加引用计数
            self._ref_counts[key] += 1
            self.logger.debug(f"UCP连接引用计数 +1: {key} (当前: {self._ref_counts[key]})")
            
            return self._connections[key]
    
    def connect(self, port: str, baudrate: int) -> 'UcpClient':
        """
        连接或获取已连接的客户端
        
        Args:
            port: 串口号
            baudrate: 波特率
            
        Returns:
            已连接的UcpClient实例
        """
        client = self.get_or_create(port, baudrate)
        
        # 如果还未连接，则连接
        if not hasattr(client, '_connected') or not client._connected:
            with self._connection_lock:
                # 双重检查
                if not hasattr(client, '_connected') or not client._connected:
                    client.connect()
                    client._connected = True
                    self.logger.debug(f"UCP连接已建立: {port}:{baudrate}")
        
        return client
    
    def release(self, port: str, baudrate: int):
        """
        释放连接引用
        
        当引用计数为0时，自动断开并删除连接
        
        Args:
            port: 串口号
            baudrate: 波特率
        """
        key = self.get_connection_key(port, baudrate)
        
        with self._connection_lock:
            if key not in self._connections:
                return
            
            # 减少引用计数
            self._ref_counts[key] -= 1
            self.logger.debug(f"UCP连接引用计数 -1: {key} (当前: {self._ref_counts[key]})")
            
            # 如果引用计数为0，断开并删除连接
            if self._ref_counts[key] <= 0:
                try:
                    client = self._connections[key]
                    if hasattr(client, 'disconnect'):
                        client.disconnect()
                    self.logger.debug(f"UCP连接已断开并移除: {key}")
                except Exception as e:
                    self.logger.warning(f"断开UCP连接时出错: {e}")
                finally:
                    del self._connections[key]
                    del self._ref_counts[key]
    
    def is_connected(self, port: str, baudrate: int) -> bool:
        """
        检查指定连接是否已建立
        
        Args:
            port: 串口号
            baudrate: 波特率
            
        Returns:
            是否已连接
        """
        key = self.get_connection_key(port, baudrate)
        with self._connection_lock:
            if key not in self._connections:
                return False
            client = self._connections[key]
            return hasattr(client, '_connected') and client._connected
    
    def get_ref_count(self, port: str, baudrate: int) -> int:
        """
        获取指定连接的引用计数
        
        Args:
            port: 串口号
            baudrate: 波特率
            
        Returns:
            引用计数
        """
        key = self.get_connection_key(port, baudrate)
        with self._connection_lock:
            return self._ref_counts.get(key, 0)
    
    def disconnect_all(self):
        """断开所有连接（清理资源）"""
        with self._connection_lock:
            for key, client in list(self._connections.items()):
                try:
                    if hasattr(client, 'disconnect'):
                        client.disconnect()
                    self.logger.debug(f"关闭UCP连接: {key}")
                except Exception as e:
                    self.logger.warning(f"关闭UCP连接时出错 {key}: {e}")
            
            self._connections.clear()
            self._ref_counts.clear()
    
    def close_all(self):
        """关闭所有连接（别名，兼容性）"""
        self.disconnect_all()

