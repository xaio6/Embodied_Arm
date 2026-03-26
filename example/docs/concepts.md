# 核心概念

本页用于统一 `Embodied_SDK` / `Control_SDK` / 示例脚本中的术语与单位，避免“同一个概念多个叫法”导致误用。

---

## 1. 分层结构（建议理解方式）

- **Control_SDK（底层）**：单电机/多电机控制、状态读取、参数修改  
  - 默认通信方式：**UCP 硬件保护模式（OmniCAN 串口 115200）**
  - 多机同步推荐：**Y42 聚合命令**
- **Embodied_SDK（上层）**：对“机械臂运动/视觉/手柄/IO/具身智能”等能力的统一封装  
  - 推荐入口：`HorizonArmSDK`
- **Main_UI（上位机）**：图形界面，不是二次开发必须依赖

---

## 2. `motors` 字典

大多数上层接口使用同一种“机械臂上下文”表示方式：

- **结构**：`{motor_id: controller_instance}`
- **motor_id**：电机地址（通常 1-6 对应 6 轴；夹爪若使用独立电机可能是 7）

示例：

```python
from Embodied_SDK import create_motor_controller

motors = {mid: create_motor_controller(motor_id=mid, port="COM14", baudrate=115200) for mid in range(1, 7)}
for m in motors.values():
    m.connect()
```

---

## 3. 电机角度 vs 关节输出角度

系统里会同时出现两种“角度”：

- **电机角度（motor angle）**：驱动器/电机端的角度，通常由 `motor.read_parameters.get_position()` 读到
- **关节输出角（joint angle）**：减速器输出端（关节）的角度，才是运动学计算更关心的值

二者的关系由 `config/motor_config.json` 决定：

- `motor_reducer_ratios`：减速比
- `motor_directions`：方向（1/-1）

很多上层逻辑会自动按该配置进行换算（例如 `MotionSDK`、`JoyconSDK`）。

---

## 4. 单位约定

- **关节角度**：度（deg）
- **末端位置**：毫米（mm），顺序 `[x, y, z]`
- **末端姿态**：度（deg），顺序 `[yaw, pitch, roll]`（在部分显示/打印中可能以 RPY 展示，请以函数参数说明为准）
- **电机速度**：RPM

---

## 5. 多电机同步

推荐同步方案是 **Y42 聚合多机命令**：

- 好处：一次通信下发多电机命令，硬件级同步启动，效率和稳定性更高
- 示例：`example/control_sdk_examples/multi_motor_sync_example.py`

旧方案“三阶段同步（multi_sync + sync_motion）”为兼容保留，不建议新项目依赖。

---

## 6. 安全与急停

- **停止（stop）**：停止运动，但保持使能（一般更安全）
- **失能（disable）**：断驱动电流，可能导致无刹车机械臂下坠（谨慎）
- **急停**：请优先使用物理急停/断电；软件急停仅作为辅助手段

推荐先阅读：[安全须知](safety.md)

