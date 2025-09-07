import argparse #lets your script accept command-line arguments (like file names or ticker symbols).
import time
from ib_async import IB, RealTimeBar
from ib_async.contract import Stock
import asyncio


#++++++++++++++++++++++++++++++++++++++++++
"""
Included the breakout function but no real time subscription now, so cant test
Video timestamp: 24:00, need to continue after subscription

"""


#======================BELOW IS Async VERSION, use command line to control========================

# Fucntions that fetches data for a single symbol
# symbol: str -> this is a hint that symbol should be a string only
async def fetch_opening_range(ib: IB, symbol: str, opening_range_minutes: int = 15):
    print(f"== Requesting data for {symbol} ==")

    #Starts a timer to measure how long fetching takes.
    start = time.perf_counter() 

    try:
        contract = Stock(symbol, "SMART", "USD")

        # --- define all API parameters up front!
        endDateTime = "20250906 05:00:00" #this is HK local time
        durationStr = "1 D"
        barSizeSetting = "1 min"
        whatToShow = "TRADES"
        useRTH = True

        # Print the parameters to catch typos
        print( 
            f"contract.symbol={contract.symbol}, "
            f"endDateTime='{endDateTime}', durationStr='{durationStr}', "
            f"barSizeSetting='{barSizeSetting}', whatToShow='{whatToShow}', useRTH={useRTH}"
        )
        
        bars = await ib.reqHistoricalDataAsync(
            contract,
            endDateTime=endDateTime,
            durationStr=durationStr,
            barSizeSetting=barSizeSetting,
            whatToShow=whatToShow,
            useRTH=useRTH
        )
        
        # print(f"Type of bars: {type(bars)}")
        print(f"=== Received {symbol} Bars ===")
        if not bars:
            print(f"No bars received for {symbol}!")
        else:
            for bar in bars[:]:
                print(f"{bar.date} O={bar.open:.2f} H={bar.high:.2f} L={bar.low:.2f} C={bar.close:.2f} V={int(bar.volume)}")
            
            
            #Getting the bars data and put all high and lows in a list -> then find highest and lowest
            opening_range_bars = bars[:opening_range_minutes]
            highs = [bar.high for bar in opening_range_bars]
            lows = [bar.low for bar in opening_range_bars]
            highest_high = max(highs)
            lowest_low = min(lows)
            
            return symbol, highest_high, lowest_low

    except Exception as e:
        print(f"Error fetching {symbol}: {e}")


    end = time.perf_counter()
    print(f"Finished fetching {symbol} in {end - start} seconds")

async def monitor_breakout(ib: IB, symbol: str): #we real request for real time bar here
    
    #This part is telling that we subscibe the 5s real time bar
    ticker = ib.reqRealTimeBars(
        Stock(symbol, "SMART", "USD"),
        barSize=5,
        whatToShow="TRADES",
        useRTH=True
        )

    # Define an event handler to process incoming bars
    """
    Parameters

    bars: a list of RealTimeBar objects (could hold OHLCV data for each time period).
    hasNewBar: a boolean indicating if there is a new bar in this update.
    
    """
    def on_bar(bars: list[RealTimeBar], hasNewBar: bool): #if no susbscription, nth will print out, just error
        print(f"\n--- {symbol} 5-sec bars (count={len(bars)}) ---")
        for bar in bars:
            print(bar)

    ticker.updateEvent += on_bar 
    #this += is not the typical addition, it's adding the on_bar function as an event handler for ticker updates.

    # keep this coroutine alive indefinitely
    await asyncio.Event().wait()





# Main function that connects once and launches all requests concurrently
# symbols is provided by user in the command line
async def main(symbols):
    #Creates and connects an IB API client (only once).
    ib = IB()
    await ib.connectAsync("127.0.0.1", 7497, clientId=1)

    start = time.perf_counter()

    # 1. Create a list of tasks (coroutines), but don't run them yet.
    # This is like setting up all the chess boards.
    coroutine_tasks = []
    for symbol in symbols:
        task = fetch_opening_range(ib, symbol, 15) # this 5 minutes replace the default 15 minutes
        coroutine_tasks.append(task)

    # 2. Run all tasks concurrently and wait for them all to complete.
    # This is Beth starting her simultaneous exhibition.
    """
    The * Operator: "Unpacking"
    *tasks unpacks a list (or tuple) of tasks into separate arguments.
    """
    results = await asyncio.gather(*coroutine_tasks)
    monitors =[]
    for result in results:
        symbol, highest_high, lowest_low = result
        print(f"{symbol}: Highest_high = {highest_high:.2f}, Lowest_low = {lowest_low:.2f}")
        monitors.append(monitor_breakout(ib, symbol)) 
        
    await asyncio.gather(*monitors)

    end = time.perf_counter()
    print(f"Finished fetching {len(symbols)} symbols in {end - start:.2f} seconds")
    
    ib.disconnect()



# start program
# Checks if this file is being run as a script (not imported elsewhere).
if __name__ == "__main__":
    # Parse command line arguments
    # User can type python script.py AAPL MSFT to fetch for multiple symbols.
    #The description is a short message explaining what your script does. This message is shown to the user if they type python script.py --help.
    p = argparse.ArgumentParser(description="Fetch 1-min bars for multiple symbols from IBKR")
    
    """
    nargs="+" means:
    The user must provide at least one symbol (e.g., AAPL),
    But they can provide as many as they want (e.g., AAPL MSFT TSLA).
    help=... provides a description that will show up in the help message.
    
    """
    
    p.add_argument("symbols", nargs="+", help="One or more ticker symbols, e.g. AAPL MSFT TSLA")
    
    args = p.parse_args()

    #Starts the main process with the user’s chosen symbols.
    asyncio.run(main(args.symbols))