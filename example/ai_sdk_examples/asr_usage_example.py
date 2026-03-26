"""
AI SDK ASR功能使用示例
展示语音识别的各种功能
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

class ASRDemo:
    """ASR功能演示类"""
    
    def __init__(self):
        """初始化演示"""
        self.sdk = AISDK()
        print("🎤 AI SDK ASR功能演示")
        print("=" * 50)
    
    def demo_file_recognition(self):
        """演示音频文件识别"""
        print("\n📁 音频文件识别演示")
        print("-" * 30)
        
        # 注意：这里需要准备一个测试音频文件
        test_files = [
            "test_audio.wav",
            "sample.mp3",
        ]
        
        for audio_file in test_files:
            if os.path.exists(audio_file):
                print(f"\n🎵 识别文件: {audio_file}")
                try:
                    result = self.sdk.asr(
                        mode="file",
                        audio_file=audio_file,
                        model="paraformer-realtime-v2",
                        enable_words=True,
                        enable_punctuation_prediction=True,
                        enable_speaker_diarization=True
                    )
                    
                    if result['success']:
                        print(f"✅ 识别成功!")
                        print(f"📝 文本: {result['text']}")
                        print(f"🎯 置信度: {result['confidence']:.2f}")
                        
                        if result.get('words'):
                            print("📊 词级别信息:")
                            for word in result['words'][:5]:  # 只显示前5个词
                                print(f"  - {word}")
                        
                        if result.get('speaker_info'):
                            print("👥 说话人信息:")
                            for speaker in result['speaker_info']:
                                print(f"  - {speaker}")
                                
                    else:
                        print(f"❌ 识别失败: {result.get('error', '未知错误')}")
                        
                except Exception as e:
                    print(f"❌ 处理失败: {e}")
            else:
                print(f"⚠️ 文件不存在: {audio_file}")
        
        if not any(os.path.exists(f) for f in test_files):
            print("💡 提示: 请准备一些测试音频文件 (支持 wav, mp3, flac, aac, m4a)")
    
    async def demo_async_file_recognition(self):
        """演示异步音频文件识别"""
        print("\n⚡ 异步音频文件识别演示")
        print("-" * 30)
        
        test_files = ["test_audio.wav", "sample.wav"]
        existing_files = [f for f in test_files if os.path.exists(f)]
        
        if not existing_files:
            print("⚠️ 没有找到测试音频文件")
            return
        
        print(f"🚀 并发识别 {len(existing_files)} 个文件...")
        
        # 并发执行多个异步识别任务
        tasks = []
        for audio_file in existing_files:
            task = self.sdk.asr(
                mode="file",
                audio_file=audio_file,
                async_mode=True
            )
            tasks.append((audio_file, task))
        
        # 等待所有任务完成
        for audio_file, task in tasks:
            try:
                result = await task
                print(f"\n📁 {audio_file}:")
                if result['success']:
                    print(f"  ✅ {result['text']}")
                    print(f"  🎯 置信度: {result['confidence']:.2f}")
                else:
                    print(f"  ❌ {result.get('error', '识别失败')}")
            except Exception as e:
                print(f"  ❌ 异步处理失败: {e}")
    
    def demo_microphone_recognition(self):
        """演示麦克风识别"""
        print("\n🎙️ 麦克风识别演示")
        print("-" * 30)
        
        try:
            durations = [3, 5, 10]
            
            for duration in durations:
                print(f"\n⏱️ {duration}秒录音测试")
                input(f"按回车开始 {duration} 秒录音...")
                
                result = self.sdk.asr(
                    mode="microphone",
                    duration=duration,
                    enable_punctuation_prediction=True,
                    enable_voice_detection=True
                )
                
                if result['success']:
                    print(f"✅ 识别结果: {result['text']}")
                    print(f"🎯 置信度: {result['confidence']:.2f}")
                    
                    if result.get('audio_duration'):
                        print(f"⏱️ 音频时长: {result['audio_duration']:.2f}秒")
                    
                    if result.get('processing_time'):
                        print(f"⚡ 处理时间: {result['processing_time']:.2f}秒")
                else:
                    print(f"❌ 识别失败: {result.get('error', '未知错误')}")
                
                if duration < durations[-1]:
                    input("\n按回车继续下一个测试...")
                    
        except Exception as e:
            print(f"❌ 麦克风识别演示失败: {e}")
            print("💡 请确保：")
            print("  1. 已安装 pyaudio: pip install pyaudio")
            print("  2. 系统有可用的麦克风")
            print("  3. 已授予麦克风权限")
    
    def demo_keyword_spotting(self):
        """演示关键词识别唤醒"""
        print("\n🔍 关键词识别唤醒演示")
        print("-" * 30)
        
        # 定义要检测的关键词
        keywords = ["你好", "小助手", "开始", "停止", "结束"]
        print(f"🎯 监听关键词: {', '.join(keywords)}")
        print("💡 系统将静默监听，只有检测到关键词时才会响应")
        print("⚠️ 按 Ctrl+C 停止监听")
        print("🔇 开始静默监听...")
        
        try:
            detection_count = 0
            max_detections = 5
            
            # 使用新的关键词检测模式
            for result in self.sdk.asr(
                mode="keyword",
                keywords=keywords,
                detection_threshold=0.7,  # 检测阈值
                silence_timeout=2.0,      # 静音超时时间
                max_audio_length=10       # 最大音频长度
            ):
                if result['success']:
                    detection_count += 1
                    print(f"\n🎉 [{time.strftime('%H:%M:%S')}] 检测到关键词 #{detection_count}")
                    print(f"🔑 关键词: {result['keyword_detected']}")
                    print(f"📝 完整文本: {result['text']}")
                    print(f"🎯 置信度: {result['confidence']:.2f}")
                    print("🚀 系统已唤醒！")
                    
                    # 检查是否是停止关键词
                    if result['keyword_detected'] in ['停止', '结束']:
                        print("🛑 检测到停止关键词，结束监听")
                        break
                    
                    if detection_count >= max_detections:
                        print(f"\n✅ 已完成 {max_detections} 次唤醒检测，演示结束")
                        break
                    else:
                        print("🔇 继续静默监听...")
                else:
                    print(f"\n❌ 识别错误: {result.get('error', '未知错误')}")
                    
        except KeyboardInterrupt:
            print("\n\n⚠️ 用户停止了关键词监听")
        except Exception as e:
            print(f"❌ 关键词检测失败: {e}")
            print("💡 请检查：")
            print("  1. 是否安装了 pyaudio: pip install pyaudio")
            print("  2. 系统是否有可用的麦克风")
            print("  3. 是否已授予麦克风权限")
            print("  4. 网络连接是否正常")
    
    def demo_simple_keyword_detection(self):
        """演示简单的关键词检测"""
        print("\n🎯 简单关键词检测演示")
        print("-" * 30)
        
        # 让用户选择关键词
        print("请选择要检测的关键词：")
        print("1. 你好")
        print("2. 小助手") 
        print("3. 开始")
        print("4. 自定义")
        
        choice = input("请输入选择 (1-4): ").strip()
        
        if choice == "1":
            keywords = ["你好"]
        elif choice == "2":
            keywords = ["小助手"]
        elif choice == "3":
            keywords = ["开始"]
        elif choice == "4":
            custom_keyword = input("请输入自定义关键词: ").strip()
            if custom_keyword:
                keywords = [custom_keyword]
            else:
                print("❌ 关键词不能为空")
                return
        else:
            print("❌ 无效选择")
            return
        
        print(f"\n🎯 开始监听关键词: {keywords[0]}")
        print("🔇 静默模式，只有检测到关键词时才会响应")
        print("⚠️ 按 Ctrl+C 停止")
        
        try:
            # 单关键词检测
            for result in self.sdk.asr(
                mode="keyword",
                keywords=keywords,
                detection_threshold=0.6,
                silence_timeout=3.0
            ):
                if result['success']:
                    print(f"\n🎉 成功检测到关键词！")
                    print(f"🔑 关键词: {result['keyword_detected']}")
                    print(f"📝 完整文本: {result['text']}")
                    print(f"🎯 置信度: {result['confidence']:.2f}")
                    print(f"⏰ 检测时间: {time.strftime('%H:%M:%S')}")
                    
                    # 检测到一次就结束
                    print("✅ 关键词检测完成！")
                    break
                else:
                    print(f"❌ 检测错误: {result.get('error', '未知错误')}")
                    break
                    
        except KeyboardInterrupt:
            print("\n⚠️ 用户停止了关键词检测")
        except Exception as e:
            print(f"❌ 关键词检测失败: {e}")
    
    def demo_continuous_keyword_monitoring(self):
        """演示连续关键词监控"""
        print("\n🔄 连续关键词监控演示")
        print("-" * 30)
        
        keywords = ["唤醒", "助手", "你好"]
        print(f"🎯 监控关键词: {', '.join(keywords)}")
        print("💡 系统将持续监听，每次检测到关键词都会响应")
        print("🛑 说'退出'或按 Ctrl+C 停止监控")
        
        try:
            detection_count = 0
            
            for result in self.sdk.asr(
                mode="keyword",
                keywords=keywords + ["退出"],  # 添加退出关键词
                detection_threshold=0.7,
                silence_timeout=1.5,
                max_audio_length=8
            ):
                if result['success']:
                    detection_count += 1
                    keyword = result['keyword_detected']
                    
                    if keyword == "退出":
                        print(f"\n🛑 检测到退出指令，停止监控")
                        break
                    
                    print(f"\n🔔 [第{detection_count}次] 检测到关键词: {keyword}")
                    print(f"📝 完整文本: {result['text']}")
                    print(f"🎯 置信度: {result['confidence']:.2f}")
                    print("🔇 继续监听中...")
                else:
                    print(f"❌ 监控错误: {result.get('error', '未知错误')}")
                    
        except KeyboardInterrupt:
            print("\n⚠️ 用户停止了关键词监控")
        except Exception as e:
            print(f"❌ 关键词监控失败: {e}")
    
    def demo_stream_recognition(self):
        """演示实时语音识别"""
        print("\n🌊 实时语音识别演示")
        print("-" * 30)
        print("🎤 使用麦克风进行实时语音识别")
        print("💡 说话时会实时显示识别结果")
        print("⚠️ 按 Ctrl+C 停止识别")
        
        try:
            import pyaudio
            
            # 音频参数
            CHUNK = 1024
            FORMAT = pyaudio.paInt16
            CHANNELS = 1
            RATE = 16000
            
            # 初始化PyAudio
            audio = pyaudio.PyAudio()
            
            # 打开音频流
            stream = audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK
            )
            
            print("\n🎙️ 麦克风已启动，开始说话...")
            print("📝 实时识别结果:")
            print("-" * 40)
            
            # 创建音频流生成器
            def audio_stream_generator():
                try:
                    while True:
                        data = stream.read(CHUNK, exception_on_overflow=False)
                        yield data
                except KeyboardInterrupt:
                    return
            
            # 开始实时识别
            sentence_count = 0
            for result in self.sdk.asr(
                mode="stream",
                audio_stream=audio_stream_generator(),
                model="paraformer-realtime-v2",
                enable_punctuation_prediction=True
            ):
                if result['success']:
                    if result.get('is_final', False):
                        # 完整句子
                        sentence_count += 1
                        print(f"\n[句子 {sentence_count}] {result['text']}")
                        print(f"  🎯 置信度: {result['confidence']:.2f}")
                        if result.get('begin_time') and result.get('end_time'):
                            duration = (result['end_time'] - result['begin_time']) / 1000
                            print(f"  ⏱️ 时长: {duration:.2f}秒")
                    else:
                        # 中间结果
                        if result['text'].strip():
                            print(f"[中间] {result['text']}", end='\r')
                else:
                    print(f"\n❌ 识别错误: {result.get('error', '未知错误')}")
                    
        except KeyboardInterrupt:
            print("\n\n⚠️ 用户停止了实时识别")
        except ImportError:
            print("❌ 缺少 pyaudio 库")
            print("💡 请安装: pip install pyaudio")
        except Exception as e:
            print(f"❌ 实时识别失败: {e}")
        finally:
            # 清理资源
            try:
                stream.stop_stream()
                stream.close()
                audio.terminate()
                print("🔧 音频资源已清理")
            except:
                pass
    
    def demo_advanced_features(self):
        """演示高级功能"""
        print("\n🚀 高级功能演示")
        print("-" * 30)
        
        # 如果有测试音频文件，演示高级参数
        test_file = "test_audio.wav"
        if os.path.exists(test_file):
            print(f"📁 使用文件: {test_file}")
            
            # 演示不同的参数配置
            configs = [
                {
                    "name": "基础识别",
                    "params": {}
                },
                {
                    "name": "高精度识别",
                    "params": {
                        "enable_words": True,
                        "enable_punctuation_prediction": True,
                        "enable_inverse_text_normalization": True,
                        "enable_voice_detection": True
                    }
                },
                {
                    "name": "说话人分离",
                    "params": {
                        "enable_speaker_diarization": True,
                        "speaker_count": 2
                    }
                },
                {
                    "name": "语义断句",
                    "params": {
                        "enable_semantic_sentence_detection": True,
                        "max_sentence_silence": 1000
                    }
                }
            ]
            
            for config in configs:
                print(f"\n🔧 {config['name']}:")
                try:
                    result = self.sdk.asr(
                        mode="file",
                        audio_file=test_file,
                        **config['params']
                    )
                    
                    if result['success']:
                        print(f"  ✅ {result['text']}")
                        print(f"  🎯 置信度: {result['confidence']:.2f}")
                    else:
                        print(f"  ❌ {result.get('error', '识别失败')}")
                        
                except Exception as e:
                    print(f"  ❌ 处理失败: {e}")
        else:
            print("⚠️ 需要测试音频文件来演示高级功能")
    
    def show_menu(self):
        """显示演示菜单"""
        print("\n" + "="*50)
        print("🎤 ASR功能演示菜单")
        print("="*50)
        print("1️⃣  音频文件识别")
        print("2️⃣  异步文件识别")
        print("3️⃣  麦克风识别")
        print("4️⃣  关键词识别唤醒")
        print("5️⃣  实时语音识别")
        print("6️⃣  高级功能演示")
        print("7️⃣  运行所有演示")
        print("0️⃣  退出")
        print("="*50)
    
    def show_keyword_menu(self):
        """显示关键词检测子菜单"""
        print("\n" + "="*40)
        print("🔍 关键词检测功能菜单")
        print("="*40)
        print("1️⃣  基础关键词唤醒")
        print("2️⃣  简单关键词检测")
        print("3️⃣  连续关键词监控")
        print("0️⃣  返回主菜单")
        print("="*40)
    
    def run_keyword_demos(self):
        """运行关键词检测演示"""
        while True:
            self.show_keyword_menu()
            choice = input("\n请选择功能 (0-3): ").strip()
            
            try:
                if choice == "0":
                    break
                elif choice == "1":
                    self.demo_keyword_spotting()
                elif choice == "2":
                    self.demo_simple_keyword_detection()
                elif choice == "3":
                    self.demo_continuous_keyword_monitoring()
                else:
                    print("❌ 无效选择，请重新输入")
            except KeyboardInterrupt:
                print("\n⚠️ 演示被用户中断")
            except Exception as e:
                print(f"❌ 演示过程中发生错误: {e}")
            
            if choice != "0":
                input("\n按回车返回关键词菜单...")
    
    def run_all_demos(self):
        """运行所有演示"""
        print("🚀 运行所有ASR功能演示")
        print("=" * 50)
        
        demos = [
            ("音频文件识别", self.demo_file_recognition),
            ("异步文件识别", lambda: asyncio.run(self.demo_async_file_recognition())),
            ("麦克风识别", self.demo_microphone_recognition),
            ("关键词识别唤醒", self.demo_keyword_spotting),
            ("实时语音识别", self.demo_stream_recognition),
            ("高级功能", self.demo_advanced_features),
        ]
        
        for name, demo_func in demos:
            print(f"\n🎯 开始 {name} 演示...")
            try:
                demo_func()
                print(f"✅ {name} 演示完成")
            except Exception as e:
                print(f"❌ {name} 演示失败: {e}")
            
            if name != demos[-1][0]:
                input("\n按回车继续下一个演示...")
        
        print("\n🎉 所有演示完成！")
    
    def run(self):
        """运行演示程序"""
        while True:
            self.show_menu()
            choice = input("\n请选择演示功能 (0-7): ").strip()
            
            try:
                if choice == "0":
                    print("\n👋 感谢使用ASR功能演示！")
                    break
                elif choice == "1":
                    self.demo_file_recognition()
                elif choice == "2":
                    asyncio.run(self.demo_async_file_recognition())
                elif choice == "3":
                    self.demo_microphone_recognition()
                elif choice == "4":
                    self.run_keyword_demos()
                elif choice == "5":
                    self.demo_stream_recognition()
                elif choice == "6":
                    self.demo_advanced_features()
                elif choice == "7":
                    self.run_all_demos()
                else:
                    print("❌ 无效选择，请重新输入")
            
            except KeyboardInterrupt:
                print("\n\n⚠️ 演示被用户中断")
            except Exception as e:
                print(f"\n❌ 演示过程中发生错误: {e}")
            
            if choice != "0":
                input("\n按回车返回主菜单...")

def main():
    """主函数"""
    print("🚀 初始化ASR演示程序...")
    try:
        demo = ASRDemo()
        demo.run()
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        print("💡 请检查：")
        print("  1. 配置文件是否正确")
        print("  2. API密钥是否有效")
        print("  3. 网络连接是否正常")
        print("  4. 依赖包是否安装完整")

if __name__ == "__main__":
    main() 