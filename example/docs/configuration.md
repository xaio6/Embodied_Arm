# 配置说明

本项目的配置默认位于项目根目录 `config/`。大多数脚本在“源码运行”模式下会自动优先读取该目录，无需额外设置。

---

## 1. 配置目录选择规则

许多模块（如 `Embodied_SDK/motion.py`、`Embodied_SDK/joycon.py`）会根据运行方式选择配置目录：

- **源码运行（未打包）**：默认使用项目内 `./config/`
- **打包运行（`sys.frozen=True`）**：优先使用环境变量
  - `HORIZONARM_CONFIG_DIR`：外置配置目录（推荐）
  - `HORIZON_DATA_DIR`：若设置，会尝试使用 `${HORIZON_DATA_DIR}/config`

如果你在自己的项目中复用 SDK，推荐显式设置：

```python
import os
os.environ["HORIZONARM_CONFIG_DIR"] = r"D:\HorizonArm\config"
```

---

## 2. 核心配置文件一览（`config/`）

### 2.1 `motor_config.json`（必读）

用于把“电机侧角度”换算到“关节输出端角度”，并统一方向约定。主要字段：

- `motor_reducer_ratios`: `{ "1": 50.0, ... }`  
  - **减速比**（电机角度 / 关节角度）
- `motor_directions`: `{ "1": -1, ... }`  
  - **方向**（1 或 -1），用于统一正方向
- `motor_directions_arm2`（可选）：
  - 双臂/副臂方向修正（仅在相关逻辑使用时生效）

影响模块：
- `MotionSDK` / `JoyconSDK`：运动学、单轴增量控制、姿态模式映射等
- 示例：`example/sdk_quickstart.py`

---

### 2.2 `calibration_parameter.json`（视觉相关）

相机标定与手眼标定参数。影响模块：
- `VisualGraspSDK` / `FollowGraspSDK`
- 示例：`example/control_sdk_examples/visual_grasp_example.py`

---

### 2.3 `hand_eye_calibration_poses.yaml`（标定采集位姿）

用于标定采集流程中的预设位姿/动作序列（具体由标定相关模块读取）。

---

### 2.4 `embodied_config/preset_actions.json`（预设动作）

预设动作字典（key 为动作名称），用于：
- `MotionSDK.execute_preset_action(name, speed=...)`
- `DigitalTwinSDK.execute_preset_action(name, speed=...)`
- 示例：`example/sdk_quickstart.py`

---

### 2.5 `aisdk_config.yaml`（AI 相关）

AI 提供商与模型的配置入口（建议使用环境变量注入密钥，避免提交到仓库）：

- Windows PowerShell：`setx ALI_API_KEY "your_key"`
- Linux/macOS：`export ALI_API_KEY=your_key`

影响模块：
- `Horizon_Core/AI_SDK`
- 示例：`example/ai_sdk_examples/config_example.py`

---

### 2.6 其他配置（按需）

- `all_parameter_config.json`：UI/系统级参数集合（上位机相关）
- `dh_parameters_config.json`：SDK 默认 FK/IK/DH 参数、`joint_offsets`、`joint_limits` 的统一配置
- `io_control/`：IO 作业/映射配置（`IOSDK` / UI IO 控件）
- `teaching_program/`：示教程序相关配置与样例

---

## 3. 常见问题

### Q1：我修改了 `config/`，为什么脚本没生效？

优先排查：
- 是否在脚本里设置了 `HORIZONARM_CONFIG_DIR` 指向了另一个目录
- 是否是打包运行（`sys.frozen=True`）导致读取外置配置

### Q2：方向反了/角度不对怎么办？

优先检查 `config/motor_config.json`：
- 方向反：修改对应电机的 `motor_directions` 为 `1` 或 `-1`
- 比例不对：修改对应电机的 `motor_reducer_ratios`

