import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

class SMABacktester():
    def __init__(self, stock ,SMA_S,SMA_L,start, end):
        self.stock = stock
        self.SMA_S = SMA_S
        self.SMA_L = SMA_L
        self.start = start
        self.end = end
        self.results = None #placeholder for now
        self.get_data()
    
    def get_data(self):
        df = yf.download(self.stock, start=self.start, end=self.end)
        data = df["Close"][f'{self.stock}'].to_frame() 
        data['returns'] = np.log(data[f'{self.stock}'].div(data[f'{self.stock}'].shift(1)))
        data['SMA_S'] = data[f"{self.stock}"].rolling(int(self.SMA_S)).mean()
        data['SMA_L'] = data[f"{self.stock}"].rolling(int(self.SMA_L)).mean()
        data.dropna(inplace=True)
        self.data2 = data
        return self.data2
        
    def test_results(self):
        data = self.data2.copy()
        data["position"]=np.where(data["SMA_S"]>data["SMA_L"],1,0)
        
        #ret_startegy is the return every interval (D, W, Month etc)
        data["ret_strategy"]=data["returns"] * data.position.shift(1)
        data.dropna(inplace=True)
        
        data["returnsbh"]=data["returns"].cumsum().apply(np.exp)
        
        #Strategybh shows the cul return overtime
        data["strategybh"]=data["ret_strategy"].cumsum().apply(np.exp)
        perf=data["strategybh"].iloc[-1]
        outperf=perf-data["returnsbh"].iloc[-1]
        self.results = data
        
        # ret = np.exp(data["ret_strategy"].sum())
        # std = data["ret_strategy"].std()*np.sqrt(252)
        
        return round(perf,6), round(outperf,6)
        
    def Plot_result(self):
        if self.results is None:
            print("No results to plot yet. Run test_results() first.")
        else:
            #plotting the cumulative return graph of both strategy
            self.results[["returnsbh","strategybh"]].plot(figsize=(12,8), fontsize=15,
            title=f"{self.stock} | SMA{self.SMA_S} & SMA{self.SMA_L}")