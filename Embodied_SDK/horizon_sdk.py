#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HorizonArmSDK 顶层聚合接口
=========================

设计目的
--------
- **单一入口**：对外只暴露一个 `HorizonArmSDK`，其他人只需要依赖这一层即可；
- **多子模块聚合**：内部组合各类子 SDK（视觉抓取 / 跟随抓取 / 运动 / 具身智能 / 手柄控制 / IO 等）；
- **可渐进扩展**：当前先接好已经完成的视觉抓取与跟随抓取，后续再把其他功能逐步 SDK 化接进来。
- **统一运动学口径**：默认通过 `config/dh_parameters_config.json` 创建 FK/IK 模型，保证位姿查询、笛卡尔运动、视觉抓取、JoyCon、MuJoCo 口径一致。

使用示例（伪代码）
------------------

    from Control_SDK.Control_Core import ZDTMotorController
    from Embodied_SDK import HorizonArmSDK

    # 1. 连接电机（示意）
    motors = {
        1: ZDTMotorController(port="/dev/ttyUSB0", baudrate=1_000_000, motor_id=1),
        2: ZDTMotorController(port="/dev/ttyUSB0", baudrate=1_000_000, motor_id=2),
        # ...
    }
    for m in motors.values():
        m.connect()

    # 2. 创建顶层 SDK，一次性绑定上下文（电机 + 相机）
    sdk = HorizonArmSDK(motors=motors, camera_id=0)

    # 3. 通过子模块实现具体功能（例如：视觉抓取 & 跟随）
    sdk.vision.grasp_at_bbox(x1, y1, x2, y2)

    # 手动框选 + 跟随
    ok_init = sdk.follow.init_manual_target(frame0, x1, y1, x2, y2)
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        sdk.follow.follow_step(frame)

后续规划
--------
- `sdk.motion`       关节/笛卡尔运动基础封装（基于 c_a_j / trajectory_executor / IK选解等）；
- `sdk.embodied`     具身智能（基于 embodied_func / hierarchical_decision_system）；
- `sdk.joycon`       手柄 / Joy-Con 控制（基于 joycon_control_widget 中的逻辑重构）；
- `sdk.io`           IO 作业 / 外设控制（基于 io_control_widget 逻辑重构）；
- `sdk.digital_twin` 数字孪生 / 仿真联动；
"""

from __future__ import annotations

from typing import Dict, Any, Optional

from .visual_grasp import VisualGraspSDK, FollowGraspSDK
from .motion import MotionSDK
from .embodied import EmbodiedSDK
from .joycon import JoyconSDK
from .io import IOSDK
from .digital_twin import DigitalTwinSDK
from Horizon_Core.core.arm_core.kinematics_factory import load_kinematics_config


class HorizonArmSDK:
    """
    顶层聚合 SDK。

    - 只负责组装/管理各子模块的上下文（电机、相机 ID 等）；
    - 各功能模块自身的实现仍然在独立文件中（如 visual_grasp.py）；
    - 其他调用方只需要依赖这一层，即可获取所有能力入口。
    """

    def __init__(
        self,
        motors: Dict[int, Any],
        *,
        camera_id: int = 0,
    ) -> None:
        """
        Args:
            motors: 电机控制实例字典 {motor_id: ZDTMotorController 实例}
            camera_id: 默认使用的相机 ID
        """
        self.motors = motors
        self.camera_id = camera_id

        print(f"\n🚀 [HorizonArmSDK] 正在初始化聚合子模块...")

        # ------------------------------------------------------------------
        # 视觉相关子 SDK（已完成的部分）
        # ------------------------------------------------------------------
        self.vision = VisualGraspSDK(camera_id=camera_id)
        self.vision.bind_motors(motors)

        self.follow = FollowGraspSDK(camera_id=camera_id)
        self.follow.bind_motors(motors)

        # 运动控制子 SDK（基础版）
        self.motion = MotionSDK()
        self.motion.bind_motors(motors)

        # 具身智能 SDK（高层自然语言控制）
        # 这里使用默认的 LLM 配置，若需要自定义可在外部替换 self.embodied 实例。
        self.embodied: Optional[Any] = EmbodiedSDK()

        # 手柄控制 SDK（可选使用，依赖 Joy-Con 硬件）
        self.joycon: Optional[Any] = JoyconSDK()
        # 默认绑定真实机械臂，若希望只控制仿真，可在外部重新 bind_arm
        self.joycon.bind_arm(motors)

        # IO 控制 SDK（ESP32）
        self.io: Optional[Any] = IOSDK()

        # 数字孪生 / MuJoCo 仿真 SDK
        self.digital_twin: Optional[Any] = DigitalTwinSDK()

        print(f"✨ [HorizonArmSDK] 所有子模块初始化完成 ✅")

    # ------------------------------------------------------------------
    # 上下文管理接口（可选）
    # ------------------------------------------------------------------

    def update_motors(self, motors: Dict[int, Any]) -> None:
        """
        重新绑定电机实例（例如重新连接 / 更换控制板时）。

        注意：会同步更新所有已存在的子模块。
        """
        self.motors = motors

        # 视觉抓取 / 跟随
        if self.vision is not None:
            self.vision.bind_motors(motors)
        if self.follow is not None:
            self.follow.bind_motors(motors)

        # 运动控制
        if self.motion is not None:
            self.motion.bind_motors(motors)

        # 手柄控制（若存在 JoyCon 控制器，则重新绑定机械臂）
        if self.joycon is not None:
            try:
                self.joycon.bind_arm(motors)  # type: ignore[call-arg]
            except Exception:
                pass

    def set_camera_id(self, camera_id: int) -> None:
        """
        更新默认相机 ID，并同步到子模块。
        """
        self.camera_id = camera_id

        if self.vision is not None:
            self.vision.camera_id = camera_id
        if self.follow is not None:
            self.follow.camera_id = camera_id

        # 同步到全局具身内部状态（供像素世界坐标转换等使用）
        try:
            from Horizon_Core import gateway as horizon_gateway
            embodied_internal = horizon_gateway.get_embodied_internal_module()
            embodied_internal._set_camera_id(camera_id)
        except Exception:
            pass

    def get_kinematics_config(self, *, force_reload: bool = False) -> Dict[str, Any]:
        """
        获取当前 SDK 默认使用的运动学配置。

        返回内容来自 `config/dh_parameters_config.json`，若缺失则回退为默认 DH + 可用限位配置。
        """
        return load_kinematics_config(force_reload=force_reload)


