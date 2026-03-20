import os
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, HumanMessage
from rich.traceback import install
install()

load_dotenv()

API_KEY=os.getenv("ARK_API_KEY")
MODEL=os.getenv("MODEL")
BASE_URL=os.getenv("BASE_URL")

class SmartTranslator:
    def __init__(self):
        self.model = init_chat_model(
            model=MODEL,
            model_provider="openai",
            base_url=BASE_URL,
            api_key=API_KEY,
            temperature=0.3
        )

    def translate(self,text:str,target_lang:str="中文",style:str="正式"):
        system_prompt = f"""你是一个专业的翻译助手。

          任务：
          1. 自动检测输入文本的语言
          2. 翻译成{target_lang}
          3. 使用{style}风格
          4. 如果有专业术语，在翻译后用括号标注原文

          输出格式：
          【原语言】: xxx
          【翻译】: xxx
          【术语解释】: （如果有）
          """
        messages=[
            SystemMessage(content=system_prompt),
            HumanMessage(content=text)
        ]
        response = self.model.invoke(messages)
        return response.content
    
def main():
    translator=SmartTranslator()
    print("🌍 智能翻译助手（LangChain 1.0）")
    print("=" * 50)

    # 示例1：英译中（技术文本）
    text1 = "LangChain is a framework for developing applications powered by large language models."
    print(f"\n📝 原文: {text1}")
    print(f"\n🔄 翻译结果:\n{translator.translate(text1, '中文', '正式')}")

    print("\n" + "=" * 50)

    # 示例2：中译英（口语风格）
    text2 = "这个框架真的超级好用，强烈推荐！"
    print(f"\n📝 原文: {text2}")
    print(f"\n🔄 翻译结果:\n{translator.translate(text2, '英文', '口语')}")

    print("\n" + "=" * 50)

    # 交互模式
    print("\n💬 进入交互模式（输入 'quit' 退出）\n")
    while True:
        text = input("请输入要翻译的文本: ")
        if text.lower() == 'quit':
            break

        target = input("目标语言（默认中文）: ") or "中文"
        style = input("翻译风格（正式/口语/文学，默认正式）: ") or "正式"

        print(f"\n🔄 翻译中...\n")
        result = translator.translate(text, target, style)
        print(result)
        print("\n" + "-" * 50 + "\n")

if __name__ == "__main__":
    main()