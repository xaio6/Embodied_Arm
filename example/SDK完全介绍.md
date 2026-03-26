# Embodied_SDK 完全介绍

## 📦 SDK 概述

**Embodied_SDK** 是 HorizonArm 机械臂的 Python 控制库，提供了从底层电机控制到高层AI功能的完整解决方案。

### 设计理念

```
高层应用
    ↑
具身智能层 (Embodied AI)
    ↑
功能模块层 (Motion, Vision, JoyCon, IO, DigitalTwin)
    ↑
电机控制层 (Motor Controller)
    ↑
通信协议层 (CAN/Serial)
```

---

## 🏗️ SDK 架构

### 核心模块总览

| 模块 | 文件 | 功能 | 适用场景 |
|------|------|------|---------|
| **电机控制** | `__init__.py` | 单电机底层控制 | 所有应用的基础 |
| **运动控制** | `motion.py` | 多关节运动学 | 机械臂轨迹规划 |
| **视觉抓取** | `visual_grasp.py` | 手眼标定+抓取 | 视觉引导操作 |
| **手柄控制** | `joycon.py` | Joy-Con遥操作 | 远程操控 |
| **IO控制** | `io.py` | 数字IO读写 | 传感器/执行器接口 |
| **数字孪生（可选）** | `digital_twin.py` | MuJoCo仿真 | 算法验证/离线开发 |
| **AI集成** | `ai.py` | AI功能封装 | 大模型/多模态AI |
| **具身智能** | `embodied.py` | 完整AI机器人 | 端到端应用 |
| **集成SDK** | `horizon_sdk.py` | 高层统一接口 | 快速开发 |

---

## 📚 模块详解

### 1️⃣ 电机控制模块 (`__init__.py`)

**核心功能：单电机底层控制**

```python
from Embodied_SDK import create_motor_controller

# 创建电机控制器
motor = create_motor_controller(
    motor_id=1,
    port="COM14",
    baudrate=115200  # UCP硬件保护模式（OmniCAN 串口）
)

# 连接电机
motor.connect()

# 控制动作
motor.control_actions.enable()                    # 使能
motor.control_actions.set_speed(speed=100)        # 速度模式
motor.control_actions.move_to_position(90, 500)   # 位置模式
motor.control_actions.stop()                      # 停止

# 读取参数
position = motor.read_parameters.get_position()   # 读位置
speed = motor.read_parameters.get_speed()         # 读速度
status = motor.read_parameters.get_motor_status() # 读状态
```

**API分类：**

| API类别 | 方法 | 说明 |
|---------|------|------|
| **连接管理** | `connect()`, `disconnect()` | 建立/断开连接 |
| **控制动作** | `control_actions.*` | 使能、运动、停止等 |
| **参数读取** | `read_parameters.*` | 位置、速度、状态等 |
| **参数设置** | `set_parameters.*` | PID、限位等配置 |
| **回零功能** | `homing_functions.*` | 各种回零模式 |

**详细示例：** `control_sdk_examples/motor_usage_example.py`

---

### 2️⃣ 运动控制模块 (`motion.py`)

**核心功能：多关节运动学和轨迹规划**

```python
from Embodied_SDK import HorizonArmSDK

# 创建机械臂SDK（自动管理6个电机）
sdk = HorizonArmSDK(motors={1: m1, 2: m2, ...})

# 关节空间运动
sdk.motion.move_joints([0, 45, 30, 0, 0, 0], duration=2.0)

# 笛卡尔空间运动
sdk.motion.move_cartesian([200, 100, 300], orientation=[0, 0, 180], duration=2.0)

# 预设动作
sdk.motion.execute_preset_action("初始位置")
sdk.motion.execute_preset_action("挥手")

# 夹爪控制
sdk.motion.control_claw(1)  # 张开
sdk.motion.control_claw(0)  # 闭合
```

