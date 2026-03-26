# -*- coding: utf-8 -*-
"""
ZDT电机控制器 - UCP
使用内部集成的ucp_sdk，完全硬件保护
"""

import struct
import time
import os
import logging
import traceback
import json
from collections import Counter
from dataclasses import dataclass
from typing import Optional, Any, List, Tuple
from types import SimpleNamespace

# 导入内部UCP SDK
from .ucp_sdk import UcpClient, UcpResponse, NativeMotorData, opcodes
from .ucp_connection_pool import UcpConnectionPool


@dataclass
class DriveParameters:
    """
    驱动参数（UCP侧的“可写入序列化结构”）

    说明：
    - MODIFY_DRIVE_PARAMETERS(0x51) 固件要求固定 34 字节 args：save_to_chip(1B) + 参数区(33B)
    - READ_DRIVE_PARAMETERS(0x38) 返回为 ZDT 原始 data bytes，长度在不同固件/设备上可能不一致；
      这里尽力按“33B参数区”的布局解析，解析失败则保留 raw_data 并给出默认值，避免上层 AttributeError。
    """

    lock_enabled: bool = False
    control_mode: int = 1
    pulse_port_function: int = 0
    serial_port_function: int = 0
    enable_pin_mode: int = 0
    motor_direction: int = 0
    subdivision: int = 256
    subdivision_interpolation: bool = False
    auto_screen_off: bool = False
    lpf_intensity: int = 0
    open_loop_current: int = 1500
    closed_loop_max_current: int = 2000
    max_speed_limit: int = 3000
    current_loop_bandwidth: int = 1500
    uart_baudrate: int = 5
    can_baudrate: int = 3
    checksum_mode: int = 0
    response_mode: int = 0
    position_precision: bool = False
    stall_protection_enabled: bool = False
    stall_protection_speed: int = 50
    stall_protection_current: int = 1500
    stall_protection_time: int = 1000
    position_arrival_window: int = 10  # 常见实现：0.1°为单位，则 10 表示 1.0°

    # 兼容/调试字段
    raw_data: bytes = b""
    parsed_ok: bool = False

    @staticmethod
    def _le_u16(b: bytes) -> int:
        return int.from_bytes(b, byteorder="little", signed=False)

    @classmethod
    def from_raw(cls, raw: bytes) -> "DriveParameters":
        """
        尝试把 READ_DRIVE_PARAMETERS 的返回解析为结构体。

        注意：由于固件可能返回 7/24/33/35/37... 等多种长度，这里只对“33B参数区”做强解析；
        解析不成功则返回 default，并带上 raw_data。
        """
        p = cls(raw_data=raw, parsed_ok=False)
        if not raw:
            return p

        # 兼容两种常见情况：
        # - 33B：直接是参数区（a[1]..a[33] 对应的字段）
        # - 34B：开头可能带一个标志位（例如保存标志），则跳过首字节
        if len(raw) == 34:
            raw = raw[1:]

        if len(raw) < 33:
            return p

        try:
            # 字段布局参考：esp32_can_firmware/.../zdt_driver.cpp case 0x51（read_le16）
            p.lock_enabled = raw[0] != 0
            p.control_mode = raw[1]
            p.pulse_port_function = raw[2]
            p.serial_port_function = raw[3]
            p.enable_pin_mode = raw[4]
            p.motor_direction = raw[5]
            p.subdivision = cls._le_u16(raw[6:8])
            p.subdivision_interpolation = raw[8] != 0
            p.auto_screen_off = raw[9] != 0
            p.lpf_intensity = raw[10]
            p.open_loop_current = cls._le_u16(raw[11:13])
            p.closed_loop_max_current = cls._le_u16(raw[13:15])
            p.max_speed_limit = cls._le_u16(raw[15:17])
            p.current_loop_bandwidth = cls._le_u16(raw[17:19])
            p.uart_baudrate = raw[19]
            p.can_baudrate = raw[20]
            p.checksum_mode = raw[21]
            p.response_mode = raw[22]
            p.position_precision = raw[23] != 0
            p.stall_protection_enabled = raw[24] != 0
            p.stall_protection_speed = cls._le_u16(raw[25:27])
            p.stall_protection_current = cls._le_u16(raw[27:29])
            p.stall_protection_time = cls._le_u16(raw[29:31])
            p.position_arrival_window = cls._le_u16(raw[31:33])
            p.parsed_ok = True
        except Exception:
            # 保留默认值，仅携带 raw_data
            p.parsed_ok = False
        return p

    def to_ucp_args(self, save_to_chip: bool) -> bytes:
        """
        构造 MODIFY_DRIVE_PARAMETERS(0x51) 所需 args（小端）。
        """
        args = bytearray()
        args.append(1 if save_to_chip else 0)
        args.append(1 if self.lock_enabled else 0)
        args.append(int(self.control_mode) & 0xFF)
        args.append(int(self.pulse_port_function) & 0xFF)
        args.append(int(self.serial_port_function) & 0xFF)
        args.append(int(self.enable_pin_mode) & 0xFF)
        args.append(int(self.motor_direction) & 0xFF)
        args += int(self.subdivision).to_bytes(2, "little", signed=False)
        args.append(1 if self.subdivision_interpolation else 0)
        args.append(1 if self.auto_screen_off else 0)
        args.append(int(self.lpf_intensity) & 0xFF)
        args += int(self.open_loop_current).to_bytes(2, "little", signed=False)
        args += int(self.closed_loop_max_current).to_bytes(2, "little", signed=False)
        args += int(self.max_speed_limit).to_bytes(2, "little", signed=False)
        args += int(self.current_loop_bandwidth).to_bytes(2, "little", signed=False)
        args.append(int(self.uart_baudrate) & 0xFF)
        args.append(int(self.can_baudrate) & 0xFF)
        args.append(int(self.checksum_mode) & 0xFF)
        args.append(int(self.response_mode) & 0xFF)
        args.append(1 if self.position_precision else 0)
        args.append(1 if self.stall_protection_enabled else 0)
        args += int(self.stall_protection_speed).to_bytes(2, "little", signed=False)
        args += int(self.stall_protection_current).to_bytes(2, "little", signed=False)
        args += int(self.stall_protection_time).to_bytes(2, "little", signed=False)
        args += int(self.position_arrival_window).to_bytes(2, "little", signed=False)
        return bytes(args)


