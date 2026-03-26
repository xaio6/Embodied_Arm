#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UCP 客户端 - 与 OmniCAN 固件通信的核心类
"""

from __future__ import annotations

import struct
import time
from dataclasses import dataclass
from typing import Optional

import serial
from serial.tools import list_ports
from threading import Lock

from .constants import (
    UCP_VERSION, 
    UCP_TYPE_REQUEST, 
    UCP_TYPE_RESPONSE,
    TlvTags,
    DriverType,
)


@dataclass
class UcpResponse:
    """UCP 响应数据结构"""
    status: int         # 状态码 (0=成功)
    err_code: int       # 错误码
    data: bytes         # 响应数据
    diag: bytes         # 诊断信息


# ============================================================================
# UCP 协议工具函数
# ============================================================================

def crc16_ibm(data: bytes) -> int:
    """
    计算 CRC16-IBM 校验码
    
    多项式: 0xA001
    初始值: 0xFFFF
    """
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            lsb = crc & 1
            crc >>= 1
            if lsb:
                crc ^= 0xA001
    return crc & 0xFFFF


def tlv(tag: int, value: bytes) -> bytes:
    """构建 TLV 数据块"""
    return bytes([tag]) + struct.pack("<H", len(value)) + value


def build_ucp_request(seq: int, payload_tlvs: bytes) -> bytes:
    """
    构建 UCP 请求帧
    
    格式: 0x55 0xAA | ver | type | seq(u16) | len(u16) | payload | crc16(u16)
    """
    header = struct.pack("<BBHH", UCP_VERSION, UCP_TYPE_REQUEST, seq, len(payload_tlvs))
    crc = crc16_ibm(header + payload_tlvs)
    return b"\x55\xAA" + header + payload_tlvs + struct.pack("<H", crc)


def parse_tlvs(buf: bytes) -> dict:
    """解析 TLV 数据块"""
    out = {}
    i = 0
    while i + 3 <= len(buf):
        tag = buf[i]
        length = buf[i + 1] | (buf[i + 2] << 8)
        i += 3
        if i + length > len(buf):
            break
        out[tag] = buf[i:i + length]
        i += length
    return out


def read_ucp_frame(ser: serial.Serial, timeout_s: float = 2.0) -> tuple:
    """
    读取 UCP 响应帧
    
    Returns:
        (type, seq, payload)
    """
    # 低延迟 + 稳定性平衡：
    # - 使用很小的 blocking timeout，避免 0.0 造成“忙等/平台差异”
    # - 优先读取 in_waiting，但在无数据时允许短暂阻塞等待数据到达
    ser.timeout = 0.02
    start = time.time()
    data = bytearray()

    def try_extract():
        # 查找帧头 0x55 0xAA
        for j in range(len(data) - 1):
            if data[j] == 0x55 and data[j + 1] == 0xAA:
                if len(data) < j + 2 + 6:  # 至少需要头部
                    return None
                
                frame_type = data[j + 3]
                seq = data[j + 4] | (data[j + 5] << 8)
                payload_len = data[j + 6] | (data[j + 7] << 8)
                total = 2 + 6 + payload_len + 2
                
                if len(data) < j + total:
                    return None
                
                frame = bytes(data[j:j + total])
                header = frame[2:2 + 6]
                payload = frame[2 + 6:2 + 6 + payload_len]
                got_crc = frame[-2] | (frame[-1] << 8)
                calc_crc = crc16_ibm(header + payload)
                
                if got_crc != calc_crc:
                    # CRC 错误，跳过这个字节继续查找
                    del data[:j + 1]
                    return None
                
                # 成功提取帧
                del data[:j + total]
                return frame_type, seq, payload
        
        # 防止缓冲区无限增长
        if len(data) > 2048:
            del data[:-2]
        return None

    while time.time() - start < timeout_s:
        n = 0
        try:
            n = int(getattr(ser, "in_waiting", 0) or 0)
        except Exception:
            n = 0
        # 有多少读多少；没有数据时读 1 个字节以触发底层轮询，但不阻塞
        chunk = ser.read(min(512, n) if n > 0 else 1)
        if chunk:
            data.extend(chunk)
            result = try_extract()
            if result:
                return result
        else:
            time.sleep(0.001)
    
    raise TimeoutError("等待 UCP 响应超时")


# ============================================================================
# UCP 客户端类
# ============================================================================

class UcpClient:
    """
    UCP 客户端
    
    负责与 OmniCAN 固件通信，管理请求序号与串口连接
    
    使用示例:
        client = UcpClient(port='COM13', baud=115200)
        client.connect()
        
        resp = client.request(
            motor_id=1,
            opcode=0x20,  # READ_REALTIME_POSITION
            args=b"",
            timeout_ms=1000
        )
        
        if resp.status == 0:
            print(f"数据: {resp.data.hex()}")
        
        client.disconnect()
    """
    
    def __init__(self, port: str = 'COM13', baud: int = 115200, driver_type: int = DriverType.ZDT):
        """
        初始化 UCP 客户端
        
        Args:
            port: 串口号 (例如: 'COM13', '/dev/ttyUSB0')
            baud: 波特率 (默认: 115200)
            driver_type: 驱动板类型 (默认: ZDT)
        """
        self.port = port
        self.baud = baud
        self.driver_type = driver_type
        self.ser: Optional[serial.Serial] = None
        self.seq: int = 1
        # 关键：共享串口连接池下必须串行化 request/response，防止多线程/多对象并发导致响应串扰与超时
        self._io_lock = Lock()
    
    def connect(self) -> None:
        """连接串口"""
        if self.ser and self.ser.is_open:
            return
        
        # 明确设置所有串口参数以确保兼容不同类型的串口
        # (USB CDC、USB虚拟串口、UART等)
        self.ser = serial.Serial(
            port=self.port,
            baudrate=self.baud,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=None,           # 读取超时在read_ucp_frame中动态设置
            write_timeout=2.0,      # 写入超时2秒，防止写入阻塞
            xonxoff=False,          # 禁用软件流控
            rtscts=False,           # 禁用硬件流控RTS/CTS
            dsrdtr=False            # 禁用硬件流控DSR/DTR
        )
        
        # 清空缓冲区，避免旧数据干扰
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()
        
        # 低延迟优化：USB CDC 通常不需要长时间等待
        time.sleep(0.05)
        self.seq = 1
    
    def disconnect(self) -> None:
        """断开串口连接"""
        if self.ser:
            try:
                self.ser.close()
            finally:
                self.ser = None
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self.ser is not None and self.ser.is_open
    
    def request(
        self, 
        motor_id: int, 
        opcode: int, 
        args: bytes = b"", 
        timeout_ms: int = 1000,
        driver_type: Optional[int] = None
    ) -> UcpResponse:
        """
        发送 UCP 请求并等待响应
        
        Args:
            motor_id: 电机 ID (0-255, 0为广播)
            opcode: 操作码
            args: 参数字节 (小端序)
            timeout_ms: 超时时间 (毫秒)
            driver_type: 驱动板类型 (不指定则使用默认值)
        
        Returns:
            UcpResponse: 响应数据
        
        Raises:
            RuntimeError: 未连接或通信错误
            TimeoutError: 超时
        """
        if not self.ser:
            raise RuntimeError("未连接串口，请先调用 connect()")
        
        with self._io_lock:
            # 关键稳定性：发送请求前丢弃串口输入缓冲区的残留字节
            # 场景：若历史上有任何非 UCP 字节/半包残留，会导致 read_ucp_frame 长时间在噪声中找帧头，
            # 进而触发“等待响应超时”，上层就会出现多次重试造成 10s~20s 的卡顿。
            try:
                n0 = int(getattr(self.ser, "in_waiting", 0) or 0)
                if n0 > 0:
                    # 直接读出丢弃（比 reset_input_buffer 更温和，避免驱动兼容性问题）
                    _ = self.ser.read(n0)
            except Exception:
                pass

            # 构建 TLV 载荷
            driver = driver_type if driver_type is not None else self.driver_type
            payload = b"".join([
                tlv(TlvTags.MOTOR_ID, struct.pack("<B", motor_id)),
                tlv(TlvTags.DRIVER, struct.pack("<B", driver)),
                tlv(TlvTags.OPCODE, struct.pack("<B", opcode)),
                tlv(TlvTags.TIMEOUT_MS, struct.pack("<H", timeout_ms)),
                tlv(TlvTags.ARGS, args),
            ])
            
            # 发送请求
            frame = build_ucp_request(self.seq, payload)
            self.ser.write(frame)
            self.ser.flush()
            
            # 接收响应
            # 为轨迹/参数写等“较长响应”留出足够余量，同时不引入 2s 的固定地板
            read_timeout = max(0.6, timeout_ms / 1000.0 + 0.5)
            frame_type, rseq, rpayload = read_ucp_frame(self.ser, timeout_s=read_timeout)
        
        # 验证响应
        if frame_type != UCP_TYPE_RESPONSE or rseq != self.seq:
            raise RuntimeError(
                f"收到不匹配响应: type=0x{frame_type:02X} seq={rseq} "
                f"(期望 type=0x{UCP_TYPE_RESPONSE:02X} seq={self.seq})"
            )
        
        # 解析 TLV
        tlvs = parse_tlvs(rpayload)
        status = tlvs.get(TlvTags.STATUS, b"\xFF")[0]
        err_bytes = tlvs.get(TlvTags.ERR_CODE, b"\x00\x00")
        err_code = err_bytes[0] | (err_bytes[1] << 8) if len(err_bytes) == 2 else 0
        data = tlvs.get(TlvTags.DATA, b"")
        diag = tlvs.get(TlvTags.DIAG, b"")
        
        # 更新请求序号
        self.seq = (self.seq + 1) & 0xFFFF
        if self.seq == 0:
            self.seq = 1
        
        return UcpResponse(status=status, err_code=err_code, data=data, diag=diag)
    
    @staticmethod
    def list_ports() -> list:
        """列出所有可用串口"""
        return [p.device for p in list_ports.comports()]
    
    def __enter__(self):
        """支持 with 语句"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """支持 with 语句"""
        self.disconnect()

