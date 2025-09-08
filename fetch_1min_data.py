import argparse #lets your script accept command-line arguments (like file names or ticker symbols).
import time
from ib_async import IB
from ib_async.contract import Stock
import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd
import pandas_market_calendars as mcal

#======================BELOW IS Async VERSION, use command line to control========================
# Fucntions that fetches data for a single symbol
# symbol: str -> this is a hint that symbol should be a string only
async def fetch_data(ib: IB, symbol: str):


    tz = ZoneInfo("America/New_York") #Convert to US timezone
    start = time.perf_counter() 
    start_date = datetime(2021, 1, 1, 9, 30, 0, tzinfo=tz)
    # start_date = datetime(2016, 1, 5, 9, 30, 0, tzinfo=tz)
    # end_date = datetime(2023, 2, 17, 18, 00, 0, tzinfo=tz)
    end_date = datetime(2022, 12, 31, 18, 00, 0, tzinfo=tz)

    # Get NYSE trading sessions (market open times)
    # Set up NYSE calendar and get the schedule of trading days
    nyse = mcal.get_calendar('NYSE')
    schedule = nyse.schedule(start_date=start_date.date(), end_date=end_date.date())
    # Convert schedule to your Amer/New York timezone
    schedule['market_open'] = schedule['market_open'].dt.tz_convert(tz)
    schedule['market_close'] = schedule['market_close'].dt.tz_convert(tz)

    all_bars = []
    
    
    try:
        contract = Stock(symbol, "SMART", "USD")
        barSizeSetting = "1 min"
        whatToShow = "TRADES"
        useRTH = True
        
        MARKET_OPEN_HOUR = 9
        MARKET_OPEN_MIN = 30
        MARKET_CLOSE_HOUR = 18
        MARKET_CLOSE_MIN = 0
        window_days = 30
        trading_opens = schedule['market_open']
        num_trading_days = len(trading_opens)
        
        for chunk_end_idx in range(num_trading_days - 1, -1, -window_days):
            # Figure out window start for this chunk
            chunk_start_idx = max(0, chunk_end_idx - window_days + 1)

            # Get the trading day datetimes for this chunk's boundaries
            start_of_chunk_day = trading_opens.iloc[chunk_start_idx]
            end_of_chunk_day = trading_opens.iloc[chunk_end_idx]

            # Build the exact datetimes for the API call window
            chunk_start_time = start_of_chunk_day.replace(
                hour=MARKET_OPEN_HOUR, 
                minute=MARKET_OPEN_MIN, 
                second=0
            )
            chunk_end_time = end_of_chunk_day.replace(
                hour=MARKET_CLOSE_HOUR, 
                minute=MARKET_CLOSE_MIN, 
                second=0
            )

            # Clamp to user-requested global range
            chunk_start_time = max(chunk_start_time, start_date)
            chunk_end_time = min(chunk_end_time, end_date)

            # Explain what we're fetching
            print(f"Requesting {window_days} trading days: {chunk_start_time} to {chunk_end_time}")

            # 3. Fetch data

            bars = await ib.reqHistoricalDataAsync(
                contract=contract,
                endDateTime=chunk_end_time.strftime("%Y%m%d %H:%M:%S"),
                durationStr=f"{window_days} D",
                barSizeSetting=barSizeSetting,
                whatToShow=whatToShow,
                useRTH=useRTH
            )

            # 4. Only keep bars actually in this chunk window
            filtered_bars = [bar for bar in bars if chunk_start_time <= bar.date < chunk_end_time]
            if not filtered_bars:
                print("  No bars received for this chunk!")
            else:
                all_bars = filtered_bars + all_bars  # Prepend for chronological order

        print(f"\n=== DONE! Total bars collected for {symbol}: {len(all_bars)} ===")


        # print(f"TYPE OF all_bars: {all_bars[1]}")
        """
        Output of 1 bar:
        TYPE OF all_bars: BarData(date=datetime.datetime(2025, 9, 2, 9, 31, tzinfo=zoneinfo.ZoneInfo(key='US/Eastern')), open=84.59, high=84.59, low=84.25, close=84.44, volume=894442.0, average=84.412, barCount=2976)
        """
        # Put each bar into a dictionary, then create a DataFrame from the list of dictionaries
        # and create a CSV file
        df = pd.DataFrame(
            [(bar.date, bar.open, bar.high, bar.low, bar.close, bar.volume) for bar in all_bars],
            columns=['date', 'open', 'high', 'low', 'close', 'volume']
        )

        # df = pd.DataFrame(all_bars_data)
        # print(df.head())
        safe_start = start_date.strftime('%Y%m%d')
        safe_end = end_date.strftime('%Y%m%d')
        filename = f'{safe_start}_{safe_end}_data.csv'
        df.to_csv(filename, index=False)

    except Exception as e:
        print(f"Error fetching {symbol}: {e}")

    end = time.perf_counter()
    print(f"Finished fetching {symbol} in {end - start:.2f} seconds\n")


# Main function that connects once and launches all requests concurrently
# symbols is provided by user in the command line
async def main(symbols):
    #Creates and connects an IB API client (only once).
    ib = IB()
    # await ib.connectAsync("127.0.0.1", 7496, clientId=1) #live
    await ib.connectAsync("127.0.0.1", 7497, clientId=1)

    # start = time.perf_counter()

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
    
    # end = time.perf_counter()
    # print(f"Finished fetching {len(symbols)} symbols in {end - start:.2f} seconds")
    
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