import argparse #lets your script accept command-line arguments (like file names or ticker symbols).
import time
from ib_async import IB
from ib_async.contract import Stock
import asyncio


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
        endDateTime = ""
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
            endDateTime="",
            durationStr="1 D",
            barSizeSetting="1 min",
            whatToShow="TRADES",
            useRTH=True
        )
        
       # print(f"Type of bars: {type(bars)}")
        print(f"=== Received {symbol} Bars ===")
        if not bars:
            print(f"No bars received for {symbol}!")
        else:
            for bar in bars[:opening_range_minutes]:
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



# Main function that connects once and launches all requests concurrently
# symbols is provided by user in the command line
async def main(symbols):
    #Creates and connects an IB API client (only once).
    ib = IB()
    await ib.connectAsync("127.0.0.1", 7497, clientId=1)

    start = time.perf_counter()

    # 1. Create a list of tasks (coroutines), but don't run them yet.
    # This is like setting up all the chess boards.
    tasks = []
    for symbol in symbols:
        task = fetch_opening_range(ib, symbol, 15) # this 5 minutes replace the default 15 minutes
        tasks.append(task)

    # 2. Run all tasks concurrently and wait for them all to complete.
    # This is Beth starting her simultaneous exhibition.
    """
    The * Operator: "Unpacking"
    *tasks unpacks a list (or tuple) of tasks into separate arguments.
    """
    results = await asyncio.gather(*tasks)
    for result in results:
        symbol, highest_high, lowest_low = result
        print(f"{symbol}: Highest_high = {highest_high:.2f}, Lowest_low = {lowest_low:.2f}")

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