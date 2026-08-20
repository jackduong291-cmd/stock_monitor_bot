from vnstock import Vnstock
import pandas as pd
from datetime import datetime, timedelta

def test():
    symbol = 'PVS'
    print(f"Testing {symbol}")
    today = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=40)).strftime("%Y-%m-%d")
    try:
        stock = Vnstock().stock(symbol=symbol, source='VCI')
        df = stock.quote.history(start=start_date, end=today)
        print("Columns:", df.columns.tolist() if isinstance(df, pd.DataFrame) else type(df))
        if df is not None and not df.empty:
            last_row = df.iloc[-1]
            print(last_row)
    except Exception as e:
        print(f"Error: {e}")

test()