class ZDTMotorController:
    """
    ZDT电机控制器 - UCP硬件保护模式
    
    核心特点：
    - 直接使用motor_control_sdk与OmniCAN通信
    - 不暴露任何ZDT协议细节
    - 所有命令构建在OmniCAN固件中完成
    - 提供简洁的高级API
    
    使用示例：
        motor = ZDTMotorControllerUCPSimple(motor_id=1, port='COM5')
        motor.connect()
        motor.enable()
        motor.move_to_position(90, speed=200)
        motor.wait_for_position()
        position = motor.get_position()
        motor.disconnect()
    """
    
    def __init__(self, motor_id: int, port: str = 'COM5', baudrate: int = 115200, 
                 auto_connect: bool = True, **kwargs):
        """
        初始化控制器
        
        Args:
            motor_id: 电机ID (1-255, 0为广播)
            port: OmniCAN 串口号
            baudrate: 串口波特率
            auto_connect: 是否自动创建client（False时需要外部注入）
            **kwargs: 兼容性参数（旧的SLCAN参数会被自动忽略）
                - interface_type: 忽略，强制使用UCP
                - shared_interface: 忽略，自动使用连接池
                - 其他旧参数也会被忽略
        """
        # 忽略旧的SLCAN参数
        if kwargs.get('interface_type'):
            self.logger = logging.getLogger(f"ZDTMotorController[ID:{motor_id}]")
            # 兼容提示默认不刷屏；需要排查“为什么没走 slcan”时再开 DEBUG。
            self.logger.debug(f"注意：interface_type='{kwargs['interface_type']}' 已被忽略，使用UCP硬件保护模式")
        
        self.motor_id = motor_id
        self.port = port
        self.baudrate = baudrate
        self._auto_connect = auto_connect
        self._connected = False
        self._use_connection_pool = kwargs.get('shared_interface', True)  # 默认使用连接池
        
        self.client: Optional[UcpClient] = None
        self.parser = NativeMotorData(driver_type='ZDT')
        self.logger = logging.getLogger(f"ZDTMotorController[ID:{motor_id}]")

        # 轨迹状态日志抑制：避免轮询时刷屏，只在状态变更时记录一次
        self._traj_last_status: Optional[int] = None
        self._traj_logged_completed: bool = False
        self._traj_logged_error: bool = False

        # UCP 错误日志节流：避免在控制回路中对于同一 status/err_code/diag 刷屏
        # 仅在错误签名发生变化时输出一次 warning
        self._last_ucp_err_signature: Optional[Tuple[int, int, str]] = None

        # === 驱动参数缓存（用于修正反馈符号） ===
        # 固件侧存在 DriveParameters.motor_direction（0/1，电机旋转正方向设置）。
        # 若上位机只按“ZDT原始sign字节”解析 position/speed，而忽略 motor_direction，
        # 则可能出现“运动命令方向正确，但读回位置/速度符号相反”的情况。
        # 这会直接让依赖反馈的笛卡尔控制（示教器/手柄）走不直线，且常表现为 J4 反号。
        self._drive_params_cache: Optional[DriveParameters] = None
        self._drive_params_cache_ts: float = 0.0
        self._drive_params_cache_ttl_s: float = 5.0  # 低频刷新，避免高频读取参数造成总线压力

        # === 进程内“驱动 motor_direction”自动归一化（只为消除硬件侧方向干扰） ===
        # 目标：让 drive motor_direction 在 1~6 轴保持一致，把“关节语义方向”完全交给上层 motor_config.json 的 motor_directions(±1)。
        #
        # 触发条件（保守）：
        # - 同一进程内已连接齐 1..6 轴；
        # - 多数派 motor_direction 数量 >= 4；
        # - 存在少数派 outlier（通常 1 个，如 J4）。
        #
        # 行为（高风险）：
        # - 自动把 outlier 的 motor_direction 写成多数派值（save_to_chip=True，写回芯片）；
        # - 这属于“修改硬件参数”的行为，可能导致用户感知为“下次启动方向概率翻转”。
        #
        # 因此：默认禁用。只有显式设置环境变量 HORIZON_ENABLE_DRV_DIR_AUTO_FIX=1 才允许执行。
        if not hasattr(ZDTMotorController, "_drv_dir_seen"):
            ZDTMotorController._drv_dir_seen = {}          # type: ignore[attr-defined]
            ZDTMotorController._drv_dir_objs = {}          # type: ignore[attr-defined]
            ZDTMotorController._drv_dir_normalized = False # type: ignore[attr-defined]

    def _get_cached_drive_parameters(self) -> Optional[DriveParameters]:
        """低频读取并缓存驱动参数（失败则返回 None）。"""
        try:
            now = time.time()
            if (
                self._drive_params_cache is not None
                and (now - float(self._drive_params_cache_ts) <= float(self._drive_params_cache_ttl_s))
            ):
                return self._drive_params_cache
            p = self.get_drive_parameters()
            self._drive_params_cache = p
            self._drive_params_cache_ts = now
            return p
        except Exception:
            return None

    def _apply_motor_direction_to_feedback(self, value: Optional[float]) -> Optional[float]:
        """
        （保留为诊断/兼容钩子，默认不做任何处理）

        重要说明：
        - “CW/CCW 哪个算正方向”在不同电机/装配上并不存在统一标准；
        - 本项目已经提供 UI 侧的 `motor_directions(±1)` 用于逐轴修正方向，这是用户真正需要可控的“关节语义”；
        - 因此这里不应再根据固件 `motor_direction(0/1)` 去二次推导/强改符号，否则会和 UI 配置叠加，造成不可预期的翻转。
        """
        return value
    
    # ==================== 连接管理 ====================
    
    def connect(self) -> None:
        """连接 OmniCAN（自动使用连接池共享串口）"""
        if self._use_connection_pool:
            # 使用连接池模式（多电机共享串口）
            pool = UcpConnectionPool.instance()
            self.client = pool.connect(self.port, self.baudrate)
            self._connected = True
            
            # 获取引用计数
            ref_count = pool.get_ref_count(self.port, self.baudrate)
            # 连接细节默认不刷屏；排障时再开 DEBUG。
            self.logger.debug(f"使用共享串口连接模式: {self.port}")
            self.logger.debug(f"已连接（UCP硬件保护模式，共享连接，引用计数={ref_count}）")
        elif self._auto_connect:
            # 独占模式（单电机独占串口，不推荐）
            if self.client is None:
                self.client = UcpClient(port=self.port, baud=self.baudrate)
            if not self._connected:
                self.client.connect()
                self._connected = True
            self.logger.debug(f"已连接（UCP硬件保护模式，独占连接）: {self.port}")
        else:
            # 手动模式：client由外部注入
            if self.client is None:
                raise RuntimeError("auto_connect=False时，需要外部注入client")
            self._connected = True
            self.logger.debug(f"使用外部注入的client")

        # 连接后低频读取一次驱动参数，便于排查“读回符号与运动方向不一致”的问题。
        # 这里打印一条 TRACE（每电机仅一次），避免依赖 logger 级别导致现场看不到关键信息。
        try:
            p = self.get_drive_parameters()
            md = int(getattr(p, "motor_direction", 0) or 0)
            try:
                # 夹爪（内部电机）不输出具体ID，避免上层日志暴露内部映射
                if int(getattr(self, "motor_id", 0) or 0) == 7:
                    print(f"[TRACE][GRIPPER_PARAMS] motor_direction={md} parsed_ok={getattr(p,'parsed_ok',False)}")
                else:
                    print(f"[TRACE][DRV_PARAMS] id={self.motor_id} motor_direction={md} parsed_ok={getattr(p,'parsed_ok',False)}")
            except Exception:
                pass
            self._drive_params_cache = p
            self._drive_params_cache_ts = time.time()

            # ---- 自动归一化（默认禁用）：收集 1..6 轴的 motor_direction，遇到 outlier 自动写回多数派 ----
            enable_autofix = (os.environ.get("HORIZON_ENABLE_DRV_DIR_AUTO_FIX") or "").strip().lower() in (
                "1", "true", "yes", "y", "on"
            )
            if enable_autofix:
                try:
                    mid = int(getattr(self, "motor_id", 0) or 0)
                    if 1 <= mid <= 6:
                        try:
                            ZDTMotorController._drv_dir_seen[mid] = int(md)  # type: ignore[attr-defined]
                            ZDTMotorController._drv_dir_objs[mid] = self     # type: ignore[attr-defined]
                        except Exception:
                            pass

                        if not bool(getattr(ZDTMotorController, "_drv_dir_normalized", False)):  # type: ignore[attr-defined]
                            seen = dict(getattr(ZDTMotorController, "_drv_dir_seen", {}) or {})  # type: ignore[attr-defined]
                            if all(i in seen for i in range(1, 7)):
                                counts = Counter(int(v) for v in seen.values())
                                baseline, baseline_n = counts.most_common(1)[0]
                                outliers = [i for i, v in seen.items() if int(v) != int(baseline)]

                                if int(baseline_n) >= 4 and outliers:
                                    for oid in outliers:
                                        try:
                                            obj = getattr(ZDTMotorController, "_drv_dir_objs", {}).get(oid)  # type: ignore[attr-defined]
                                            if obj is None:
                                                continue
                                            old_p = obj.get_drive_parameters()
                                            old_md = int(getattr(old_p, "motor_direction", 0) or 0)
                                            if old_md == int(baseline):
                                                continue
                                            setattr(old_p, "motor_direction", int(baseline))
                                            r = obj.modify_drive_parameters(old_p, save_to_chip=True, timeout_ms=2000)
                                            ok = bool(getattr(r, "success", False))
                                            print(f"[TRACE][DRV_DIR_FIX] id={oid} motor_direction {old_md} -> {int(baseline)} success={ok}")
                                            # 软刷新缓存，避免短时间内仍读旧值
                                            try:
                                                obj._drive_params_cache = old_p
                                                obj._drive_params_cache_ts = time.time()
                                            except Exception:
                                                pass
                                        except Exception as e:
                                            print(f"[TRACE][DRV_DIR_FIX] id={oid} failed err={e}")

                                # 只评估一次（避免每次 connect 都写）
                                ZDTMotorController._drv_dir_normalized = True  # type: ignore[attr-defined]
                except Exception:
                    pass
        except Exception:
            pass
    
    def disconnect(self) -> None:
        """断开连接"""
        if self._use_connection_pool:
            # 使用连接池模式：释放引用
            pool = UcpConnectionPool.instance()
            pool.release(self.port, self.baudrate)
            self._connected = False
            self.logger.debug(f"已断开（释放连接池引用）")
        elif self._auto_connect:
            # 独占自动模式：断开并清理
            if self.client:
                self.client.disconnect()
                self.client = None
            self._connected = False
            self.logger.debug(f"已断开（关闭独占连接）")
        else:
            # 手动模式：只标记未连接
            self._connected = False
            self.logger.debug(f"已断开（保留外部client）")
    
    # ==================== 关节限位检查 ====================
    
    _joint_limits_cache: Optional[List[Tuple[float, float]]] = None
    _joint_limits_cache_src: str = ""
    _motor_config_cache: Optional[dict] = None
    
    @staticmethod
    def _load_joint_limits(force_reload: bool = False) -> Optional[List[Tuple[float, float]]]:
        """
        从配置文件加载关节限位
        
        Returns:
            关节限位列表 [(min1, max1), (min2, max2), ...]，共6个关节
            如果加载失败返回 None
        """
        if (not force_reload) and ZDTMotorController._joint_limits_cache is not None:
            return ZDTMotorController._joint_limits_cache
        
        # 尝试从多个可能的路径查找配置文件
        possible_config_dirs = []
        
        # 1. 从当前文件位置推导项目根目录
        current_file = os.path.abspath(__file__)
        # Horizon_Core/Control_SDK/Control_Core/motor_controller_ucp_simple.py -> 项目根目录
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file))))
        possible_config_dirs.append(os.path.join(project_root, "config"))
        
        # 2. 尝试从工作目录查找
        try:
            cwd = os.getcwd()
            possible_config_dirs.append(os.path.join(cwd, "config"))
        except Exception:
            pass
        
        # 3. 尝试环境变量指定的配置目录
        try:
            import sys
            if not getattr(sys, "frozen", False):
                # 源码运行：优先使用项目内 config
                pass
            else:
                # 打包运行：尝试环境变量
                env_dir = os.environ.get("HORIZONARM_CONFIG_DIR", "").strip()
                if env_dir and os.path.isdir(env_dir):
                    possible_config_dirs.insert(0, env_dir)
                data_root = os.environ.get("HORIZON_DATA_DIR", "").strip()
                if data_root:
                    candidate = os.path.join(data_root, "config")
                    if os.path.isdir(candidate):
                        possible_config_dirs.insert(0, candidate)
        except Exception:
            pass
        
        # 查找第一个存在的配置文件
        dh_config_path = None
        all_config_path = None
        
        for config_dir in possible_config_dirs:
            candidate_dh = os.path.join(config_dir, "dh_parameters_config.json")
            candidate_all = os.path.join(config_dir, "all_parameter_config.json")
            if os.path.exists(candidate_dh) and dh_config_path is None:
                dh_config_path = candidate_dh
            if os.path.exists(candidate_all) and all_config_path is None:
                all_config_path = candidate_all
            if dh_config_path and all_config_path:
                break
        
        # 优先读取 dh_parameters_config.json
        if dh_config_path and os.path.exists(dh_config_path):
            try:
                with open(dh_config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    jl = config.get("joint_limits", {})
                    if isinstance(jl, dict):
                        limits = []
                        for i in range(1, 7):
                            v = jl.get(str(i), None)
                            if isinstance(v, list) and len(v) == 2:
                                mn, mx = float(v[0]), float(v[1])
                                if mn > mx:
                                    mn, mx = mx, mn
                                limits.append((mn, mx))
                        if len(limits) == 6:
                            ZDTMotorController._joint_limits_cache = limits
                            ZDTMotorController._joint_limits_cache_src = dh_config_path
                            return limits
            except Exception as e:
                pass
        
        # 回退到 all_parameter_config.json
        if all_config_path:
            try:
                with open(all_config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    # 递归查找 joint_limits
                    def find_joint_limits(obj):
                        if isinstance(obj, dict):
                            if "joint_limits" in obj and isinstance(obj["joint_limits"], list):
                                lst = obj["joint_limits"]
                                if len(lst) == 6 and all(isinstance(x, list) and len(x) == 2 for x in lst):
                                    limits = []
                                    for x in lst:
                                        mn, mx = float(x[0]), float(x[1])
                                        if mn > mx:
                                            mn, mx = mx, mn
                                        limits.append((mn, mx))
                                    return limits
                            for v in obj.values():
                                r = find_joint_limits(v)
                                if r:
                                    return r
                        elif isinstance(obj, list):
                            for v in obj:
                                r = find_joint_limits(v)
                                if r:
                                    return r
                        return None
                    
                    limits = find_joint_limits(config)
                    if limits and len(limits) == 6:
                        ZDTMotorController._joint_limits_cache = limits
                        ZDTMotorController._joint_limits_cache_src = all_config_path
                        return limits
            except Exception:
                pass
        
        return None
    
    @staticmethod
    def _load_motor_config(force_reload: bool = False) -> Optional[dict]:
        """
        从配置文件加载电机配置（减速比和方向）
        
        Returns:
            电机配置字典，包含 motor_reducer_ratios 和 motor_directions
            如果加载失败返回 None
        """
        if (not force_reload) and ZDTMotorController._motor_config_cache is not None:
            return ZDTMotorController._motor_config_cache
        
        # 尝试从多个可能的路径查找配置文件
        possible_config_dirs = []
        
        # 1. 从当前文件位置推导项目根目录
        current_file = os.path.abspath(__file__)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file))))
        possible_config_dirs.append(os.path.join(project_root, "config"))
        
        # 2. 尝试从工作目录查找
        try:
            cwd = os.getcwd()
            possible_config_dirs.append(os.path.join(cwd, "config"))
        except Exception:
            pass
        
        # 3. 尝试环境变量指定的配置目录
        try:
            import sys
            if not getattr(sys, "frozen", False):
                pass
            else:
                env_dir = os.environ.get("HORIZONARM_CONFIG_DIR", "").strip()
                if env_dir and os.path.isdir(env_dir):
                    possible_config_dirs.insert(0, env_dir)
                data_root = os.environ.get("HORIZON_DATA_DIR", "").strip()
                if data_root:
                    candidate = os.path.join(data_root, "config")
                    if os.path.isdir(candidate):
                        possible_config_dirs.insert(0, candidate)
        except Exception:
            pass
        
        # 默认配置
        default_config = {
            "motor_reducer_ratios": {
                "1": 50.0, "2": 50.0, "3": 50.0,
                "4": 30.0, "5": 30.0, "6": 30.0
            },
            "motor_directions": {
                "1": -1, "2": 1, "3": 1,
                "4": -1, "5": -1, "6": 1
            }
        }
        
        # 查找 motor_config.json
        motor_config_path = None
        for config_dir in possible_config_dirs:
            candidate = os.path.join(config_dir, "motor_config.json")
            if os.path.exists(candidate):
                motor_config_path = candidate
                break
        
        config = default_config.copy()
        
        if motor_config_path:
            try:
                with open(motor_config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if "motor_reducer_ratios" in loaded:
                        config["motor_reducer_ratios"].update(loaded["motor_reducer_ratios"])
                    if "motor_directions" in loaded:
                        config["motor_directions"].update(loaded["motor_directions"])
            except Exception:
                pass
        
        ZDTMotorController._motor_config_cache = config
        return config
    
    def _motor_angle_to_joint_angle(self, motor_angle: float, motor_id: int) -> float:
        """
        将电机角度转换为关节角度（输出端角度）
        
        参考其他功能的转换公式：
        - 关节角度 → 电机角度：motor_angle = joint_angle * reducer_ratio * direction
        - 电机角度 → 关节角度：joint_angle = motor_angle / (reducer_ratio * direction)
        
        Args:
            motor_angle: 电机角度（度）
            motor_id: 电机ID
            
        Returns:
            关节角度（度）
        """
        motor_config = self._load_motor_config()
        if motor_config is None:
            # 如果无法加载配置，假设减速比为1，方向为1
            return motor_angle
        
        reducer_ratio = float(motor_config.get("motor_reducer_ratios", {}).get(str(motor_id), 1.0))
        direction = int(motor_config.get("motor_directions", {}).get(str(motor_id), 1))
        
        # 关节角度 = 电机角度 / (减速比 * 方向)
        # 这是 motor_angle = joint_angle * reducer_ratio * direction 的逆运算
        joint_angle = motor_angle / (reducer_ratio * direction)
        
        return joint_angle
    
    def _parse_angles_from_args(self, opcode: int, args: bytes) -> List[Tuple[int, float]]:
        """
        从 opcode 和 args 中解析角度参数
        
        Args:
            opcode: 操作码
            args: 参数字节
            
        Returns:
            列表 [(motor_id, angle_deg), ...]，motor_id 从1开始（索引0对应关节1）
            如果无法解析或不是位置控制命令，返回空列表
        """
        angles = []
        
        try:
            # POSITION_DIRECT (0x12): <iHBB = 位置×10(4B), 速度×10(2B), is_absolute(1B), multi_sync(1B)
            if opcode == opcodes.POSITION_DIRECT and len(args) >= 8:
                pos_x10 = struct.unpack("<i", args[0:4])[0]
                angle_deg = pos_x10 / 10.0
                angles.append((self.motor_id, angle_deg))
            
            # POSITION_TRAPEZOID (0x13): <iHHHBB = 位置×10(4B), 速度×10(2B), 加速度(2B), 减速度(2B), is_absolute(1B), multi_sync(1B)
            elif opcode == opcodes.POSITION_TRAPEZOID and len(args) >= 10:
                pos_x10 = struct.unpack("<i", args[0:4])[0]
                angle_deg = pos_x10 / 10.0
                angles.append((self.motor_id, angle_deg))
            
            # Y42_MULTI_MOTOR (0x30): expected_motor_id(1B) + Y42帧
            # Y42帧格式: AA(1B) + 长度(2B BE) + payload + 6B(1B)
            # payload 中每个子命令: motor_id(1B) + ZDT命令
            # ZDT 0xFB位置命令: FB(1B) + Dir(1B) + Speed(2B BE) + Position(4B BE) + Abs/Rel(1B) + Sync(1B) + 6B(1B)
            elif opcode == opcodes.Y42_MULTI_MOTOR and len(args) >= 5:
                # 跳过 expected_motor_id(1B)
                y42_frame = args[1:]
                if len(y42_frame) >= 4 and y42_frame[0] == 0xAA:
                    # 解析长度
                    total_len = struct.unpack(">H", y42_frame[1:3])[0]
                    payload = y42_frame[3:-1]  # 去掉末尾的 0x6B
                    
                    # 解析子命令
                    idx = 0
                    while idx < len(payload):
                        if idx + 1 > len(payload):
                            break
                        motor_id = payload[idx]
                        idx += 1
                        
                        # 查找 ZDT 0xFB 命令（位置直通）
                        if idx < len(payload) and payload[idx] == 0xFB:
                            # FB + Dir(1B) + Speed(2B BE) + Position(4B BE) + Abs/Rel(1B) + Sync(1B) + 6B
                            # 字节布局: [FB] [Dir] [Speed_H] [Speed_L] [Pos_B3] [Pos_B2] [Pos_B1] [Pos_B0] [Abs/Rel] [Sync] [6B]
                            if idx + 11 <= len(payload):
                                # Position在ZDT命令中的位置：FB(0) + Dir(1) + Speed(2-3) + Position(4-7)
                                pos_val = struct.unpack(">I", payload[idx+4:idx+8])[0]
                                motor_angle_deg = pos_val / 10.0
                                angles.append((motor_id, motor_angle_deg))
                                idx += 11  # 跳过整个ZDT命令（11字节）
                            else:
                                break
                        else:
                            # 不是0xFB命令，跳过到下一个子命令（查找下一个motor_id或结束）
                            # 简单策略：跳过到下一个可能的0xFB或结束
                            found_next = False
                            for j in range(idx, min(idx + 20, len(payload))):
                                if payload[j] == 0xFB:
                                    idx = j - 1  # 回退1，因为外层会+1
                                    found_next = True
                                    break
                            if not found_next:
                                break
        except Exception:
            # 解析失败，返回空列表（不阻止下发，避免误判）
            pass
        
        return angles
    
    def _check_joint_limits_before_send(self, opcode: int, args: bytes) -> None:
        """
        在下发前检查关节限位
        
        Raises:
            RuntimeError: 如果角度超出限位
        """
        # 只检查位置控制相关的 opcode
        if opcode not in (opcodes.POSITION_DIRECT, opcodes.POSITION_TRAPEZOID, opcodes.Y42_MULTI_MOTOR):
            return
        
        # 加载关节限位
        limits = self._load_joint_limits()
        if limits is None:
            # 限位未配置，跳过检查
            return
        
        # 解析角度
        angles = self._parse_angles_from_args(opcode, args)
        if not angles:
            # 无法解析角度，跳过检查（可能是其他类型的命令）
            return
        
        # 检查每个角度（需要将电机角度转换为关节角度）
        violations = []
        for motor_id, motor_angle_deg in angles:
            # 将电机角度转换为关节角度
            joint_angle_deg = self._motor_angle_to_joint_angle(motor_angle_deg, motor_id)
            
            # motor_id 从1开始，转换为索引（0-5）
            joint_idx = motor_id - 1
            if 0 <= joint_idx < 6:
                min_limit, max_limit = limits[joint_idx]
                if joint_angle_deg < min_limit or joint_angle_deg > max_limit:
                    # 保存电机角度（目标角度）和关节角度，错误信息中显示电机角度
                    violations.append((motor_id, joint_idx + 1, motor_angle_deg, joint_angle_deg, min_limit, max_limit))
        
        if violations:
            # 构建错误消息（显示关节角度）
            msg_parts = ["⛔ 关节限位检查失败，拒绝下发命令："]
            for motor_id, joint_num, motor_angle, joint_angle, min_lim, max_lim in violations:
                msg_parts.append(
                    f"  电机{motor_id}(关节{joint_num}): 关节角度 {joint_angle:.2f}° 超出限位 [{min_lim:.2f}°, {max_lim:.2f}°]"
                )
            error_msg = "\n".join(msg_parts)
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def _request(
        self,
        opcode: int,
        args: bytes = b"",
        # 低延迟策略：实时控制与状态读取默认使用更短的超时，避免“无效等待”放大成卡顿。
        # 需要长时间的操作（例如回零/参数写入/轨迹上传）会在各自函数中显式传入更大的 timeout_ms。
        timeout_ms: int = 500,
        *,
        suppress_err_log: bool = False,
    ) -> UcpResponse:
        """发送UCP请求"""
        if not self.client:
            raise RuntimeError("未连接，请先调用 connect()")
        
        # 在下发前检查关节限位
        try:
            self._check_joint_limits_before_send(opcode, args)
        except RuntimeError:
            # 限位检查失败，直接抛出异常，阻止下发
            raise
        except Exception as e:
            # 限位检查过程中出现其他异常，记录但不阻止下发（避免限位检查本身的问题影响功能）
            self.logger.warning(f"关节限位检查异常（已放行）: {e}")
        
        try:
            resp = self.client.request(self.motor_id, opcode, args, timeout_ms)
        except TimeoutError as e:
            # 轮询/控制回路里“偶发丢包/总线瞬态”很常见：
            # - 让上层的重试逻辑基于 resp.status/err_code 生效（否则会被异常直接打断）
            # - 避免 logger.exception 打印 traceback 造成刷屏
            if not suppress_err_log:
                try:
                    msg = (
                        f"[UCP][TIMEOUT] id={self.motor_id} opcode=0x{opcode:02X} "
                        f"args={args.hex()} timeout_ms={timeout_ms} err={e}"
                    )
                    self.logger.warning(msg)
                except Exception:
                    pass
            # 约定：用 status=3 + err_code=0x4034 表示“等待ACK/响应超时”（与固件侧超时语义对齐）
            return UcpResponse(status=3, err_code=0x4034, data=b"", diag=b"")
        except Exception as e:
            try:
                msg = f"[UCP][EXC] id={self.motor_id} opcode=0x{opcode:02X} args={args.hex()} timeout_ms={timeout_ms} err={e}"
                if suppress_err_log:
                    self.logger.debug(msg)
                else:
                    self.logger.exception(msg)
            except Exception:
                pass
            raise

        # 关键：UCP 返回非 0 时，默认在终端输出一条“同款错误”方便诊断。
        # 但对“可恢复错误/会自动重试”的场景，应避免刷屏。
        status = int(getattr(resp, "status", 0) or 0)
        err_code = int(getattr(resp, "err_code", 0) or 0) & 0xFFFF
        recoverable_noisy = (status == 4 and err_code == 0x0101)

        # 正常返回时，重置错误签名，确保后续新的错误还能再次打印
        if status == 0:
            self._last_ucp_err_signature = None

        if (not suppress_err_log) and status != 0 and (not recoverable_noisy):
            try:
                diag_hex = resp.diag.hex() if getattr(resp, "diag", None) else ""
                signature = (status, err_code, diag_hex)
                # 仅在错误签名变化时输出一条 warning，避免同一错误在轮询中持续刷屏
                if signature != self._last_ucp_err_signature:
                    msg = (
                        f"[UCP][ERR] id={self.motor_id} opcode=0x{opcode:02X} args={args.hex()} "
                        f"status={status} err_code=0x{err_code:04X} diag={diag_hex}"
                    )
                    self.logger.warning(msg)
                    self._last_ucp_err_signature = signature
            except Exception:
                pass

        return resp

    # ==================== 旧SLCAN兼容字段（占位） ====================

    @property
    def can_interface(self) -> Any:
        """
        兼容旧代码：motor.can_interface = broadcast.can_interface

        UCP模式下该字段不参与通信，仅为避免旧脚本/文档路径触发 AttributeError。
        """
        return getattr(self, "_can_interface_compat", None)

    @can_interface.setter
    def can_interface(self, value: Any) -> None:
        self._can_interface_compat = value
        self.logger.warning("UCP模式下 can_interface 已弃用（仅兼容占位，不参与通信）")
    
    # ==================== 基础控制 ====================
    
    def enable(self, multi_sync: bool = False, **kwargs) -> None:
        """使能电机（单电机立即执行）
        
        多电机同步请使用：ZDTMotorControllerUCPSimple.y42_sync_enable()
        """
        if bool(multi_sync):
            raise RuntimeError("multi_sync 同步预加载已被禁用：本项目多机同步仅允许 Y42。")
        args = struct.pack("<BB", 1, int(bool(multi_sync)))  # enabled=1
        resp = self._request(opcodes.ENABLE, args)
        if resp.status != 0:
            err_msg = f"使能失败: status={resp.status}, err_code=0x{resp.err_code:04X}"
            if resp.diag:
                err_msg += f", diag={resp.diag.hex()}"
            self.logger.warning(err_msg)
            raise RuntimeError(err_msg)
        self.logger.info("电机已使能")
    
    def disable(self, multi_sync: bool = False, **kwargs) -> None:
        """失能电机（单电机立即执行）
        
        多电机同步请使用：ZDTMotorControllerUCPSimple.y42_sync_enable()
        """
        if bool(multi_sync):
            raise RuntimeError("multi_sync 同步预加载已被禁用：本项目多机同步仅允许 Y42。")
        args = struct.pack("<BB", 0, int(bool(multi_sync)))  # enabled=0
        resp = self._request(opcodes.ENABLE, args)
        if resp.status != 0:
            raise RuntimeError(f"失能失败: status={resp.status}")
        self.logger.info("电机已失能")
    
    def stop(self, multi_sync: bool = False, **kwargs) -> None:
        """立即停止"""
        if bool(multi_sync):
            raise RuntimeError("multi_sync 同步预加载已被禁用：本项目多机同步仅允许 Y42。")
        args = struct.pack("<B", int(bool(multi_sync)))
        resp = self._request(opcodes.STOP, args)
        if resp.status != 0:
            raise RuntimeError(f"停止失败: status={resp.status}")

    def emergency_stop(self) -> None:
        """紧急停止（兼容 TriggerActionsModule）：先 stop 再 disable，尽量进入安全状态"""
        try:
            self.logger.warning(f"EMERGENCY_STOP(id={self.motor_id})")
        except Exception:
            pass
        try:
            self.stop(multi_sync=False)
        except Exception as e:
            self.logger.warning(f"EMERGENCY_STOP stop 失败: {e}")
        try:
            self.disable(multi_sync=False)
        except Exception as e:
            self.logger.warning(f"EMERGENCY_STOP disable 失败: {e}")

    # 注意：本项目约束为“多机只允许 Y42 同步”，禁止旧的 Pre-load + SYNC_MOTION 触发方式。
    # 兼容层的 sync_motion() 入口保留在文件后部，但会直接抛错，防止误用。
    
    # ==================== 运动控制 ====================
    
    def move_to_position(
        self, 
        position: float, 
        speed: float = 200.0,
        is_absolute: bool = True,
        multi_sync: bool = False,
        timeout_ms: int = 2000,
        **kwargs
    ) -> None:
        """
        位置控制（单电机立即执行）
        
        多电机同步请使用：ZDTMotorControllerUCPSimple.y42_sync_position()
        
        Args:
            position: 目标位置（度）
            speed: 运动速度（RPM）
            is_absolute: 是否绝对位置（推荐True）
            timeout_ms: 超时时间（毫秒）
        """
        if bool(multi_sync):
            raise RuntimeError("multi_sync 同步预加载已被禁用：请使用 Y42 多机同步接口。")

        # ----------------------------
        # 兼容层：历史代码可能用 max_speed/acceleration/deceleration 调 move_to_position()
        # - 直通位置模式仅支持 speed
        # - 若传入了 acceleration/deceleration，则自动降级为梯形曲线位置模式
        # ----------------------------
        try:
            if "max_speed" in kwargs and kwargs.get("max_speed") is not None:
                speed = float(kwargs.get("max_speed"))
        except Exception:
            pass
        if ("acceleration" in kwargs) or ("deceleration" in kwargs):
            try:
                acc = int(kwargs.get("acceleration", 1000) or 1000)
            except Exception:
                acc = 1000
            try:
                dec = int(kwargs.get("deceleration", 1000) or 1000)
            except Exception:
                dec = 1000
            # 保持行为一致：在同一个入口里自动转梯形曲线
            return self.move_to_position_trapezoid(
                position=float(position),
                max_speed=float(speed),
                acceleration=int(acc),
                deceleration=int(dec),
                is_absolute=bool(is_absolute),
                multi_sync=bool(multi_sync),
                timeout_ms=int(timeout_ms),
            )
        pos_x10 = int(position * 10)
        speed_x10 = int(speed * 10)
        args = struct.pack("<iHBB", pos_x10, speed_x10, int(is_absolute), int(bool(multi_sync)))
        
        resp = self._request(opcodes.POSITION_DIRECT, args, timeout_ms)
        if resp.status != 0:
            err_msg = f"位置控制失败: status={resp.status}, err_code=0x{resp.err_code:04X}"
            if resp.diag:
                err_msg += f", diag={resp.diag.hex()}"
            raise RuntimeError(err_msg)
        
        self.logger.info(f"位置命令: {position}度 @ {speed}RPM")
    
    def move_to_position_trapezoid(
        self,
        position: float,
        max_speed: float = 200.0,
        acceleration: int = 1000,
        deceleration: int = 1000,
        is_absolute: bool = False,
        multi_sync: bool = False,
        timeout_ms: int = 2000
    ) -> None:
        """梯形曲线位置控制"""
        if bool(multi_sync):
            raise RuntimeError("multi_sync 同步预加载已被禁用：请使用 Y42 多机同步接口。")
        pos_x10 = int(position * 10)
        vmax_x10 = int(max_speed * 10)
        args = struct.pack("<iHHHBB", pos_x10, vmax_x10, acceleration, deceleration, 
                          int(is_absolute), int(multi_sync))
        
        resp = self._request(opcodes.POSITION_TRAPEZOID, args, timeout_ms)
        if resp.status != 0:
            raise RuntimeError(f"梯形位置控制失败: status={resp.status}")
    
    def set_speed(
        self, 
        speed: float, 
        acceleration: int = 1000,
        multi_sync: bool = False
    ) -> None:
        """速度控制"""
        if bool(multi_sync):
            raise RuntimeError("multi_sync 同步预加载已被禁用：请使用 Y42 多机同步接口。")
        rpm_x10 = int(speed * 10)
        if rpm_x10 < -32768 or rpm_x10 > 32767:
            raise ValueError(f"速度超出范围: {speed} RPM")
        
        args = struct.pack("<hHB", rpm_x10, acceleration, int(multi_sync))
        # 对实时速度控制：0x0101 常见为“设备忙/瞬态不可用”，在高频下发时出现较多。
        # 这里抑制 [UCP][ERR] 刷屏，并将 0x0101 视为可恢复（直接返回，让上层下一周期再发）。
        resp = self._request(opcodes.SPEED_MODE, args, timeout_ms=200, suppress_err_log=True)
        if resp.status != 0:
            try:
                ec = int(getattr(resp, "err_code", 0) or 0) & 0xFFFF
            except Exception:
                ec = 0
            if ec == 0x0101:
                return
            raise RuntimeError(f"速度控制失败: status={resp.status} err_code=0x{ec:04X}")
    
    def set_torque(self, current: int, slope: int = 1000, multi_sync: bool = False) -> None:
        """力矩/电流控制"""
        if bool(multi_sync):
            raise RuntimeError("multi_sync 同步预加载已被禁用：请使用 Y42 多机同步接口。")
        args = struct.pack("<hHB", int(current), int(slope), int(multi_sync))
        resp = self._request(opcodes.TORQUE_MODE, args)
        if resp.status != 0:
            raise RuntimeError(f"力矩控制失败: status={resp.status}")
    
    # ==================== 状态读取 ====================
    
    def get_position(self) -> float:
        """读取当前位置（度）"""
        # 偶发读失败（例如总线瞬态/超时）应自动重试，避免上层 UI/轨迹验证被打断。
        max_attempts = 3
        retry_delay_s = 0.03
        last_resp: Optional[UcpResponse] = None

        for attempt in range(1, max_attempts + 1):
            # 前几次失败不打印 [UCP][ERR]，最后一次失败再输出（避免刷屏）
            last = attempt == max_attempts
            resp = self._request(opcodes.READ_REALTIME_POSITION, timeout_ms=300, suppress_err_log=not last)
            last_resp = resp

            if getattr(resp, "status", 0) == 0:
                # 诊断输出（默认关闭，避免刷屏）：仅在显式开启时输出 J4 的“原始回包字节 + sign/pos_raw”
                # 注意：这里不做任何符号修正；符号修正应由上层 motor_config_manager.motor_directions(±1) 统一处理。
                try:
                    import os as _os
                    if str(_os.environ.get("HORIZON_TRACE_POS_RAW", "0")).strip() in ("1", "true", "True", "YES", "yes"):
                        if int(getattr(self, "motor_id", 0) or 0) == 4:
                            now = time.time()
                            last_ts = float(getattr(self, "_trace_pos_raw_last_ts", 0.0) or 0.0)
                            if now - last_ts >= 0.5:
                                setattr(self, "_trace_pos_raw_last_ts", now)
                                data = resp.data or b""
                                sign = int(data[0]) if len(data) >= 1 else None
                                pos_raw = struct.unpack(">I", data[1:5])[0] if len(data) >= 5 else None
                                hx = ""
                                try:
                                    hx = data.hex()
                                except Exception:
                                    hx = "<hex_fail>"
                                print(
                                    f"[TRACE][POS_RAW] id={self.motor_id} opcode=0x{opcodes.READ_REALTIME_POSITION:02X} "
                                    f"data={hx} sign={sign} pos_raw={pos_raw}"
                                )
                except Exception:
                    pass
                pos = self.parser.parse_position(resp.data)
                # 这里返回“电机原生坐标”的位置，方向修正由上层 motor_config_manager.motor_directions(±1) 统一处理。
                return float(pos or 0.0)

            # 仅对“可恢复”的失败做重试（常见：TIMEOUT/瞬态CAN错误）
            status = int(getattr(resp, "status", 0) or 0)
            err_code = int(getattr(resp, "err_code", 0) or 0)
            recoverable = (status in (3, 4)) or (err_code in (0x0101, 0x4034))
            if recoverable and attempt < max_attempts:
                time.sleep(retry_delay_s)
                continue

            # 不可恢复或已到最后一次
            diag_hex = ""
            try:
                diag_hex = resp.diag.hex() if getattr(resp, "diag", None) else ""
            except Exception:
                diag_hex = ""
            raise RuntimeError(f"读取位置失败: status={status} err_code=0x{err_code:04X} diag={diag_hex}")

        # 理论不可达：兜底
        if last_resp is not None:
            status = int(getattr(last_resp, "status", 0) or 0)
            err_code = int(getattr(last_resp, "err_code", 0) or 0)
            raise RuntimeError(f"读取位置失败: status={status} err_code=0x{err_code:04X}")
        raise RuntimeError("读取位置失败: unknown")
    
    def get_speed(self) -> float:
        """读取当前转速（RPM）"""
        resp = self._request(opcodes.READ_REALTIME_SPEED)
        if resp.status != 0:
            raise RuntimeError(f"读取速度失败: status={resp.status}")
        spd = self.parser.parse_speed(resp.data)
        # 这里返回“电机原生坐标”的速度，方向修正由上层 motor_config_manager.motor_directions(±1) 统一处理。
        return float(spd or 0.0)
    
    def get_motor_status(self):
        """
        读取电机状态（返回具有属性的对象，兼容GUI）
        
        Returns:
            SimpleNamespace对象，包含以下属性：
            - enabled: 使能状态
            - in_position: 到位状态
            - stalled: 堵转状态
            - stall_protection: 堵转保护状态
        """
        # 与 get_position 一致：对偶发 TIMEOUT/CAN_ERROR 做静默重试，避免高频轮询时刷屏
        max_attempts = 3
        retry_delay_s = 0.03
        last_resp: Optional[UcpResponse] = None

        for attempt in range(1, max_attempts + 1):
            last = attempt == max_attempts
            resp = self._request(opcodes.READ_MOTOR_STATUS, timeout_ms=300, suppress_err_log=not last)
            last_resp = resp
            if getattr(resp, "status", 0) == 0:
                break

            status = int(getattr(resp, "status", 0) or 0)
            err_code = int(getattr(resp, "err_code", 0) or 0)
            recoverable = (status in (3, 4)) or (err_code in (0x0101, 0x4034))
            if recoverable and attempt < max_attempts:
                time.sleep(retry_delay_s)
                continue

            diag_hex = ""
            try:
                diag_hex = resp.diag.hex() if getattr(resp, "diag", None) else ""
            except Exception:
                diag_hex = ""
            raise RuntimeError(f"读取状态失败: status={status} err_code=0x{err_code:04X} diag={diag_hex}")

        if last_resp is None:
            raise RuntimeError("读取状态失败: unknown")
        if resp.data and len(resp.data) >= 1:
            b = resp.data[0]
            status_dict = {
                'enabled': bool(b & 0x01),
                'in_position': bool(b & 0x02),
                'stalled': bool(b & 0x04),
                'stall_protection': bool(b & 0x08)
            }
            # 转换为对象，支持 .enabled 和 .in_position 等属性访问
            return SimpleNamespace(**status_dict)
        return SimpleNamespace(enabled=False, in_position=False, stalled=False, stall_protection=False)
    
    def get_temperature(self) -> float:
        """读取温度（°C）"""
        resp = self._request(opcodes.READ_TEMPERATURE)
        if resp.status != 0:
            raise RuntimeError(f"读取温度失败: status={resp.status}")
        return self.parser.parse_temperature(resp.data)
    
    def get_bus_voltage(self) -> float:
        """读取总线电压（V）"""
        resp = self._request(opcodes.READ_BUS_VOLTAGE)
        if resp.status != 0:
            raise RuntimeError(f"读取电压失败: status={resp.status}")
        return self.parser.parse_voltage(resp.data)
    
    def get_current(self) -> float:
        """读取相电流（A）"""
        resp = self._request(opcodes.READ_PHASE_CURRENT)
        if resp.status != 0:
            raise RuntimeError(f"读取电流失败: status={resp.status}")
        return self.parser.parse_current(resp.data)
    
    def get_bus_current(self) -> float:
        """读取总线电流（A）"""
        resp = self._request(opcodes.READ_BUS_CURRENT)
        if resp.status != 0:
            raise RuntimeError(f"读取总线电流失败: status={resp.status}")
        return self.parser.parse_current(resp.data)
    
    def get_position_error(self) -> float:
        """读取位置误差（度）"""
        resp = self._request(opcodes.READ_POSITION_ERROR)
        if resp.status != 0:
            raise RuntimeError(f"读取位置误差失败: status={resp.status}")
        return self.parser.parse_position(resp.data)
    
    def get_target_position(self) -> float:
        """读取目标位置（度）"""
        resp = self._request(opcodes.READ_TARGET_POSITION)
        if resp.status != 0:
            raise RuntimeError(f"读取目标位置失败: status={resp.status}")
        return self.parser.parse_position(resp.data)
    
    def get_realtime_target_position(self) -> float:
        """读取实时目标位置（度）"""
        resp = self._request(opcodes.READ_REALTIME_TARGET_POSITION)
        if resp.status != 0:
            raise RuntimeError(f"读取实时目标位置失败: status={resp.status}")
        return self.parser.parse_position(resp.data)
    
    def get_encoder_raw(self) -> int:
        """读取编码器原始值"""
        resp = self._request(opcodes.READ_ENCODER_RAW)
        if resp.status != 0:
            raise RuntimeError(f"读取编码器原始值失败: status={resp.status}")
        if len(resp.data) >= 2:
            return struct.unpack("<H", resp.data[:2])[0]
        return 0
    
    def get_encoder_calibrated(self) -> int:
        """读取编码器校准值"""
        resp = self._request(opcodes.READ_ENCODER_CALIBRATED)
        if resp.status != 0:
            raise RuntimeError(f"读取编码器校准值失败: status={resp.status}")
        if len(resp.data) >= 2:
            return struct.unpack("<H", resp.data[:2])[0]
        return 0
    
    def get_pulse_count(self) -> int:
        """读取脉冲计数"""
        resp = self._request(opcodes.READ_PULSE_COUNT)
        if resp.status != 0:
            raise RuntimeError(f"读取脉冲计数失败: status={resp.status}")
        if len(resp.data) >= 4:
            return struct.unpack("<i", resp.data[:4])[0]
        return 0
    
    def get_input_pulse(self) -> int:
        """读取输入脉冲"""
        resp = self._request(opcodes.READ_INPUT_PULSE)
        if resp.status != 0:
            raise RuntimeError(f"读取输入脉冲失败: status={resp.status}")
        if len(resp.data) >= 4:
            return struct.unpack("<i", resp.data[:4])[0]
        return 0
    
    def get_pid_parameters(self) -> dict:
        """读取PID参数"""
        resp = self._request(opcodes.READ_PID_PARAMS)
        if resp.status != 0:
            raise RuntimeError(f"读取PID参数失败: status={resp.status}")

        # 优先兼容“原SDK解析器”常见的 16B（4 个 int32）布局：
        # trapezoid_position_kp / direct_position_kp / speed_kp / speed_ki
        if len(resp.data) >= 16:
            try:
                t_kp, d_kp, s_kp, s_ki = struct.unpack("<iiii", resp.data[:16])
                return {
                    "trapezoid_position_kp": t_kp,
                    "direct_position_kp": d_kp,
                    "speed_kp": s_kp,
                    "speed_ki": s_ki,
                    "raw_data": resp.data,
                }
            except Exception:
                pass

        # 兼容旧占位：12B float32*3
        if len(resp.data) >= 12:
            try:
                kp, ki, kd = struct.unpack("<fff", resp.data[:12])
                return {"kp": kp, "ki": ki, "kd": kd, "raw_data": resp.data}
            except Exception:
                pass

        return {"raw_data": resp.data}
    
    def get_drive_parameters(self) -> DriveParameters:
        """读取驱动参数（返回结构体，避免上层 AttributeError）"""
        resp = self._request(opcodes.READ_DRIVE_PARAMETERS)
        if resp.status != 0:
            raise RuntimeError(f"读取驱动参数失败: status={resp.status}")
        params = DriveParameters.from_raw(resp.data)
        if not params.parsed_ok:
            self.logger.warning(f"驱动参数解析不完整: len={len(resp.data)}（已保留 raw_data 并使用默认值占位）")
        return params
    
    def get_status_info(self) -> dict:
        """读取系统状态信息（详细）"""
        resp = self._request(opcodes.READ_SYSTEM_STATUS)
        if resp.status != 0:
            raise RuntimeError(f"读取系统状态失败: status={resp.status}")
        # 返回系统状态，包含多个状态字段
        return {'raw_data': resp.data}
    
    def get_system_status(self) -> dict:
        """读取系统状态（别名）"""
        return self.get_status_info()
    
    def get_resistance_inductance(self) -> dict:
        """
        读取电机电阻电感参数
        
        Returns:
            dict: {'resistance': float, 'inductance': float}
        """
        # 尝试读取电机参数（使用正确的opcode）
        try:
            resp = self._request(opcodes.READ_RESISTANCE_INDUCTANCE)
            if resp.status == 0 and len(resp.data) >= 8:
                # 返回格式：resistance(float32) + inductance(float32)
                resistance, inductance = struct.unpack("<ff", resp.data[:8])
                return {
                    'resistance': resistance,
                    'inductance': inductance
                }
        except Exception as e:
            self.logger.warning(f"电阻电感读取失败: {e}")
        
        # 如果不支持或失败，返回默认值
        return {
            'resistance': 0.0,
            'inductance': 0.0
        }
    
    def get_version(self) -> dict:
        """读取版本信息"""
        resp = self._request(opcodes.READ_VERSION)
        if resp.status != 0 or len(resp.data) < 4:
            raise RuntimeError(f"读取版本失败: status={resp.status}")
        
        fw = (resp.data[0] << 8) | resp.data[1]
        hw = (resp.data[2] << 8) | resp.data[3]
        
        fw_major = fw // 100
        fw_minor = (fw % 100) // 10
        fw_patch = fw % 10
        hw_major = hw // 100
        hw_minor = (hw % 100) // 10
        
        return {
            'firmware': f"ZDT_X57_V{fw_major}.{fw_minor}.{fw_patch}",
            'hardware': f"ZDT_X57_V{hw_major}.{hw_minor}",
            'firmware_raw': fw,
            'hardware_raw': hw
        }
    
    # ==================== 回零功能 ====================
    
    def trigger_homing(self, mode: int = None, homing_mode: int = None, multi_sync: bool = False, **kwargs) -> None:
        """
        触发回零
        
        Args:
            mode: 回零模式 (0-5)，推荐参数名
            homing_mode: 回零模式 (0-5)，兼容旧参数名
                0: 单圈就近回零
                1: 单圈方向回零
                2: 无限位碰撞回零
                3: 限位回零
                4: 回到绝对位置坐标零点（推荐）
                5: 回到上次掉电位置
            multi_sync: 是否多机同步（已弃用，保留兼容性）
            **kwargs: 其他兼容性参数
        """
        # 兼容旧参数名
        actual_mode = mode if mode is not None else (homing_mode if homing_mode is not None else 4)
        
        args = struct.pack("<BB", actual_mode, int(multi_sync))
        resp = self._request(opcodes.TRIGGER_HOMING, args, timeout_ms=300, suppress_err_log=True)
        if getattr(resp, "status", 0) == 0:
            return
        status = int(getattr(resp, "status", 0) or 0)
        err_code = int(getattr(resp, "err_code", 0) or 0)
        if status == 4 and err_code == 0x0101:
            return
        if status == 3 and err_code == 0x4034:
            return
        raise RuntimeError(f"触发回零失败: status={status} err_code=0x{err_code:04X}")
    
    def set_zero_position(self, save_to_chip: bool = True) -> None:
        """设置当前位置为零点"""
        try:
            self.logger.info(f"SET_ZERO_POSITION(id={self.motor_id}, save_to_chip={save_to_chip})")
        except Exception:
            pass
        args = struct.pack("<B", int(save_to_chip))
        resp = self._request(opcodes.SET_ZERO_POSITION, args)
        if resp.status != 0:
            raise RuntimeError(f"设置零点失败: status={resp.status}")
    
    def get_homing_status(self) -> dict:
        """读取回零状态"""
        resp = self._request(opcodes.READ_HOMING_STATUS)
        if resp.status != 0:
            raise RuntimeError(f"读取回零状态失败: status={resp.status}")
        return self.parser.parse_homing_status(resp.data)
    
    def is_homing_complete(self) -> bool:
        """检查回零是否完成"""
        try:
            status = self.get_homing_status()
            return not status.get('homing_in_progress', False)
        except:
            return False
    
    def wait_for_homing_complete(self, timeout: float = 30.0) -> bool:
        """等待回零完成"""
        start = time.time()
        while time.time() - start < timeout:
            if self.is_homing_complete():
                return True
            time.sleep(0.5)
        return False
    
    def force_stop_homing(self) -> None:
        """强制停止回零"""
        try:
            resp = self._request(opcodes.FORCE_STOP_HOMING)
            if resp.status != 0:
                raise RuntimeError(f"强制停止回零失败: status={resp.status}")
        except Exception as e:
            self.logger.warning(f"强制停止回零失败: {e}")
    
    def trigger_encoder_calibration(self) -> None:
        """触发编码器标定"""
        try:
            resp = self._request(opcodes.TRIGGER_ENCODER_CALIBRATION)
            if resp.status != 0:
                raise RuntimeError(f"触发编码器标定失败: status={resp.status}")
        except Exception as e:
            self.logger.warning(f"触发编码器标定失败: {e}")
    
    def get_homing_parameters(self):
        """
        读取回零参数（返回可用属性访问的对象）
        
        Returns:
            SimpleNamespace: 回零参数对象，包含属性：
                - mode: 回零模式
                - direction: 回零方向
                - speed: 回零速度
                - timeout: 超时时间
                - current_threshold: 电流阈值
                - collision_detection_speed: 碰撞检测速度
                - collision_detection_current: 碰撞检测电流
                - collision_detection_time: 碰撞检测时间
                - auto_homing_enabled: 自动回零使能
        """
        from types import SimpleNamespace
        
        try:
            # 该接口常在 UI 初始化/轮询时被调用；失败属于“可降级”，避免 warning 刷屏。
            resp = self._request(opcodes.READ_HOMING_PARAMS, suppress_err_log=True)
            if getattr(resp, "status", 0) == 0:
                data_len = len(resp.data)
                
                # 15B（ZDT原始字段序列，按 ESP_can_firmware/test_motor.py 的 fallback 解析：大端）
                # [0]mode(u8) [1]direction(u8)
                # [2..3]speed(u16,BE) [4..7]timeout_ms(u32,BE)
                # [8..9]collision_speed(u16,BE) [10..11]collision_current(u16,BE)
                # [12..13]collision_time(u16,BE) [14]auto_homing(u8)
                if data_len == 15:
                    try:
                        mode = resp.data[0]
                        direction = resp.data[1]
                        speed = int.from_bytes(resp.data[2:4], byteorder="big", signed=False)
                        timeout_ms = int.from_bytes(resp.data[4:8], byteorder="big", signed=False)
                        coll_speed = int.from_bytes(resp.data[8:10], byteorder="big", signed=False)
                        coll_current = int.from_bytes(resp.data[10:12], byteorder="big", signed=False)
                        coll_time = int.from_bytes(resp.data[12:14], byteorder="big", signed=False)
                        auto_homing = bool(resp.data[14])
                        return SimpleNamespace(
                            mode=mode,
                            direction=direction,
                            speed=speed,
                            timeout=timeout_ms,
                            current_threshold=1000,  # 旧字段仅保留兼容
                            collision_detection_speed=coll_speed,
                            collision_detection_current=coll_current,
                            collision_detection_time=coll_time,
                            auto_homing_enabled=auto_homing
                        )
                    except Exception as e:
                        self.logger.debug(f"回零参数解析失败(15B): {e}")
                
                # 兼容：8B（旧实现里用到的 <BBHHh>，需要 8 字节）
                if data_len >= 8:
                    try:
                        mode, direction, speed_x10, timeout, current = struct.unpack("<BBHHh", resp.data[:8])
                        return SimpleNamespace(
                            mode=mode,
                            direction=direction,
                            speed=speed_x10 / 10.0,
                            timeout=timeout,
                            current_threshold=current,
                            collision_detection_speed=50,  # 默认值
                            collision_detection_current=500,
                            collision_detection_time=100,
                            auto_homing_enabled=False
                        )
                    except Exception as e:
                        self.logger.debug(f"回零参数解析失败(>=8B兼容): {e}")
                
                # 长度异常：直接回退默认值（不刷 warning）
                self.logger.debug(f"回零参数数据长度异常: {data_len}字节")
            else:
                status = int(getattr(resp, "status", 0) or 0)
                err_code = int(getattr(resp, "err_code", 0) or 0)
                self.logger.debug(f"读取回零参数失败: status={status} err_code=0x{err_code:04X}")
                
        except Exception as e:
            # 读取异常：回退默认值（不刷 warning）
            self.logger.debug(f"读取回零参数异常: {e}")
        
        # 返回默认值
        return SimpleNamespace(
            mode=4,
            direction=0,
            speed=50.0,
            timeout=30,
            current_threshold=1000,
            collision_detection_speed=50,
            collision_detection_current=500,
            collision_detection_time=100,
            auto_homing_enabled=False
        )
    
    def get_homing_parameters_raw(self) -> bytes:
        """
        读取回零参数（原始字节）
        
        Returns:
            bytes: 原始回零参数数据
        """
        try:
            resp = self._request(opcodes.READ_HOMING_PARAMS, suppress_err_log=True)
            if getattr(resp, "status", 0) == 0:
                return resp.data
        except Exception as e:
            self.logger.debug(f"读取回零参数（原始）异常: {e}")
        
        # 返回默认值的字节表示
        return struct.pack("<BBHHh", 4, 0, 500, 30, 1000)
    
    def modify_homing_parameters(self, 
                                mode: int = None, 
                                direction: int = None, 
                                speed: int = None, 
                                timeout: int = None, 
                                current_threshold: int = None,
                                collision_detection_speed: int = None,
                                collision_detection_current: int = None,
                                collision_detection_time: int = None,
                                auto_homing_enabled: bool = None,
                                save_to_chip: bool = False) -> None:
        """
        修改回零参数（优先16B固件格式；保留旧格式兜底）
        
        Args:
            mode: 回零模式 (0-5)，None表示不修改
            direction: 回零方向 (0=逆时针, 1=顺时针)，None表示不修改
            speed: 回零速度 (RPM)，None表示不修改
            timeout: 回零超时时间 (秒)，None表示不修改
            current_threshold: 堵转电流阈值 (mA)，None表示不修改（旧参数，保留兼容）
            collision_detection_speed: 碰撞检测速度，None表示不修改
            collision_detection_current: 碰撞检测电流，None表示不修改
            collision_detection_time: 碰撞检测时间，None表示不修改
            auto_homing_enabled: 自动回零使能，None表示不修改
            save_to_chip: 是否保存到芯片（默认False）
        """
        # 先读取当前参数
        current_params = self.get_homing_parameters()
        
        # 使用提供的值或当前值
        mode = mode if mode is not None else current_params.mode
        direction = direction if direction is not None else current_params.direction
        speed = speed if speed is not None else current_params.speed
        timeout = timeout if timeout is not None else current_params.timeout
        
        # 新参数
        coll_speed = collision_detection_speed if collision_detection_speed is not None else current_params.collision_detection_speed
        coll_current = collision_detection_current if collision_detection_current is not None else current_params.collision_detection_current
        coll_time = collision_detection_time if collision_detection_time is not None else current_params.collision_detection_time
        auto_homing = int(auto_homing_enabled) if auto_homing_enabled is not None else int(current_params.auto_homing_enabled)
        
        # 固件格式：16B（参考 esp32_can_firmware/Control_Core/ZDT_SDK/zdt_driver.cpp case 0x50）
        # args（UCP，小端）:
        # save(u8), mode(u8), direction(u8), speed_rpm(u16), timeout_ms(u32),
        # collision_speed(u16), collision_current(u16), collision_time(u16), auto(u8)
        try:
            args = struct.pack(
                "<BBBHIHHHB",
                int(bool(save_to_chip)),
                int(mode),
                int(direction),
                int(speed),
                int(timeout),
                int(coll_speed),
                int(coll_current),
                int(coll_time),
                int(bool(auto_homing)),
            )
            
            resp = self._request(opcodes.MODIFY_HOMING_PARAMS, args)
            if resp.status == 0:
                self.logger.info("回零参数已更新（16字节固件格式）")
                return
            else:
                self.logger.debug(f"16字节固件格式失败: status={resp.status}，尝试旧格式兼容")
        except Exception as e:
            self.logger.debug(f"16字节固件格式发送失败: {e}，尝试旧格式兼容")
        
        # 兼容：旧格式（部分老固件可能接受更短参数）
        try:
            speed_x10 = int(speed * 10)
            current_threshold_val = current_threshold if current_threshold is not None else current_params.current_threshold
            args = struct.pack("<BBHHh", int(mode), int(direction), int(speed_x10), int(timeout), int(current_threshold_val))
            
            resp = self._request(opcodes.MODIFY_HOMING_PARAMS, args)
            if resp.status != 0:
                raise RuntimeError(
                    f"修改回零参数失败: status={resp.status}, err_code=0x{resp.err_code:04X}"
                )
            self.logger.info("回零参数已更新（旧格式兼容）")
        except Exception as e:
            raise RuntimeError(f"修改回零参数失败（兼容路径）: {e}")
    
    # ==================== 便捷方法 ====================
    
    def is_enabled(self) -> bool:
        """检查是否使能"""
        try:
            status = self.get_motor_status()
            return status.enabled  # SimpleNamespace对象，使用属性访问
        except:
            return False
    
    def is_in_position(self) -> bool:
        """检查是否到位"""
        try:
            status = self.get_motor_status()
            return status.in_position  # SimpleNamespace对象，使用属性访问
        except:
            return False
    
    def wait_for_position(self, timeout: float = 10.0, interval: float = 0.2) -> bool:
        """等待到位"""
        start = time.time()
        while time.time() - start < timeout:
            if self.is_in_position():
                return True
            time.sleep(interval)
        return False
    
    def wait_for_homing(self, timeout: float = 30.0, interval: float = 0.5) -> bool:
        """等待回零完成"""
        start = time.time()
        while time.time() - start < timeout:
            status = self.get_homing_status()
            if not status.get('homing_in_progress', False):
                return not status.get('homing_failed', True)
            time.sleep(interval)
        return False
    
    # ==================== 工具功能 ====================
    
    def clear_position(self) -> None:
        """清零位置"""
        try:
            self.logger.info(f"CLEAR_POSITION(id={self.motor_id})")
        except Exception:
            pass
        resp = self._request(opcodes.CLEAR_POSITION)
        if resp.status != 0:
            raise RuntimeError(f"清零位置失败: status={resp.status}")
    
    def release_stall_protection(self) -> None:
        """解除堵转保护"""
        try:
            self.logger.info(f"RELEASE_STALL_PROTECTION(id={self.motor_id})")
        except Exception:
            pass
        resp = self._request(opcodes.RELEASE_STALL_PROTECTION)
        if resp.status != 0:
            raise RuntimeError(f"解除堵转失败: status={resp.status}")

    def factory_reset(self) -> None:
        """恢复出厂设置（谨慎使用）"""
        try:
            self.logger.warning(f"FACTORY_RESET(id={self.motor_id})")
        except Exception:
            pass
        resp = self._request(opcodes.FACTORY_RESET)
        if resp.status != 0:
            raise RuntimeError(f"恢复出厂设置失败: status={resp.status}")
    
    # ==================== Y42多机同步（官方推荐方案 ⭐） ====================
    # Y42聚合模式是 OmniCAN 固件官方推荐且充分测试的多机同步方案：
    # - 一次UCP通信完成多电机同步（最高效）
    # - 所有电机绝对同步启动（无延迟）
    # - 硬件层面保证同步性
    # ================================================================
    
    @staticmethod
    def y42_sync_position(
        controllers: dict,
        targets: dict,
        speed: float = 500.0,
        is_absolute: bool = True,
        timeout_ms: int = 2000,
        allow_status3: bool = True
    ) -> None:
        """
        Y42多机同步位置控制（官方推荐 ⭐ 最高效）
        
        Args:
            controllers: {motor_id: ZDTMotorControllerUCPSimple} 字典
            targets: {motor_id: target_position} 字典
            speed: 运动速度（RPM）
            is_absolute: 是否绝对位置
            timeout_ms: 超时时间（毫秒）
        
        示例：
            controllers = {1: ctrl1, 2: ctrl2}
            targets = {1: 90.0, 2: 180.0}
            ZDTMotorControllerUCPSimple.y42_sync_position(controllers, targets, speed=500)
        """
        if not controllers or not targets:
            raise ValueError("controllers和targets不能为空")
        
        # 检查关节限位
        first_ctrl = list(controllers.values())[0]
        limits = first_ctrl._load_joint_limits()
        if limits is not None:
            violations = []
            motor_config = first_ctrl._load_motor_config()
            for motor_id, target_motor_angle in targets.items():
                # 注意：y42_sync_position 的 targets 参数是电机角度（通过 get_actual_angle 转换后的）
                # 需要转换为关节角度后再与限位比较
                joint_angle = first_ctrl._motor_angle_to_joint_angle(target_motor_angle, motor_id)
                
                joint_idx = motor_id - 1
                if 0 <= joint_idx < 6:
                    min_limit, max_limit = limits[joint_idx]
                    if joint_angle < min_limit or joint_angle > max_limit:
                        # 保存电机角度（目标角度）和关节角度，错误信息中显示电机角度
                        violations.append((motor_id, joint_idx + 1, target_motor_angle, joint_angle, min_limit, max_limit))
            if violations:
                msg_parts = ["⛔ 关节限位检查失败，拒绝下发Y42同步位置命令："]
                for motor_id, joint_num, motor_angle, joint_angle, min_lim, max_lim in violations:
                    msg_parts.append(
                        f"  电机{motor_id}(关节{joint_num}): 关节角度 {joint_angle:.2f}° 超出限位 [{min_lim:.2f}°, {max_lim:.2f}°]"
                    )
                error_msg = "\n".join(msg_parts)
                first_ctrl.logger.error(error_msg)
                raise RuntimeError(error_msg)
        
        # 构建Y42子命令
        sub_commands = []
        for motor_id, target in targets.items():
            # 位置参数
            direction = 1 if target < 0 else 0
            pos_val = int(abs(target) * 10)
            spd_val = int(speed * 10)
            
            # ZDT 0xFB 位置直通命令（大端序）
            # FB + Dir(1B) + Speed(2B BE) + Position(4B BE) + Abs/Rel(1B) + Sync(1B) + 6B
            zdt_cmd = struct.pack(">BBHI", 0xFB, direction, spd_val, pos_val) + \
                      struct.pack(">BB", int(is_absolute), 0) + b"\x6B"
            
            # 子命令格式: [motor_id(1B)] + [ZDT命令]
            sub_commands.append(bytes([motor_id]) + zdt_cmd)
        
        # 构建Y42帧: AA + 长度(2B BE) + payload + 6B
        payload = b"".join(sub_commands)
        total_len = len(payload) + 1  # +1 for trailing 0x6B
        y42_frame = b"\xAA" + struct.pack(">H", total_len) + payload + b"\x6B"
        
        # UCP args: expected_response_motor_id(1B) + Y42帧
        first_motor_id = list(targets.keys())[0]
        args = struct.pack("<B", first_motor_id) + y42_frame
        
        # 使用第一个控制器的client发送（motor_id=0广播）
        first_ctrl = list(controllers.values())[0]
        if not first_ctrl.client:
            raise RuntimeError("未连接，请先调用 connect()")
        
        resp = first_ctrl.client.request(
            motor_id=0,  # 必须广播
            opcode=opcodes.Y42_MULTI_MOTOR,
            args=args,
            timeout_ms=timeout_ms
        )

        # 打印诊断信息（便于定位“已执行但不回ACK / BUS_OFF / 总线错误”等）
        try:
            if getattr(resp, "diag", b""):
                diag_hex = " ".join(f"{x:02X}" for x in resp.diag)
                pass
        except Exception:
            pass
        
        if resp.status != 0:
            # 在你的实际表现中：status=3/0x4034 仍可能“命令已生效但ACK缺失”。
            # 因此：仅对 0x4034 做“可选放行”，避免 UI 误报导致功能不可用。
            if resp.status == 3 and resp.err_code == 0x4034 and allow_status3:
                first_ctrl.logger.warning(
                    f"Y42同步位置 ACK 超时(0x4034) 但已放行（命令可能已执行）: "
                    f"status=3 err_code=0x{resp.err_code:04X}"
                )
            else:
                raise RuntimeError(f"Y42同步位置失败: status={resp.status}, err_code=0x{resp.err_code:04X}")
        
        first_ctrl.logger.info(f"Y42同步位置已触发: {len(targets)}个电机")
    
    @staticmethod
    def y42_sync_speed(
        controllers: dict,
        speeds: dict,
        acceleration: int = 1000,
        timeout_ms: int = 2000,
        allow_status3: bool = True
    ) -> None:
        """
        Y42多机同步速度控制（官方推荐 ⭐）
        
        Args:
            controllers: {motor_id: ZDTMotorControllerUCPSimple} 字典
            speeds: {motor_id: target_speed_rpm} 字典
            acceleration: 加速度（RPM/s）
            timeout_ms: 超时时间（毫秒）
        """
        if not controllers or not speeds:
            raise ValueError("controllers和speeds不能为空")
        
        # 构建Y42子命令
        sub_commands = []
        for motor_id, target_speed in speeds.items():
            direction = 1 if target_speed < 0 else 0
            spd_val = int(abs(target_speed) * 10)
            
            # ZDT 0xF6 速度模式（大端序）
            # F6 + Dir(1B) + Accel(2B BE) + Speed(2B BE) + Sync(1B) + 6B
            zdt_cmd = struct.pack(">BBHH", 0xF6, direction, acceleration, spd_val) + \
                      struct.pack(">B", 0) + b"\x6B"
            
            sub_commands.append(bytes([motor_id]) + zdt_cmd)
        
        # 构建Y42帧
        payload = b"".join(sub_commands)
        total_len = len(payload) + 1
        y42_frame = b"\xAA" + struct.pack(">H", total_len) + payload + b"\x6B"
        
        # 发送
        first_motor_id = list(speeds.keys())[0]
        args = struct.pack("<B", first_motor_id) + y42_frame
        
        first_ctrl = list(controllers.values())[0]
        if not first_ctrl.client:
            raise RuntimeError("未连接，请先调用 connect()")
        
        resp = first_ctrl.client.request(
            motor_id=0,
            opcode=opcodes.Y42_MULTI_MOTOR,
            args=args,
            timeout_ms=timeout_ms
        )

        try:
            if getattr(resp, "diag", b""):
                diag_hex = " ".join(f"{x:02X}" for x in resp.diag)
                pass
        except Exception:
            pass
        
        if resp.status != 0:
            if resp.status == 3 and resp.err_code == 0x4034 and allow_status3:
                first_ctrl.logger.warning(
                    f"Y42同步速度 ACK 超时(0x4034) 但已放行（命令可能已执行）: "
                    f"status=3 err_code=0x{resp.err_code:04X}"
                )
            else:
                raise RuntimeError(f"Y42同步速度失败: status={resp.status}, err_code=0x{resp.err_code:04X}")
        
        first_ctrl.logger.info(f"Y42同步速度已触发: {len(speeds)}个电机")
    
    @staticmethod
    def y42_sync_enable(
        controllers: dict,
        enabled: bool = True,
        timeout_ms: int = 2000,
        allow_status3: bool = True
    ) -> None:
        """
        Y42多机同步使能/失能（官方推荐 ⭐）
        
        Args:
            controllers: {motor_id: ZDTMotorControllerUCPSimple} 字典
            enabled: True=使能, False=失能
            timeout_ms: 超时时间（毫秒）
        """
        if not controllers:
            raise ValueError("controllers不能为空")
        
        # 构建Y42子命令
        sub_commands = []
        for motor_id in controllers.keys():
            # ZDT 0xF3 使能命令（大端序）
            # F3 + Enabled(1B) + Sync(1B) + 6B
            zdt_cmd = struct.pack(">BB", 0xF3, int(enabled)) + \
                      struct.pack(">B", 0) + b"\x6B"
            
            sub_commands.append(bytes([motor_id]) + zdt_cmd)
        
        # 构建Y42帧
        payload = b"".join(sub_commands)
        total_len = len(payload) + 1
        y42_frame = b"\xAA" + struct.pack(">H", total_len) + payload + b"\x6B"
        
        # 发送
        first_motor_id = list(controllers.keys())[0]
        args = struct.pack("<B", first_motor_id) + y42_frame
        
        first_ctrl = list(controllers.values())[0]
        if not first_ctrl.client:
            raise RuntimeError("未连接，请先调用 connect()")
        
        resp = first_ctrl.client.request(
            motor_id=0,
            opcode=opcodes.Y42_MULTI_MOTOR,
            args=args,
            timeout_ms=timeout_ms
        )

        try:
            if getattr(resp, "diag", b""):
                diag_hex = " ".join(f"{x:02X}" for x in resp.diag)
                pass
        except Exception:
            pass
        
        if resp.status != 0:
            if resp.status == 3 and resp.err_code == 0x4034 and allow_status3:
                first_ctrl.logger.warning(
                    f"Y42同步使能 ACK 超时(0x4034) 但已放行（命令可能已执行）: "
                    f"status=3 err_code=0x{resp.err_code:04X}"
                )
            else:
                raise RuntimeError(f"Y42同步使能失败: status={resp.status}, err_code=0x{resp.err_code:04X}")
        
        action = "使能" if enabled else "失能"
        first_ctrl.logger.info(f"Y42同步{action}已触发: {len(controllers)}个电机")
    
    # ==================== 上下文管理器 ====================
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
    
    # ==================== 兼容性属性（支持模块化API调用方式） ====================
    
    @property
    def control_actions(self):
        """
        兼容模块化API：motor.control_actions.enable()
        实际上调用的是 motor.enable()
        """
        return self
    
    @property
    def read_parameters(self):
        """
        兼容模块化API：motor.read_parameters.get_position()
        实际上调用的是 motor.get_position()
        """
        return self
    
    @property
    def homing_commands(self):
        """
        兼容模块化API：motor.homing_commands.trigger_homing()
        实际上调用的是 motor.trigger_homing()
        """
        return self

    @property
    def trigger_actions(self):
        """
        兼容模块化API：motor.trigger_actions.clear_position()
        UI/示例代码会通过该入口触发“清零位置/解除堵转/恢复出厂”等动作。
        """
        return self

    @property
    def modify_parameters(self):
        """
        兼容模块化API：motor.modify_parameters.set_motor_id(...)
        以及示例脚本中的 modify_drive_parameters / create_default_drive_parameters / set_pid_parameters 等入口。
        """
        return self

    # ==================== 参数修改（兼容 modify_parameters 模块） ====================

    def set_motor_id(self, new_id: int, save_to_chip: bool = True) -> SimpleNamespace:
        """修改电机ID（UCP: MODIFY_MOTOR_ID=0x52）"""
        if new_id <= 0 or new_id > 255:
            raise ValueError(f"new_id 超出范围: {new_id}（期望 1..255）")
        args = struct.pack("<BB", int(bool(save_to_chip)), int(new_id) & 0xFF)
        resp = self._request(opcodes.MODIFY_MOTOR_ID, args)
        ok = (resp.status == 0)
        if ok:
            # 注意：部分驱动可能需要重启后生效，但从控制器视角仍应更新 motor_id，避免后续继续用旧ID
            old = self.motor_id
            self.motor_id = int(new_id)
            self.logger.warning(f"电机ID修改命令已发送: {old} -> {new_id}（save_to_chip={save_to_chip}）")
            return SimpleNamespace(success=True, status=resp.status, err_code=resp.err_code, error_message="")
        return SimpleNamespace(
            success=False,
            status=resp.status,
            err_code=resp.err_code,
            error_message=f"修改电机ID失败: status={resp.status}, err_code=0x{resp.err_code:04X}",
        )

    def create_default_drive_parameters(self) -> DriveParameters:
        """创建默认驱动参数（用于 UI/脚本在读取失败时填充一个可编辑对象）"""
        return DriveParameters()

    def modify_drive_parameters(self, params: Any, save_to_chip: bool = True, timeout_ms: int = 2000) -> SimpleNamespace:
        """
        修改驱动参数（UCP: MODIFY_DRIVE_PARAMETERS=0x51）

        params 可以是：
        - DriveParameters
        - 具有同名属性的对象（SimpleNamespace 等）
        - dict（键为字段名）
        """
        if isinstance(params, DriveParameters):
            p = params
        elif isinstance(params, dict):
            p = DriveParameters(**{k: params.get(k, getattr(DriveParameters(), k)) for k in DriveParameters().__dict__.keys() if k in DriveParameters().__dict__})
        else:
            # 尝试按属性拷贝
            base = DriveParameters()
            for k in base.__dict__.keys():
                if k in ("raw_data", "parsed_ok"):
                    continue
                if hasattr(params, k):
                    setattr(base, k, getattr(params, k))
            p = base

        args = p.to_ucp_args(save_to_chip=save_to_chip)
        resp = self._request(opcodes.MODIFY_DRIVE_PARAMETERS, args, timeout_ms=timeout_ms)
        ok = (resp.status == 0)
        if ok:
            self.logger.info(f"驱动参数已更新（save_to_chip={save_to_chip}）")
            return SimpleNamespace(success=True, status=resp.status, err_code=resp.err_code, error_message="")
        return SimpleNamespace(
            success=False,
            status=resp.status,
            err_code=resp.err_code,
            error_message=f"修改驱动参数失败: status={resp.status}, err_code=0x{resp.err_code:04X}",
        )

    def set_pid_parameters(self, **kwargs) -> SimpleNamespace:
        """
        兼容占位：设置PID参数。

        当前 UCP 固件 opcodes 中仅定义 READ_PID_PARAMS(0x36)，未提供明确的 MODIFY_PID_PARAMS。
        为避免上层 AttributeError，这里返回失败结果并输出提示。
        """
        msg = "当前固件未提供 PID 写入接口（仅支持 READ_PID_PARAMS）。"
        self.logger.warning(msg + f" kwargs={kwargs}")
        return SimpleNamespace(success=False, status=-1, err_code=0, error_message=msg)
    
    @property
    def command_builder(self):
        """
        兼容SLCAN API：motor.command_builder.position_mode_direct()
        
        返回一个命令构建器兼容对象，主要用于多电机同步控制中的Y42聚合模式。
        旧的SLCAN代码使用 command_builder 来构建CAN命令，在UCP模式下，
        我们提供兼容层将其转换为ZDT命令体（用于Y42聚合）。
        """
        if not hasattr(self, '_command_builder_compat'):
            self._command_builder_compat = _CommandBuilderCompat(self)
        return self._command_builder_compat
    
    def multi_motor_command(self, commands: list, expected_ack_motor_id: int = 1,
                           wait_ack: bool = False, timeout_ms: int = 2000, allow_status3=None,
                           max_ack_candidates: int = 2, **kwargs):
        """
        多机聚合命令（Y42模式）
        
        兼容旧API，用于UI和示例代码中的Y42多机同步控制。
        
        Args:
            commands: 子命令列表，每个元素格式为 [motor_id, func_code, ...params, 0x6B]
            expected_ack_motor_id: 期望响应的电机ID（通常是第一个电机）
            wait_ack: 是否等待应答（UCP模式忽略此参数）
            timeout_ms: 超时时间（毫秒）
            allow_status3: 是否允许 status==3（例如 0x4034 ACK 超时）不抛异常直接放行。
                - None（默认）：若 `mode` 为空或为 'control'，则默认放行（更符合 UI/示教器“动作已执行但 ACK 可能收不到”的现实）。
                - True：强制放行
                - False：保持严格，ACK 超时会抛异常
            max_ack_candidates: 最多尝试多少个“期望响应电机ID”（用户主观逻辑：最多试到第二个，再不行就认为都不行）。
            **kwargs: 兼容参数（如mode等）
            
        Returns:
            UcpResponse: UCP响应对象
            
        示例：
            # 构建多个子命令
            cmd1 = [1] + list(motor1.command_builder.position_mode_direct(90, 500))
            cmd2 = [2] + list(motor2.command_builder.position_mode_direct(180, 500))
            
            # 发送Y42聚合命令
            motor1.multi_motor_command([cmd1, cmd2])
        """
        if not self.client:
            error_msg = "未连接，请先调用 connect()"
            raise RuntimeError(error_msg)

        # ---- 默认策略：UI/示教器场景（mode='control' 或未传 mode）不应因 ACK 超时直接判“同步失败” ----
        # 说明：
        # - 固件对 Y42 默认会等待某一台电机 ACK；
        # - 但在某些链路上 ACK 丢失/被过滤/电机不回包时，电机依然可能已执行动作；
        # - 上位机此时更需要“继续流程 + 输出告警”，而不是直接抛异常中断。
        mode = kwargs.get("mode", "")
        if allow_status3 is None:
            allow_status3 = (mode in ("", None, "control"))
        allow_status3 = bool(allow_status3)
        try:
            max_ack_candidates = int(max_ack_candidates)
        except Exception:
            max_ack_candidates = 2
        if max_ack_candidates < 1:
            max_ack_candidates = 1
        
        try:
            # 检查关节限位（在构建命令前）
            limits = self._load_joint_limits()
            if limits is not None:
                violations = []
                for i, cmd in enumerate(commands):
                    # cmd可能是list、bytes或tuple
                    if isinstance(cmd, (list, tuple)):
                        cmd_bytes = bytes(cmd)
                    elif isinstance(cmd, bytes):
                        cmd_bytes = cmd
                    else:
                        continue
                    
                    # 解析Y42子命令中的角度：motor_id(1B) + ZDT命令
                    # ZDT 0xFB位置命令格式: FB(1B) + Dir(1B) + Speed(2B BE) + Position(4B BE) + Abs/Rel(1B) + Sync(1B) + 6B(1B)
                    # 子命令格式: [motor_id(1B)] + [ZDT命令(11B)] = 总共12字节
                    # 字节布局: [motor_id] [FB] [Dir] [Speed_H] [Speed_L] [Pos_B3] [Pos_B2] [Pos_B1] [Pos_B0] [Abs/Rel] [Sync] [6B]
                    if len(cmd_bytes) >= 12 and cmd_bytes[1] == 0xFB:
                        motor_id = cmd_bytes[0]
                        # Position在子命令中的位置：motor_id(0) + FB(1) + Dir(2) + Speed(3-4) + Position(5-8)
                        pos_val = struct.unpack(">I", cmd_bytes[5:9])[0]
                        motor_angle_deg = pos_val / 10.0
                        
                        # 将电机角度转换为关节角度
                        joint_angle_deg = self._motor_angle_to_joint_angle(motor_angle_deg, motor_id)
                        
                        joint_idx = motor_id - 1
                        if 0 <= joint_idx < 6:
                            min_limit, max_limit = limits[joint_idx]
                            if joint_angle_deg < min_limit or joint_angle_deg > max_limit:
                                # 保存电机角度（目标角度）和关节角度，错误信息中显示电机角度
                                violations.append((motor_id, joint_idx + 1, motor_angle_deg, joint_angle_deg, min_limit, max_limit))
                
                if violations:
                    msg_parts = ["⛔ 关节限位检查失败，拒绝下发Y42多机聚合命令："]
                    for motor_id, joint_num, motor_angle, joint_angle, min_lim, max_lim in violations:
                        msg_parts.append(
                            f"  电机{motor_id}(关节{joint_num}): 关节角度 {joint_angle:.2f}° 超出限位 [{min_lim:.2f}°, {max_lim:.2f}°]"
                        )
                    error_msg = "\n".join(msg_parts)
                    self.logger.error(error_msg)
                    raise RuntimeError(error_msg)
            
            # 将命令列表转换为字节串
            sub_commands = []
            for i, cmd in enumerate(commands):
                # cmd可能是list、bytes或tuple
                if isinstance(cmd, (list, tuple)):
                    cmd_bytes = bytes(cmd)
                elif isinstance(cmd, bytes):
                    cmd_bytes = cmd
                else:
                    error_msg = f"子命令 {i+1} 类型错误: {type(cmd)}"
                    raise TypeError(error_msg)
                
                sub_commands.append(cmd_bytes)
                # no stdout
            
            # 构建Y42帧: AA + 长度(2B BE) + payload + 0x6B
            payload = b"".join(sub_commands)
            total_len = len(payload) + 1  # +1 for trailing 0x6B
            y42_frame = struct.pack('>BH', 0xAA, total_len) + payload + b'\x6B'
            
            # no stdout
            
            # 选择“期望响应电机ID”（很关键）：
            # 固件侧会“广播发送”，但只从 expected_ack_motor_id 等待 ACK。
            # 如果固定等 1 号，而 1 号电机不在线/ID不对/不回包，则整次Y42都会以 0x4034 超时失败。
            cand_ids = []
            try:
                cand_ids = sorted({b[0] for b in sub_commands if b})
            except Exception:
                cand_ids = []
            if not cand_ids:
                cand_ids = [expected_ack_motor_id] if expected_ack_motor_id else [1]

            # 将用户传入的 expected_ack_motor_id 放到首选；若不在本次子命令集合内，则自动回退
            if expected_ack_motor_id in cand_ids:
                ordered_ack_ids = [expected_ack_motor_id] + [i for i in cand_ids if i != expected_ack_motor_id]
            else:
                ordered_ack_ids = cand_ids
            # 主观逻辑约束：最多尝试 N 个候选（默认 2）
            ordered_ack_ids = ordered_ack_ids[:max_ack_candidates]

            last_resp = None
            last_error = None
            for ack_id in ordered_ack_ids:
                # UCP args: expected_response_motor_id(1B) + Y42帧
                args = bytes([ack_id]) + y42_frame

                # 发送UCP请求（broadcast to motor_id=0）
                resp = self.client.request(
                    motor_id=0,  # 广播地址
                    opcode=opcodes.Y42_MULTI_MOTOR,
                    args=args,
                    timeout_ms=timeout_ms
                )
                last_resp = resp

                # 关键诊断：打印 OmniCAN 返回的TWAI状态（便于区分“没回包”vs“总线错误/过滤/BusOff”）
                try:
                    if getattr(resp, "diag", b""):
                        diag_hex = " ".join(f"{x:02X}" for x in resp.diag)
                except Exception:
                    pass

                # 成功直接返回
                if resp.status == 0:
                    # 该函数可能在高频控制回路中被反复调用；INFO 会造成刷屏。
                    # 如需排查通讯，可将对应 logger 等级调到 DEBUG 再观察。
                    self.logger.debug(
                        "Y42聚合命令已发送: %d个子命令 (ack_motor_id=%s)",
                        len(commands),
                        ack_id,
                    )
                    return resp

                # 如果是“CAN超时(0x4034)”且还有候选电机，则自动换一个电机ID再试
                if resp.status == 3 and resp.err_code == 0x4034 and ack_id != ordered_ack_ids[-1]:
                    continue

                # 允许 status==3 放行（用于上位机控制场景，避免“动作已执行但 ACK 丢失”导致流程中断）
                if resp.status == 3 and allow_status3:
                    warn_msg = (
                        f"Y42聚合命令收到 status=3（可能 ACK 超时），但已按 allow_status3 放行: "
                        f"err_code=0x{resp.err_code:04X}, ack_motor_id={ack_id}, mode={mode!r}"
                    )
                    self.logger.warning(warn_msg)
                    return resp

                last_error = RuntimeError(f"Y42聚合命令失败: status={resp.status}, err_code=0x{resp.err_code:04X}")
                break
            
            # 所有候选都失败：抛出最后一次的错误
            if last_error is None and last_resp is not None:
                last_error = RuntimeError(f"Y42聚合命令失败: status={last_resp.status}, err_code=0x{last_resp.err_code:04X}")
            if last_error is None:
                last_error = RuntimeError("Y42聚合命令失败：未知错误（无响应对象）")
            self.logger.error(str(last_error))
            raise last_error
            
        except Exception as e:
            raise
    
    def send_broadcast_command(self, command_data: bytes = b"") -> None:
        """
        发送广播命令（兼容性方法）
        
        注意：UCP模式下，广播命令已被Y42聚合模式取代。
        此方法保留兼容性，但不执行任何操作。
        
        Args:
            command_data: 命令数据（被忽略）
        """
        self.logger.warning(
            f"[电机{self.motor_id}] send_broadcast_command() 在UCP模式下不可用，"
            "请使用 multi_motor_command() 或 y42_sync_xxx() 进行多机控制"
        )
    
    def sync_motion(self) -> None:
        """
        同步运动触发（兼容性方法）
        
        注意：本项目已禁用"Pre-load + Trigger"同步方式（仅允许 Y42）。
        请使用 Y42 多机聚合同步方法：
        - ZDTMotorController.y42_sync_position()
        - ZDTMotorController.y42_sync_speed()
        - ZDTMotorController.y42_sync_enable()
        """
        raise RuntimeError("sync_motion() 已被禁用：本项目多机同步仅允许 Y42。")
    
    # ==================== 静态方法（连接池管理） ====================
    
    @staticmethod
    def close_all_shared_interfaces():
        """
        关闭所有共享接口（UCP模式通过连接池管理）
        
        在UCP模式下，此方法会断开连接池中的所有串口连接。
        """
        pool = UcpConnectionPool.instance()
        pool.disconnect_all()
    
    @staticmethod
    def get_shared_interface_info():
        """
        获取共享接口信息（UCP模式返回连接池状态）
        
        Returns:
            dict: 包含以下信息：
            - active_connections: 活跃连接数
            - connections: 每个连接的详细信息（端口、波特率、引用计数）
        """
        pool = UcpConnectionPool.instance()
        connections_info = {}
        for key in pool._connections.keys():
            port, baudrate = key.split(":")
            ref_count = pool._ref_counts.get(key, 0)
            connections_info[key] = {
                "port": port,
                "baudrate": int(baudrate),
                "ref_count": ref_count
            }
        
        return {
            "mode": "UCP",
            "active_connections": len(pool._connections),
            "connections": connections_info
        }
    
    # ==================== 轨迹批量执行接口 ====================
    
    def upload_trajectory(self, trajectory_points: list, timeout_ms: int = 5000) -> bool:
        """
        批量上传轨迹点到 OmniCAN 缓存
        
        轨迹点格式（每个点）：
        {
            'interval_ms': int,  # 距离上一个点的时间间隔(ms)
            'positions': [float]*6,  # 6个电机的目标位置（电机端角度）
            'speeds': [float]*6  # 6个电机的运动速度(RPM)
        }
        
        Args:
            trajectory_points: 轨迹点列表
            timeout_ms: 超时时间(ms)
            
        Returns:
            bool: 上传成功返回True
        """
        if not self.client:
            raise RuntimeError("未连接，请先调用 connect()")

        # ✅ 固件侧轨迹缓存容量有限：点数过多会返回 err=0x7003。
        # 上层通常按 20ms 生成点列，遇到姿态欧拉跳变/轨迹过长时容易超过固件上限。
        # 这里做“上传前抽稀”，并把被删点的 interval_ms 累加到下一保留点，保证总时间尺度不变。
        MAX_TRAJECTORY_POINTS = 120  # 保守值：宁可更粗一点也避免 0x7003

        def _decimate_points_keep_timing(points: list, max_points: int) -> list:
            n = len(points)
            if max_points is None or max_points <= 0 or n <= max_points:
                return points
            if n <= 2 or max_points == 1:
                return [points[-1]] if points else []

            # 选取均匀索引（含首尾），并确保严格递增且不重复
            keep = []
            last = -1
            for i in range(max_points):
                idx = int(round(i * (n - 1) / float(max_points - 1)))
                if idx <= last:
                    idx = last + 1
                if idx >= n:
                    idx = n - 1
                keep.append(idx)
                last = idx
            if keep[-1] != n - 1:
                keep[-1] = n - 1

            out = []
            prev_idx = None
            for idx in keep:
                pt = dict(points[idx])
                if prev_idx is None:
                    out.append(pt)
                else:
                    interval_sum = 0
                    for k in range(prev_idx + 1, idx + 1):
                        try:
                            interval_sum += int(points[k].get("interval_ms", 0) or 0)
                        except Exception:
                            interval_sum += 0
                    pt["interval_ms"] = int(interval_sum)
                    out.append(pt)
                prev_idx = idx
            return out
        
        try:
            t_upload0 = time.perf_counter()

            try:
                if isinstance(trajectory_points, list) and len(trajectory_points) > MAX_TRAJECTORY_POINTS:
                    original_n = len(trajectory_points)
                    trajectory_points = _decimate_points_keep_timing(trajectory_points, MAX_TRAJECTORY_POINTS)
                    self.logger.warning(f"⚠️ 轨迹点数过多，已自动抽稀: {original_n} -> {len(trajectory_points)}（避免 err=0x7003）")
            except Exception:
                pass

            # 检查轨迹点中的关节限位
            limits = self._load_joint_limits()
            if limits is not None and trajectory_points:
                violations = []
                for point_idx, pt in enumerate(trajectory_points):
                    positions = pt.get("positions", [])
                    if len(positions) >= 6:
                        for motor_idx in range(6):
                            motor_id = motor_idx + 1
                            motor_angle_deg = float(positions[motor_idx])
                            # 将电机角度转换为关节角度
                            joint_angle_deg = self._motor_angle_to_joint_angle(motor_angle_deg, motor_id)
                            
                            # 检查限位
                            if 0 <= motor_idx < 6:
                                min_limit, max_limit = limits[motor_idx]
                                if joint_angle_deg < min_limit or joint_angle_deg > max_limit:
                                    violations.append((point_idx, motor_id, motor_idx + 1, joint_angle_deg, min_limit, max_limit))
                
                if violations:
                    # 构建错误消息（只显示前几个超限的点，避免消息过长）
                    msg_parts = ["⛔ 关节限位检查失败，拒绝上传轨迹："]
                    # 按电机ID分组显示，每个电机只显示第一个超限的点
                    shown_motors = set()
                    for point_idx, motor_id, joint_num, joint_angle, min_lim, max_lim in violations[:10]:  # 最多显示10个
                        if motor_id not in shown_motors:
                            msg_parts.append(
                                f"  轨迹点{point_idx}: 电机{motor_id}(关节{joint_num}) 关节角度 {joint_angle:.2f}° 超出限位 [{min_lim:.2f}°, {max_lim:.2f}°]"
                            )
                            shown_motors.add(motor_id)
                    if len(violations) > 10:
                        msg_parts.append(f"  ... 还有 {len(violations) - 10} 个超限点未显示")
                    error_msg = "\n".join(msg_parts)
                    self.logger.error(error_msg)
                    raise RuntimeError(error_msg)

            # 1. 开始上传（清空缓存）
            try:
                resp = self.client.request(
                    motor_id=0,  # 轨迹命令不需要motor_id
                    opcode=0x70,  # TRAJECTORY_UPLOAD
                    args=bytes([0]),  # mode=0: 开始上传
                    timeout_ms=timeout_ms
                )
            except TimeoutError as e:
                raise TimeoutError(f"轨迹上传开始阶段超时: {e}") from e
            if resp.status != 0:
                raise RuntimeError(f"开始上传失败: status={resp.status}, err=0x{resp.err_code:04X}")

            # 2. 上传轨迹点
            #
            # 固件支持两种方式：
            # - mode=1：单点追加（兼容旧固件，但串口往返次数=点数）
            # - mode=3：批量追加（新固件，显著降低“点按钮->开动”的启动延迟）
            #
            # 由于 OmniCAN 的 UCP payload 最大 512B，且请求里还有 TLV 开销，
            # args 建议控制在 <=492 字节。
            # 单点 pt_size=38B，mode=3 包格式: [3][n][n*38] => n_max=12

            def _encode_one_point(pt: dict) -> bytes:
                b = bytearray()
                interval = int(pt["interval_ms"])
                b.extend(struct.pack("<H", interval))
                for motor_idx in range(6):
                    pos_deg = float(pt["positions"][motor_idx])
                    pos_i32 = int(pos_deg * 100)  # 0.01°
                    b.extend(struct.pack("<i", pos_i32))
                    spd_rpm = float(pt["speeds"][motor_idx])
                    spd_u16 = int(spd_rpm * 10)  # 0.1RPM
                    b.extend(struct.pack("<H", spd_u16))
                return bytes(b)

            # 调试输出：对齐固件 TrajectoryPoint（interval_ms + 6×(i32 pos_x0.01deg + u16 spd_x0.1rpm)）
            # 只打印首尾点，避免刷屏。
            try:
                if trajectory_points:
                    def _fmt_pt(idx: int) -> str:
                        pt = trajectory_points[idx]
                        interval = int(pt.get("interval_ms", 0) or 0)
                        pos_deg = [float(x) for x in (pt.get("positions") or [])][:6]
                        spd_rpm = [float(x) for x in (pt.get("speeds") or [])][:6]
                        pos_i32 = [int(x * 100) for x in pos_deg]
                        spd_u16 = [int(x * 10) for x in spd_rpm]
                        return (
                            f"idx={idx} interval_ms={interval} "
                            f"pos_deg={pos_deg} pos_i32={pos_i32} "
                            f"spd_rpm={spd_rpm} spd_u16={spd_u16}"
                        )
                    # 简化日志输出，避免刷屏
                    # self.logger.info(f"[UCP][TRAJ] upload { _fmt_pt(0) }")
                    # if len(trajectory_points) > 1:
                    #     self.logger.info(f"[UCP][TRAJ] upload { _fmt_pt(len(trajectory_points) - 1) }")
            except Exception:
                pass

            pt_size = 2 + 6 * (4 + 2)  # 38
            # 经验值：在 Windows + USB CDC + 较多并发模块场景下，大包更容易出现“偶发无响应”
            # 这里默认更小的批量包，换取更稳定、更低的最差延迟（避免 10~20s 卡顿）。
            safe_max_args_bytes = 200
            max_points_per_batch = max(2, (safe_max_args_bytes - 2) // pt_size)

            # 先尝试批量模式；若固件不支持则回退单点模式
            use_bulk = True
            idx = 0
            def _send_bulk(n: int):
                args = bytearray()
                args.append(3)  # mode=3: 批量追加
                args.append(n)
                for k in range(n):
                    args.extend(_encode_one_point(trajectory_points[idx + k]))
                if len(args) != 2 + n * pt_size:
                    raise RuntimeError("批量轨迹编码长度异常")
                return self.client.request(motor_id=0, opcode=0x70, args=bytes(args), timeout_ms=timeout_ms)

            def _send_single(i: int):
                args = bytearray()
                args.append(1)
                args.extend(_encode_one_point(trajectory_points[i]))
                return self.client.request(motor_id=0, opcode=0x70, args=bytes(args), timeout_ms=timeout_ms)

            while idx < len(trajectory_points):
                remaining = len(trajectory_points) - idx

                if use_bulk and remaining > 1:
                    n = min(max_points_per_batch, remaining)

                    # 如果批量上传超时，不要直接失败：自动“缩包重试”，直到退化为单点，提升稳定性
                    while n > 1:
                        try:
                            t_req0 = time.perf_counter()
                            resp = _send_bulk(n)
                        except TimeoutError:
                            try:
                                self.logger.warning(f"⚠️ 轨迹批量包超时，缩包重试: idx={idx} n={n}")
                            except Exception:
                                pass
                            n = n // 2
                            continue
                        finally:
                            try:
                                dt_ms = (time.perf_counter() - t_req0) * 1000.0
                                if dt_ms >= 1000.0:
                                    self.logger.warning(f"⚠️ 轨迹批量包耗时偏长: idx={idx} n={n} {dt_ms:.0f}ms")
                            except Exception:
                                pass

                        if resp.status == 0:
                            idx += n
                            break

                        # 旧固件不支持 mode=3：回退到单点
                        if resp.status in (1, 2) and resp.err_code in (0x7005,):
                            use_bulk = False
                            break

                        raise RuntimeError(f"批量上传失败: status={resp.status}, err=0x{resp.err_code:04X}")

                    if n > 1:
                        continue

                    # 退化为单点
                    try:
                        self.logger.warning(f"⚠️ 轨迹上传降级为单点模式: idx={idx}")
                    except Exception:
                        pass
                    use_bulk = False

                # mode=1: 单点追加
                try:
                    resp = _send_single(idx)
                except TimeoutError as e:
                    raise TimeoutError(f"轨迹单点上传超时(idx={idx}): {e}") from e
                if resp.status != 0:
                    raise RuntimeError(f"上传点{idx}失败: status={resp.status}, err=0x{resp.err_code:04X}")
                idx += 1
            
            # 3. 完成上传
            try:
                resp = self.client.request(
                    motor_id=0,
                    opcode=0x70,
                    args=bytes([2]),  # mode=2: 完成上传
                    timeout_ms=timeout_ms
                )
            except TimeoutError as e:
                raise TimeoutError(f"轨迹上传完成阶段超时: {e}") from e
            if resp.status != 0:
                raise RuntimeError(f"完成上传失败: status={resp.status}, err=0x{resp.err_code:04X}")
            
            # 简化日志输出（由上层统一输出）
            # try:
            #     dt_ms = (time.perf_counter() - t_upload0) * 1000.0
            #     self.logger.info(f"✅ 轨迹上传成功: {len(trajectory_points)}个点 ({dt_ms:.0f}ms)")
            # except Exception:
            #     self.logger.info(f"✅ 轨迹上传成功: {len(trajectory_points)}个点")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 轨迹上传失败: {e}")
            raise
    
    def execute_trajectory(self, timeout_ms: int = 2000) -> bool:
        """
        执行已上传的轨迹
        
        Args:
            timeout_ms: 超时时间(ms)
            
        Returns:
            bool: 执行启动成功返回True
        """
        if not self.client:
            raise RuntimeError("未连接，请先调用 connect()")

        # 新一轮轨迹开始：重置状态变更日志标记
        self._traj_last_status = None
        self._traj_logged_completed = False
        self._traj_logged_error = False
        
        resp = self.client.request(
            motor_id=0,
            opcode=0x71,  # TRAJECTORY_EXECUTE
            args=b"",
            timeout_ms=timeout_ms
        )
        if resp.status != 0:
            raise RuntimeError(f"执行轨迹失败: status={resp.status}, err=0x{resp.err_code:04X}")
        
        # 简化日志输出（由上层统一输出）
        # self.logger.info("✅ 轨迹开始执行")
        return True
    
    def stop_trajectory(self, timeout_ms: int = 1000) -> bool:
        """
        停止轨迹执行
        
        Args:
            timeout_ms: 超时时间(ms)
            
        Returns:
            bool: 停止成功返回True
        """
        if not self.client:
            raise RuntimeError("未连接，请先调用 connect()")
        
        resp = self.client.request(
            motor_id=0,
            opcode=0x72,  # TRAJECTORY_STOP
            args=b"",
            timeout_ms=timeout_ms
        )
        if resp.status != 0:
            raise RuntimeError(f"停止轨迹失败: status={resp.status}, err=0x{resp.err_code:04X}")
        
        self.logger.info("✅ 轨迹已停止")
        return True
    
    def get_trajectory_status(self, timeout_ms: int = 1000) -> dict:
        """
        查询轨迹执行状态
        
        Args:
            timeout_ms: 超时时间(ms)
            
        Returns:
            dict: 状态信息
            - status: 0=idle, 1=uploading, 2=ready, 3=running, 4=completed, 5=error
            - total_points: 总点数
            - current_index: 当前执行到第几个点
            - last_y42_status: 最后一次Y42命令的状态
            - last_y42_err_code: 最后一次Y42命令的错误码
        """
        if not self.client:
            raise RuntimeError("未连接，请先调用 connect()")
        
        resp = self.client.request(
            motor_id=0,
            opcode=0x73,  # TRAJECTORY_STATUS
            args=b"",
            timeout_ms=timeout_ms
        )
        if resp.status != 0:
            raise RuntimeError(f"查询状态失败: status={resp.status}, err=0x{resp.err_code:04X}")
        
        # 解析响应数据
        data = resp.data
        if len(data) < 8:
            raise RuntimeError(f"状态数据长度不足: {len(data)}字节")
        
        status_map = {0: 'idle', 1: 'uploading', 2: 'ready', 3: 'running', 4: 'completed', 5: 'error'}
        
        result = {
            'status': data[0],
            'status_name': status_map.get(data[0], 'unknown'),
            'total_points': data[1] | (data[2] << 8),
            'current_index': data[3] | (data[4] << 8),
            'last_y42_status': data[5],
            'last_y42_err_code': data[6] | (data[7] << 8),
            'y42_success_count': 0,
            'y42_fail_count': 0
        }
        
        # 如果有额外的调试数据（新版固件）
        if len(data) >= 12:
            result['y42_success_count'] = data[8] | (data[9] << 8)
            result['y42_fail_count'] = data[10] | (data[11] << 8)

        # 仅在状态变更时输出一次关键日志（开始执行日志在 execute_trajectory() 已输出）
        try:
            last = getattr(self, "_traj_last_status", None)
            cur = int(result.get("status", -1))
            if last != cur:
                self._traj_last_status = cur
                if cur == 4 and not getattr(self, "_traj_logged_completed", False):
                    self._traj_logged_completed = True
                    # 简化日志输出（由上层统一输出）
                    # self.logger.info(
                    #     f"✅ 轨迹执行完成: {result.get('current_index', 0)}/{result.get('total_points', 0)}"
                    # )
                elif cur == 5 and not getattr(self, "_traj_logged_error", False):
                    self._traj_logged_error = True
                    self.logger.error(
                        "❌ 轨迹执行错误: "
                        f"last_y42_status=0x{int(result.get('last_y42_status', 0)):02X}, "
                        f"err_code=0x{int(result.get('last_y42_err_code', 0)):04X}"
                    )
        except Exception:
            pass

        return result
    
    def __repr__(self) -> str:
        status = "已连接" if self.client else "未连接"
        return f"ZDTMotorController(motor_id={self.motor_id}, port={self.port}, {status})"


# ==================== 命令构建器兼容层 ====================

class _CommandBuilderCompat:
    """
    命令构建器兼容层
    
    为旧的SLCAN API提供兼容支持，主要用于多电机同步控制中的Y42聚合模式。
    旧代码通过 motor.command_builder.xxx() 构建CAN命令字节，在UCP模式下，
    我们将其转换为ZDT命令体（用于Y42聚合）。
    """
    
    def __init__(self, motor: ZDTMotorController):
        self.motor = motor
        self.logger = logging.getLogger(f"CommandBuilderCompat[ID:{motor.motor_id}]")
    
    def position_mode_direct(self, position: float, speed: float, 
                            is_absolute: bool = True, multi_sync: bool = False) -> bytes:
        """
        构建位置控制命令（直接模式）
        
        ⚠️ 参照 ESP_can_firmware/test_multi_motor_ucp.py:315-319
        
        ZDT 0xFB 位置直通命令（大端序）：
        FB + Dir(1B) + Speed(2B BE) + Position(4B BE) + Abs/Rel(1B) + Sync(1B) + 6B
        
        Args:
            position: 目标位置（度）
            speed: 速度（RPM）
            is_absolute: 是否绝对位置
            multi_sync: 是否多机同步（Y42模式下忽略此参数）
            
        Returns:
            bytes: ZDT命令体（10字节，包含0x6B校验字节）
        """
        # 参数转换（与ESP_can_firmware一致）
        direction = 1 if position < 0 else 0
        pos_val = int(round(abs(position) * 10.0))  # 度 → 0.1度单位
        spd_val = int(round(abs(speed) * 10.0))     # RPM → 0.1RPM单位
        
        # ZDT 0xFB 命令（大端序）
        sub_body = struct.pack(">BBHI", 0xFB, direction, spd_val, pos_val) + \
                   struct.pack(">BB", 1 if is_absolute else 0, 0) + \
                   b"\x6B"
        
        return sub_body
    
    def position_mode_trapezoid(self, position: float, max_speed: float,
                               acceleration: int, deceleration: int,
                               is_absolute: bool = True, multi_sync: bool = False) -> bytes:
        """
        构建位置控制命令（梯形曲线模式）
        
        ⚠️ 梯形曲线仍使用0xFB命令，参数含义相同
        
        Args:
            position: 目标位置（度）
            max_speed: 最大速度（RPM）
            acceleration: 加速度（RPM/s）（暂不使用，保留兼容性）
            deceleration: 减速度（RPM/s）（暂不使用，保留兼容性）
            is_absolute: 是否绝对位置
            multi_sync: 是否多机同步
            
        Returns:
            bytes: ZDT命令体（10字节）
        """
        # 梯形曲线模式仍使用0xFB，加速度通过其他机制控制
        return self.position_mode_direct(position, max_speed, is_absolute, multi_sync)
    
    def speed_mode(self, speed: float, acceleration: int = 1000, 
                   multi_sync: bool = False) -> bytes:
        """
        构建速度控制命令
        
        ⚠️ 参照 ESP_can_firmware/test_multi_motor_ucp.py:343-345
        
        ZDT 0xF6 速度模式（大端序）：
        F6 + Dir(1B) + Accel(2B BE) + Speed(2B BE) + Sync(1B) + 6B
        
        Args:
            speed: 目标速度（RPM）
            acceleration: 加速度（RPM/s）
            multi_sync: 是否多机同步
            
        Returns:
            bytes: ZDT命令体（8字节）
        """
        # 参数转换
        direction = 1 if speed < 0 else 0
        spd_val = int(round(abs(speed) * 10.0))  # RPM → 0.1RPM单位
        acc_val = acceleration  # 直接使用RPM/s
        
        # ZDT 0xF6 命令（大端序）⚠️ 注意：加速度在前，速度在后！
        sub_body = struct.pack(">BBHH B", 0xF6, direction, acc_val, spd_val, 0) + b"\x6B"
        
        return sub_body
    
    def homing_mode(self, mode: int = 4, **kwargs) -> bytes:
        """
        构建回零命令
        
        ⚠️ 参照 ESP_can_firmware/test_multi_motor_ucp.py:423-424
        
        ZDT 0x9A 回零（大端序）：
        9A + Mode(1B) + Sync(1B) + 6B
        
        Args:
            mode: 回零模式（0-5）
            **kwargs: 其他参数
            
        Returns:
            bytes: ZDT命令体（4字节）
        """
        # ZDT 0x9A 命令（大端序）
        sub_body = struct.pack(">BB B", 0x9A, mode, 0) + b"\x6B"
        
        return sub_body
    
    def multi_sync_motion(self) -> bytes:
        """
        构建多机同步触发命令
        
        注意：本项目已禁用"Pre-load + Trigger"同步方式（仅允许 Y42）。
        此方法仅保留兼容性，实际不应被调用。
        
        Returns:
            bytes: 空字节（不可用）
        """
        raise RuntimeError("multi_sync_motion() 已被禁用：本项目多机同步仅允许 Y42。")
    
    def read_drive_parameters(self) -> bytes:
        """
        构建读取驱动参数命令（兼容性）
        
        注意：UCP模式下应直接调用 motor.get_drive_parameters()
        """
        self.logger.warning(
            "command_builder.read_drive_parameters() 已废弃，"
            "请使用 motor.get_drive_parameters()"
        )
        return b''
    
    def read_system_status(self) -> bytes:
        """
        构建读取系统状态命令（兼容性）
        
        注意：UCP模式下应直接调用 motor.get_system_status()
        """
        self.logger.warning(
            "command_builder.read_system_status() 已废弃，"
            "请使用 motor.get_system_status()"
        )
        return b''

