#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Joy-Con 手柄控制 SDK 封装
=========================

目标：
- 复用现有 `core.joycon_arm_controller.JoyConArmController` 的所有控制逻辑；
- 提供一个**无界面依赖**的手柄控制接口，方便在桌面 / ROS / 后端服务中直接启用 Joy-Con 控制。
"""

from __future__ import annotations

from typing import Dict, Any, Tuple, Optional, List

from Horizon_Core.core.joycon_arm_controller import JoyConArmController, ControlMode
from Horizon_Core.core.arm_core.kinematics_factory import create_configured_kinematics

# 可选：夹爪（内部电机ID=7，力矩模式，UCP/OmniCAN 硬件保护）
try:
    from .gripper_sdk import ZDTGripperSDK
    _FORCE_GRIPPER_AVAILABLE = True
except Exception:
    ZDTGripperSDK = None  # type: ignore
    _FORCE_GRIPPER_AVAILABLE = False


class _JoyconForceGripperAdapter:
    """
    适配 JoyConArmController 的 claw_controller 接口：
    - open(angle)  -> gripper.open(current_ma=...)
    - close(angle) -> gripper.clamp(current_ma=...)
    """

    def __init__(self, *, motor, params: Dict[str, Any]):
        self._motor = motor
        self._params = params
        # 直接复用电机连接对象（UCP连接池共享）
        self._gripper = ZDTGripperSDK(motor=self._motor)  # type: ignore

    def is_connected(self) -> bool:
        try:
            return bool(self._gripper.is_connected())
        except Exception:
            return False

    def open(self, _angle: float = 0.0) -> None:
        # 当前版本：夹爪不使用角度/电流参数，直接张开（使用硬件默认配置）
        self._gripper.open()

    def close(self, _angle: float = 90.0) -> None:
        # 当前版本：夹爪不使用角度/电流参数，直接闭合（使用硬件默认配置）
        self._gripper.clamp()

def _load_motor_config():
    """从 motor_config.json 加载电机配置（仅保留 Mark）。"""
    import os
    import json
    import sys
    
    # 默认配置
    config = {
        "motor_reducer_ratios": {
            # 默认减速比
            "1": 50.0, "2": 50.0, "3": 50.0, "4": 30.0, "5": 30.0, "6": 30.0
        },
        "motor_directions": {
            # 默认方向
            "1": -1, "2": 1, "3": 1, "4": -1, "5": -1, "6": 1
        }
    }
    
    try:
        # 源码运行：强制用项目内 ./config；打包运行：用外置可写配置目录
        if not getattr(sys, "frozen", False):
            current_dir = os.path.dirname(os.path.abspath(__file__))
            config_dir = os.path.join(os.path.dirname(current_dir), "config")
        else:
            config_dir = os.environ.get("HORIZONARM_CONFIG_DIR", "").strip()
            if not config_dir:
                data_root = os.environ.get("HORIZON_DATA_DIR", "").strip()
                if data_root:
                    cand = os.path.join(data_root, "config")
                    if os.path.isdir(cand):
                        config_dir = cand
            if not config_dir:
                current_dir = os.path.dirname(os.path.abspath(__file__))
                config_dir = os.path.join(os.path.dirname(current_dir), "config")

        def _safe_read(p: str) -> dict:
            try:
                if not os.path.exists(p):
                    return {}
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f) or {}
            except Exception:
                return {}

        config_path = os.path.join(config_dir, "motor_config.json")
        if config_path:
            loaded = _safe_read(config_path)
            if "motor_reducer_ratios" in loaded:
                config["motor_reducer_ratios"].update(loaded["motor_reducer_ratios"])
            if "motor_directions" in loaded:
                config["motor_directions"].update(loaded["motor_directions"])
    except Exception as e:
        print(f" ⚠️ [JoyconSDK] 加载电机配置失败，使用默认值: {e}")
        
    return config

class JoyconSDK:
    """
    Joy-Con 手柄控制 SDK。

    - 内部封装一个 JoyConArmController；
    - 只提供绑定机械臂 + 连接手柄 + 启动/停止控制等高层接口；
    - 具体按键映射 / 运动学控制完全复用 core.joycon_arm_controller 内部实现。
    """

    def __init__(self) -> None:
        self._controller = JoyConArmController()
        self._force_gripper_adapter = None

    # ------------------------------------------------------------------
    # 透传底层状态（供 UI 使用）
    # ------------------------------------------------------------------
    @property
    def control_mode(self):
        return getattr(self._controller, "control_mode", None)

    # ------------------------------------------------------------------
    # 夹爪控制（供 GUI / JoyConArmController 调用）
    # ------------------------------------------------------------------

    @property
    def claw_controller(self):
        return getattr(self._controller, "claw_controller", None)

    @claw_controller.setter
    def claw_controller(self, controller) -> None:
        setattr(self._controller, "claw_controller", controller)

    def set_claw_controller_arm2(self, controller) -> None:
        """绑定机械臂2夹爪控制器（用于双臂姿态模式左手柄开合夹爪）。"""
        try:
            arm2 = getattr(self._controller, "_arm2_controller", None)
            if arm2 is not None:
                setattr(arm2, "claw_controller", controller)
        except Exception:
            pass

    def attach_can_force_gripper_from_motors(self, motors: Dict[int, Any]) -> bool:
        """
        使用机械臂已连接的夹爪电机控制器，挂载夹爪到 JoyCon。
        """
        if not _FORCE_GRIPPER_AVAILABLE:
            return False
        if not motors:
            return False

        try:
            motor7 = motors.get(7, None)
            if motor7 is None:
                return False

            self._force_gripper_adapter = _JoyconForceGripperAdapter(
                motor=motor7,
                params=self._controller.params,
            )
            self._controller.claw_controller = self._force_gripper_adapter
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # 机械臂绑定
    # ------------------------------------------------------------------

    def bind_arm(
        self,
        motors: Dict[int, Any],
        *,
        use_motor_config: bool = True,
        kinematics: Optional[RobotKinematics] = None,
        mujoco_controller: Optional[Any] = None,
    ) -> None:
        """
        绑定真实机械臂对象到 Joy-Con 控制器。

        Args:
            motors: 电机实例字典 {motor_id: ZDTMotorController}
            use_motor_config: 是否使用当前 active 版本文件 motor_config_{1/2/3}.json 里的减速比/方向
            kinematics: 可选，若不传则自动创建一个按 `dh_parameters_config.json` 配置的运动学对象
            mujoco_controller: 可选，用于同时驱动 MuJoCo 数字孪生
        """
        mcm = None
        if use_motor_config:
            # 这里的 _load_motor_config 会被后续 controller 使用
            # 注意：JoyConArmController 内部原本可能期望一个有 get_all_* 方法的对象
            # 我们需要检查一下 JoyConArmController 的实现
            config = _load_motor_config()
            # 为了兼容，我们构造一个简单的类模拟 motor_config_manager
            class SimpleConfigManager:
                def __init__(self, cfg):
                    self.cfg = cfg

                def get_all_reducer_ratios(self):
                    return {int(k): v for k, v in self.cfg["motor_reducer_ratios"].items()}

                def get_all_directions(self):
                    return {int(k): v for k, v in self.cfg["motor_directions"].items()}

                # ----------------------------
                # 单电机查询接口（兼容不同版本实现）
                # ----------------------------
                def get_motor_reducer_ratio(self, motor_id: int):
                    ratios = self.get_all_reducer_ratios()
                    return float(ratios.get(int(motor_id), 1.0))

                def get_motor_direction(self, motor_id: int):
                    dirs = self.get_all_directions()
                    return int(dirs.get(int(motor_id), 1))

                # 兼容某些二进制封装里存在的历史拼写错误：
                # JoyConArmController 可能会调用 geet_motor_reducer_ratio
                def geet_motor_reducer_ratio(self, motor_id: int):
                    return self.get_motor_reducer_ratio(motor_id)
            mcm = SimpleConfigManager(config)

        kin = kinematics if kinematics is not None else create_configured_kinematics()

        self._controller.set_arm(
            motors=motors,
            motor_config_manager=mcm,
            kinematics=kin,
            mujoco_controller=mujoco_controller,
        )

    # 兼容旧接口：保持 set_arm 与 GUI 现有调用一致
    def set_arm(
        self,
        motors: Dict[int, Any],
        motor_config_manager=None,
        kinematics: Optional[RobotKinematics] = None,
        mujoco_controller: Optional[Any] = None,
        arm_index: Optional[int] = None,
    ) -> None:
        # 若 GUI 传入 motor_config_manager，则直接透传给底层控制器，保证双臂方向/减速比按 active_arm_index 生效
        if motor_config_manager is not None:
            try:
                self._controller.set_arm(
                    motors=motors,
                    motor_config_manager=motor_config_manager,
                    kinematics=kinematics if kinematics is not None else create_configured_kinematics(),
                    mujoco_controller=mujoco_controller,
                    arm_index=arm_index,
                )
                return
            except Exception:
                # 回退到旧逻辑（从 motor_config.json 读取）
                pass
        self.bind_arm(
            motors=motors,
            use_motor_config=True,
            kinematics=kinematics,
            mujoco_controller=mujoco_controller,
        )

    # ------------------------------------------------------------------
    # 手柄连接 / 控制启动
    # ------------------------------------------------------------------

    def connect_joycon(self) -> Tuple[bool, bool]:
        """
        连接 Joy-Con 手柄。

        Returns:
            (left_ok, right_ok): 左/右手柄是否连接成功。
        """
        return self._controller.connect_joycon()

    def disconnect_joycon(self) -> None:
        """断开 Joy-Con 连接。"""
        self._controller.disconnect_joycon()

    # ------------------------------------------------------------------
    # 手柄状态读取（用于无 UI 调试 / 可视化）
    # ------------------------------------------------------------------

    def get_left_joycon_status(self) -> Optional[Dict[str, Any]]:
        """
        获取左 Joy-Con 当前状态（按键、摇杆、电池、陀螺仪等）。

        Returns:
            dict 或 None：若未连接或读取失败则返回 None。
        """
        try:
            joycon = getattr(self._controller, "joycon", None)
            if joycon is None:
                return None
            return joycon.get_left_status()
        except Exception:
            return None

    def get_right_joycon_status(self) -> Optional[Dict[str, Any]]:
        """
        获取右 Joy-Con 当前状态（按键、摇杆、电池、陀螺仪等）。

        Returns:
            dict 或 None：若未连接或读取失败则返回 None。
        """
        try:
            joycon = getattr(self._controller, "joycon", None)
            if joycon is None:
                return None
            return joycon.get_right_status()
        except Exception:
            return None

    def start_control(self) -> None:
        """启动 Joy-Con 控制循环（开启独立线程）。"""
        self._controller.start()

    def stop_control(self) -> None:
        """停止 Joy-Con 控制循环。"""
        self._controller.stop()

    # ------------------------------------------------------------------
    # 姿态模式（供 UI 单独开关）
    # ------------------------------------------------------------------

    # 姿态模式实现（两种子模式）
    # - 1: TCP 模式（原 Mode1）
    # - 2: 关节模式（原 Mode2）
    ATTITUDE_MODE_TCP = 1
    ATTITUDE_MODE_JOINT = 2
    # 兼容旧命名
    ATTITUDE_MODE_1 = 1
    ATTITUDE_MODE_2 = 2

    def set_attitude_mode(self, mode) -> None:
        """
        选择姿态模式实现（建议在启用姿态模式前设置）。

        - TCP 模式（推荐用于“末端姿态 + TCP 旋转定点”手感）：`1 / "tcp" / "tcp_mode" / "mode1" / "legacy"`
        - 关节模式（推荐用于“IMU -> 关节轴对轴映射”手感）：`2 / "joint" / "joint_mode" / "mode2" / "main"`
        """
        m = mode
        try:
            if isinstance(m, str):
                s = m.strip().lower()
                if s in ("1", "mode1", "legacy", "m1", "tcp", "tcp_mode", "tcp-mode", "tcp模式"):
                    m = 1
                elif s in ("2", "mode2", "main", "m2", "attitude2", "joint", "joint_mode", "joint-mode", "关节模式"):
                    m = 2
                else:
                    # 默认：关节模式（你当前主推）
                    m = 2
            else:
                m = int(m)
        except Exception:
            m = 2

        # 统一走底层开关：True=关节模式（原 mode2），False=TCP模式（原 mode1）
        try:
            if hasattr(self._controller, "set_attitude_mode2_enabled"):
                self._controller.set_attitude_mode2_enabled(bool(int(m) == 2))
        except Exception:
            pass

    def get_attitude_mode(self) -> int:
        """返回当前姿态模式实现编号（1 或 2）。"""
        try:
            v = int(getattr(self._controller, "_att_mode_variant", 1))
            return 2 if v == 2 else 1
        except Exception:
            return 1

    def enable_attitude(self, *, mode="joint") -> bool:
        """
        启用姿态模式（ATTITUDE）。

        默认启用主推的关节模式（原 Mode2：第一人称平移 + 轴对轴姿态映射）。
        """
        try:
            self.set_attitude_mode(mode)
        except Exception:
            pass
        return bool(self._controller.enable_attitude_mode())

    def enable_attitude_mode(self) -> bool:
        """
        兼容旧接口：按当前已选择的姿态实现启用姿态模式。

        如需强制选择实现，优先使用 `enable_attitude(mode=...)`。
        """
        return bool(self._controller.enable_attitude_mode())

    def disable_attitude_mode(self) -> None:
        self._controller.disable_attitude_mode()

    def move_to_joycon_start_pose(self, *, force: bool = False) -> bool:
        return bool(self._controller.move_to_joycon_start_pose(force=force))

    def pause_control(self) -> None:
        """暂停控制（不再响应手柄输入，但不断开连接）。"""
        self._controller.pause()

    def resume_control(self) -> None:
        """恢复控制。"""
        self._controller.resume()

    def emergency_stop(self) -> None:
        """紧急停止（停止所有电机，并置位急停标志）。"""
        self._controller.emergency_stop()

    # ------------------------------------------------------------------
    # 模式 / 速度 / 常用动作
    # ------------------------------------------------------------------

    def toggle_mode(self) -> None:
        """在笛卡尔模式 / 关节模式之间切换。"""
        self._controller.toggle_control_mode()

    def set_mode_cartesian(self) -> None:
        """强制切换到笛卡尔控制模式。"""
        if self._controller.control_mode != ControlMode.CARTESIAN:
            self._controller.toggle_control_mode()

    def set_mode_joint(self) -> None:
        """强制切换到关节控制模式。"""
        if self._controller.control_mode != ControlMode.JOINT:
            self._controller.toggle_control_mode()

    def increase_speed(self) -> None:
        """提高手柄控制速度等级。"""
        self._controller.increase_speed()

    def decrease_speed(self) -> None:
        """降低手柄控制速度等级。"""
        self._controller.decrease_speed()

    def move_to_home(self) -> None:
        """回到软件定义的 home 姿态（所有关节 0）。"""
        self._controller.move_to_home()

    def home_to_hardware_zero(self) -> None:
        """回到驱动器保存的硬件零位（与示教器的回零位(坐标原点)一致）。"""
        self._controller.home_to_hardware_zero()

    # ------------------------------------------------------------------
    # 参数配置（保持与 JoyConArmController.params / 限位一致）
    # ------------------------------------------------------------------

    def set_stick_deadzone(self, deadzone: int) -> None:
        """
        设置摇杆死区（对应 JoyConArmController.params['stick_deadzone']）。
        """
        self._controller.params["stick_deadzone"] = int(deadzone)

    def configure_cartesian(
        self,
        *,
        position_step: Optional[float] = None,
        rotation_step: Optional[float] = None,
        max_speed: Optional[float] = None,
        max_angular_speed: Optional[float] = None,
    ) -> None:
        """
        配置笛卡尔模式参数（对应 params 中 cartesian_* 字段）。
        """
        p = self._controller.params
        if position_step is not None:
            p["cartesian_position_step"] = float(position_step)
        if rotation_step is not None:
            p["cartesian_rotation_step"] = float(rotation_step)
        if max_speed is not None:
            p["cartesian_max_speed"] = float(max_speed)
        if max_angular_speed is not None:
            p["cartesian_max_angular_speed"] = float(max_angular_speed)

    def configure_joint(
        self,
        *,
        angle_step: Optional[float] = None,
        max_speed: Optional[int] = None,
        acceleration: Optional[int] = None,
        deceleration: Optional[int] = None,
    ) -> None:
        """
        配置关节模式参数（对应 params 中 joint_* 字段）。
        """
        p = self._controller.params
        if angle_step is not None:
            p["joint_angle_step"] = float(angle_step)
        if max_speed is not None:
            p["joint_max_speed"] = int(max_speed)
        if acceleration is not None:
            p["joint_acceleration"] = int(acceleration)
        if deceleration is not None:
            p["joint_deceleration"] = int(deceleration)

    def configure_speed_levels(
        self,
        levels: Optional[List[float]] = None,
        current_index: Optional[int] = None,
    ) -> None:
        """
        配置速度等级数组及当前等级索引（对应 params['speed_levels'] / params['current_speed_index']）。
        """
        p = self._controller.params
        if levels is not None and len(levels) > 0:
            p["speed_levels"] = [float(v) for v in levels]
        if current_index is not None:
            idx = int(current_index)
            idx = max(0, min(idx, len(p.get("speed_levels", [])) - 1))
            p["current_speed_index"] = idx

    def configure_workspace(
        self,
        *,
        min_radius: Optional[float] = None,
        max_radius: Optional[float] = None,
        min_z: Optional[float] = None,
        max_z: Optional[float] = None,
    ) -> None:
        """
        配置工作空间限制（对应 JoyConArmController.workspace_limits）。
        """
        ws = self._controller.workspace_limits
        if min_radius is not None:
            ws["min_radius"] = float(min_radius)
        if max_radius is not None:
            ws["max_radius"] = float(max_radius)
        if min_z is not None:
            ws["min_z"] = float(min_z)
        if max_z is not None:
            ws["max_z"] = float(max_z)

    def configure_force_gripper_currents(
        self,
        *,
        open_current_ma: Optional[int] = None,
        close_current_ma: Optional[int] = None,
    ) -> None:
        """兼容接口（已废弃）：当前版本不再允许上位机配置夹爪电流。"""
        return

    # 兼容旧名称：历史上叫 configure_gripper_angles（舵机夹爪时代），现在语义改为电流（mA）
    def configure_gripper_angles(
        self,
        *,
        open_angle: Optional[float] = None,
        close_angle: Optional[float] = None,
    ) -> None:
        """兼容接口（已废弃）：当前版本不再存在夹爪角度参数。"""
        return

    def set_joint_limits(self, limits: Optional[List[Tuple[float, float]]] = None) -> None:
        """
        设置关节角度限位（对应 JoyConArmController.joint_limits）。

        Args:
            limits: 长度为 6 的列表，每项为 (min_angle, max_angle)。
        """
        if not limits:
            return
        if len(limits) != 6:
            raise ValueError("joint_limits 长度必须为 6")
        self._controller.joint_limits = [(float(a), float(b)) for a, b in limits]

    # ------------------------------------------------------------------
    # 状态查询
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """
        查询当前 Joy-Con 控制器状态（直接转发 JoyConArmController.get_status）。
        """
        return self._controller.get_status()

    def get_status_arm2(self) -> Optional[Dict[str, Any]]:
        """查询机械臂2状态（双臂姿态模式用）。"""
        try:
            if hasattr(self._controller, "get_status_arm2"):
                return self._controller.get_status_arm2()
        except Exception:
            pass
        return None

    def get_input_status(self) -> Dict[str, Any]:
        """获取左右手柄输入状态（包含IMU roll/pitch/yaw 等 raw 字段）。"""
        try:
            if hasattr(self._controller, "get_input_status"):
                return self._controller.get_input_status()
        except Exception:
            pass
        return {"left": {}, "right": {}}

    def set_arm2(
        self,
        motors: Dict[int, Any],
        motor_config_manager=None,
        kinematics: Optional[RobotKinematics] = None,
        mujoco_controller: Optional[Any] = None,
        arm_index: Optional[int] = 2,
        preferred_side: str = "left",
    ) -> None:
        """绑定副臂（不启动控制线程，仅用于双臂姿态模式）。"""
        try:
            if hasattr(self._controller, "set_arm2"):
                self._controller.set_arm2(
                    motors=motors,
                    motor_config_manager=motor_config_manager,
                    kinematics=kinematics if kinematics is not None else create_configured_kinematics(),
                    mujoco_controller=mujoco_controller,
                    arm_index=arm_index,
                    preferred_side=str(preferred_side or "left"),
                )
        except Exception:
            pass

    def set_dual_attitude_enabled(self, enabled: bool) -> None:
        """设置双臂姿态模式开关（仅 ATTITUDE 模式生效）。"""
        try:
            if hasattr(self._controller, "set_dual_attitude_enabled"):
                self._controller.set_dual_attitude_enabled(bool(enabled))
        except Exception:
            pass

    def set_dual_arm_binding(self, right_arm_index: int, left_arm_index: int) -> None:
        """设置双臂绑定（右/左 Joy-Con -> Arm1/Arm2），用于按钮/夹爪分发与输入侧选择。"""
        try:
            if hasattr(self._controller, "set_dual_arm_binding"):
                self._controller.set_dual_arm_binding(int(right_arm_index), int(left_arm_index))
        except Exception:
            pass

    def set_preferred_side(self, side: str) -> None:
        """设置主臂在姿态模式下监听的 Joy-Con 侧（left/right）。"""
        try:
            if hasattr(self._controller, "set_preferred_side"):
                self._controller.set_preferred_side(str(side or "right"))
        except Exception:
            pass

    def set_attitude_mode2_enabled(self, enabled: bool) -> None:
        """设置姿态模式2开关（需在启用姿态模式前设置）。"""
        try:
            if hasattr(self._controller, "set_attitude_mode2_enabled"):
                self._controller.set_attitude_mode2_enabled(bool(enabled))
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 兼容底层属性访问（供 GUI 等高层代码复用现有逻辑）
    # ------------------------------------------------------------------

    @property
    def running(self) -> bool:
        """当前控制线程是否在运行。"""
        return bool(getattr(self._controller, "running", False))

    @property
    def params(self) -> Dict[str, Any]:
        """暴露底层控制参数字典（只读引用，供配置界面使用）。"""
        return self._controller.params

    @property
    def joint_limits(self) -> List[Tuple[float, float]]:
        """暴露关节角度限位（列表长度为 6）。"""
        return self._controller.joint_limits

    @joint_limits.setter
    def joint_limits(self, limits: List[Tuple[float, float]]) -> None:
        self._controller.joint_limits = [(float(a), float(b)) for a, b in limits]

    @property
    def workspace_limits(self) -> Dict[str, float]:
        """暴露工作空间限制字典。"""
        return self._controller.workspace_limits

    @workspace_limits.setter
    def workspace_limits(self, limits: Dict[str, float]) -> None:
        self._controller.workspace_limits.update(
            {
                "min_radius": float(limits.get("min_radius", self._controller.workspace_limits.get("min_radius", 0.0))),
                "max_radius": float(limits.get("max_radius", self._controller.workspace_limits.get("max_radius", 0.0))),
                "min_z": float(limits.get("min_z", self._controller.workspace_limits.get("min_z", 0.0))),
                "max_z": float(limits.get("max_z", self._controller.workspace_limits.get("max_z", 0.0))),
            }
        )


