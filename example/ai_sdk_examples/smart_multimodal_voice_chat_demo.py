#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能多模态语音对话演示程序
展示AI SDK的智能多模态语音对话功能

功能包括：
1. 图像理解语音对话 - 通过语音提问图片并语音回答
2. 视频分析语音对话 - 通过语音提问视频并语音回答
3. 多图像比较语音对话 - 通过语音提问比较多张图片并语音回答
4. 自定义模型和配置 - 演示不同模型和参数的效果
5. 支持语音激活和持续对话
"""

import os
import sys
import time
import asyncio
import platform

# 将项目根目录添加到 python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from Embodied_SDK import AISDK

# -----------------------------------------------------------------------------

# 尝试导入彩色文本库
try:
    from colorama import init, Fore, Style
    init()  # 初始化colorama
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False
    print("提示: 安装colorama可获得彩色输出体验 (pip install colorama)")

def colored(text, color=None, style=None):
    """根据是否有colorama返回彩色文本"""
    if not HAS_COLOR:
        return text
        
    color_map = {
        'red': Fore.RED,
        'green': Fore.GREEN, 
        'yellow': Fore.YELLOW,
        'blue': Fore.BLUE,
        'magenta': Fore.MAGENTA,
        'cyan': Fore.CYAN,
        'white': Fore.WHITE
    }
    
    style_map = {
        'bold': Style.BRIGHT,
        'dim': Style.DIM,
        'normal': Style.NORMAL
    }
    
    result = ""
    if color and color in color_map:
        result += color_map[color]
    if style and style in style_map:
        result += style_map[style]
        
    result += text + Style.RESET_ALL
    return result

def print_separator(title=""):
    """打印分隔线"""
    print("\n" + "="*60)
    if title:
        if HAS_COLOR:
            print(colored(f" {title} ", "cyan", "bold"))
        else:
            print(f" {title} ")
        print("="*60)

def print_result(result, title="对话结果"):
    """格式化打印结果"""
    print("\n" + "-" * 40)
    if HAS_COLOR:
        print(colored(f"{title}:", "cyan", "bold"))
    else:
        print(f"{title}:")
    print("-" * 40)
    
    if result.get('success', True):
        print(colored("状态: ✅ 成功", "green"))
        
        # 打印会话信息
        conversations = result.get('conversations', [])
        print(f"对话轮次: {len(conversations)}")
        
        # 打印媒体信息
        print(f"媒体类型: {result.get('media_type', '未知')}")
        print(f"媒体信息: {result.get('media_info', '未知')}")
        
        # 如果有详细对话内容
        if conversations:
            print(colored("\n对话内容摘要:", "cyan"))
            for i, conv in enumerate(conversations):
                print(colored(f"\n--- 对话 {i+1} ---", "blue"))
                print(colored(f"🗣️ 用户: ", "yellow") + f"{conv.get('user_input', '')}")
                ai_response = conv.get('ai_response', '')
                truncated = ai_response[:150] + "..." if len(ai_response) > 150 else ai_response
                print(colored(f"🤖 AI: ", "green") + f"{truncated}")
    else:
        print(colored(f"状态: ❌ 失败", "red"))
        print(colored(f"错误: {result.get('error', '未知错误')}", "red"))

def show_progress(message="处理中", delay=0.1, max_dots=3):
    """显示进度动画"""
    for i in range(max_dots + 1):
        sys.stdout.write(f"\r{message}" + "." * i + " " * (max_dots - i))
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write("\r" + " " * (len(message) + max_dots + 1) + "\r")
    sys.stdout.flush()

def demo_image_voice_chat(sdk):
    """演示图像语音对话"""
    print_separator("图像语音对话演示")
    
    # 使用在线图片URL进行演示
    image_url = "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20241022/emyrja/dog_and_girl.jpeg"
    
    print(colored(f"图片: ", "blue") + f"{image_url}")
    print(colored("说明: ", "cyan") + "请通过语音提问图片内容，AI将通过分析图片并用语音回答")
    print(colored("设置: ", "magenta") + "使用qwen-vl-max-latest模型，启用流式输出和实时语音合成")
    print(colored("交互: ", "yellow") + "需说'你好助手'激活，说'结束对话'退出")
    
    # 显示准备就绪提示
    print("\n" + colored("🎙️ 开始智能多模态语音对话...", "green", "bold"))
    print(colored("请说 '你好助手' 来激活对话", "yellow", "bold"))
    
    try:
        # 优化参数配置
        result = sdk.smart_multimodal_voice_chat(
            image_path=image_url,
            # llm_provider 默认 alibaba
            llm_model="qwen-vl-max-latest",
            # tts_provider 默认 alibaba
            tts_model="sambert-zhichu-v1",
            voice="zhixiaoxia",
            activation_phrase="你好助手",
            activate_once=True,
            end_phrase="结束对话",
            duration=5,
            continue_conversation=True,
            use_context=True,
            verbose=True,           # 显示详细日志
            stream_output=True,     # 启用流式输出
            realtime_tts=True,      # 启用实时TTS
            temperature=0.7,        # 控制创造性
            max_tokens=1500         # 增加输出长度
        )
        print_result(result, "图像语音对话结果")
        
    except KeyboardInterrupt:
        print("\n" + colored("用户中断对话", "yellow"))
    except Exception as e:
        print("\n" + colored(f"图像语音对话失败: {str(e)}", "red"))

def demo_video_voice_chat(sdk):
    """演示视频语音对话"""
    print_separator("视频语音对话演示")
    
    # 使用在线视频URL
    video_url = "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20241115/cqqkru/1.mp4"
    
    print(colored(f"视频: ", "blue") + f"{video_url}")
    print(colored("说明: ", "cyan") + "请通过语音提问视频内容，AI将通过分析视频并用语音回答")
    print(colored("设置: ", "magenta") + "使用qwen-vl-max-latest模型，视频帧率1fps，启用流式输出和实时语音合成")
    print(colored("交互: ", "yellow") + "需说'你好助手'激活，说'结束对话'退出")
    
    print("\n" + colored("🎙️ 开始智能多模态语音对话...", "green", "bold"))
    print(colored("请说 '你好助手' 来激活对话", "yellow", "bold"))
    
    try:
        # 优化参数配置
        result = sdk.smart_multimodal_voice_chat(
            video_path=video_url,
            # llm_provider 默认 alibaba
            llm_model="qwen-vl-max-latest",
            # tts_provider 默认 alibaba
            tts_model="sambert-zhichu-v1",
            voice="zhixiaoxia",
            activation_phrase="你好助手",
            activate_once=True,
            end_phrase="结束对话",
            duration=5,
            continue_conversation=True,
            use_context=True,
            fps=1.0,
            verbose=True,           # 显示详细日志
            stream_output=True,     # 启用流式输出
            realtime_tts=True,      # 启用实时TTS
            temperature=0.7,        # 控制创造性
            max_tokens=1500         # 增加输出长度
        )
        print_result(result, "视频语音对话结果")
        
    except KeyboardInterrupt:
        print("\n" + colored("用户中断对话", "yellow"))
    except Exception as e:
        print("\n" + colored(f"视频语音对话失败: {str(e)}", "red"))

def demo_multiple_images_voice_chat(sdk):
    """演示多图像语音对话"""
    print_separator("多图像语音对话演示")
    
    # 使用多张在线图片URL
    image_urls = [
        "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20241022/emyrja/dog_and_girl.jpeg",
        "https://dashscope.oss-cn-beijing.aliyuncs.com/images/tiger.png"
    ]
    
    print(colored(f"图片数量: ", "blue") + f"{len(image_urls)}")
    for i, url in enumerate(image_urls, 1):
        print(f"  {colored(f'图片{i}:', 'blue')} {url}")
    
    print(colored("说明: ", "cyan") + "请通过语音提问比较图片内容，AI将通过分析图片并用语音回答")
    print(colored("设置: ", "magenta") + "使用qwen-vl-plus-latest模型，启用流式输出和实时语音合成")
    print(colored("交互: ", "yellow") + "需说'小助手'激活，说'停止对话'退出")
    
    print("\n" + colored("🎙️ 开始智能多模态语音对话...", "green", "bold"))
    print(colored("请说 '小助手' 来激活对话", "yellow", "bold"))
    
    try:
        # 优化参数配置
        result = sdk.smart_multimodal_voice_chat(
            image_paths=image_urls,
            # llm_provider 默认 alibaba
            llm_model="qwen-vl-plus-latest",
            # tts_provider 默认 alibaba
            tts_model="sambert-zhichu-v1",
            voice="zhixiaoxia",
            activation_phrase="小助手",
            activate_once=True,
            end_phrase="停止对话",
            duration=5,
            continue_conversation=True,
            use_context=True,
            verbose=True,           # 显示详细日志
            stream_output=True,     # 启用流式输出
            realtime_tts=True,      # 启用实时TTS
            temperature=0.7,        # 控制创造性
            max_tokens=1500         # 增加输出长度
        )
        print_result(result, "多图像语音对话结果")
        
    except KeyboardInterrupt:
        print("\n" + colored("用户中断对话", "yellow"))
    except Exception as e:
        print("\n" + colored(f"多图像语音对话失败: {str(e)}", "red"))

def demo_custom_voice_model(sdk):
    """演示自定义语音和模型"""
    print_separator("自定义语音和模型演示")
    
    image_url = "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20241022/emyrja/dog_and_girl.jpeg"
    
    print(colored(f"图片: ", "blue") + f"{image_url}")
    print(colored("说明: ", "cyan") + "请通过语音提问图片内容，AI将通过优质男声回答")
    print(colored("设置: ", "magenta") + "使用qwen-vl-max-latest模型，CosyVoice-v1模型男声，启用流式输出和实时语音合成")
    print(colored("交互: ", "yellow") + "需说'智能助手'激活，说'结束对话'退出")
    
    print("\n" + colored("🎙️ 开始智能多模态语音对话...", "green", "bold"))
    print(colored("请说 '智能助手' 来激活对话", "yellow", "bold"))
    
    try:
        # 优化参数配置
        result = sdk.smart_multimodal_voice_chat(
            image_path=image_url,
            # llm_provider 默认 alibaba
            llm_model="qwen-vl-max-latest",
            # tts_provider 默认 alibaba
            tts_model="cosyvoice-v1",
            voice="longxiaochun",    # 使用优质男声
            activation_phrase="智能助手",  # 自定义激活词
            activate_once=True,
            end_phrase="结束对话",
            duration=5,
            continue_conversation=True,
            use_context=True,
            verbose=True,           # 显示详细日志
            stream_output=True,     # 启用流式输出
            realtime_tts=True,      # 启用实时TTS
            temperature=0.7,        # 控制创造性
            max_tokens=1500         # 增加输出长度
        )
        print_result(result, "自定义语音和模型对话结果")
        
    except KeyboardInterrupt:
        print("\n" + colored("用户中断对话", "yellow"))
    except Exception as e:
        print("\n" + colored(f"自定义语音和模型对话失败: {str(e)}", "red"))

def demo_direct_voice_chat(sdk):
    """演示直接语音对话（无需激活）"""
    print_separator("直接语音对话演示")
    
    image_url = "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20241022/emyrja/dog_and_girl.jpeg"
    
    print(colored(f"图片: ", "blue") + f"{image_url}")
    print(colored("说明: ", "cyan") + "无需激活词，直接开始语音提问图片内容")
    print(colored("设置: ", "magenta") + "无激活词模式，启用流式输出和实时语音合成")
    print(colored("交互: ", "yellow") + "说'退出程序'结束对话")
    
    print("\n" + colored("🎙️ 开始智能多模态语音对话...", "green", "bold"))
    print(colored("直接开始说话，无需激活词", "yellow", "bold"))
    
    try:
        # 优化参数配置
        result = sdk.smart_multimodal_voice_chat(
            image_path=image_url,
            # llm_provider 默认 alibaba
            llm_model="qwen-vl-max-latest",
            # tts_provider 默认 alibaba
            tts_model="sambert-zhichu-v1",
            activation_phrase=None,  # 无需激活词
            end_phrase="退出程序",
            duration=10,             # 较长的录音时间
            silence_timeout=1.5,     # 更快的静音识别
            continue_conversation=True,
            use_context=True,
            verbose=True,            # 显示详细日志
            stream_output=True,      # 启用流式输出
            realtime_tts=True,       # 启用实时TTS
            temperature=0.7,         # 控制创造性
            max_tokens=1500          # 增加输出长度
        )
        print_result(result, "直接语音对话结果")
        
    except KeyboardInterrupt:
        print("\n" + colored("用户中断对话", "yellow"))
    except Exception as e:
        print("\n" + colored(f"直接语音对话失败: {str(e)}", "red"))

def demo_local_file(sdk):
    """演示本地文件语音对话"""
    print_separator("本地文件语音对话演示")
    
    # 获取测试文件的绝对路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    test_dir = os.path.join(current_dir, "test_file")
    test_video = os.path.join(test_dir, "lsz.mp4")
    
    # 检查文件是否存在
    if not os.path.exists(test_video):
        print(colored(f"❌ 测试视频文件不存在: {test_video}", "red"))
        print(colored("请确保test_file/lsz.mp4存在", "yellow"))
        return
    
    print(colored(f"视频: ", "blue") + f"{test_video}")
    print(colored("说明: ", "cyan") + "请通过语音提问视频内容，AI将通过分析视频并用语音回答")
    print(colored("设置: ", "magenta") + "使用本地视频文件进行分析，启用流式输出和实时语音合成")
    print(colored("交互: ", "yellow") + "需说'你好助手'激活，说'结束对话'退出")
    
    print("\n" + colored("🎙️ 开始智能多模态语音对话...", "green", "bold"))
    print(colored("请说 '你好助手' 来激活对话", "yellow", "bold"))
    
    try:
        # 显示加载提示
        print(colored("正在加载本地视频...", "cyan"))
        
        # 优化参数配置
        result = sdk.smart_multimodal_voice_chat(
            video_path=test_video,
            # llm_provider 默认 alibaba
            llm_model="qwen-vl-max-latest",
            # tts_provider 默认 alibaba
            tts_model="sambert-zhichu-v1",
            voice="zhixiaoxia",
            activation_phrase="你好助手",
            activate_once=True,
            end_phrase="结束对话",
            duration=5,
            continue_conversation=True,
            use_context=True,
            verbose=True,           # 显示详细日志
            stream_output=True,     # 启用流式输出
            realtime_tts=True,      # 启用实时TTS
            temperature=0.7,        # 控制创造性
            max_tokens=1500,        # 增加输出长度
            fps=1.0                 # 设置视频帧率
        )
        print_result(result, "本地文件语音对话结果")
        
    except KeyboardInterrupt:
        print("\n" + colored("用户中断对话", "yellow"))
    except Exception as e:
        print("\n" + colored(f"本地文件语音对话失败: {str(e)}", "red"))

def show_menu():
    """显示菜单"""
    try:
        # 清屏
        if platform.system() == "Windows":
            os.system('cls')
        else:
            os.system('clear')
    except:
        print("\n" * 3)  # 如果清屏失败，打印几行空行
        
    if HAS_COLOR:
        title = colored(" AI SDK 智能多模态语音对话演示 ", "cyan", "bold")
    else:
        title = " AI SDK 智能多模态语音对话演示 "
        
    print("\n" + "="*60)
    print(title)
    print("="*60)
    
    options = [
        ("1", "图像语音对话演示", "在线图片 + 流式输出 + 实时语音"),
        ("2", "视频语音对话演示", "在线视频 + 流式输出 + 实时语音"),
        ("3", "多图像语音对话演示", "在线多图比较 + 流式输出 + 实时语音"),
        ("4", "自定义语音和模型演示", "CosyVoice男声 + 自定义激活词"),
        ("5", "直接语音对话演示", "无激活词模式 + 快速响应"),
        ("6", "本地文件语音对话演示", "本地视频文件 + 流式输出 + 实时语音"),
        ("7", "运行所有演示", "依次运行全部演示"),
        ("0", "退出", "退出程序")
    ]
    
    for num, name, desc in options:
        if HAS_COLOR:
            print(f"{colored(num, 'green', 'bold')}. {colored(name, 'white')} {colored('(' + desc + ')', 'blue')}")
        else:
            print(f"{num}. {name} ({desc})")
    
    print("="*60)
    print("提示: 需要麦克风和扬声器设备支持")

async def main():
    """主函数"""
    # 打印欢迎信息
    print(colored("初始化AI SDK...", "cyan"))
    
    try:
        # 初始化SDK
        sdk = AISDK()
        print(colored("AI SDK初始化成功！", "green", "bold"))
        
        while True:
            show_menu()
            choice = input("\n" + colored("请选择功能 (0-7): ", "yellow")).strip()
            
            if choice == "0":
                print(colored("感谢使用，再见！", "cyan"))
                break
            elif choice == "1":
                demo_image_voice_chat(sdk)
            elif choice == "2":
                demo_video_voice_chat(sdk)
            elif choice == "3":
                demo_multiple_images_voice_chat(sdk)
            elif choice == "4":
                demo_custom_voice_model(sdk)
            elif choice == "5":
                demo_direct_voice_chat(sdk)
            elif choice == "6":
                demo_local_file(sdk)
            elif choice == "7":
                print(colored("运行所有演示...", "magenta", "bold"))
                demos = [
                    demo_image_voice_chat,
                    demo_video_voice_chat, 
                    demo_multiple_images_voice_chat,
                    demo_custom_voice_model,
                    demo_direct_voice_chat,
                    demo_local_file
                ]
                
                for i, demo in enumerate(demos):
                    print(colored(f"\n正在运行演示 {i+1}/{len(demos)}...", "cyan"))
                    demo(sdk)
                    if i < len(demos) - 1:  # 如果不是最后一个演示，等待用户准备好
                        input(colored("\n按回车键继续下一个演示...", "yellow"))
                        
                print(colored("\n所有演示完成！", "green", "bold"))
            else:
                print(colored("无效选择，请重新输入", "red"))
            
            if choice != "0" and choice != "7":
                input(colored("\n按回车键返回主菜单...", "yellow"))
            
    except KeyboardInterrupt:
        print(colored("\n\n程序被用户中断", "yellow"))
    except Exception as e:
        print(colored(f"\n程序运行出错: {str(e)}", "red"))
        print(colored("请检查配置文件和网络连接", "yellow"))

if __name__ == "__main__":
    asyncio.run(main())