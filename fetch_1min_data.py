import argparse #lets your script accept command-line arguments (like file names or ticker symbols).
import time
from ib_async import IB
from ib_async.contract import Stock
import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd


tz = ZoneInfo("America/New_York") #Convert to US timezone
#======================BELOW IS Async VERSION, use command line to control========================

# Fucntions that fetches data for a single symbol
# symbol: str -> this is a hint that symbol should be a string only
async def fetch_data(ib: IB, symbol: str):
    print(f"== Requesting data for {symbol} ==")

    start = time.perf_counter() 

    start_date = datetime(2025, 9, 1, 9, 30, 0, tzinfo=tz)
    end_date = datetime(2025, 9, 4, 18, 00, 0, tzinfo=tz)
    current_end = end_date

    all_bars = []

    try:
        contract = Stock(symbol, "SMART", "USD")
        barSizeSetting = "1 min"
        whatToShow = "TRADES"
        useRTH = True
        
        window_days = 1
        
        while current_end > start_date:
            # Always request 1 D, but clamp to start_date if less than 1 day left
            chunk_start = max(current_end - timedelta(days=window_days), start_date)
            duration_str = f"{window_days} D"
            endDateTime = current_end.strftime("%Y%m%d %H:%M:%S")

            print(
                f"\nRequesting chunk: {duration_str} ending at {endDateTime} "
                f"(from {chunk_start} to {current_end})"
            )

            bars = await ib.reqHistoricalDataAsync(
                contract,
                endDateTime=endDateTime,
                durationStr=duration_str,
                barSizeSetting=barSizeSetting,
                whatToShow=whatToShow,
                useRTH=useRTH
            )

            # Filter bars to within the window you actually want
            filtered_bars = [
                bar for bar in bars
                if chunk_start <= bar.date < current_end
            ]

            if not filtered_bars:
                print("  No bars received for this chunk!")
            else:
                print(f"Before: {len(all_bars)} bars")
                all_bars = filtered_bars + all_bars
                print(f"After: {len(all_bars)} bars")

            current_end = chunk_start  # Move window back

        print(f"\n=== DONE! Total bars collected for {symbol}: {len(all_bars)} ===")
        print("\nFirst 2 bars:")
        for bar in all_bars[:2]:
            print(f"{bar.date} O={bar.open:.2f} H={bar.high:.2f} L={bar.low:.2f} C={bar.close:.2f} V={int(bar.volume)}")

        print("\nLast 2 bars:")
        for bar in all_bars[-2:]:
            print(f"{bar.date} O={bar.open:.2f} H={bar.high:.2f} L={bar.low:.2f} C={bar.close:.2f} V={int(bar.volume)}")
            
        # print(f"TYPE OF all_bars: {all_bars[1]}")
        """
        Output of 1 bar:
        TYPE OF all_bars: BarData(date=datetime.datetime(2025, 9, 2, 9, 31, tzinfo=zoneinfo.ZoneInfo(key='US/Eastern')), open=84.59, high=84.59, low=84.25, close=84.44, volume=894442.0, average=84.412, barCount=2976)
        """

        
        # Put each bar into a dictionary, then create a DataFrame from the list of dictionaries
        # and create a CSV file
        all_bars_data = [{
                'date': bar.date,
                'open': bar.open,
                'high': bar.high,
                'low': bar.low,
                'close': bar.close,
                'volume': bar.volume,
            } for bar in all_bars]

        df = pd.DataFrame(all_bars_data)
        print(df.head())
        df.to_csv(f'{start_date}_{end_date}_data.csv', index=False)

    except Exception as e:
        print(f"Error fetching {symbol}: {e}")

    end = time.perf_counter()
    print(f"Finished fetching {symbol} in {end - start:.2f} seconds\n")


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
        task = fetch_data(ib, symbol)
        tasks.append(task)

    # 2. Run all tasks concurrently and wait for them all to complete.
    # This is Beth starting her simultaneous exhibition.
    """
    The * Operator: "Unpacking"
    *tasks unpacks a list (or tuple) of tasks into separate arguments.
    """
    await asyncio.gather(*tasks)
    
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