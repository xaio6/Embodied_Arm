# JoyconSDK - 手柄控制

**对应源码：** `Embodied_SDK/joycon.py`

## 概述

`JoyconSDK` 提供 Nintendo Joy-Con 手柄控制机械臂的能力，支持多种控制模式：
- **关节模式**：直接控制各关节角度
- **笛卡尔模式**：控制末端在空间中的位置和姿态
- **姿态模式**：使用IMU控制末端姿态（新功能）
  - **关节模式**（推荐，原 Mode2）
  - **TCP模式**（兼容，原 Mode1）
- **双臂姿态模式**：同时控制两个机械臂（新功能）

## 模块入口

```python
from Embodied_SDK import JoyconSDK

joycon = JoyconSDK()
```

---

## 使用流程

### 1. 连接手柄

#### `connect_joycon() -> (bool, bool)`

连接 Joy-Con 手柄。

**返回值：**
- `(left_ok, right_ok)`: 左右手柄连接状态

**示例：**
```python
left_ok, right_ok = joycon.connect_joycon()

if left_ok and right_ok:
    print("✅ 手柄连接成功")
else:
    print("❌ 手柄连接失败")
```

---

### 2. 绑定机械臂

#### `bind_arm(motors, use_motor_config=True, kinematics=None, mujoco_controller=None)`

绑定机械臂电机。

**参数：**
- `motors`: 电机字典 `{motor_id: controller}`
- `use_motor_config`: 是否从配置文件加载参数
- `kinematics`: 运动学对象（可选；不传时默认按 `config/dh_parameters_config.json` 创建）
- `mujoco_controller`: MuJoCo 控制器（可选，用于仿真）

**示例：**
```python
from Horizon_Core import gateway as horizon_gateway

motors = {mid: horizon_gateway.create_motor_controller(motor_id=mid, port="COM14") for mid in range(1, 7)}
for m in motors.values():
    m.connect()

joycon.bind_arm(motors, use_motor_config=True)
```

---

### 3. 启动控制

#### `start_control()`

启动手柄控制循环。

**示例：**
```python
joycon.start_control()
print("手柄控制已启动，按 Joy-Con 按钮控制机械臂")
print("按 Ctrl+C 退出")

try:
    while True:
        time.sleep(0.1)
except KeyboardInterrupt:
    joycon.stop_control()
```

---

## 控制方法

### 停止/暂停/恢复

```python
# 停止控制
joycon.stop_control()

# 暂停控制
joycon.pause_control()

# 恢复控制
joycon.resume_control()
```

### 模式切换

#### `toggle_mode()`

在关节模式和笛卡尔模式之间切换。

```python
joycon.toggle_mode()
```

**说明：**
- **关节模式**：直接控制各关节角度
- **笛卡尔模式**：控制末端在空间中的位置和姿态

#### `enable_attitude(mode="joint") -> bool`

启用姿态模式（使用右手柄IMU控制末端姿态）。

```python
success = joycon.enable_attitude()  # 默认 joint
if success:
    print("姿态模式已启用")
```

**说明：**
- 姿态模式有两种“子模式”：TCP模式 / 关节模式（推荐）
- 两种子模式都支持：X 暂停/恢复 IMU（平移仍可用），HOME 短按对齐/长按回安全位+对齐

#### `disable_attitude_mode()`

禁用姿态模式，回到基础控制模式。

```python
joycon.disable_attitude_mode()
```

#### `set_attitude_mode(mode)`

选择姿态模式子模式（建议在启用姿态模式前设置）。

```python
# 关节模式（推荐，原 Mode2）
joycon.set_attitude_mode("joint")

# TCP模式（兼容，原 Mode1）
joycon.set_attitude_mode("tcp")
```

**说明：**
- **TCP模式（原 Mode1）**：
  - IMU：控制末端姿态（Yaw/Pitch/Roll）
  - 右摇杆：X/Y 平移（世界坐标系）
  - R/ZR：Z 轴升降（世界坐标系）
