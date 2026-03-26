#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
夹爪（电机ID=7）独立SDK交互式测试工具（力矩模式）
====================================================

风格尽量对齐 example/ 目录下其他 test_*.py：
- 交互式菜单
- connect/ensure_connected/各功能独立方法

本测试只展示两件事怎么做：
- 闭合：调用 gripper.clamp()
- 张开：调用 gripper.open()
"""

import os
import sys
import time
from typing import Optional

# 添加项目根目录到路径（与 example/ 下其他 test 脚本一致）
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Embodied_SDK import ZDTGripperSDK


class ZDTGripperTorqueTester:
    """夹爪力矩模式交互式测试器"""

    def __init__(self):
        self.gripper: Optional[ZDTGripperSDK] = None
        self.connected: bool = False

        print("=" * 60)
        print(" 夹爪独立SDK交互式测试工具")
        print("=" * 60)
        print()

    # ---------- 连接管理 ----------
    def connect_gripper(self) -> bool:
        """连接夹爪电机"""
        if self.connected and self.gripper is not None:
            print(" 夹爪已连接")
            return True

        print(" 连接夹爪电机...")
        default_port = "COM14"
        default_baudrate = 115200
        print(f"默认配置: {default_port}, {default_baudrate}波特率（UCP硬件保护模式）")
        use_default = input("使用默认配置? (Enter确认, n取消): ").strip().lower()

        if use_default != "n":
            port = default_port
            baudrate = default_baudrate
        else:
            port = input(f"串口号 (例如: {default_port}): ").strip() or default_port
            baudrate = int(input(f"波特率 (默认: {default_baudrate}): ").strip() or str(default_baudrate))

        try:
            self.gripper = ZDTGripperSDK(port=port, baudrate=baudrate)
            self.gripper.connect()
            self.connected = True
            print(f" 夹爪连接成功! (端口: {port})")
            return True
        except Exception as e:
            print(f" 夹爪连接失败: {e}")
            self.gripper = None
            self.connected = False
            return False

    def disconnect_gripper(self) -> None:
        """断开夹爪连接"""
        if self.gripper and self.connected:
            try:
                self.gripper.disconnect()
                print(" 夹爪已断开连接")
            except Exception as e:
                print(f" 断开连接时出现警告: {e}")
        else:
            print(" 夹爪未连接")
        self.gripper = None
        self.connected = False

    def ensure_connected(self) -> bool:
        """确保夹爪已连接"""
        if not self.connected or self.gripper is None:
            print(" 夹爪未连接，请先连接夹爪")
            return False
        return True

    # ---------- 两个动作接口 ----------
    def test_clamp(self) -> None:
        """夹紧（clamp）"""
        if not self.ensure_connected():
            return

        print("\n 夹紧测试 (clamp)")
        print("-" * 30)
        try:
            current = int(input("夹紧电流(mA, 正值，默认 1200): ").strip() or "1200")
            slope = int(input("电流斜率(mA/s, 默认 1000): ").strip() or "1000")

            print(f"夹紧: current={current}mA, slope={slope}mA/s")
            self.gripper.clamp(abs(current), slope_ma_s=slope)
            print(" 夹紧完成（将一直夹着，直到你执行张开或断电）")
        except Exception as e:
            print(f" 夹紧失败: {e}")

    def test_open(self) -> None:
        """张开（open）"""
        if not self.ensure_connected():
            return

        print("\n 张开测试 (open)")
        print("-" * 30)
        try:
            current = int(input("张开电流(mA, 正值，默认 1200): ").strip() or "1200")
            slope = int(input("电流斜率(mA/s, 默认 1000): ").strip() or "1000")
            settle_s = float(input("stop/失能/使能之间等待(s, 默认 0.1): ").strip() or "0.1")

            print(f"张开: current={current}mA, slope={slope}mA/s（固定反向运行1秒）")
            self.gripper.open(abs(current), slope_ma_s=slope, settle_s=settle_s)
        except Exception as e:
            print(f" 张开失败: {e}")

    def test_grasp_release_cycle(self) -> None:
        """夹紧/松开循环测试"""
        if not self.ensure_connected():
            return

        print("\n 夹紧/松开循环测试")
        print("-" * 30)
        try:
            cycles = int(input("循环次数(默认 3): ").strip() or "3")
            grasp_current = int(input("夹紧电流(mA, 正值，默认 1200): ").strip() or "1200")
            release_current = int(input("松开电流(mA, 正值，默认 1200): ").strip() or "1200")
            slope = int(input("电流斜率(mA/s, 默认 1000): ").strip() or "1000")
            settle_s = float(input("stop/失能/使能之间等待(s, 默认 0.1): ").strip() or "0.1")
            interval_s = float(input("每步之间额外等待(s, 默认 0.2): ").strip() or "0.2")

            for i in range(cycles):
                print(f" 第{i+1}/{cycles}次：夹紧")
                self.gripper.clamp(abs(grasp_current), slope_ma_s=slope)
                time.sleep(max(0.0, interval_s))

                print(f" 第{i+1}/{cycles}次：松开")
                # 兼容硬件：反向力矩1秒 -> stop -> disable -> enable（默认启用）
                self.gripper.open(
                    abs(release_current),
                    slope_ma_s=slope,
                    settle_s=settle_s,
                )
                time.sleep(max(0.0, interval_s))

            print(" 循环测试完成")
        except Exception as e:
            print(f" 循环测试失败: {e}")

    # ---------- 菜单 ----------
    def print_menu(self) -> None:
        print("\n" + "=" * 60)
        print(" 夹爪测试菜单")
        print("=" * 60)
        print("1. 连接夹爪")
        print("2. 夹紧 (clamp)")
        print("3. 张开 (open)")
        print("4. 夹紧/张开循环测试")
        print("7. 断开连接")
        print("0. 退出")
        print("=" * 60)

    def run(self) -> None:
        """主循环"""
        while True:
            self.print_menu()
            choice = input("请选择操作 (0-7): ").strip()

            if choice == "1":
                self.connect_gripper()
            elif choice == "2":
                self.test_clamp()
            elif choice == "3":
                self.test_open()
            elif choice == "4":
                self.test_grasp_release_cycle()
            elif choice == "7":
                self.disconnect_gripper()
            elif choice == "0":
                print(" 退出测试工具...")
                break
            else:
                print(" 无效选择，请重新输入")

        # 退出时清理
        try:
            self.disconnect_gripper()
        except Exception:
            pass


def main():
    tester = ZDTGripperTorqueTester()
    tester.run()


if __name__ == "__main__":
    main()


