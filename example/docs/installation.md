# 安装与环境

本项目面向 **Python 脚本/二次开发** 的推荐入口是 `Embodied_SDK`；底层电机控制使用 `Horizon_Core/Control_SDK` 的 **UCP 硬件保护模式**（OmniCAN 串口 115200）。

---

## 1. 系统要求

- **Python**：3.12+（推荐与 `requirements.txt` 保持一致）
- **操作系统**：Windows 10/11（也可在 Ubuntu 20.04+ 以纯脚本方式运行）
- **硬件（真实机械臂）**：
  - ZDT 闭环驱动板 + CAN 总线
  - OmniCAN（UCP 模式，电脑侧表现为普通串口）

---

## 2. 安装依赖（推荐）

在项目根目录执行：

```bash
pip install -r requirements.txt
```

### 2.1 常见依赖说明

- **电机控制**：`pyserial`
- **视觉/跟踪（可选）**：`opencv-contrib-python`
- **GUI（可选）**：`PyQt5`
- **AI（可选）**：`dashscope`、`openai`、`PyYAML`、`python-dotenv` 等

### 2.2 Windows 安装 pyaudio（可选）

部分环境下 `pyaudio` 需要额外步骤（仅在使用麦克风 ASR/TTS 播放等功能时需要）：

```bash
pip install pipwin && pipwin install pyaudio
```

---

## 3. 可选组件

### 3.1 MuJoCo 数字孪生（可选）

如果要运行 `DigitalTwinSDK` 或 `example/mujoco_control.py`：

```bash
pip install mujoco
```

### 3.2 Joy-Con 手柄（可选）

如果要运行 `JoyconSDK` 或 `example/control_sdk_examples/joycon_control_example.py`：

- 依赖：`joycon-python`、`hidapi`（已在 `requirements.txt` 中列出）
- 手柄需要在系统蓝牙中完成配对

---

## 4. 验证安装

建议按以下顺序验证（从“最小依赖”到“完整系统”）：

1. **单电机入门**：`example/quickstart_guide.py`
2. **完整交互示例**：`example/sdk_quickstart.py`
3. **多机同步（Y42）**：`example/control_sdk_examples/multi_motor_sync_example.py`
4. **视觉/仿真/手柄/AI**：按需运行对应示例

