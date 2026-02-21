import asyncio
from engine.collectors import EnhancedNewsCollector
from engine.config import SignalConfig
from engine.llm_analyzer import LLMAnalyzer

async def main():
    config = SignalConfig()
    collector = EnhancedNewsCollector(config)
    news = await collector.get_stock_news("005930", 5, "삼성전자")
    print(f"Num news: {len(news)}")
    for n in news:
         print(f" - {n.title}")
         
    llm = LLMAnalyzer()
    print("LLM model:", llm.model)
         
if __name__ == "__main__":
    asyncio.run(main())
