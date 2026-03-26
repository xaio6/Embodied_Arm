#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IO控制功能完全指南
==========================================

本示例是 test_io.py 的**场景化增强版**，新增：
✨ 实际应用场景演示（传感器联动、流程控制）
✨ 常用IO控制模式（脉冲、延时、循环）
✨ 错误处理和故障排除
✨ 接线示意和安全提示

核心功能：
1. **DI (Digital Input)**: 读取传感器状态（光电开关、按钮等）
2. **DO (Digital Output)**: 控制执行器（继电器、指示灯等）
3. **实时监控**: 循环读取IO状态

应用场景：
- 场景1: 传感器触发抓取（检测到物体→执行抓取）
- 场景2: 指示灯控制（运动中→黄灯，到位→绿灯）
- 场景3: 气动夹爪控制（DO控制电磁阀）
- 场景4: 安全光栅联动（光栅触发→急停）

硬件接线提示：
DI接线: 传感器信号→DIx, VCC/GND→电源
DO接线: DOx→继电器/固态继电器→负载
"""

import os
import sys
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from Embodied_SDK import IOSDK

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    print("=" * 70)
    print(" 🔌 IO控制功能完全指南")
    print("=" * 70)
    print("本程序演示数字IO的读写和实际应用场景。\n")

class IOControlGuide:
    """IO控制教学工具"""
    
    def __init__(self):
        self.io = None
        self.port = "COM15"
    
    def connect(self):
        """连接IO控制器"""
        print("\n📡 连接IO控制器")
        print("-" * 50)
        
        port = input(f"请输入IO控制器串口号 (默认 {self.port}): ").strip()
        if port:
            self.port = port
        
        try:
            self.io = IOSDK(port=self.port)
            if self.io.connect():
                print(f"✅ IO控制器连接成功 ({self.port})")
                return True
            else:
                print("❌ 连接失败")
                return False
        except Exception as e:
            print(f"❌ 连接异常: {e}")
            return False
    
    def basic_read_di(self):
        """基础功能：读取DI"""
        clear_screen()
        print("=" * 70)
        print(" 📥 读取数字输入 (DI)")
        print("=" * 70)
        
        print("\n💡 功能说明：")
        print("  DI用于读取外部传感器的开关量信号")
        print("  常见传感器：")
        print("    - 光电开关（检测物体）")
        print("    - 接近开关（检测金属）")
        print("    - 限位开关（检测到位）")
        print("    - 按钮（人工触发）")
        
        print("\n🔌 接线说明：")
        print("  NPN型: 信号线→DI, 棕色→VCC, 蓝色→GND")
        print("  PNP型: 信号线→DI, 棕色→VCC, 黑色→GND")
        print("  状态: HIGH(有信号) / LOW(无信号)")
        
        input("\n按 Enter 读取当前状态...")
        
        try:
            states = self.io.read_di_states()
            
            print(f"\n检测到 {len(states)} 个DI引脚:")
            for pin, state in states.items():
                status = "🟢 HIGH (有信号)" if state else "⚪ LOW  (无信号)"
                print(f"  DI {pin}: {status}")
        except Exception as e:
            print(f"❌ 读取失败: {e}")
    
    def basic_write_do(self):
        """基础功能：控制DO"""
        clear_screen()
        print("=" * 70)
        print(" 📤 控制数字输出 (DO)")
        print("=" * 70)
        
        print("\n💡 功能说明：")
        print("  DO用于控制外部执行器的开关")
        print("  常见执行器：")
        print("    - 继电器（控制大功率设备）")
        print("    - 电磁阀（控制气动/液压）")
        print("    - 指示灯（状态显示）")
        print("    - 蜂鸣器（报警提示）")
        
        print("\n🔌 接线说明：")
        print("  DO→继电器线圈→GND")
        print("  继电器触点→负载")
        print("  控制: HIGH(开启/通电) / LOW(关闭/断电)")
        
        pin = input("\n请输入DO引脚号 (0-7): ").strip()
        try:
            pin = int(pin)
        except:
            print("❌ 无效引脚号")
            return
        
        print(f"\n控制 DO {pin}:")
        print("  1. 设置为 HIGH (开启)")
        print("  2. 设置为 LOW  (关闭)")
        
        action = input("请选择 (1/2): ").strip()
        state = True if action == '1' else False
        
        try:
            self.io.set_do(pin, state)
            state_str = "HIGH 🟢" if state else "LOW ⚪"
            print(f"✅ DO {pin} 已设置为 {state_str}")
        except Exception as e:
            print(f"❌ 设置失败: {e}")
    
    def scenario1_sensor_trigger(self):
        """场景1：传感器触发控制"""
        clear_screen()
        print("=" * 70)
        print(" 🎯 场景1: 传感器触发抓取")
        print("=" * 70)
        
        print("\n📖 场景描述：")
        print("  传送带上有光电传感器检测物体")
        print("  当传感器检测到物体时（DI0变HIGH）：")
        print("    1. 点亮指示灯（DO0=HIGH）")
        print("    2. 触发机械臂抓取")
        print("    3. 抓取完成后熄灯（DO0=LOW）")
        
        print("\n🔌 接线要求：")
        print("  DI0: 光电传感器信号线")
        print("  DO0: 指示灯控制线")
        
        di_pin = int(input("\n传感器DI引脚 (默认0): ").strip() or "0")
        do_pin = int(input("指示灯DO引脚 (默认0): ").strip() or "0")
        
        print(f"\n开始监控 DI{di_pin}...")
        print("按 Ctrl+C 退出")
        
        try:
            last_state = False
            
            while True:
                di_states = self.io.read_di_states()
                current_state = di_states.get(di_pin, False)
                
                # 检测上升沿（从LOW变HIGH）
                if current_state and not last_state:
                    print(f"\n🔔 检测到物体！DI{di_pin}=HIGH")
                    
                    # 点亮指示灯
                    self.io.set_do(do_pin, True)
                    print(f"  → DO{do_pin}=HIGH (指示灯亮)")
                    
                    # 模拟抓取动作
                    print("  → 执行抓取动作...")
                    time.sleep(2)
                    print("  ✅ 抓取完成")
                    
                    # 熄灯
                    self.io.set_do(do_pin, False)
                    print(f"  → DO{do_pin}=LOW (指示灯灭)")
                
                last_state = current_state
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\n\n已停止监控")
            self.io.set_do(do_pin, False)  # 确保熄灯
    
    def scenario2_indicator_control(self):
        """场景2：指示灯状态显示"""
        clear_screen()
        print("=" * 70)
        print(" 💡 场景2: 运动状态指示灯")
        print("=" * 70)
        
        print("\n📖 场景描述：")
        print("  使用LED指示机械臂状态：")
        print("    绿灯（DO0）: 空闲/待命")
        print("    黄灯（DO1）: 运动中")
        print("    红灯（DO2）: 故障/急停")
        
        print("\n演示：模拟状态切换")
        
        states = [
            ("空闲", [0], [1, 2]),
            ("运动中", [1], [0, 2]),
            ("到位", [0], [1, 2]),
            ("故障", [2], [0, 1])
        ]
        
        try:
            for state_name, on_pins, off_pins in states:
                print(f"\n状态: {state_name}")
                
                # 点亮指定灯
                for pin in on_pins:
                    self.io.set_do(pin, True)
                    print(f"  DO{pin}=ON")
                
                # 熄灭其他灯
                for pin in off_pins:
                    self.io.set_do(pin, False)
                
                time.sleep(2)
            
            # 全部熄灭
            for pin in [0, 1, 2]:
                self.io.set_do(pin, False)
            
            print("\n✅ 演示完成")
            
        except Exception as e:
            print(f"❌ 执行失败: {e}")
    
    def scenario3_pneumatic_gripper(self):
        """场景3：气动夹爪控制"""
        clear_screen()
        print("=" * 70)
        print(" 🤏 场景3: 气动夹爪控制")
        print("=" * 70)
        
        print("\n📖 场景描述：")
        print("  使用DO控制双作用气缸夹爪：")
        print("    DO0=HIGH, DO1=LOW  → 夹爪闭合")
        print("    DO0=LOW,  DO1=HIGH → 夹爪张开")
        print("    (通过电磁阀切换气路)")
        
        print("\n🔌 接线：")
        print("  DO0 → 电磁阀线圈A（闭合）")
        print("  DO1 → 电磁阀线圈B（张开）")
        
        print("\n控制选项：")
        print("  1. 夹爪闭合")
        print("  2. 夹爪张开")
        print("  3. 夹爪复位（全部关闭）")
        
        choice = input("\n请选择 (1-3): ").strip()
        
        try:
            if choice == '1':
                self.io.set_do(0, True)
                self.io.set_do(1, False)
                print("✅ 夹爪闭合")
            elif choice == '2':
                self.io.set_do(0, False)
                self.io.set_do(1, True)
                print("✅ 夹爪张开")
            elif choice == '3':
                self.io.set_do(0, False)
                self.io.set_do(1, False)
                print("✅ 夹爪复位")
            
        except Exception as e:
            print(f"❌ 执行失败: {e}")
    
    def realtime_monitor(self):
        """实时监控"""
        clear_screen()
        print("=" * 70)
        print(" 🔄 实时IO监控")
        print("=" * 70)
        
        print("\n实时显示所有DI和DO状态...")
        print("按 Ctrl+C 退出\n")
        
        try:
            while True:
                di_states = self.io.read_di_states()
                do_states = self.io.read_do_states()
                
                # 格式化输出
                di_str = " | ".join([f"DI{k}:{'H' if v else 'L'}" for k, v in di_states.items()])
                do_str = " | ".join([f"DO{k}:{'H' if v else 'L'}" for k, v in do_states.items()])
                
                print(f"\r[输入] {di_str}   [输出] {do_str}    ", end='', flush=True)
                
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\n\n✅ 已停止监控")
    
    def run(self):
        """主循环"""
        clear_screen()
        print_header()
        
        # 连接
        if not self.connect():
            return
        
        input("\n✅ 连接完成！按 Enter 继续...")
        
        while True:
            clear_screen()
            print_header()
            
            print("📋 功能菜单：")
            print("\n【基础功能】")
            print("  1. 读取DI状态")
            print("  2. 控制DO输出")
            print("  3. 实时IO监控")
            print("\n【应用场景】")
            print("  4. 场景1: 传感器触发抓取")
            print("  5. 场景2: 运动状态指示灯")
            print("  6. 场景3: 气动夹爪控制")
            print("\n  0. 退出")
            
            choice = input("\n请选择 (0-6): ").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                self.basic_read_di()
            elif choice == '2':
                self.basic_write_do()
            elif choice == '3':
                self.realtime_monitor()
            elif choice == '4':
                self.scenario1_sensor_trigger()
            elif choice == '5':
                self.scenario2_indicator_control()
            elif choice == '6':
                self.scenario3_pneumatic_gripper()
            else:
                print("❌ 无效选择")
            
            input("\n按 Enter 继续...")
        
        # 清理
        if self.io:
            self.io.disconnect()
        
        print("\n👋 感谢使用！")

if __name__ == "__main__":
    try:
        guide = IOControlGuide()
        guide.run()
    except KeyboardInterrupt:
        print("\n\n⚠️  程序被中断")

