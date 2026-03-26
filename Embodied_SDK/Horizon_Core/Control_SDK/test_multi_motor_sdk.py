# -*- coding: utf-8 -*-
"""
Control_SDK 多电机同步测试工具（交互式菜单）
测试通过 OmniCAN 的多电机同步控制
"""

import sys
import os
import time
from typing import List, Dict

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


class MultiMotorSDKTester:
    """Control_SDK 多电机同步测试器"""
    
    def __init__(self):
        self.controllers: Dict[int, ZDTMotorController] = {}
        self.port = "COM31"
        self.motor_ids: List[int] = []
        self.connected = False
        
        print("="*70)
        print(" Control_SDK 多电机同步测试工具")
        print(" (Y42聚合模式 - 一次通信高效同步)")
        print("="*70)
    
    def show_menu(self):
        """显示菜单"""
        print("\n" + "="*70)
        print("多电机同步测试菜单 (Y42聚合模式)")
        print("="*70)
        ids_str = ",".join(str(id) for id in self.motor_ids) if self.motor_ids else "无"
        print(f"当前配置: 端口={self.port}, 电机ID=[{ids_str}], "
              f"连接={'是' if self.connected else '否'}")
        print()
        print("连接管理:")
        print("  1. 连接多电机")
        print("  2. 断开连接")
        print("  3. 修改配置")
        print()
        print("状态读取:")
        print("  4. 读取所有电机状态")
        print("  5. 读取所有电机位置")
        print()
        print("基础控制:")
        print("  6. 使能所有电机 (Y42)")
        print("  7. 失能所有电机 (Y42)")
        print("  8. 停止所有电机")
        print()
        print("同步运动:")
        print("  9. 多机同步位置控制 (Y42)")
        print("  10. 多机同步回零")
        print()
        print("综合测试:")
        print("  11. 完整同步控制流程测试")
        print()
        print("  0. 退出")
        print("="*70)
    
    def connect_motors(self):
        """连接多电机"""
        if self.connected:
            print("\n⚠️  已连接，请先断开")
            return
        
        if not self.motor_ids:
            print("\n⚠️  请先配置电机ID（菜单3）")
            return
        
        print(f"\n连接多电机 (ID={self.motor_ids})...")
        try:
            # 创建第一个控制器并连接
            first_id = self.motor_ids[0]
            first_ctrl = ZDTMotorController(
                motor_id=first_id,
                port=self.port,
                baudrate=115200
            )
            first_ctrl.connect()
            self.controllers[first_id] = first_ctrl
            
            # 其他控制器共享同一个UCP client
            for motor_id in self.motor_ids[1:]:
                ctrl = ZDTMotorController(
                    motor_id=motor_id,
                    port=self.port,
                    baudrate=115200
                )
                ctrl.client = first_ctrl.client  # 共享连接
                self.controllers[motor_id] = ctrl
            
            self.connected = True
            print(f"✓ 连接成功 ({len(self.motor_ids)}个电机)")
        except Exception as e:
            print(f"✗ 连接失败: {e}")
            self.controllers = {}
    
    def disconnect_motors(self):
        """断开连接"""
        if not self.connected:
            print("\n⚠️  未连接")
            return
        
        print("\n断开连接...")
        if self.controllers:
            # 只需断开第一个（其他共享连接）
            first_ctrl = next(iter(self.controllers.values()))
            first_ctrl.disconnect()
        self.controllers = {}
        self.connected = False
        print("✓ 已断开")
    
    def modify_config(self):
        """修改配置"""
        if self.connected:
            print("\n⚠️  请先断开连接")
            return
        
        print("\n修改配置:")
        self.port = prompt_str(f"  COM口 [当前:{self.port}]: ", self.port)
        ids_input = prompt_str("  电机ID列表(逗号分隔) [当前:" + 
                              ",".join(str(id) for id in self.motor_ids) + "]: ", "")
        if ids_input:
            self.motor_ids = [int(id.strip()) for id in ids_input.split(',') if id.strip()]
        print(f"✓ 配置已更新: 端口={self.port}, 电机ID={self.motor_ids}")
    
    def ensure_connected(self) -> bool:
        """确保已连接"""
        if not self.connected or not self.controllers:
            print("\n⚠️  请先连接电机（菜单1）")
            return False
        return True
    
    def read_all_status(self):
        """读取所有电机状态"""
        if not self.ensure_connected():
            return
        
        print("\n读取所有电机状态...")
        for motor_id, ctrl in self.controllers.items():
            try:
                status = ctrl.get_motor_status()
                print(f"  电机{motor_id}: 使能={status['enabled']}, "
                      f"到位={status['in_position']}")
            except Exception as e:
                print(f"  电机{motor_id}: ✗ {e}")
    
    def read_all_positions(self):
        """读取所有电机位置"""
        if not self.ensure_connected():
            return
        
        print("\n读取所有电机位置...")
        for motor_id, ctrl in self.controllers.items():
            try:
                pos = ctrl.get_position()
                print(f"  电机{motor_id}: {pos:.2f}度")
            except Exception as e:
                print(f"  电机{motor_id}: ✗ {e}")
    
    def enable_all(self):
        """使能所有电机（Y42聚合模式）"""
        if not self.ensure_connected():
            return
        
        print(f"\n使能所有电机 (Y42聚合模式)...")
        
        try:
            ZDTMotorController.y42_sync_enable(self.controllers, enabled=True)
            print(f"  ✓ Y42命令已发送，{len(self.controllers)}个电机同时使能")
        except Exception as e:
            print(f"  ✗ 失败: {e}")
    
    def disable_all(self):
        """失能所有电机（Y42聚合模式）"""
        if not self.ensure_connected():
            return
        
        print(f"\n失能所有电机 (Y42聚合模式)...")
        
        try:
            ZDTMotorController.y42_sync_enable(self.controllers, enabled=False)
            print(f"  ✓ Y42命令已发送，{len(self.controllers)}个电机同时失能")
        except Exception as e:
            print(f"  ✗ 失败: {e}")
    
    def stop_all(self):
        """停止所有电机"""
        if not self.ensure_connected():
            return
        
        print("\n停止所有电机...")
        for motor_id, ctrl in self.controllers.items():
            try:
                ctrl.stop()
                print(f"  电机{motor_id}: ✓ 已停止")
            except Exception as e:
                print(f"  电机{motor_id}: ✗ {e}")
    
    def sync_position_control(self):
        """同步位置控制（Y42聚合模式）"""
        if not self.ensure_connected():
            return
        
        print(f"\n多机同步位置控制 (Y42聚合模式):")
        print("  为每个电机设置目标位置...")
        
        targets = {}
        for motor_id in self.motor_ids:
            target = prompt_float(f"    电机{motor_id}目标位置(度) [默认:90]: ", 90.0)
            targets[motor_id] = target
        
        speed = prompt_float("  运动速度(RPM) [默认:500]: ", 500.0)
        
        try:
            # Y42聚合模式：一次通信完成
            print(f"\n发送Y42聚合命令...")
            ZDTMotorController.y42_sync_position(
                self.controllers, targets, speed, is_absolute=True
            )
            print("✓ Y42命令已发送，所有电机同时运动")
        except Exception as e:
            print(f"✗ 同步失败: {e}")
            return
        
        # 监控
        print("\n监控运动...")
        for i in range(20):
            time.sleep(1)
            status_line = f"  [{i+1}s]"
            all_in_pos = True
            
            for motor_id in self.motor_ids:
                try:
                    ctrl = self.controllers[motor_id]
                    status = ctrl.get_motor_status()
                    pos = ctrl.get_position()
                    target = targets[motor_id]
                    
                    if not status['in_position']:
                        all_in_pos = False
                    
                    status_str = "[到位]" if status['in_position'] else "      "
                    status_line += f" | M{motor_id}:{pos:6.1f}°→{target:4.0f}° {status_str}"
                except:
                    status_line += f" | M{motor_id}:?"
                    all_in_pos = False
            
            print(status_line)
            
            if all_in_pos:
                print("\n✓ 所有电机已到位")
                break
        else:
            print("\n⚠️  监控超时")
    
    def sync_homing(self):
        """同步回零"""
        if not self.ensure_connected():
            return
        
        print("\n多机同步回零:")
        print("  0. 单圈就近回零")
        print("  4. 回到绝对零点 (推荐)")
        mode = prompt_int("  选择回零模式 [默认:4]: ", 4)
        
        # 约束：本项目多机同步统一使用 Y42（禁止 Pre-load + SYNC_MOTION 触发）
        print(f"\n发送 Y42 同步回零命令（模式{mode}）...")
        try:
            from Control_Core.motor_controller_ucp_simple import ZDTMotorController
            targets = {mid: float(mode) for mid in self.controllers.keys()}  # 占位，实际回零不需要 targets
            # 这里直接构建回零子命令并用 multi_motor_command 下发
            first_ctrl = next(iter(self.controllers.values()))
            commands = []
            for mid, ctrl in self.controllers.items():
                func_body = ctrl.command_builder.homing_mode(mode)
                commands.append(bytes([mid]) + func_body)
            first_ctrl.multi_motor_command(commands, expected_ack_motor_id=1, wait_ack=False, mode='control')
            print("✓ Y42 已下发，所有电机开始回零")
        except Exception as e:
            print(f"✗ 发送失败: {e}")
            return
        
        # 监控
        print("\n监控回零...")
        for i in range(30):
            time.sleep(1)
            status_line = f"  [{i+1}s]"
            all_done = True
            
            for motor_id in self.motor_ids:
                try:
                    ctrl = self.controllers[motor_id]
                    status = ctrl.get_motor_status()
                    pos = ctrl.get_position()
                    
                    if not status['in_position']:
                        all_done = False
                    
                    status_str = "[完成]" if status['in_position'] else "      "
                    status_line += f" | M{motor_id}:{pos:7.1f}° {status_str}"
                except:
                    status_line += f" | M{motor_id}:?"
                    all_done = False
            
            print(status_line)
            
            if all_done:
                print("\n✓ 所有电机回零完成")
                break
        else:
            print("\n⚠️  监控超时")
    
    def full_sync_test(self):
        """完整同步控制流程测试"""
        if not self.ensure_connected():
            return
        
        print("\n" + "="*70)
        print("完整同步控制流程测试")
        print("="*70)
        
        try:
            # 1. 读取初始状态
            print("\n【1/5】读取初始状态...")
            for motor_id, ctrl in self.controllers.items():
                status = ctrl.get_motor_status()
                pos = ctrl.get_position()
                print(f"  电机{motor_id}: 使能={status['enabled']}, 位置={pos:.2f}度")
            
            # 2. 使能所有电机
            print("\n【2/5】使能所有电机...")
            for motor_id, ctrl in self.controllers.items():
                if not ctrl.get_motor_status()['enabled']:
                    ctrl.enable()
                    print(f"  电机{motor_id}: ✓ 已使能")
                else:
                    print(f"  电机{motor_id}: 已使能，跳过")
            
            # 3. 同步移动到90/-90度（Y42）
            print("\n【3/5】同步位置控制（Y42）...")
            targets = {}
            commands = []
            for i, motor_id in enumerate(self.motor_ids):
                target = 90.0 if i % 2 == 0 else -90.0
                targets[motor_id] = target
                ctrl = self.controllers[motor_id]
                func_body = ctrl.command_builder.position_mode_direct(position=target, speed=500, is_absolute=True, multi_sync=False)
                commands.append(bytes([motor_id]) + func_body)
                print(f"  电机{motor_id}: target={target:.0f}度")
            first_ctrl = next(iter(self.controllers.values()))
            first_ctrl.multi_motor_command(commands, expected_ack_motor_id=1, wait_ack=False, mode='control')
            print("  ✓ Y42 已下发")
            
            # 等待到位
            print("\n  等待到位...")
            for i in range(15):
                time.sleep(1)
                all_in_pos = True
                for motor_id in self.motor_ids:
                    if not self.controllers[motor_id].is_in_position():
                        all_in_pos = False
                        break
                if all_in_pos:
                    print(f"  ✓ 全部到位 ({i+1}秒)")
                    break
            
            # 4. 同步回零（Y42：回到0度）
            print("\n【4/5】同步回零（Y42）...")
            commands = []
            for motor_id, ctrl in self.controllers.items():
                func_body = ctrl.command_builder.position_mode_direct(position=0, speed=500, is_absolute=True, multi_sync=False)
                commands.append(bytes([motor_id]) + func_body)
                print(f"  电机{motor_id}: target=0度")
            first_ctrl.multi_motor_command(commands, expected_ack_motor_id=1, wait_ack=False, mode='control')
            print("  ✓ Y42 已下发")
            time.sleep(10)  # 等待回零
            
            # 5. 失能
            print("\n【5/5】失能所有电机...")
            for motor_id, ctrl in self.controllers.items():
                ctrl.disable()
                print(f"  电机{motor_id}: ✓ 已失能")
            
            print("\n" + "="*70)
            print("✓ 完整同步测试完成！")
            print("="*70)
            
        except Exception as e:
            print(f"\n✗ 测试失败: {e}")
            import traceback
            traceback.print_exc()
    
    def run(self):
        """运行主循环"""
        while True:
            self.show_menu()
            choice = prompt_str("\n请选择操作 (0-11): ", "")
            
            if choice == "0":
                if self.connected:
                    self.disconnect_motors()
                print("\n再见！")
                break
            elif choice == "1":
                self.connect_motors()
            elif choice == "2":
                self.disconnect_motors()
            elif choice == "3":
                self.modify_config()
            elif choice == "4":
                self.read_all_status()
            elif choice == "5":
                self.read_all_positions()
            elif choice == "6":
                self.enable_all()
            elif choice == "7":
                self.disable_all()
            elif choice == "8":
                self.stop_all()
            elif choice == "9":
                self.sync_position_control()
            elif choice == "10":
                self.sync_homing()
            elif choice == "11":
                self.full_sync_test()
            else:
                print("\n⚠️  无效选择")
            
            input("\n按回车键继续...")


def main():
    tester = MultiMotorSDKTester()
    tester.run()


if __name__ == "__main__":
    main()