- **关节模式（原 Mode2，推荐）**：
  - IMU：轴对轴映射到关节（Yaw→J1，Pitch→J5，Roll→J6）
  - 右摇杆：第一人称平移（沿末端前向/右向，需 IK）
  - R/ZR：Z 轴升降（世界坐标系）

**方向/映射符号调整（常用排查项）：**
- TCP模式左右手柄镜像翻转：`attitude_left_flip_roll` / `attitude_left_flip_pitch` / `attitude_left_flip_yaw`
- 关节模式映射符号（右/左手柄）：`attitude_mode2_yaw_sign_right/left`、`attitude_mode2_pitch_sign_right/left`、`attitude_mode2_roll_sign_right/left`
- 若双臂需要单独微调 arm2：`attitude_mode2_arm2_yaw_sign_mult/pitch_sign_mult/roll_sign_mult`

> 兼容说明：旧接口 `set_attitude_mode2_enabled(True/False)` 仍保留，但推荐使用 `set_attitude_mode(...)`。

#### `set_dual_attitude_enabled(enabled: bool)`

设置双臂姿态模式开关（仅在姿态模式下生效）。

```python
# 启用双臂姿态模式
joycon.set_dual_attitude_enabled(True)

# 禁用双臂姿态模式
joycon.set_dual_attitude_enabled(False)
```

**说明：**
- 双臂姿态模式需要同时连接左右Joy-Con
- 右手柄控制机械臂1（Arm1）
- 左手柄控制机械臂2（Arm2）
- 需要先通过 `set_arm2()` 绑定机械臂2

#### `set_arm2(motors, motor_config_manager=None, kinematics=None, mujoco_controller=None, arm_index=2)`

绑定机械臂2（用于双臂姿态模式）。

```python
# 连接机械臂2的电机
from Horizon_Core import gateway as horizon_gateway

motors_arm2 = {mid: horizon_gateway.create_motor_controller(motor_id=mid, port="COM15") for mid in range(1, 7)}
for m in motors_arm2.values():
    m.connect()

# 绑定机械臂2
joycon.set_arm2(motors_arm2, motor_config_manager, kinematics)
```

#### `move_to_joycon_start_pose(force=False) -> bool`

移动到手柄控制的起始位姿（安全位姿）。

```python
success = joycon.move_to_joycon_start_pose()
if success:
    print("已移动到起始位姿")
```

---

### 紧急停止

#### `emergency_stop()`

触发紧急停止。

```python
joycon.emergency_stop()
```

---

## 状态查询

### 获取控制状态

#### `get_status() -> dict`

获取当前控制状态。

```python
status = joycon.get_status()
print(f"模式: {status['mode']}")
print(f"速度倍率: {status['speed_multiplier']}")
print(f"是否运行: {status['running']}")
```

---

### 获取手柄状态

#### `get_left_joycon_status()` / `get_right_joycon_status()`

获取手柄原始状态（用于监控）。

```python
left_status = joycon.get_left_joycon_status()
right_status = joycon.get_right_joycon_status()

if left_status:
    print(f"左摇杆: {left_status.get('stick_l')}")
if right_status:
    print(f"右摇杆: {right_status.get('stick_r')}")
```

---

## 完整示例

请参考 `example/test_joycon_arm_control.py`，该文件展示了如何构建一个全功能的交互式控制台：

1.  **交互式配置**：启动时询问串口号和电机 ID。
2.  **安全检查**：显示详细的控制键位说明。
3.  **主控制循环**：
    *   实时读取手柄状态
    *   根据模式计算目标位姿
    *   调用 SDK 执行运动
    *   刷新屏幕显示状态

```python
# 代码片段：主控制逻辑示意
def main():
    # ... (连接电机与手柄) ...
    
    joycon.bind_arm(motors, use_motor_config=True)
    joycon.start_control()
    
    try:
        while True:
            # 刷新状态显示
            status = joycon.get_status()
            print_status(status, motors)
            time.sleep(0.1)
    except KeyboardInterrupt:
        joycon.stop_control()
```

