from screener import SmartMoneyScreener

def main():
    screener = SmartMoneyScreener()
    print("Testing SmartMoneyScreener Option 1 (run_screening)...")
    df = screener.run_screening(max_stocks=10)
    if not df.empty:
        print("Columns:", df.columns.tolist())
        print("Data size:", len(df))
        for idx, row in df.iterrows():
            print(f"- {row['ticker']}: {row['name']}, 외국인 {row['foreign_buy']}, 기관 {row['inst_buy']}")
    else:
        print("DataFrame is empty.")

if __name__ == "__main__":
    main()