**功能特性：**
- ✅ 关节空间运动（Joint Space）
- ✅ 笛卡尔空间运动（Cartesian Space）
- ✅ 逆运动学解算（IK）
- ✅ 轨迹插值（平滑运动）
- ✅ 预设动作管理
- ✅ 夹爪控制

**详细示例：** `sdk_quickstart.py`（完整版）

---

### 3️⃣ 视觉抓取模块 (`visual_grasp.py`)

**核心功能：手眼标定和视觉引导操作**

```python
from Embodied_SDK import HorizonArmSDK

sdk = HorizonArmSDK(motors=motors, camera_id=0)

# 像素点抓取（将屏幕像素转换为机械臂坐标）
sdk.vision.grasp_at_pixel(u=320, v=240)

# 框选抓取（抓取矩形框中心）
sdk.vision.grasp_at_bbox(x1=100, y1=100, x2=200, y2=200)

# 视觉跟随
sdk.follow.init_manual_target(frame, x1, y1, x2, y2)
sdk.follow.follow_step(frame)
```

**功能特性：**
- ✅ 手眼标定（Camera-Arm Calibration）
- ✅ 像素→机械臂坐标转换
- ✅ 深度估计（Depth Estimation）
- ✅ 目标跟踪（Object Tracking）
- ✅ 视觉伺服（Visual Servoing）

**前置条件：**
- 需要完成相机标定（生成 `config/calibration_parameter.json`）
- 摄像头已连接

**详细示例：** `control_sdk_examples/visual_grasp_example.py`

---

### 4️⃣ 手柄控制模块 (`joycon.py`)

**核心功能：Joy-Con手柄遥操作机械臂**

```python
from Embodied_SDK import JoyconSDK

sdk = JoyconSDK()

# 连接手柄
left_ok, right_ok = sdk.connect_joycon()

# 读取状态
left_status = sdk.get_left_joycon_status()
right_status = sdk.get_right_joycon_status()

# 绑定机械臂
sdk.bind_arm(motors)

# 启动控制循环
sdk.start_control()  # 手柄输入自动映射到机械臂运动

# 启用姿态模式（新功能）
sdk.set_attitude_mode("joint")   # 推荐：关节模式（原 Mode2）
sdk.enable_attitude()            # 启用姿态模式（默认 joint）

# 双臂姿态模式（新功能）
sdk.set_arm2(motors_arm2, motor_config_manager, kinematics)  # 绑定机械臂2
sdk.set_dual_attitude_enabled(True)  # 启用双臂姿态模式
```

**控制模式：**

1. **关节模式**：直接控制各关节角度
2. **笛卡尔模式**：控制末端在空间中的位置和姿态
3. **姿态模式**（新功能）：使用IMU控制末端姿态
   - **TCP模式（原 Mode1）**：IMU 控制末端姿态；右摇杆控制世界坐标系平移
   - **关节模式（原 Mode2，推荐）**：IMU 轴对轴映射到关节；右摇杆控制第一人称平移
4. **双臂姿态模式**（新功能）：同时控制两个机械臂

**基础模式控制映射：**

| 手柄 | 输入 | 笛卡尔模式 | 关节模式 |
|------|------|-----------|---------|
| **左手柄** | 摇杆H | X轴移动 | J1旋转 |
| **左手柄** | 摇杆V | Y轴移动 | J2旋转 |
| **左手柄** | L/ZL | Z轴升降 | J3旋转 |
| **右手柄** | 摇杆H | Roll旋转 | J4旋转 |
| **右手柄** | 摇杆V | Pitch旋转 | J5旋转 |
| **右手柄** | R/ZR | Yaw旋转 | J6旋转 |
| **右手柄** | A | 夹爪闭合 | 夹爪闭合 |
| **右手柄** | B | 夹爪张开 | 夹爪张开 |
| **右手柄** | X | 切换模式 | 切换模式 |
| **右手柄** | HOME | 紧急停止 | 紧急停止 |