---

## 按键映射

### 基础模式（关节/笛卡尔）

#### 左 Joy-Con
- **摇杆**：XY平面移动（笛卡尔）/ J1-J2转动（关节）
- **L/ZL**：Z轴升降（笛卡尔）/ J3转动（关节）
- **减号(-)**：降低速度

#### 右 Joy-Con
- **摇杆**：俯仰/翻滚（笛卡尔）/ J4-J5转动（关节）
- **R/ZR**：偏航旋转（笛卡尔）/ J6转动（关节）
- **X 键**：切换关节/笛卡尔模式
- **A 键**：闭合夹爪
- **B 键**：打开夹爪
- **加号(+)**：提高速度
- **HOME**：紧急停止

### 姿态模式（ATTITUDE）

#### 右 Joy-Con（单臂模式）
- **IMU（陀螺仪）**：控制末端姿态（Roll/Pitch/Yaw）
- **摇杆**：控制X/Y平移（世界坐标系）
- **R/ZR**：控制Z轴升降（世界坐标系）
- **X 键**：暂停/恢复IMU（摇杆平移仍可用）
- **HOME**：短按=姿态对齐，长按=回安全位+对齐
- **A 键**：闭合夹爪
- **B 键**：打开夹爪

#### 左 Joy-Con（双臂模式）
- **IMU（陀螺仪）**：控制机械臂2末端姿态
- **摇杆**：控制机械臂2的X/Y平移
- **L/ZL**：控制机械臂2的Z轴升降
- **方向键左(←)**：暂停/恢复IMU
- **方向键上(↑)**：回零
- **方向键右(→)**：闭合夹爪
- **方向键下(↓)**：打开夹爪

---

## 注意事项

1. **手柄连接**：
   - 确保 Joy-Con 已通过蓝牙配对
   - Windows 系统需要安装对应驱动

2. **控制模式**：
   - 关节模式更直观，适合新手
   - 笛卡尔模式更灵活，需要熟练使用
   - 姿态模式使用IMU控制，提供更直观的操作体验

3. **速度调节**：
   - 可通过手柄按键调节速度倍率
   - 首次使用建议使用低速模式

4. **姿态模式**：
   - 首次使用建议先进行姿态对齐（按HOME键）
   - 可以随时按X键暂停IMU控制
   - 关节模式（原 Mode2）提供更直观的“IMU→关节”手感与第一人称平移

5. **双臂姿态模式**：
   - 需要同时连接左右Joy-Con
   - 需要先通过 `set_arm2()` 绑定机械臂2
   - 右手柄控制Arm1，左手柄控制Arm2

---

## 相关文档

- [MotionSDK](motion.md) - 运动控制接口
- [安全须知](safety.md) - 安全操作指南
- [API 详细参考](api_detailed.md) - 完整 API 说明

## 示例脚本

- **`example/control_sdk_examples/joycon_control_example.py`**  
  **用途：** 基础连接测试工具。  
  **功能：** 仅用于测试手柄与电脑的蓝牙连接及按键响应，不涉及机械臂控制。用于排查手柄连接问题。

- **`example/test_joycon_arm_control.py`**  
  **用途：** 全功能手柄控制台。  
  **功能：** 包含完整的机械臂控制功能，支持模式切换（关节/笛卡尔）、速度调节、夹爪控制，并提供实时状态显示和交互式连接向导。

- **`example/test_joycon_display.py`**  
  **用途：** 手柄状态可视化监控。

- **`example/control_sdk_examples/joycon_control_example.py`**  
  **用途：** 完整的手柄控制教学示例。  
  **功能：** 提供分级学习路径，包括连接测试、数据监控、基础控制、姿态模式演示和参数配置。支持姿态模式 TCP模式 / 关节模式 的演示。
