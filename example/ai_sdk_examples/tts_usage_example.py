#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TTS功能演示程序
展示AI SDK的语音合成功能
"""

import asyncio
import time
import os
import sys

# 将项目根目录添加到 python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from Embodied_SDK import AISDK

# -----------------------------------------------------------------------------


def main():
    """主函数"""
    print("🔊 AI SDK - TTS语音合成功能演示")
    print("=" * 50)
    
    # 初始化SDK
    try:
        sdk = AISDK()
        print("✅ SDK初始化成功")
    except Exception as e:
        print(f"❌ SDK初始化失败: {e}")
        return
    
    while True:
        print("\n📋 请选择功能:")
        print("1. 文本转语音保存文件")
        print("2. 文本转语音扬声器播放")
        print("3. 流式文本转语音")
        print("4. LLM + TTS 智能对话")
        print("5. 异步语音合成")
        print("6. 模型和音色测试")
        print("0. 退出")
        
        choice = input("\n请输入选择 (0-6): ").strip()
        
        if choice == '0':
            print("👋 再见！")
            break
        elif choice == '1':
            demo_text_to_file(sdk)
        elif choice == '2':
            demo_text_to_speaker(sdk)
        elif choice == '3':
            demo_stream_tts(sdk)
        elif choice == '4':
            demo_llm_tts(sdk)
        elif choice == '5':
            asyncio.run(demo_async_tts(sdk))
        elif choice == '6':
            demo_model_voice_test(sdk)
        else:
            print("❌ 无效选择，请重新输入")


def demo_text_to_file(sdk):
    """演示文本转语音保存文件"""
    print("\n🎵 文本转语音保存文件演示")
    print("-" * 30)
    
    text = input("请输入要合成的文本: ").strip()
    if not text:
        text = "你好，这是AI SDK的语音合成功能演示。"
    
    output_file = input("请输入输出文件名 (默认: output.mp3): ").strip()
    if not output_file:
        output_file = "output.mp3"
    
    print(f"\n🔄 正在合成语音: {text}")
    
    try:
        # 优化调用：省略 provider (默认alibaba)，将 text 作为第一个参数
        result = sdk.tts(
            text,
            mode="file",
            output_file=output_file,
            model="cosyvoice-v1",
            voice="longxiaochun"
        )
        
        if result['success']:
            print(f"✅ 语音合成成功!")
            print(f"📁 输出文件: {result['output_file']}")
            print(f"🎭 使用模型: {result['model']}")
            print(f"🎤 使用音色: {result['voice']}")
            print(f"📝 文本长度: {result['text_length']} 字符")
            print(f"⏱️ 处理时间: {result['processing_time']:.2f} 秒")
        else:
            print(f"❌ 语音合成失败: {result['error']}")
    
    except Exception as e:
        print(f"❌ 合成过程出错: {e}")


def demo_text_to_speaker(sdk):
    """演示文本转语音扬声器播放"""
    print("\n🔊 文本转语音扬声器播放演示")
    print("-" * 30)
    
    text = input("请输入要播放的文本: ").strip()
    if not text:
        text = "你好，这是通过扬声器播放的语音合成演示。"
    
    print(f"\n🔄 正在合成并播放语音: {text}")
    
    try:
        # 优化调用：省略 provider，使用默认参数
        result = sdk.tts(
            text,
            mode="speaker",
            model="sambert-zhichu-v1",  # 使用Sambert模型，支持实时播放
            sample_rate=48000
        )
        
        if result['success']:
            print(f"✅ 语音播放完成!")
            print(f"🎭 使用模型: {result['model']}")
            print(f"🎤 使用音色: {result['voice']}")
            print(f"📝 文本长度: {result['text_length']} 字符")
            print(f"⏱️ 处理时间: {result['processing_time']:.2f} 秒")
        else:
            print(f"❌ 语音播放失败: {result['error']}")
    
    except Exception as e:
        print(f"❌ 播放过程出错: {e}")


def demo_stream_tts(sdk):
    """演示流式文本转语音"""
    print("\n🌊 流式文本转语音演示")
    print("-" * 30)
    
    # 模拟流式文本输入
    text_chunks = [
        "欢迎使用",
        "AI SDK",
        "的流式",
        "语音合成",
        "功能。",
        "这可以配合",
        "大语言模型",
        "的流式输出",
        "使用。"
    ]
    
    print("🔄 开始流式语音合成...")
    
    try:
        # 优化调用：text_chunks 作为第一个参数
        for i, result in enumerate(sdk.tts(
            text_chunks,
            mode="stream",
            model="cosyvoice-v1",
            voice="longxiaochun"
        )):
            if result['success']:
                print(f"✅ 第{i+1}块合成完成: {result['text_chunk']}")
            else:
                print(f"❌ 第{i+1}块合成失败: {result['error']}")
        
        print("🎉 流式语音合成完成!")
    
    except Exception as e:
        print(f"❌ 流式合成过程出错: {e}")


def demo_llm_tts(sdk):
    """演示LLM + TTS智能对话"""
    print("\n🤖 LLM + TTS 智能对话演示")
    print("-" * 30)
    
    question = input("请输入你的问题: ").strip()
    if not question:
        question = "请介绍一下人工智能的发展历史"
    
    print("\n" + "="*50)
    print("🚀 开始实时智能对话（边生成边播放语音）...")
    
    try:
        # 使用smart_chat一键完成LLM+TTS，启用实时模式
        result = sdk.smart_chat(
            prompt=question,
            stream_chat=True,              # 🔑 启用流式输出
            tts_mode="speaker",            # 🔑 扬声器播放模式  
            llm_model="qwen-turbo",
            tts_model="cosyvoice-v1",
            temperature=0.7,
            voice="longxiaochun"
        )
        
        if result['success']:
            print(f"\n✅ 实时智能对话完成!")
            print(f"📝 AI回答: {result['answer'][:100]}...")
            print(f"🤖 LLM: {result['llm_provider']}/{result['llm_model']}")
            print(f"🔊 TTS: {result['tts_provider']}/{result['tts_model']}")
            print(f"🎭 模式: {result['tts_mode']}")
        else:
            print(f"❌ 智能对话失败: {result['error']}")
    
    except Exception as e:
        print(f"❌ 对话过程出错: {e}")
    
    print("="*50)


async def demo_async_tts(sdk):
    """演示异步语音合成"""
    print("\n⚡ 异步语音合成演示")
    print("-" * 30)
    
    texts = [
        "这是第一段文本",
        "这是第二段文本", 
        "这是第三段文本"
    ]
    
    print("🔄 开始并发异步语音合成...")
    
    try:
        # 并发执行多个语音合成任务
        tasks = []
        for i, text in enumerate(texts):
            # 优化调用：支持 async_mode
            task = sdk.tts(
                text,
                mode="file",
                output_file=f"async_output_{i+1}.mp3",
                model="cosyvoice-v1",
                voice="longxiaochun",
                async_mode=True
            )
            tasks.append(task)
        
        # 等待所有任务完成
        results = await asyncio.gather(*tasks)
        
        for i, result in enumerate(results):
            if result['success']:
                print(f"✅ 任务{i+1}完成: {result['output_file']}")
            else:
                print(f"❌ 任务{i+1}失败: {result['error']}")
        
        print("🎉 所有异步任务完成!")
    
    except Exception as e:
        print(f"❌ 异步合成过程出错: {e}")


def demo_model_voice_test(sdk):
    """演示不同模型和音色测试"""
    print("\n🎭 模型和音色测试演示")
    print("-" * 30)
    
    test_text = "你好，我是AI语音助手。"
    
    # 测试配置
    test_configs = [
        {
            "name": "CosyVoice - 龙小春",
            "model": "cosyvoice-v1",
            "voice": "longxiaochun"
        },
        {
            "name": "Sambert - 知楚",
            "model": "sambert-zhichu-v1",
            "voice": None  # Sambert模型音色在模型名中
        }
    ]
    
    for i, config in enumerate(test_configs):
        print(f"\n🎤 测试 {i+1}: {config['name']}")
        
        try:
            # 优化调用
            kwargs = {
                "mode": "file",
                "text": test_text,
                "output_file": f"test_{i+1}_{config['model']}.mp3",
                "model": config['model']
            }
            
            if config['voice']:
                kwargs['voice'] = config['voice']
            
            result = sdk.tts(**kwargs)
            
            if result['success']:
                print(f"✅ 合成成功: {result['output_file']}")
                print(f"⏱️ 处理时间: {result['processing_time']:.2f} 秒")
            else:
                print(f"❌ 合成失败: {result['error']}")
        
        except Exception as e:
            print(f"❌ 测试过程出错: {e}")


if __name__ == "__main__":
    main() 