**姿态模式控制映射：**

| 手柄 | 输入 | 功能 |
|------|------|------|
| **右手柄** | IMU（陀螺仪） | 控制末端姿态（Roll/Pitch/Yaw） |
| **右手柄** | 摇杆 | 控制X/Y平移（世界坐标系） |
| **右手柄** | R/ZR | 控制Z轴升降（世界坐标系） |
| **右手柄** | X | 暂停/恢复IMU（摇杆平移仍可用） |
| **右手柄** | HOME | 短按=姿态对齐，长按=回安全位+对齐 |
| **右手柄** | A/B | 闭合/打开夹爪 |

**双臂姿态模式：**
- 右手柄控制机械臂1（Arm1）
- 左手柄控制机械臂2（Arm2）
- 左手柄方向键提供额外控制功能

**详细示例：** `control_sdk_examples/joycon_control_example.py`

---

### 5️⃣ IO控制模块 (`io.py`)

**核心功能：数字输入输出控制**

```python
from Embodied_SDK import IOSDK

io = IOSDK(port="COM15")
io.connect()

# 读取数字输入（DI）
di_states = io.read_di_states()  # 返回 {0: True, 1: False, ...}

# 控制数字输出（DO）
io.set_do(pin=0, state=True)   # 设置DO0为高电平
io.set_do(pin=1, state=False)  # 设置DO1为低电平

# 读取数字输出状态
do_states = io.read_do_states()
```

**应用场景：**
- 🔌 传感器信号读取（光电开关、接近开关、限位开关）
- 🔌 执行器控制（继电器、电磁阀、指示灯）
- 🔌 安全光栅联动
- 🔌 气动夹爪控制

**详细示例：** `control_sdk_examples/io_control_example.py`

---

### 6️⃣ 数字孪生模块 (`digital_twin.py`)

**核心功能：MuJoCo 物理仿真（可选）**

```python
from Embodied_SDK import DigitalTwinSDK

sdk = DigitalTwinSDK()

# 启动仿真窗口
sdk.start_simulation()

# 直接设置关节角度（瞬间）
sdk.set_joint_angles([0, 45, 30, 0, 0, 0])

# 平滑移动（带插值）
sdk.move_joints([90, 0, 0, 0, 0, 0], duration=2.0)

# 执行预设动作
sdk.execute_preset_action("初始位置")

# 停止仿真
sdk.stop_simulation()
```

**应用场景：**
- 🦾 算法验证（无需真实硬件）
- 🦾 轨迹预览（可视化运动路径）
- 🦾 离线开发（在家也能开发）
- 🦾 教学演示（安全展示）

**详细示例：**
- `control_sdk_examples/digital_twin_example.py`（教学版最短示例）
- `mujoco_control.py`（交互式完整演示）

---

### 7️⃣ AI集成模块 (`ai.py`)

**核心功能：AI功能封装（LLM、ASR、TTS、多模态）**

```python
from Embodied_SDK import AISDK

ai = AISDK()

# 大语言模型（LLM）
response = ai.llm.chat("请帮我规划一个抓取任务")

# 语音识别（ASR）
text = ai.asr.recognize(audio_data)

# 语音合成（TTS）
audio = ai.tts.synthesize("任务完成")

# 多模态理解
result = ai.multimodal.analyze(image, prompt="这是什么物体？")
```

**支持的AI能力：**
- 🧠 大语言模型（LLM）
- 🎤 语音识别（ASR）
- 🔊 语音合成（TTS）
- 👁️ 视觉理解（Vision）
- 🌐 多模态交互（Multimodal）

**详细示例：** `ai_sdk_examples/` 目录下的所有示例

---

### 8️⃣ 具身智能模块 (`embodied.py`)

**核心功能：端到端AI机器人系统**

```python
from Embodied_SDK import EmbodiedSDK

embodied = EmbodiedSDK()
result = embodied.run_nl_instruction("帮我把桌上的红色方块拿起来")
print(result)
```

