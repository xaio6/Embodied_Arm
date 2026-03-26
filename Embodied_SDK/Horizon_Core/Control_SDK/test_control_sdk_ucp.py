# -*- coding: utf-8 -*-
"""
Control_SDK UCP模式测试工具（交互式菜单）
测试通过 OmniCAN 的电机控制
"""

import sys
import os
import time

# 确保导入路径
sys.path.insert(0, os.path.dirname(__file__))

from Control_Core import ZDTMotorController

def prompt_str(msg: str, default: str = "") -> str:
    """提示输入字符串"""
    s = input(msg).strip()
    return s if s else default

def prompt_int(msg: str, default: int = 0) -> int:
    """提示输入整数"""
    s = input(msg).strip()
    try:
        return int(s) if s else default
    except ValueError:
        return default

def prompt_float(msg: str, default: float = 0.0) -> float:
    """提示输入浮点数"""
    s = input(msg).strip()
    try:
        return float(s) if s else default
    except ValueError:
        return default


class ControlSDKUcpTester:
    """Control_SDK UCP模式测试器"""
    
    def __init__(self):
        self.controller = None
        self.port = "COM31"
        self.motor_id = 1
        self.connected = False
        
        print("="*70)
        print(" Control_SDK UCP模式测试工具")
        print(" (测试通过 OmniCAN 的 Control_SDK API)")
        print("="*70)
    
    def show_menu(self):
        """显示菜单"""
        print("\n" + "="*70)
        print("主菜单")
        print("="*70)
        print(f"当前配置: 端口={self.port}, 电机ID={self.motor_id}, "
              f"连接={'是' if self.connected else '否'}")
        print()
        print("连接管理:")
        print("  1. 连接电机")
        print("  2. 断开连接")
        print("  3. 修改配置")
        print()
        print("状态读取:")
        print("  4. 读取版本信息")
        print("  5. 读取电机状态")
        print("  6. 读取位置信息")
        print("  7. 读取速度信息")
        print()
        print("基础控制:")
        print("  8. 使能电机")
        print("  9. 失能电机")
        print("  10. 停止电机")
        print()
        print("运动控制:")
        print("  11. 位置控制（移动到指定位置）")
        print("  12. 速度控制")
        print("  13. 回零")
        print()
        print("综合测试:")
        print("  14. 完整控制流程测试")
        print()
        print("  0. 退出")
        print("="*70)
    
    def connect_motor(self):
        """连接电机"""
        if self.connected:
            print("\n⚠️  已连接，请先断开")
            return
        
        print("\n连接电机...")
        try:
            self.controller = ZDTMotorController(
                motor_id=self.motor_id,
                port=self.port,
                baudrate=115200
            )
            self.controller.connect()
            self.connected = True
            print(f"✓ 连接成功 (端口={self.port}, 电机ID={self.motor_id})")
        except Exception as e:
            print(f"✗ 连接失败: {e}")
            self.controller = None
    
    def disconnect_motor(self):
        """断开连接"""
        if not self.connected:
            print("\n⚠️  未连接")
            return
        
        print("\n断开连接...")
        if self.controller:
            self.controller.disconnect()
        self.controller = None
        self.connected = False
        print("✓ 已断开")
    
    def modify_config(self):
        """修改配置"""
        if self.connected:
            print("\n⚠️  请先断开连接")
            return
        
        print("\n修改配置:")
        self.port = prompt_str(f"  COM口 [当前:{self.port}]: ", self.port)
        self.motor_id = prompt_int(f"  电机ID [当前:{self.motor_id}]: ", self.motor_id)
        print(f"✓ 配置已更新: 端口={self.port}, 电机ID={self.motor_id}")
    
    def ensure_connected(self) -> bool:
        """确保已连接"""
        if not self.connected or not self.controller:
            print("\n⚠️  请先连接电机（菜单1）")
            return False
        return True
    
    def read_version(self):
        """读取版本"""
        if not self.ensure_connected():
            return
        
        print("\n读取版本信息...")
        try:
            version = self.controller.get_version()
            print(f"✓ 固件版本: {version['firmware']}")
            print(f"✓ 硬件版本: {version['hardware']}")
        except Exception as e:
            print(f"✗ 读取失败: {e}")
    
    def read_status(self):
        """读取状态"""
        if not self.ensure_connected():
            return
        
        print("\n读取电机状态...")
        try:
            status = self.controller.get_motor_status()
            print(f"✓ 使能状态: {status['enabled']}")
            print(f"✓ 到位状态: {status['in_position']}")
        except Exception as e:
            print(f"✗ 读取失败: {e}")
    
    def read_position(self):
        """读取位置"""
        if not self.ensure_connected():
            return
        
        print("\n读取位置信息...")
        try:
            pos = self.controller.get_position()
            print(f"✓ 当前位置: {pos:.2f}度")
        except Exception as e:
            print(f"✗ 读取失败: {e}")
    
    def read_speed(self):
        """读取速度"""
        if not self.ensure_connected():
            return
        
        print("\n读取速度信息...")
        try:
            speed = self.controller.get_speed()
            print(f"✓ 当前速度: {speed:.2f} RPM")
        except Exception as e:
            print(f"✗ 读取失败: {e}")
    
    def enable_motor(self):
        """使能电机"""
        if not self.ensure_connected():
            return
        
        print("\n使能电机...")
        try:
            self.controller.enable()
            print("✓ 电机已使能")
        except Exception as e:
            print(f"✗ 使能失败: {e}")
    
    def disable_motor(self):
        """失能电机"""
        if not self.ensure_connected():
            return
        
        print("\n失能电机...")
        try:
            self.controller.disable()
            print("✓ 电机已失能")
        except Exception as e:
            print(f"✗ 失能失败: {e}")
    
    def stop_motor(self):
        """停止电机"""
        if not self.ensure_connected():
            return
        
        print("\n停止电机...")
        try:
            self.controller.stop()
            print("✓ 电机已停止")
        except Exception as e:
            print(f"✗ 停止失败: {e}")
    
    def position_control(self):
        """位置控制"""
        if not self.ensure_connected():
            return
        
        print("\n位置控制:")
        target = prompt_float("  目标位置(度) [默认:90]: ", 90.0)
        speed = prompt_float("  运动速度(RPM) [默认:500]: ", 500.0)
        is_absolute = prompt_str("  绝对位置? (y/N) [默认:N]: ", "n").lower() in ('y', 'yes')
        
        print(f"\n移动到 {target:.1f}度 (速度={speed:.0f}RPM, "
              f"{'绝对' if is_absolute else '相对'}位置)...")
        try:
            self.controller.move_to_position(target, speed, is_absolute)
            print("✓ 位置命令已发送")
            
            # 等待到位
            wait = prompt_str("\n是否等待到位? (Y/n) [默认:Y]: ", "y").lower()
            if wait in ('y', 'yes', ''):
                print("\n等待到位...")
                timeout = 20.0
                if self.controller.wait_for_position(timeout):
                    final_pos = self.controller.get_position()
                    print(f"✓ 到位成功！最终位置: {final_pos:.2f}度")
                else:
                    print("⚠️  等待超时")
        except Exception as e:
            print(f"✗ 位置控制失败: {e}")
    
    def speed_control(self):
        """速度控制"""
        if not self.ensure_connected():
            return
        
        print("\n速度控制:")
        speed = prompt_float("  目标速度(RPM) [默认:100]: ", 100.0)
        duration = prompt_float("  运行时间(秒) [默认:5]: ", 5.0)
        
        print(f"\n以 {speed:.0f}RPM 运行 {duration:.1f}秒...")
        try:
            self.controller.set_speed(speed)
            print("✓ 速度命令已发送")
            
            # 监控
            print("\n监控运行...")
            start = time.time()
            while time.time() - start < duration:
                curr_speed = self.controller.get_speed()
                elapsed = time.time() - start
                print(f"  [{elapsed:.1f}s] 当前速度: {curr_speed:.1f} RPM")
                time.sleep(1.0)
            
            # 停止
            print("\n停止电机...")
            self.controller.stop()
            print("✓ 已停止")
        except Exception as e:
            print(f"✗ 速度控制失败: {e}")
    
    def homing(self):
        """回零"""
        if not self.ensure_connected():
            return
        
        print("\n回零操作:")
        print("  0. 单圈就近回零")
        print("  4. 回到绝对零点 (推荐)")
        mode = prompt_int("  选择回零模式 [默认:4]: ", 4)
        
        print(f"\n执行回零（模式{mode}）...")
        try:
            self.controller.trigger_homing(mode)
            print("✓ 回零命令已发送")
            
            # 等待回零完成
            wait = prompt_str("\n是否等待回零完成? (Y/n) [默认:Y]: ", "y").lower()
            if wait in ('y', 'yes', ''):
                print("\n等待回零...")
                # 简化版：轮询到位状态
                for i in range(30):
                    time.sleep(1)
                    try:
                        status = self.controller.get_motor_status()
                        pos = self.controller.get_position()
                        print(f"  [{i+1}s] 位置: {pos:.2f}度, 到位: {status['in_position']}")
                        if status['in_position']:
                            print("✓ 回零完成")
                            break
                    except:
                        pass
                else:
                    print("⚠️  等待超时")
        except Exception as e:
            print(f"✗ 回零失败: {e}")
    
    def full_test(self):
        """完整控制流程测试"""
        if not self.ensure_connected():
            return
        
        print("\n" + "="*70)
        print("完整控制流程测试")
        print("="*70)
        
        try:
            # 1. 读取初始状态
            print("\n【1/6】读取初始状态...")
            version = self.controller.get_version()
            status = self.controller.get_motor_status()
            pos = self.controller.get_position()
            print(f"  固件: {version['firmware']}")
            print(f"  使能: {status['enabled']}, 到位: {status['in_position']}")
            print(f"  位置: {pos:.2f}度")
            
            # 2. 使能（如果未使能）
            if not status['enabled']:
                print("\n【2/6】使能电机...")
                self.controller.enable()
                print("  ✓ 已使能")
            else:
                print("\n【2/6】电机已使能，跳过")
            
            # 3. 移动到90度
            print("\n【3/6】位置控制：移动到90度（绝对位置）...")
            self.controller.move_to_position(90, speed=500, is_absolute=True)
            print("  ✓ 命令已发送")
            if self.controller.wait_for_position(15.0):
                pos = self.controller.get_position()
                print(f"  ✓ 到位: {pos:.2f}度")
            else:
                print("  ⚠️  超时")
            
            # 4. 移动回0度
            print("\n【4/6】位置控制：移动回0度...")
            self.controller.move_to_position(0, speed=500, is_absolute=True)
            print("  ✓ 命令已发送")
            if self.controller.wait_for_position(15.0):
                pos = self.controller.get_position()
                print(f"  ✓ 到位: {pos:.2f}度")
            else:
                print("  ⚠️  超时")
            
            # 5. 速度控制
            print("\n【5/6】速度控制：100RPM运行3秒...")
            self.controller.set_speed(100)
            print("  ✓ 命令已发送")
            time.sleep(3.0)
            self.controller.stop()
            print("  ✓ 已停止")
            
            # 6. 失能
            print("\n【6/6】失能电机...")
            self.controller.disable()
            print("  ✓ 已失能")
            
            print("\n" + "="*70)
            print("✓ 完整测试完成！")
            print("="*70)
            
        except Exception as e:
            print(f"\n✗ 测试失败: {e}")
            import traceback
            traceback.print_exc()
    
    def run(self):
        """运行主循环"""
        while True:
            self.show_menu()
            choice = prompt_str("\n请选择操作 (0-14): ", "")
            
            if choice == "0":
                if self.connected:
                    self.disconnect_motor()
                print("\n再见！")
                break
            elif choice == "1":
                self.connect_motor()
            elif choice == "2":
                self.disconnect_motor()
            elif choice == "3":
                self.modify_config()
            elif choice == "4":
                self.read_version()
            elif choice == "5":
                self.read_status()
            elif choice == "6":
                self.read_position()
            elif choice == "7":
                self.read_speed()
            elif choice == "8":
                self.enable_motor()
            elif choice == "9":
                self.disable_motor()
            elif choice == "10":
                self.stop_motor()
            elif choice == "11":
                self.position_control()
            elif choice == "12":
                self.speed_control()
            elif choice == "13":
                self.homing()
            elif choice == "14":
                self.full_test()
            else:
                print("\n⚠️  无效选择")
            
            input("\n按回车键继续...")


def main():
    tester = ControlSDKUcpTester()
    tester.run()


if __name__ == "__main__":
    main()

