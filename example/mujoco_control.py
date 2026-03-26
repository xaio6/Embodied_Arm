#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MuJoCo 仿真交互演示（DigitalTwinSDK）
====================================

说明：
- 本脚本演示 `Embodied_SDK.digital_twin.DigitalTwinSDK` 的推荐用法；
- **不依赖 GUI**，会弹出 MuJoCo Viewer 窗口；
- MuJoCo 为可选依赖：未安装 `mujoco` 时会给出提示并退出。

如果你需要“直接操作 mujoco.viewer/ctrl 滑块”的更底层示例，请参考：
`example/developer_tools/mujoco_slider_viewer.py`
"""

from __future__ import annotations

import os
import sys
import time
import numpy as np

# 添加项目根目录
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from Embodied_SDK import DigitalTwinSDK


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def print_header() -> None:
    print("=" * 70)
    print(" 🦾 MuJoCo 仿真交互演示（DigitalTwinSDK）")
    print("=" * 70)
    print("本程序将启动 MuJoCo Viewer 窗口。")
    print("你可以在不连接真实机械臂的情况下测试运动逻辑。")
    print("提示：若未安装 mujoco，请执行 `pip install mujoco`。")
    print("=" * 70)


def demo_auto_wave(sdk: DigitalTwinSDK) -> None:
    """连续波形演示：高频 set_joint_angles 更新姿态。"""
    print("\n🌊 自动波形演示")
    print("-" * 30)
    print("机械臂 J1 和 J2 关节将进行正弦摆动。")
    print("观察仿真窗口中的运动...")
    print("按 Ctrl+C 停止演示。")
    input("按 Enter 开始...")

    print("🚀 正在运行波形控制...")
    try:
        start_time = time.time()
        while sdk.is_running():
            t = time.time() - start_time

            # J1: 幅度 +/- 45度, 频率 0.5Hz
            angle_j1 = 45 * np.sin(2 * np.pi * 0.5 * t)

            # J2: 幅度 +/- 20度, 频率 0.25Hz, 偏置 45度(避免碰撞地面)
            angle_j2 = 20 * np.sin(2 * np.pi * 0.25 * t) + 45

            target = [angle_j1, angle_j2, 0, 0, 0, 0]
            sdk.set_joint_angles(target)

            # 约 100Hz
            time.sleep(0.01)
    except KeyboardInterrupt:
        print("\n✅ 停止演示")


def _load_preset_actions(project_root_path: str) -> list[str]:
    actions: list[str] = []
    try:
        import json

        cfg_path = os.path.join(project_root_path, "config", "embodied_config", "preset_actions.json")
        if os.path.exists(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                actions = list(data.keys())
    except Exception:
        return []
    return actions


def demo_preset_action(sdk: DigitalTwinSDK, project_root_path: str) -> None:
    """预设动作演示：执行 preset_actions.json 中定义的动作。"""
    print("\n🎬 预设动作演示")
    print("-" * 30)

    actions = _load_preset_actions(project_root_path)

    alias: dict[str, str] = {}
    if "初始位置" in actions:
        alias["home"] = "初始位置"
    if "挥手" in actions:
        alias["wave"] = "挥手"

    action: str | None = None
    if actions:
        print("可用动作：")
        for i, name in enumerate(actions, 1):
            print(f"  {i}. {name}")
        print("  0. 返回")

        choice = input("\n请选择序号或输入动作名: ").strip()
        if choice == "0" or not choice:
            return
        if choice.isdigit():
            idx = int(choice)
            if idx < 1 or idx > len(actions):
                print("❌ 无效选择")
                return
            action = actions[idx - 1]
        else:
            action = alias.get(choice.lower(), choice)
    else:
        print("  1. Home (归零 - 直立状态)")
        print("  2. Wave (挥手 - 示例动作)")
        choice = input("请选择动作 (1-2): ").strip()
        if choice == "1":
            action = "home"
        elif choice == "2":
            action = "wave"

    if not action:
        print("❌ 无效选择")
        return

    print(f"🚀 执行动作: '{action}'...")
    sdk.execute_preset_action(action)
    time.sleep(2)
    print("✅ 动作完成")


def demo_random_pose(sdk: DigitalTwinSDK) -> None:
    """随机姿态演示：随机生成关节角，并用 move_joints 平滑移动。"""
    print("\n🎲 随机姿态演示")
    print("-" * 30)

    target = list(np.random.uniform(-45, 45, 6))
    target[1] += 30  # 抬起一点，避免碰地

    target_str = ", ".join([f"{x:.1f}" for x in target])
    print(f"目标关节角: [{target_str}]")

    print("🚀 开始移动 (耗时 1.5s)...")
    sdk.move_joints(target, duration=1.5)
    time.sleep(1.5)
    print("✅ 到达目标")


def main() -> None:
    clear_screen()
    print_header()

    print("\n[1/2] 正在启动 MuJoCo 仿真器...")
    try:
        sdk = DigitalTwinSDK()
        if not sdk.start_simulation():
            print("❌ 仿真启动失败")
            print("可能原因：")
            print("1. 未安装 mujoco 库 (pip install mujoco)")
            print("2. 模型文件 (xml) 路径错误")
            input("按 Enter 退出...")
            return
        print("✅ 仿真已启动 (请查看弹出的窗口)")
    except Exception as e:
        print(f"❌ 初始化异常: {e}")
        return

    while True:
        if not sdk.is_running():
            print("\n⚠️  仿真窗口已关闭，程序结束。")
            break

        print("\n📋 功能菜单:")
        print("  1. 自动波形演示 (Auto Wave - 连续控制)")
        print("  2. 执行预设动作 (Preset Action - 离散动作)")
        print("  3. 移动到随机姿态 (Random Pose - 轨迹规划)")
        print("  0. 退出程序")

        choice = input("\n请选择 (0-3): ").strip()

        if choice == "0":
            print("👋 正在停止仿真...")
            break
        if choice == "1":
            demo_auto_wave(sdk)
        elif choice == "2":
            demo_preset_action(sdk, project_root)
        elif choice == "3":
            demo_random_pose(sdk)
        else:
            print("❌ 无效选择")

    sdk.stop_simulation()
    print("程序已安全退出。")


if __name__ == "__main__":
    main()