**整合能力：**
- 🤖 自然语言理解 → 动作规划 → 执行
- 🤖 视觉感知 → AI决策 → 机械臂控制
- 🤖 语音交互 → 任务执行 → 反馈

---

### 9️⃣ 高层集成SDK (`horizon_sdk.py`)

**核心功能：统一接口，简化开发**

```python
from Embodied_SDK import HorizonArmSDK
from Embodied_SDK import create_motor_controller

# 一次性初始化所有功能（电机需要先由你连接并组成 motors 字典）
motors = {mid: create_motor_controller(motor_id=mid, port="COM14", baudrate=115200) for mid in range(1, 7)}
for m in motors.values():
    m.connect()

sdk = HorizonArmSDK(motors=motors, camera_id=0)

# 使用统一接口
sdk.vision.grasp_at_pixel(320, 240)  # 视觉抓取
sdk.motion.move_cartesian([100, 200, 300], orientation=[0, 0, 180])  # 运动控制
```

---

## 🔑 核心概念

### 1. 电机控制器 (Motor Controller)

每个电机对应一个控制器实例：
```python
motor = create_motor_controller(motor_id=1, port="COM14")
```

**关键参数：**
- `motor_id`: 电机ID（1-255），通过拨码开关或上位机设置
- `port`: 串口号（Windows: COMx, Linux: /dev/ttyUSBx）
- `baudrate`: 默认 115200（UCP硬件保护模式；一般不需要修改）
- `interface_type` / `shared_interface`: 旧SLCAN方案遗留参数，当前版本会自动忽略（不建议再使用）

### 2. 多电机连接（UCP 连接池共享）

UCP 模式下，多电机会自动共享同一串口连接（连接池机制），通常不需要额外的 `shared_interface` 配置：

```python
motors = {mid: create_motor_controller(motor_id=mid, port="COM14", baudrate=115200) for mid in range(1, 7)}
for m in motors.values():
    m.connect()
```

### 3. 多电机同步控制（推荐：Y42 聚合）

推荐使用 `ZDTMotorController.y42_sync_*` 进行同步控制（一次通信下发多电机命令，硬件级同步启动）：

```python
from Horizon_Core.Control_SDK.Control_Core import ZDTMotorController

controllers = {1: motor1, 2: motor2}
targets = {1: 90.0, 2: 45.0}  # 单位：度（电机角度）

ZDTMotorController.y42_sync_enable(controllers, enabled=True)
ZDTMotorController.y42_sync_position(controllers, targets=targets, speed=500)
```

### 4. 坐标系统

**关节空间（Joint Space）：**
- 直接控制每个关节的角度
- 参数：[J1, J2, J3, J4, J5, J6]（单位：度）
- 优点：直观、精确
- 缺点：需要手动计算姿态

**笛卡尔空间（Cartesian Space）：**
- 控制末端执行器的位置和姿态
- 参数：[X, Y, Z, Roll, Pitch, Yaw]（位置单位：mm，姿态单位：度）
- 优点：符合直觉（前后左右上下）
- 缺点：依赖逆运动学解算

### 5. 手眼标定 (Hand-Eye Calibration)

**原理：**
```
像素坐标 (u, v) → 相机坐标 → 机械臂基座标 → 关节角度
```

**标定过程：**
1. 采集标定数据（棋盘格）
2. 计算相机内参（camera_matrix, dist_coeffs）
3. 计算手眼关系（旋转向量rvec, 平移向量tvec）
4. 保存标定文件（`config/calibration_parameter.json`）

**使用：**
```python
sdk.vision.grasp_at_pixel(u=320, v=240)  # SDK自动加载标定文件
```

---

## 🎯 典型应用流程

### 场景1：简单的机械臂运动

