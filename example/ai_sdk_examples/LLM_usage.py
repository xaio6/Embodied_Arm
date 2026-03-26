"""
AI SDK 完整功能测试工具
用户可以选择测试不同的LLM功能
"""

import asyncio
import os
import sys

# 将项目根目录添加到 python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from Embodied_SDK import AISDK


class LLMTester:
    """LLM功能测试器"""
    
    def __init__(self):
        """初始化测试器"""
        self.sdk = AISDK()
        self.test_prompts = {
            'basic': [
                "你好，请简单介绍一下自己",
                "今天天气怎么样？",
                "请解释一下什么是人工智能"
            ],
            'creative': [
                "写一首关于春天的诗",
                "编一个关于小猫的故事",
                "设计一个创新的手机应用想法"
            ],
            'analytical': [
                "分析一下电商行业的发展趋势",
                "比较Python和Java编程语言的优缺点",
                "解释区块链技术的工作原理"
            ],
            'conversation': [
                "我叫张三，今年25岁，是一名程序员",
                "我的工作是什么？",
                "我多少岁了？"
            ],
            'coding': [
                "写一个Python函数计算斐波那契数列",
                "解释这段代码的作用：for i in range(10): print(i)",
                "如何优化数据库查询性能？"
            ]
        }
    
    def show_menu(self):
        """显示主菜单"""
        print("\n" + "="*60)
        print("🚀 AI SDK LLM功能测试工具")
        print("="*60)
        print("请选择要测试的功能：")
        print()
        print("1️⃣  基础对话测试")
        print("2️⃣  流式输出测试")
        print("3️⃣  上下文对话测试")
        print("4️⃣  多会话管理测试")
        print("5️⃣  异步调用测试")
        print("6️⃣  参数调优测试")
        print("7️⃣  提供商对比测试")
        print("8️⃣  创意生成测试")
        print("9️⃣  代码生成测试")
        print("🔟  分析推理测试")
        print("1️⃣1️⃣ 压力测试")
        print("1️⃣2️⃣ 综合功能演示")
        print("1️⃣3️⃣ 自定义测试")
        print("0️⃣  退出")
        print("="*60)
    
    def test_basic_chat(self):
        """测试基础对话功能"""
        print("\n🎯 基础对话测试")
        print("-" * 40)
        
        for i, prompt in enumerate(self.test_prompts['basic'], 1):
            print(f"\n📝 测试 {i}/3: {prompt}")
            try:
                response = self.sdk.chat(
                    prompt=prompt,
                    model="qwen-turbo",
                    temperature=0.7,
                    max_tokens=200
                )
                print(f"🤖 回复: {response['choices'][0]['message']['content']}")
                print(f"📊 Token使用: {response.get('usage', {})}")
            except Exception as e:
                print(f"❌ 错误: {e}")
            
            input("\n按回车继续下一个测试...")
    
    def test_stream_chat(self):
        """测试流式输出功能"""
        print("\n🌊 流式输出测试")
        print("-" * 40)
        
        prompts = [
            "请详细介绍一下机器学习的发展历程",
            "写一个关于未来科技的短文",
            "解释深度学习的基本原理"
        ]
        
        for i, prompt in enumerate(prompts, 1):
            print(f"\n📝 流式测试 {i}/3: {prompt}")
            print("🤖 实时回复: ", end="", flush=True)
            
            try:
                full_content = ""
                for chunk in self.sdk.chat(
                    prompt=prompt,
                    model="qwen-turbo",
                    stream=True,
                    temperature=0.8,
                    max_tokens=300
                ):
                    content = chunk['choices'][0]['delta']['content']
                    print(content, end="", flush=True)
                    full_content += content
                
                print(f"\n📏 总字符数: {len(full_content)}")
            except Exception as e:
                print(f"\n❌ 错误: {e}")
            
            input("\n按回车继续下一个测试...")
    
    def test_context_chat(self):
        """测试上下文对话功能"""
        print("\n💬 上下文对话测试")
        print("-" * 40)
        
        # 清空历史记录
        self.sdk.clear_conversation_history()
        
        conversation_flow = [
            ("我叫李明，是一名软件工程师", "建立身份信息"),
            ("我在北京工作", "添加地理信息"),
            ("我喜欢编程和阅读", "添加兴趣爱好"),
            ("我叫什么名字？", "测试姓名记忆"),
            ("我在哪里工作？", "测试地点记忆"),
            ("我的爱好是什么？", "测试兴趣记忆"),
            ("根据我的信息，推荐一些适合我的书籍", "综合信息应用")
        ]
        
        for i, (prompt, purpose) in enumerate(conversation_flow, 1):
            print(f"\n📝 步骤 {i}/7 ({purpose}): {prompt}")
            try:
                response = self.sdk.chat(
                    prompt=prompt,
                    model="qwen-turbo",
                    use_context=True,
                    temperature=0.7,
                    max_tokens=150
                )
                print(f"🤖 回复: {response['choices'][0]['message']['content']}")
                
                # 显示当前历史记录数量
                history = self.sdk.get_conversation_history()
                print(f"📚 历史记录数量: {len(history)}")
                
            except Exception as e:
                print(f"❌ 错误: {e}")
            
            if i < len(conversation_flow):
                input("\n按回车继续下一步...")
    
    def test_multi_session(self):
        """测试多会话管理功能"""
        print("\n👥 多会话管理测试")
        print("-" * 40)
        
        # 清空所有历史
        self.sdk.clear_conversation_history()
        
        # 用户A的对话场景
        print("\n🔵 用户A (学生) 的对话:")
        user_a_prompts = [
            "我是一名大学生，正在学习计算机科学",
            "我需要学习哪些编程语言？",
            "推荐一些适合初学者的项目"
        ]
        
        for prompt in user_a_prompts:
            print(f"👤 用户A: {prompt}")
            try:
                response = self.sdk.chat(
                    prompt=prompt,
                    model="qwen-turbo",
                    use_context=True,
                    session_id="student_user",
                    temperature=0.7,
                    max_tokens=150
                )
                print(f"🤖 回复: {response['choices'][0]['message']['content']}")
            except Exception as e:
                print(f"❌ 错误: {e}")
        
        # 用户B的对话场景
        print("\n🟢 用户B (创业者) 的对话:")
        user_b_prompts = [
            "我是一名创业者，正在开发一个电商平台",
            "我需要关注哪些技术栈？",
            "如何进行市场推广？"
        ]
        
        for prompt in user_b_prompts:
            print(f"👤 用户B: {prompt}")
            try:
                response = self.sdk.chat(
                    prompt=prompt,
                    model="qwen-turbo",
                    use_context=True,
                    session_id="entrepreneur_user",
                    temperature=0.7,
                    max_tokens=150
                )
                print(f"🤖 回复: {response['choices'][0]['message']['content']}")
            except Exception as e:
                print(f"❌ 错误: {e}")
        
        # 显示会话隔离效果
        print("\n📊 会话隔离验证:")
        history_a = self.sdk.get_conversation_history("student_user")
        history_b = self.sdk.get_conversation_history("entrepreneur_user")
        print(f"用户A历史记录数量: {len(history_a)}")
        print(f"用户B历史记录数量: {len(history_b)}")
    
    async def test_async_chat(self):
        """测试异步调用功能"""
        print("\n⚡ 异步调用测试")
        print("-" * 40)
        
        prompts = [
            "解释什么是云计算",
            "介绍人工智能的应用领域",
            "分析大数据的发展趋势"
        ]
        
        print("🚀 并发执行3个异步请求...")
        
        try:
            # 并发执行多个异步请求
            tasks = []
            for i, prompt in enumerate(prompts, 1):
                task = self.sdk.chat(
                    prompt=prompt,
                    model="qwen-turbo",
                    async_mode=True,
                    temperature=0.7,
                    max_tokens=200
                )
                tasks.append((i, prompt, task))
            
            # 等待所有任务完成
            for i, prompt, task in tasks:
                response = await task
                print(f"\n📝 任务 {i}: {prompt}")
                print(f"🤖 回复: {response['choices'][0]['message']['content']}")
        
        except Exception as e:
            print(f"❌ 错误: {e}")
    
    def test_parameter_tuning(self):
        """测试参数调优功能"""
        print("\n⚙️ 参数调优测试")
        print("-" * 40)
        
        prompt = "写一首关于秋天的诗"
        
        # 测试不同的temperature值
        temperatures = [0.1, 0.5, 0.9, 1.5]
        
        for temp in temperatures:
            print(f"\n🌡️ Temperature = {temp}")
            try:
                response = self.sdk.chat(
                    prompt=prompt,
                    model="qwen-turbo",
                    temperature=temp,
                    max_tokens=200,
                    top_p=0.8
                )
                print(f"🤖 回复: {response['choices'][0]['message']['content']}")
            except Exception as e:
                print(f"❌ 错误: {e}")
            
            input("\n按回车测试下一个参数...")
    
    def test_provider_comparison(self):
        """测试提供商对比"""
        print("\n🏭 提供商对比测试")
        print("-" * 40)
        
        prompt = "请解释什么是量子计算"
        providers = [
            ("alibaba", "qwen-turbo"),
            ("deepseek", "deepseek-chat")
        ]
        
        for provider, model in providers:
            print(f"\n🔧 测试 {provider.upper()} - {model}")
            try:
                response = self.sdk.chat(
                    provider=provider,
                    model=model,
                    prompt=prompt,
                    temperature=0.7,
                    max_tokens=200
                )
                print(f"🤖 回复: {response['choices'][0]['message']['content']}")
                print(f"📊 Token使用: {response.get('usage', {})}")
            except Exception as e:
                print(f"❌ 错误: {e}")
            
            input("\n按回车测试下一个提供商...")
    
    def test_creative_generation(self):
        """测试创意生成功能"""
        print("\n🎨 创意生成测试")
        print("-" * 40)
        
        for i, prompt in enumerate(self.test_prompts['creative'], 1):
            print(f"\n📝 创意测试 {i}/3: {prompt}")
            try:
                response = self.sdk.chat(
                    prompt=prompt,
                    model="qwen-turbo",
                    temperature=1.0,  # 高创造性
                    max_tokens=300,
                    top_p=0.9
                )
                print(f"🤖 创意回复: {response['choices'][0]['message']['content']}")
            except Exception as e:
                print(f"❌ 错误: {e}")
            
            input("\n按回车继续下一个创意测试...")
    
    def test_code_generation(self):
        """测试代码生成功能"""
        print("\n💻 代码生成测试")
        print("-" * 40)
        
        for i, prompt in enumerate(self.test_prompts['coding'], 1):
            print(f"\n📝 代码测试 {i}/3: {prompt}")
            try:
                response = self.sdk.chat(
                    prompt=prompt,
                    model="qwen-turbo",
                    temperature=0.3,  # 低创造性，更准确
                    max_tokens=400
                )
                print(f"🤖 代码回复: {response['choices'][0]['message']['content']}")
            except Exception as e:
                print(f"❌ 错误: {e}")
            
            input("\n按回车继续下一个代码测试...")
    
    def test_analytical_reasoning(self):
        """测试分析推理功能"""
        print("\n🧠 分析推理测试")
        print("-" * 40)
        
        for i, prompt in enumerate(self.test_prompts['analytical'], 1):
            print(f"\n📝 分析测试 {i}/3: {prompt}")
            try:
                response = self.sdk.chat(
                    prompt=prompt,
                    model="qwen-turbo",
                    temperature=0.5,
                    max_tokens=400
                )
                print(f"🤖 分析回复: {response['choices'][0]['message']['content']}")
            except Exception as e:
                print(f"❌ 错误: {e}")
            
            input("\n按回车继续下一个分析测试...")
    
    def test_stress_test(self):
        """压力测试"""
        print("\n🔥 压力测试")
        print("-" * 40)
        
        print("执行10次连续请求测试...")
        
        success_count = 0
        error_count = 0
        
        for i in range(1, 11):
            print(f"\n📝 请求 {i}/10")
            try:
                response = self.sdk.chat(
                    prompt=f"这是第{i}次测试请求，请简单回复",
                    model="qwen-turbo",
                    temperature=0.7,
                    max_tokens=50
                )
                print(f"✅ 成功: {response['choices'][0]['message']['content']}")
                success_count += 1
            except Exception as e:
                print(f"❌ 失败: {e}")
                error_count += 1
        
        print(f"\n📊 压力测试结果:")
        print(f"成功: {success_count}/10")
        print(f"失败: {error_count}/10")
        print(f"成功率: {success_count/10*100:.1f}%")
    
    def test_comprehensive_demo(self):
        """综合功能演示"""
        print("\n🎪 综合功能演示")
        print("-" * 40)
        
        print("🎯 演示场景：AI助手帮助用户规划学习路径")
        
        # 清空历史
        self.sdk.clear_conversation_history()
        
        conversation = [
            "我想学习人工智能，但是我是零基础",
            "我应该从哪些数学知识开始学？",
            "推荐一些入门的编程语言",
            "制定一个3个月的学习计划"
        ]
        
        for i, prompt in enumerate(conversation, 1):
            print(f"\n👤 用户: {prompt}")
            
            # 使用流式输出 + 上下文
            print("🤖 AI助手: ", end="", flush=True)
            try:
                for chunk in self.sdk.chat(
                    prompt=prompt,
                    model="qwen-turbo",
                    stream=True,
                    use_context=True,
                    session_id="learning_plan",
                    temperature=0.7,
                    max_tokens=300
                ):
                    content = chunk['choices'][0]['delta']['content']
                    print(content, end="", flush=True)
                print("\n")
            except Exception as e:
                print(f"\n❌ 错误: {e}")
            
            if i < len(conversation):
                input("按回车继续对话...")
    
    def test_custom(self):
        """自定义测试"""
        print("\n🛠️ 自定义测试")
        print("-" * 40)
        
        while True:
            print("\n请选择自定义测试选项:")
            print("1. 自定义提示词测试")
            print("2. 自定义参数测试")
            print("3. 返回主菜单")
            
            choice = input("\n请输入选择 (1-3): ").strip()
            
            if choice == "1":
                prompt = input("\n请输入自定义提示词: ").strip()
                if prompt:
                    try:
                        response = self.sdk.chat(
                            prompt=prompt,
                            model="qwen-turbo",
                            temperature=0.7,
                            max_tokens=300
                        )
                        print(f"\n🤖 回复: {response['choices'][0]['message']['content']}")
                    except Exception as e:
                        print(f"❌ 错误: {e}")
            
            elif choice == "2":
                prompt = input("\n请输入提示词: ").strip()
                if prompt:
                    try:
                        temp = float(input("请输入temperature (0.0-2.0): ") or "0.7")
                        max_tokens = int(input("请输入max_tokens (1-2000): ") or "300")
                        top_p = float(input("请输入top_p (0.0-1.0): ") or "0.8")
                        
                        response = self.sdk.chat(
                            prompt=prompt,
                            model="qwen-turbo",
                            temperature=temp,
                            max_tokens=max_tokens,
                            top_p=top_p
                        )
                        print(f"\n🤖 回复: {response['choices'][0]['message']['content']}")
                    except Exception as e:
                        print(f"❌ 错误: {e}")
            
            elif choice == "3":
                break
            else:
                print("❌ 无效选择，请重新输入")
    
    def run(self):
        """运行测试工具"""
        while True:
            self.show_menu()
            choice = input("\n请输入选择 (0-13): ").strip()
            
            try:
                if choice == "0":
                    print("\n👋 感谢使用AI SDK测试工具！")
                    break
                elif choice == "1":
                    self.test_basic_chat()
                elif choice == "2":
                    self.test_stream_chat()
                elif choice == "3":
                    self.test_context_chat()
                elif choice == "4":
                    self.test_multi_session()
                elif choice == "5":
                    asyncio.run(self.test_async_chat())
                elif choice == "6":
                    self.test_parameter_tuning()
                elif choice == "7":
                    self.test_provider_comparison()
                elif choice == "8":
                    self.test_creative_generation()
                elif choice == "9":
                    self.test_code_generation()
                elif choice == "10":
                    self.test_analytical_reasoning()
                elif choice == "11":
                    self.test_stress_test()
                elif choice == "12":
                    self.test_comprehensive_demo()
                elif choice == "13":
                    self.test_custom()
                else:
                    print("❌ 无效选择，请重新输入")
            
            except KeyboardInterrupt:
                print("\n\n⚠️ 测试被用户中断")
            except Exception as e:
                print(f"\n❌ 测试过程中发生错误: {e}")
            
            if choice != "0":
                input("\n按回车返回主菜单...")

def main():
    """主函数"""
    print("🚀 初始化AI SDK测试工具...")
    try:
        tester = LLMTester()
        tester.run()
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        print("请检查配置文件和网络连接")

if __name__ == "__main__":
    main() 