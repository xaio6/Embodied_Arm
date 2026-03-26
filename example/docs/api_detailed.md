# API 详细参考（导航页）

本项目的 API 范围较大（电机控制/运动学/视觉/手柄/IO/AI/具身智能）。本页不重复堆叠所有函数签名，而是提供“**权威入口** + **推荐阅读顺序**”，让你快速定位到真实可用的接口说明。

---

## 1. 上层 SDK（推荐二次开发入口）

### 1.1 `Embodied_SDK`（脚本/ROS/Web 后端推荐）

- 统一入口：`from Embodied_SDK import HorizonArmSDK`
- 常用模块：
  - `sdk.motion`：运动控制（关节/笛卡尔/预设动作/夹爪）
  - `sdk.vision`：视觉抓取（点/框）
  - `sdk.follow`：视觉跟随
  - `sdk.joycon`：Joy-Con 遥操作
  - `sdk.digital_twin`：MuJoCo 仿真
  - `sdk.io`：IO 控制
  - `sdk.embodied`：自然语言具身智能

建议先看：
- [API 速查](api_reference.md)
- [快速入门](quickstart.md)

对应源码：
- `Embodied_SDK/horizon_sdk.py`
- `Embodied_SDK/motion.py`
- `Embodied_SDK/visual_grasp.py`
- `Embodied_SDK/joycon.py`

---

## 2. 底层 Control SDK（电机控制）

权威文档：
- `Horizon_Core/Control_SDK/README.md`

权威源码：
- `Horizon_Core/Control_SDK/Control_Core/motor_controller_ucp_simple.py`

你会重点用到：
- `ZDTMotorController(...)` 及其 `control_actions/read_parameters/modify_parameters/...`
- 多机同步（推荐）：`ZDTMotorController.y42_sync_enable / y42_sync_position / y42_sync_speed`

---

## 3. AI SDK

权威文档：
- `Horizon_Core/AI_SDK/README.md`

常用入口：
- `from Horizon_Core.AI_SDK import AISDK`

---

## 4. UI 相关（非二次开发必须）

如果你需要复用 UI 的交互逻辑与配置管理，可以参考：
- `Main_UI/` 目录（各个 widget 内通常包含参数约束、交互流程与安全提示）