```python
from Embodied_SDK import create_motor_controller
from Horizon_Core.Control_SDK.Control_Core import ZDTMotorController
import time

# 1. 创建控制器（默认：OmniCAN / UCP 115200）
motors = {}
for mid in [1, 2, 3, 4, 5, 6]:
    m = create_motor_controller(motor_id=mid, port="COM14", baudrate=115200)
    m.connect()
    motors[mid] = m

# 2. Y42 同步使能（推荐）
ZDTMotorController.y42_sync_enable(motors, enabled=True)
time.sleep(0.2)

# 3. Y42 聚合同步位置控制（推荐）
targets = {1: 0, 2: 45, 3: 30, 4: 0, 5: 0, 6: 0}
ZDTMotorController.y42_sync_position(motors, targets=targets, speed=500)

# 4. 等待到位
time.sleep(3)

# 5. 清理
for m in motors.values():
    m.disconnect()
```

### 场景2：视觉引导抓取

```python
from Embodied_SDK import HorizonArmSDK

# 1. 初始化SDK（自动连接电机和相机）
sdk = HorizonArmSDK(motors=motors, camera_id=0)

# 2. 移动到观察位置
sdk.motion.execute_preset_action("观察位置")

# 3. 获取图像
import cv2
cap = cv2.VideoCapture(0)
ret, frame = cap.read()

# 4. 用户点击目标（或AI识别）
# 假设用户点击了像素点(320, 240)
u, v = 320, 240

# 5. 执行视觉抓取
sdk.vision.grasp_at_pixel(u, v)

# 6. 移动到放置位置
sdk.motion.move_cartesian([200, 0, 200], orientation=[0, 0, 180])

# 7. 松开夹爪
sdk.motion.control_claw(1)  # 张开
```

### 场景3：AI交互式机器人

```python
from Embodied_SDK import HorizonArmSDK
from Embodied_SDK import AISDK

# 1. 初始化
arm = HorizonArmSDK(motors=motors, camera_id=0)
ai = AISDK()

# 2. 语音识别用户指令
audio = record_audio()  # 录音函数（需自己实现）
command = ai.asr.recognize(audio)
print(f"用户说: {command}")

# 3. LLM理解指令并生成动作序列
prompt = f"用户指令：{command}\n请分解为机械臂动作序列"
response = ai.llm.chat(prompt)
actions = parse_actions(response)  # 解析动作（需自己实现）

# 4. 执行动作
for action in actions:
    if action['type'] == 'move':
        arm.move_to_position(**action['params'])
    elif action['type'] == 'grasp':
        arm.claw.close()
    elif action['type'] == 'release':
        arm.claw.open()

# 5. 语音反馈
feedback_audio = ai.tts.synthesize("任务完成")
play_audio(feedback_audio)  # 播放函数（需自己实现）
```

---

## 📦 安装和配置

### 1. 安装依赖

```bash
# 基础依赖
pip install numpy opencv-python pyserial

# MuJoCo仿真（可选）
pip install mujoco

# Joy-Con控制（可选）
pip install joycon-python hidapi

# AI功能（可选）
pip install openai anthropic requests
```

### 2. 配置文件

**机械臂配置：**
- `config/embodied_config/preset_actions.json` - 预设动作定义
- `config/dh_parameters_config.json` - SDK 默认 FK/IK/DH 参数、`joint_offsets`、`joint_limits`
- `config/motor_config.json` - 电机减速比与方向配置

**AI配置：**
- `config/aisdk_config.yaml` - AI SDK 统一配置入口

**视觉配置：** `config/`
- `calibration_parameter.json` - 手眼标定参数

---

## 🔧 高级特性

### 1. 运动轨迹插值

SDK自动在关键点之间插值：
```python
# 以下会生成平滑轨迹
sdk.motion.move_joints([0, 0, 0, 0, 0, 0], duration=2.0)
sdk.motion.move_joints([90, 45, 30, 0, 0, 0], duration=2.0)
```

### 2. 碰撞检测（仿真中）

