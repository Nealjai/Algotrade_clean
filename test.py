import yfinance as yf
import pandas as pd

df = yf.download('AAPL', period='6mo', interval='1d', progress=False, auto_adjust=False, threads=False)
print('Empty?', df.empty)
print('Columns:', list(df.columns))
print(df.head())