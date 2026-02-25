from kr_ai_analyzer import KrAiAnalyzer

def test():
    analyzer = KrAiAnalyzer()
    print("Testing Market Outlook...")
    result = analyzer.analyze_market_outlook()
    print("\n[RESULT]")
    print(result)

if __name__ == "__main__":
    test()
