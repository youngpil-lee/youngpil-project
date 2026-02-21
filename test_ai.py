from kr_ai_analyzer import KrAiAnalyzer

def main():
    analyzer = KrAiAnalyzer()
    print("Testing analyze_stock...")
    result = analyzer.analyze_stock("005930")
    print("Result:", result)

if __name__ == "__main__":
    main()
