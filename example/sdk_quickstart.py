#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HorizonArm SDK 快速入门示例
======================================

本示例展示了如何使用 Embodied_SDK 进行基础的机械臂控制。
代码结构设计旨在清晰展示 SDK 的核心调用流程，适合人类开发者阅读。

核心概念：
1. **HorizonArmSDK**: 顶层入口，聚合了 Motion, Vision, IO 等所有功能。
2. **Motor Controller**: 底层电机驱动，通过 `create_motor_controller` 创建。
3. **Motion Params**: 运动参数（速度、加速度），这对安全至关重要。
4. **Joint vs Cartesian**: 两种核心运动模式的区别。

使用方法：
    python sdk_quickstart.py
    
    (程序启动后会引导用户输入串口号和电机ID)
"""

import os
import sys
import time
import json
from typing import List, Optional

# 确保能找到项目根目录 (用于开发环境，安装包用户不需要)
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 关键：统一配置目录（让 MotionSDK / VisualGraspSDK / JoyconSDK / 底层 .pyd 都优先使用本工程 config/）
default_cfg_dir = os.path.join(project_root, "config")
os.environ.setdefault("HORIZONARM_CONFIG_DIR", default_cfg_dir)

from Embodied_SDK import HorizonArmSDK, create_motor_controller

def _load_motor_cfg():
    """
    读取 config/motor_config.json（与 MotionSDK 的读取字段一致）
    - motor_reducer_ratios: { "1": 62.0, ... }
    - motor_directions: { "1": 1/-1, ... }
    """
    # 仅保留 Mark 单一机械臂配置文件
    cfg_path = os.path.join(project_root, "config", "motor_config.json")
    cfg = {"motor_reducer_ratios": {}, "motor_directions": {}}
    try:
        if os.path.exists(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                cfg["motor_reducer_ratios"] = data.get("motor_reducer_ratios", {}) or {}
                cfg["motor_directions"] = data.get("motor_directions", {}) or {}
    except Exception:
        pass
    # 统一成 int key，便于使用
    rr = {int(k): float(v) for k, v in (cfg["motor_reducer_ratios"] or {}).items()}
    dd = {int(k): int(v) for k, v in (cfg["motor_directions"] or {}).items()}
    return rr, dd

def _warn_no_auto_disable(reason: str):
    """
    重要：根据用户要求，示例代码**不允许**自动失能/断开/停机控制。
    因此当出现未到位/超时/通信异常时，这里只做提示，不对电机执行 stop/disable/disconnect。
    """
    print(f"\n⚠️ 警告：{reason}")
    print("⚠️ 按你的要求，示例不会自动失能/断开电机。若你观察到异常运动，请立即人工急停/断电。")

def _motor_deg_to_joint_deg(motor_deg: float, motor_id: int, rr: dict, dd: dict) -> float:
    """
    把电机侧角度（读参返回值）换算为关节输出端角度（度）。
    底层 embodied_internal 的 _get_motor_position 也是这个逻辑：output = (motor / direction) / ratio
    """
    ratio = float(rr.get(int(motor_id), 16.0))
    direction = int(dd.get(int(motor_id), 1))
    if direction == 0 or ratio == 0:
        return float("nan")
    return (float(motor_deg) / float(direction)) / float(ratio)

def _read_current_joint_angles(sdk) -> Optional[List[float]]:
    """
    读取当前 6 轴关节输出端角度（度）。
    注意：电机 API 的 get_position() 通常返回电机端角度，需要用 motor_config 的减速比/方向换算。
    """
    rr, dd = _load_motor_cfg()
    motors = getattr(sdk, "motors", {}) or {}
    if not motors:
        return None
    angles = []
    for mid in range(1, 7):
        m = motors.get(mid)
        if m is None:
            angles.append(0.0)
            continue
        try:
            motor_deg = float(m.read_parameters.get_position())
            angles.append(_motor_deg_to_joint_deg(motor_deg, mid, rr, dd))
        except Exception:
            angles.append(0.0)
    return angles

def _move_single_joint_delta(sdk, joint_id: int, delta_deg: float, timeout_s: float = 10.0, tol_deg: float = 2.0) -> bool:
    """
    单轴“转多少度然后停下”（位置模式梯形控制，电机到位会自动停止）。
    - 不会对其他轴下发任何目标
    - 不做 stop/disable/disconnect（按你的要求）
    """
    motors = getattr(sdk, "motors", {}) or {}
    m = motors.get(int(joint_id))
    if m is None:
        print(f"❌ 未找到电机/关节 {joint_id}")
        return False

    rr, dd = _load_motor_cfg()
    ratio = float(rr.get(int(joint_id), 16.0))
    direction = int(dd.get(int(joint_id), 1))
    if direction == 0 or ratio == 0:
        print(f"❌ 配置异常：joint {joint_id} ratio/direction 无效（ratio={ratio}, direction={direction}）")
        return False

    # 读取当前电机端角度（度）
    try:
        cur_motor_deg = float(m.read_parameters.get_position())
    except Exception as e:
        print(f"❌ 读取电机{joint_id}当前位置失败: {e}")
        return False

    # 输出端增量 -> 电机端增量（带方向）
    delta_motor_deg = float(delta_deg) * ratio * direction
    target_motor_deg = cur_motor_deg + delta_motor_deg

    # 下发单轴梯形位置命令：
    # 为了兼容不同 Control_SDK 版本，这里**优先使用最小参数集**（只给目标位置），
    # 避免触发某些版本里 DefaultValues.MAX_SPEED 等常量缺失导致的异常。
    try:
        if hasattr(m, "move_to_position"):
            try:
                # 最小参数：目标位置 + 绝对模式（若支持）
                m.move_to_position(position=target_motor_deg, is_absolute=True, multi_sync=False)
            except TypeError:
                # 某些版本不支持关键字/这些参数
                try:
                    m.move_to_position(position=target_motor_deg)
                except TypeError:
                    m.move_to_position(target_motor_deg)
        elif hasattr(m, "control_actions") and hasattr(m.control_actions, "move_to_position"):
            # 某些版本接口不同：只传位置
            try:
                m.control_actions.move_to_position(position=target_motor_deg)
            except TypeError:
                m.control_actions.move_to_position(target_motor_deg)
        else:
            print(f"❌ 电机{joint_id}不支持位置控制接口 move_to_position")
            return False
    except Exception as e:
        print(f"❌ 电机{joint_id}下发位置命令失败: {e}")
        return False

    # 到位检测（不做任何停机动作，只是确认是否到位）
    t0 = time.time()
    tol_motor_deg = abs(float(tol_deg) * ratio) + 1e-6
    while time.time() - t0 < float(timeout_s):
        try:
            pos_motor = float(m.read_parameters.get_position())
            if abs(pos_motor - target_motor_deg) <= tol_motor_deg:
                print(f"✅ 关节{joint_id}到位并停止（Δ={delta_deg}°）")
                return True
        except Exception:
            pass
        time.sleep(0.1)

    _warn_no_auto_disable(f"关节{joint_id}到位检测超时（已下发Δ={delta_deg}°，但未能确认到位；可能是通信超时/参数不匹配）")
    return False

def _monitor_j3_or_abort(sdk, target_j3_deg: float, timeout_s: float, tol_j3_deg: float = 2.0):
    """
    监测 3 号电机位置是否收敛到目标（超时则 stop + disconnect）。
    说明：
    - 这里用 motor_config 的 reducer_ratio/direction，把“关节角”换算到“电机角”，避免直接比对不一致的角度体系。
    - tol_j3_deg 是关节角容差（默认 ±2°），会自动换算成电机侧容差。
    """
    m3 = getattr(sdk, "motors", {}).get(3)
    if m3 is None:
        return

    rr, dd = _load_motor_cfg()
    ratio = float(rr.get(3, 1.0))
    direction = int(dd.get(3, 1))

    try:
        target_motor_deg = float(target_j3_deg) * ratio * direction
        tol_motor_deg = abs(float(tol_j3_deg) * ratio) + 1e-6
    except Exception:
        return

    t0 = time.time()
    stable_hits = 0
    last_pos = None
    while time.time() - t0 < timeout_s:
        try:
            pos = float(m3.read_parameters.get_position())
        except Exception:
            time.sleep(0.1)
            continue

        err = pos - target_motor_deg
        if abs(err) <= tol_motor_deg:
            stable_hits += 1
            if stable_hits >= 5:
                return
        else:
            stable_hits = 0

        # 简单“跑飞”检测：位置持续远离目标且变化明显
        if last_pos is not None:
            if abs(err) > 3 * tol_motor_deg and abs(pos - last_pos) > 5.0:
                # 若误差很大且还在明显移动，继续等待一点点，但超时会停
                pass
        last_pos = pos
        time.sleep(0.1)

    _warn_no_auto_disable(f"J3 超时未到位（目标关节{target_j3_deg}°）")

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    print("=" * 70)
    print(" 🚀 HorizonArm SDK 快速入门 (交互模式)")
    print("=" * 70)
    print("本程序将引导您测试机械臂的核心运动功能。")
    # 打印当前生效配置目录与关键电机参数（避免“到底有没有用到 config”）
    cfg_dir = os.environ.get("HORIZONARM_CONFIG_DIR", "").strip() or "(未设置)"
    rr, dd = _load_motor_cfg()
    print(f"配置目录(HORIZONARM_CONFIG_DIR): {cfg_dir}")
    if rr or dd:
        # 只打印 1-6，避免太多输出
        ratios_str = ", ".join([f"{i}:{rr.get(i,'?')}" for i in range(1, 7)])
        dirs_str = ", ".join([f"{i}:{dd.get(i,'?')}" for i in range(1, 7)])
        print(f"减速比(motor_reducer_ratios): {ratios_str}")
        print(f"方向(motor_directions): {dirs_str}")
    print("请确保：")
    print("1. 机械臂已上电")
    print("2. OmniCAN（UCP）已连接（电脑侧表现为串口）")
    print("3. 急停按钮处于可触及位置 (安全第一！)")
    print("=" * 70)

def connect_motors():
    """
    连接电机向导
    
    LLM Note: 
    - 使用 `create_motor_controller` 工厂函数创建实例。
    - 必须调用 `connect()` 建立物理通信。
    - 返回一个字典 {motor_id: controller_instance}。
    """
    print("\n[配置] 连接机械臂电机")
    print("-" * 30)
    
    default_port = "COM14"
    port = input(f"请输入串口号 (默认 {default_port}): ").strip()
    if not port:
        port = default_port
        
    ids_str = input("请输入电机ID列表 (默认 1,2,3,4,5,6): ").strip()
    if not ids_str:
        motor_ids = [1, 2, 3, 4, 5, 6]
    else:
        try:
            motor_ids = [int(x.strip()) for x in ids_str.split(',')]
        except:
            print("❌ ID格式错误，使用默认值")
            motor_ids = [1, 2, 3, 4, 5, 6]

    motors = {}
    print(f"\n正在连接电机 (Port: {port})...")
    for mid in motor_ids:
        try:
            print(f"  连接电机 {mid}...", end='', flush=True)
            # 关键：创建并连接电机
            # 当前默认：UCP 硬件保护模式（OmniCAN 串口 115200）
            m = create_motor_controller(motor_id=mid, port=port, baudrate=115200)
            m.connect()
            motors[mid] = m
            print(" ✅ OK")
        except Exception as e:
            print(f" ❌ 失败 ({e})")

    if not motors:
        print("\n🛑 未连接任何电机")
        return None
        
    return motors

def demo_joint_motion(sdk):
    """
    演示关节空间运动 (Joint Space Motion)
    
    原理：
    - 直接控制 6 个关节的角度。
    - 优点：绝对可靠，不会出现逆运动学无解的情况。
    - 缺点：末端轨迹非直线。
    
    SDK API:
    - sdk.motion.move_joints(angles, duration)
    """
    print("\n🦾 关节空间运动演示")
    print("-" * 30)
    print("⚠️  注意：机械臂即将运动，请确保周围安全")
    
    targets = [
        ("标准姿态 (绝对)", [0, 90, 0, 0, 0, 0], "绝对目标角：会让 6 轴都到指定值（用于快速回到常用姿态）"),
        ("姿态 A：只转 J3 +45° (增量)", None, "增量模式：只改变 J3，其他轴保持当前角度"),
        ("姿态 B：只转 J1 +45° (增量)", None, "增量模式：只改变 J1，其他轴保持当前角度"),
        ("自定义 (绝对)", None, "手动输入 6 轴绝对角度"),
    ]
    
    print("请选择目标姿态:")
    for i, (name, _, desc) in enumerate(targets):
        print(f"  {i+1}. {name:<15} - {desc}")
        
    choice = input("\n请输入选择 (1-4): ").strip()
    
    target_angles = []
    if choice == '1':
        target_angles = targets[0][1]
    elif choice == '2':
        # 单轴增量：只给 3 号电机下发一次位置命令
        _move_single_joint_delta(sdk, joint_id=3, delta_deg=45.0)
        return
    elif choice == '3':
        # 单轴增量：只给 1 号电机下发一次位置命令
        _move_single_joint_delta(sdk, joint_id=1, delta_deg=45.0)
        return
    elif choice == '4':
        try:
            inp = input("请输入6个关节角度 (逗号分隔): ").strip()
            target_angles = [float(x) for x in inp.split(',')]
            if len(target_angles) != 6: raise ValueError
        except:
            print("❌ 输入格式错误")
            return
    else:
        print("❌ 无效选择")
        return

    # 注意：底层是“位置到点”的梯形控制，到位会停。
    # 这里不再让用户输入“运动时间”，避免误解为“到时间才停”。
    print(f"\n🚀 开始运动 -> {target_angles}（到位即停）")
    try:
        # 核心调用：执行关节运动（底层会等待到位并返回 True/False）
        ok = bool(sdk.motion.move_joints(target_angles, duration=None))
        if ok:
            print("✅ 已到位并停止")
        else:
            print("❌ 未到位/超时（可能是方向/零点/减速比不匹配或通信异常）")
            _warn_no_auto_disable("关节运动未到位/超时")
    except Exception as e:
        print(f"❌ 运动失败: {e}")

def demo_cartesian_motion(sdk):
    """
    演示笛卡尔空间运动 (Cartesian Space Motion)
    
    原理：
    - 控制机械臂末端 (End-Effector) 在空间中的 XYZ 位置和 RPY 姿态。
    - SDK 内部会进行逆运动学 (IK) 解算。
    
    SDK API:
    - sdk.motion.move_cartesian(position, orientation, duration)
    """
    print("\n🌐 笛卡尔空间运动演示")
    print("-" * 30)
    print("⚠️  注意：IK计算可能无解，请确保目标在工作空间内")
    
    print("当前预设目标 (单位: mm, 度):")
    print("  1. 前方抓取点 Pos=[200, 0, 150], Ori=[0, 0, 180] (水平向前)")
    print("  2. 上方放置点 Pos=[200, 0, 250], Ori=[0, 0, 180] (垂直抬升)")
    
    choice = input("\n请输入选择 (1-2): ").strip()
    
    pos, ori = [], []
    if choice == '1':
        pos = [200, 0, 150]
        ori = [0, 0, 180] # Roll=180 通常指夹爪向下
    elif choice == '2':
        pos = [200, 0, 250]
        ori = [0, 0, 180]
    else:
        print("❌ 无效选择")
        return

    # 注意：笛卡尔运动底层同样是“到位即停”，不以 duration 作为“到时间才停”的逻辑。
    print(f"\n🚀 开始运动 -> Pos:{pos}, Ori:{ori}（到位即停）")
    try:
        ok = bool(sdk.motion.move_cartesian(position=pos, orientation=ori, duration=None))
        if ok:
            print("✅ 已到位并停止")
        else:
            print("❌ 未到位/超时（可能是IK无解、参数不匹配或通信异常）")
            _warn_no_auto_disable("笛卡尔运动未到位/超时")
    except Exception as e:
        print(f"❌ 运动失败: {e}")

def demo_claw_control(sdk):
    """
    演示夹爪控制
    
    原理：
    - 控制末端执行器的开合。
    - 通常 0.0 表示闭合，1.0 表示全开。
    
    SDK API:
    - sdk.motion.control_claw(action)
    """
    print("\n🤏 夹爪控制演示")
    print("-" * 30)
    print("  1. 打开夹爪 (action=1.0)")
    print("  2. 关闭夹爪 (action=0.0)")
    print("  3. 自定义角度 (0.0 - 1.0)")
    
    choice = input("\n请选择 (1-3): ").strip()
    
    action = 0.0
    if choice == '1': action = 1.0
    elif choice == '2': action = 0.0
    elif choice == '3':
        try:
            val = float(input("请输入开合程度 (0.0 - 1.0): ").strip())
            action = max(0.0, min(1.0, val))
        except:
            print("❌ 输入错误")
            return
    else:
        return

    print(f"🚀 执行夹爪动作: {action}")
    try:
        # 核心调用：控制夹爪
        ok = bool(sdk.motion.control_claw(action=action))
        if ok:
            print("✅ 完成")
        else:
            print("❌ 夹爪动作失败")
    except Exception as e:
        print(f"❌ 失败: {e}")

def demo_preset_action(sdk):
    """
    演示预设动作 (Preset Actions)
    
    原理：
    - 执行配置文件 (config/embodied_config/preset_actions.json) 中定义的动作序列。
    - 适合复用复杂的组合动作（如“挥手”、“抓取准备”）。
    
    SDK API:
    - sdk.motion.execute_preset_action(name, speed)
    """
    print("\n🏠 预设动作演示")
    print("-" * 30)

    # 动态读取配置里的动作列表，避免示例写死英文名导致“找不到动作”
    actions = []
    try:
        import json
        # 项目根目录在文件开头已计算过：project_root
        cfg_path = os.path.join(project_root, "config", "embodied_config", "preset_actions.json")
        if os.path.exists(cfg_path):
            data = json.load(open(cfg_path, "r", encoding="utf-8"))
            if isinstance(data, dict):
                actions = list(data.keys())
    except Exception:
        actions = []

    # 常用别名映射（兼容英文菜单/用户习惯）
    # - home -> 初始位置
    alias = {}
    if "初始位置" in actions:
        alias["home"] = "初始位置"

    if actions:
        print("可用动作（来自 config/embodied_config/preset_actions.json ）：")
        for i, name in enumerate(actions, 1):
            print(f"  {i}. {name}")
        print("  0. 返回")
        print("\n你也可以直接输入动作名（例如：初始位置 / 点头 / 摇头），或输入英文别名 home。")

        choice = input("\n请选择序号或输入动作名: ").strip()
        if choice == "0" or not choice:
            return
        if choice.isdigit():
            idx = int(choice)
            if idx < 1 or idx > len(actions):
                print("❌ 无效选择")
                return
            action_name = actions[idx - 1]
        else:
            action_name = alias.get(choice.lower(), choice)
    else:
        # 兜底：如果配置读取失败，保留旧行为
        print("⚠️ 未读取到 preset_actions.json，使用默认示例动作名（可能与配置不一致）")
        print("  1. home")
        print("  2. sleep")
        choice = input("\n请选择 (1-2): ").strip()
        action_name = ""
        if choice == "1":
            action_name = "home"
        elif choice == "2":
            action_name = "sleep"
        else:
            return

    # 注意：预设动作内部是分段关节到点控制，到位即停，不用 sleep 兜底等待。
    print(f"🚀 执行动作: '{action_name}'（到位即停）")
    try:
        # 核心调用：执行预设动作（name 必须是 JSON 中的 key）
        ok = bool(sdk.motion.execute_preset_action(action_name, speed="normal"))
        if ok:
            print("✅ 动作完成")
        else:
            print("❌ 动作未完成/超时")
            _warn_no_auto_disable("预设动作未完成/超时")
    except Exception as e:
        print(f"❌ 失败: {e}")

def main():
    clear_screen()
    print_header()
    
    # 1. 初始化连接
    motors = connect_motors()
    if not motors:
        input("\n按 Enter 退出...")
        return

    # 2. 初始化 SDK
    # HorizonArmSDK 是核心类，它接收电机字典并管理所有子模块
    print("\n🔄 初始化 SDK...")
    try:
        sdk = HorizonArmSDK(motors=motors)
        
        # 3. 设置全局运动参数 (安全关键!)
        # max_speed: 最大速度 (RPM)
        # acceleration: 加速度 (RPM/s)
        # deceleration: 减速度 (RPM/s)
        print("⚙️  设置安全运动参数 (Speed=100)...")
        sdk.motion.set_motion_params(max_speed=100, acceleration=80, deceleration=80)
        
        print("✅ SDK 初始化成功")
    except Exception as e:
        print(f"❌ SDK 初始化失败: {e}")
        return

    # 4. 主菜单循环
    while True:
        print("\n📋 功能菜单:")
        print("  1. 关节空间运动 (Joint Motion)")
        print("  2. 笛卡尔空间运动 (Cartesian Motion)")
        print("  3. 夹爪控制 (Claw Control)")
        print("  4. 执行预设动作 (Preset Actions)")
        print("  5. 查看电机状态 (Debug)")
        print("  0. 退出程序")
        
        choice = input("\n请选择功能 (0-5): ").strip()
        
        if choice == '0':
            print("\n👋 正在断开连接并退出...")
            for m in motors.values():
                try: 
                    m.disconnect()
                except: pass
            break
        elif choice == '1':
            demo_joint_motion(sdk)
        elif choice == '2':
            demo_cartesian_motion(sdk)
        elif choice == '3':
            demo_claw_control(sdk)
        elif choice == '4':
            demo_preset_action(sdk)
        elif choice == '5':
            print("\n📊 电机状态:")
            rr, dd = _load_motor_cfg()
            for mid, m in motors.items():
                try:
                    motor_deg = float(m.read_parameters.get_position())
                    joint_deg = _motor_deg_to_joint_deg(motor_deg, mid, rr, dd)
                    print(f"  Motor {mid}: motor={motor_deg:.2f}° -> joint≈{joint_deg:.2f}°")
                except:
                    print(f"  Motor {mid}: Error")
        else:
            print("❌ 无效选择")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ 程序已强制终止")
