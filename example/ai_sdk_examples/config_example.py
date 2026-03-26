#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI SDK 配置管理示例
演示如何使用YAML配置文件
"""

import os
import sys

# 将项目根目录添加到 python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import yaml
from Embodied_SDK import AISDK

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def basic_config_example():
    """基础配置使用示例"""
    print("\n=== 基础配置使用示例 ===")
    
    # 使用默认配置文件
    sdk = AISDK()
    
    # 获取配置信息
    print("📋 当前配置信息:")
    print(f"- 默认历史记录数: {sdk.get_config('session.default_max_history')}")
    print(f"- 最大会话数: {sdk.get_config('session.max_sessions')}")
    print(f"- 自动清理: {sdk.get_config('session.auto_cleanup')}")
    print(f"- 请求超时: {sdk.get_config('request.timeout')}")
    print(f"- 调试模式: {sdk.get_config('development.debug')}")
    print()
    
    # 获取厂商配置
    print("🏭 厂商配置:")
    alibaba_models = sdk.get_config('models.alibaba.llm')
    deepseek_models = sdk.get_config('models.deepseek.llm')
    print(f"- 阿里云模型: {alibaba_models}")
    print(f"- DeepSeek模型: {deepseek_models}")
    print()

def custom_config_example():
    """自定义配置示例"""
    print("\n=== 自定义配置示例 ===")
    
    # 创建自定义配置文件
    custom_config = {
        'api_keys': {
            'alibaba': '${ALIBABA_API_KEY:}',
            'deepseek': '${DEEPSEEK_API_KEY:}'
        },
        'session': {
            'default_max_history': 15,  # 自定义默认历史记录数
            'max_sessions': 50,         # 自定义最大会话数
            'auto_cleanup': True,
            'cleanup_interval': 1800    # 30分钟清理一次
        },
        'request': {
            'timeout': 30,              # 自定义超时时间
            'max_retries': 5
        },
        'development': {
            'debug': True,              # 启用调试模式
            'log_requests': True
        }
    }
    
    # 保存自定义配置
    config_path = 'custom_config.yaml'
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(custom_config, f, default_flow_style=False, allow_unicode=True, indent=2)
    
    print(f"✅ 创建自定义配置文件: {config_path}")
    
    # 使用自定义配置
    sdk = AISDK(config_path=config_path)
    
    print("📋 自定义配置信息:")
    print(f"- 默认历史记录数: {sdk.get_config('session.default_max_history')}")
    print(f"- 最大会话数: {sdk.get_config('session.max_sessions')}")
    print(f"- 请求超时: {sdk.get_config('request.timeout')}")
    print(f"- 调试模式: {sdk.get_config('development.debug')}")
    print()
    
    # 清理临时文件
    if os.path.exists(config_path):
        os.remove(config_path)
    print(f"🗑️ 清理临时配置文件: {config_path}\n")

def runtime_config_example():
    """运行时配置修改示例"""
    print("\n=== 运行时配置修改示例 ===")
    
    sdk = AISDK()
    
    # 查看原始配置
    print("📋 原始配置:")
    print(f"- 默认历史记录数: {sdk.get_config('session.default_max_history')}")
    print(f"- 调试模式: {sdk.get_config('development.debug')}")
    
    # 运行时修改配置
    print("\n🔧 修改配置...")
    sdk.set_config('session.default_max_history', 30)
    sdk.set_config('development.debug', True)
    
    # 查看修改后的配置
    print("📋 修改后配置:")
    print(f"- 默认历史记录数: {sdk.get_config('session.default_max_history')}")
    print(f"- 调试模式: {sdk.get_config('development.debug')}")
    
    # 保存配置到文件
    temp_config_path = 'temp_config.yaml'
    sdk.save_config(temp_config_path)
    print(f"💾 配置已保存到: {temp_config_path}")
    
    # 验证保存的配置
    with open(temp_config_path, 'r', encoding='utf-8') as f:
        saved_config = yaml.safe_load(f)
    
    print(f"✅ 验证保存的配置:")
    print(f"- 默认历史记录数: {saved_config['session']['default_max_history']}")
    print(f"- 调试模式: {saved_config['development']['debug']}")
    
    # 清理临时文件
    if os.path.exists(temp_config_path):
        os.remove(temp_config_path)
    print(f"🗑️ 清理临时配置文件\n")

def config_validation_example():
    """配置验证示例"""
    print("\n=== 配置验证示例 ===")
    
    sdk = AISDK()
    
    # 验证当前配置
    validation_result = sdk.config.validate_config()
    
    print("🔍 配置验证结果:")
    if validation_result['errors']:
        print("❌ 错误:")
        for error in validation_result['errors']:
            print(f"   - {error}")
    else:
        print("✅ 没有配置错误")
    
    if validation_result['warnings']:
        print("⚠️ 警告:")
        for warning in validation_result['warnings']:
            print(f"   - {warning}")
    else:
        print("✅ 没有配置警告")
    print()

def session_config_example():
    """会话配置示例"""
    print("\n=== 会话配置示例 ===")
    
    sdk = AISDK()
    
    # 查看会话统计信息
    stats = sdk.get_session_stats()
    print("📊 会话管理器统计:")
    for key, value in stats.items():
        print(f"- {key}: {value}")
    print()
    
    # 创建会话（使用配置中的默认值）
    session1 = sdk.create_session(session_id="config_demo_1")
    print(f"✅ 创建会话1: {session1.session_id}")
    print(f"   最大历史记录: {session1.max_history}")
    
    # 创建会话（覆盖默认值）
    session2 = sdk.create_session(
        session_id="config_demo_2", 
        max_history=10  # 覆盖配置中的默认值
    )
    print(f"✅ 创建会话2: {session2.session_id}")
    print(f"   最大历史记录: {session2.max_history}")
    
    # 查看更新后的统计信息
    updated_stats = sdk.get_session_stats()
    print(f"\n📊 更新后的会话数量: {updated_stats['total_sessions']}")

def environment_variable_example():
    """环境变量配置示例"""
    print("\n=== 环境变量配置示例 ===")
    
    # 设置测试环境变量
    os.environ['TEST_API_KEY'] = 'test_key_123'
    os.environ['TEST_TIMEOUT'] = '45'
    
    # 创建包含环境变量的配置
    config_with_env = {
        'api_keys': {
            'test_provider': '${TEST_API_KEY:default_key}'
        },
        'request': {
            'timeout': '${TEST_TIMEOUT:60}'
        },
        'custom_setting': '${NON_EXISTENT_VAR:default_value}'
    }
    
    # 保存配置文件
    env_config_path = 'env_config.yaml'
    with open(env_config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config_with_env, f, default_flow_style=False, allow_unicode=True, indent=2)
    
    print(f"✅ 创建环境变量配置文件: {env_config_path}")
    
    # 使用包含环境变量的配置
    sdk = AISDK(config_path=env_config_path)
    
    print("🌍 环境变量替换结果:")
    print(f"- test_provider API密钥: {sdk.get_config('api_keys.test_provider')}")
    print(f"- 请求超时: {sdk.get_config('request.timeout')}")
    print(f"- 自定义设置: {sdk.get_config('custom_setting')}")
    
    # 清理
    if os.path.exists(env_config_path):
        os.remove(env_config_path)
    if 'TEST_API_KEY' in os.environ: del os.environ['TEST_API_KEY']
    if 'TEST_TIMEOUT' in os.environ: del os.environ['TEST_TIMEOUT']
    print(f"🗑️ 清理环境变量和临时文件\n")

def main():
    """主函数"""
    while True:
        clear_screen()
        print("=" * 60)
        print(" 🛠️  AI SDK 配置管理演示")
        print("=" * 60)
        print("  1. 基础配置读取 (Basic Config)")
        print("  2. 自定义配置文件 (Custom Config File)")
        print("  3. 运行时动态修改 (Runtime Modification)")
        print("  4. 配置合法性验证 (Validation)")
        print("  5. 会话配置演示 (Session Config)")
        print("  6. 环境变量替换 (Environment Variables)")
        print("  0. 退出 (Exit)")
        print("=" * 60)
        
        choice = input("\n请输入选择 (0-6): ").strip()
        
        if choice == '0':
            print("👋 再见")
            break
        elif choice == '1':
            basic_config_example()
        elif choice == '2':
            custom_config_example()
        elif choice == '3':
            runtime_config_example()
        elif choice == '4':
            config_validation_example()
        elif choice == '5':
            session_config_example()
        elif choice == '6':
            environment_variable_example()
        else:
            print("❌ 无效选择")
            
        input("\n按 Enter 键继续...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n程序已终止")