```python
sdk = DigitalTwinSDK()
sdk.enable_collision_detection(True)
```

### 3. 力控模式

```python
motor.control_actions.set_torque(current=500, current_slope=1000)
```

### 4. 自定义预设动作

编辑 `config/embodied_config/preset_actions.json`：
```json
{
  "我的动作": {
    "joints": [0, 45, 30, 0, 0, 0],
    "duration": 2.0,
    "description": "自定义动作描述"
  }
}
```

---

## 📖 学习资源

### 示例代码索引

| 学习目标 | 示例文件 | 难度 | 时间 |
|---------|---------|------|------|
| **快速入门** | `quickstart_guide.py` | ⭐ | 5分钟 |
| **单电机控制** | `control_sdk_examples/motor_usage_example.py` | ⭐⭐ | 30分钟 |
| **机械臂运动** | `sdk_quickstart.py` | ⭐⭐ | 30分钟 |
| **视觉抓取** | `control_sdk_examples/visual_grasp_example.py` | ⭐⭐⭐ | 45分钟 |
| **多机同步** | `control_sdk_examples/multi_motor_sync_example.py` | ⭐⭐⭐ | 20分钟 |
| **手柄控制** | `control_sdk_examples/joycon_control_example.py` | ⭐⭐⭐ | 40分钟 |
| **IO控制** | `control_sdk_examples/io_control_example.py` | ⭐⭐ | 20分钟 |
| **MuJoCo仿真** | `control_sdk_examples/digital_twin_example.py` | ⭐⭐ | 15分钟 |
| **AI功能** | `ai_sdk_examples/LLM_usage.py` | ⭐⭐⭐ | 30分钟 |

### 文档

- **总导航**: `example/README.md`
- **学习路径**: `example/control_sdk_examples/README.md`
- **API参考**: `docs/api_reference.md`
- **故障排除**: `docs/troubleshooting.md`

---

## ⚠️ 常见问题

### Q1: 电机连接失败？
**A:** 检查：
1. 串口号是否正确（设备管理器查看）
2. 电机ID是否正确
3. 电机是否上电
4. 没有其他程序占用串口

### Q2: 多电机控制失败？
**A:** 当前默认是 UCP 模式，多电机会自动共享同一串口连接（连接池）。建议按下面方式创建即可：
```python
motors = {mid: create_motor_controller(motor_id=mid, port="COM14", baudrate=115200) for mid in range(1, 7)}
for m in motors.values():
    m.connect()
```

### Q3: 视觉抓取位置不准？
**A:** 
1. 检查是否完成手眼标定
2. 确认标定文件路径正确
3. 检查相机和机械臂相对位置是否改变

### Q4: 仿真窗口无法打开？
**A:** 
```bash
pip install mujoco
```

### Q5: Joy-Con无法连接？
**A:** 
1. 在系统蓝牙设置中删除手柄
2. 按住手柄侧面同步按钮重新配对
3. 确保没有其他程序占用（Steam, Yuzu等）

---

## 🚀 从示例到生产

### 代码复用建议

1. **复制核心代码片段** - 示例代码可直接复制
2. **添加错误处理** - 生产环境加强异常处理
3. **添加日志记录** - 使用 `setup_logging()`
4. **参数配置化** - 将硬编码参数移到配置文件
5. **多线程处理** - 视觉/AI/控制分离线程

### 性能优化

- 🚀 使用共享接口减少串口开销
- 🚀 批量读取参数（多机同步场景）
- 🚀 异步处理耗时操作（AI推理）
- 🚀 预加载配置文件（避免重复读取）

---

## 📞 技术支持

- **示例代码**: `example/` 目录
- **开发者工具**: `example/developer_tools/`
- **技术文档**: `docs/`
- **问题反馈**: 联系技术支持团队

---

**版本**: 1.4  
**更新日期**: 2024  
**维护**: HorizonArm Team

