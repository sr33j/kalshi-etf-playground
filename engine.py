# starter client: recommended for all levels of programming experience (what this client is implemented using)
from KalshiClientsBaseV2 import ExchangeClient

import time
import re
import pandas as pd

import os
from dotenv import load_dotenv
load_dotenv()

prod_email = os.environ['KALSHI_PROD_EMAIL'] # change these to be your personal credentials
prod_password = os.environ['KALSHI_PROD_PASSWORD'] # (for extra security, we recommend using a config file)
prod_api_base = "https://trading-api.kalshi.com/trade-api/v2"
exchange_client = ExchangeClient(exchange_api_base=prod_api_base, email = prod_email, password = prod_password)

## implement caching for when we want to do 365 days of data
MAX_DATA_PULL_DAYS = 30
CURRENT_TIME = round(time.time())
START_TIME = CURRENT_TIME - MAX_DATA_PULL_DAYS*24*60*60

def get_price_series_for_ticker(ticker, yes=True):
    ## Pulls historical price series from Kalshi
    all_data = []
    market_history_params = {'ticker': ticker,
                                'limit': 100,
                                'cursor': None,
                                'max_ts': None, # pass in unix_ts
                                'min_ts': START_TIME # passing a recent unix_ts
                                    }
    market_history_response = exchange_client.get_market_history(**market_history_params)
    df = pd.DataFrame(market_history_response['history'])
    all_data.append(df)
    while df.shape[0] > 0 and df['ts'].min() > START_TIME and market_history_response['cursor'] is not None:
        market_history_params['cursor'] = market_history_response['cursor']
        market_history_response = exchange_client.get_market_history(**market_history_params)
        df = pd.DataFrame(market_history_response['history'])
        if df.shape[0] > 0:
            all_data.append(df)

    full_price_data = pd.concat(all_data)
    full_price_data = full_price_data.sort_values('ts')
    full_price_data['datetime'] = pd.to_datetime(full_price_data['ts'], unit='s')
    full_price_data['date'] = full_price_data['datetime'].dt.date

    if yes:
        full_price_data['midprice'] = (full_price_data['yes_bid'] + full_price_data['yes_ask'])/2
    else:
        full_price_data['midprice'] = (full_price_data['no_bid'] + full_price_data['no_ask'])/2
    
    price_series = full_price_data[['date', 'midprice']].groupby('date').last()
    price_series = price_series.sort_index()

    return price_series

def download_all_variable_names():
    all_data = []
    market_params = {'limit':100,
                        'cursor':None, # passing in the cursor from the previous get_markets call
                        'event_ticker': None,
                        'series_ticker': None,
                        'max_close_ts': None, # pass in unix_ts
                        'min_close_ts': START_TIME, # pass in unix_ts
                        'status': None,
                        'tickers':None}

    markets_response = exchange_client.get_markets(**market_params)
    df = pd.DataFrame(markets_response['markets'])
    df = df[['ticker', 'event_ticker', 'open_time', 'close_time']]
    all_data.append(df)
    while df.shape[0] > 0 and pd.to_datetime(df['close_time']).min().timestamp() > START_TIME and markets_response['cursor'] is not None:
        market_params['cursor'] = markets_response['cursor']
        markets_response = exchange_client.get_markets(**market_params)
        df = pd.DataFrame(markets_response['markets'])
        if df.shape[0] > 0:
            df = df[['ticker', 'event_ticker', 'open_time', 'close_time']]
            all_data.append(df)

    full_market_data = pd.concat(all_data)

    def get_series_info(event_ticker):
        event_params = {'event_ticker': event_ticker}
        index = ['event_ticker','series_ticker']
        try:
            event_response = exchange_client.get_event(**event_params)
            series_ticker = event_response['event']['series_ticker']
            return pd.Series([event_ticker, series_ticker], index=index)
        except:  
            return pd.Series([event_ticker, None], index=index)

    series_data = []
    event_tickers = full_market_data['event_ticker'].dropna().unique()
    for event_ticker in event_tickers:
        series_data.append(get_series_info(event_ticker))
    series_df = pd.DataFrame(series_data) 

    full_market_data = full_market_data.merge(series_df, on='event_ticker', how='left')
    full_market_data.to_csv("cache/full_market_data.csv", index=False)

def get_price_series_for_existing_index(index_ticker):
    ## just run evaluate_expression for that index's expression
    pass

def get_price_series_for_series(series_ticker):
    pass

def extract_number_from_string(string):
  # Use a regular expression to search for a sequence of one or more digits
  # followed by a decimal point and zero or more digits at the end of the string
  match = re.search(r'\d+\.\d*$', string)
  if match:
    # If a match is found, return the matched digits as a float
    return float(match.group())
  else:
    # If no match is found, return None
    return None

def get_price_series_for_event(event_ticker):
    all_market_data = pd.read_csv("cache/full_market_data.csv")
    event_data = all_market_data[all_market_data['event_ticker'] == event_ticker]


def get_price_series_for_instrument(instrument_name):

    all_market_data = pd.read_csv("cache/full_market_data.csv")

    ## TODO: add existing indices
    normal_tickers = list(all_market_data['ticker'].dropna().unique())
    event_tickers = list(all_market_data['event_ticker'].dropna().unique()) 
    series_tickers = list(all_market_data['series_ticker'].dropna().unique())
    
    if instrument_name in normal_tickers:
        return get_price_series_for_existing_index(instrument_name)
    elif instrument_name in event_tickers:
        return get_price_series_for_event(instrument_name)
    elif instrument_name in series_tickers:
        return get_price_series_for_series(instrument_name)
    else:
        raise Exception("Instrument not found")

def clean_expression(expression):
    pass

def variable_name_generator():
    letters = 'abcdefghijklmnopqrstuvwxyz'
    for c1 in letters:
        yield c1
    for c1 in letters:
        for c2 in letters:
            yield c1 + c2

        
def evaluate_expression(expression):
    ## TODO: validate the absolute sum of the ticker weights is 1

    ## pull all variables from the expression
    new_expression = expression
    all_market_data = pd.read_csv("cache/full_market_data.csv")

    all_instruments = list(set(all_market_data['ticker'].dropna().tolist() + all_market_data['event_ticker'].dropna().tolist() + all_market_data['series_ticker'].dropna().tolist()))
    # sort instruments by string length so that we replace the longer ones first
    all_instruments.sort(key=len, reverse=True)

    ## get the values of all variables from the expression, make into a df and fill in missing values
    all_price_data = []
    varname_generator = variable_name_generator()
    for instrument in all_instruments:
        if instrument in new_expression:
            var = next(varname_generator)
            new_expression = new_expression.replace(instrument, var)
            price_series = get_price_series_for_instrument(instrument)
            price_series.name = var
            all_price_data.append(price_series)

    ## put then in a df into a dictionary of series representation .to_dict(orient='series')
    instrument_prices = pd.concat(all_price_data, axis=1).fillna(method='ffill')
    variable_dictionary = instrument_prices.to_dict(orient='series')

    ## use eval() to evaluate the expression and add the dictionary as an argument
    index_price_series = eval(new_expression, variable_dictionary)
    return index_price_series


def main():
    # print(get_price_series_for_ticker('ACPI-22-B5.5'))
    # download_all_variable_names()
    # print(pd.read_csv("cache/full_market_data.csv").head())
    generator = variable_name_generator()
    for i in range(100):
        print(next(generator)) 


if __name__ == "__main__":
    main()