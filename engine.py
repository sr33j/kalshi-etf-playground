# starter client: recommended for all levels of programming experience (what this client is implemented using)
from KalshiClientsBaseV2 import ExchangeClient

import time
import re
import pandas as pd
import numpy as np
import datetime as dt

import os
from dotenv import load_dotenv
load_dotenv()

import warnings
warnings.simplefilter("ignore")

prod_email = os.environ['KALSHI_PROD_EMAIL'] # change these to be your personal credentials
prod_password = os.environ['KALSHI_PROD_PASSWORD'] # (for extra security, we recommend using a config file)
prod_api_base = "https://trading-api.kalshi.com/trade-api/v2"
exchange_client = ExchangeClient(exchange_api_base=prod_api_base, email = prod_email, password = prod_password)

## implement caching for when we want to do 365 days of data
MAX_DATA_PULL_DAYS = 30
CURRENT_TIME = round(time.time())
START_TIME = CURRENT_TIME - MAX_DATA_PULL_DAYS*24*60*60

def get_return_series_for_ticker(ticker, yes=True):
    ## check if we have the data in cache
    if os.path.exists("cache/price_data/{}.csv".format(ticker)):
        return_series = pd.read_csv("cache/price_data/{}.csv".format(ticker), index_col=0, parse_dates=True)
        return_series = return_series.sort_index()[return_series.columns[0]]
        return_series.index  = return_series.index.map(lambda x: x.date())
        return return_series

    print("downloading return series for {}".format(ticker))

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
    if df.shape[0] == 0:
        return pd.Series([])
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
    
    price_series = full_price_data[['date', 'midprice']].groupby('date')['midprice'].last()
    price_series = price_series.sort_index()

    date_range = pd.date_range(start=price_series.index.min(), end=price_series.index.max())
    price_series = price_series.reindex(date_range)
    price_series = price_series.fillna(method='ffill')

    return_series = price_series.pct_change()

    ## save to csv in cache/price_data
    return_series.to_csv("cache/price_data/{}.csv".format(ticker))

    return return_series

def download_all_kalshi_market_info():
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
    df = df[['ticker', 'event_ticker', 'open_time', 'close_time', 'subtitle']]
    all_data.append(df)
    while df.shape[0] > 0 and pd.to_datetime(df['close_time']).min().timestamp() > START_TIME and markets_response['cursor'] is not None:
        market_params['cursor'] = markets_response['cursor']
        markets_response = exchange_client.get_markets(**market_params)
        df = pd.DataFrame(markets_response['markets'])
        if df.shape[0] > 0:
            df = df[['ticker', 'event_ticker', 'open_time', 'close_time', 'subtitle']]
            all_data.append(df)

    full_market_data = pd.concat(all_data)

    def get_series_info(event_ticker):
        event_params = {'event_ticker': event_ticker}
        index = ['event_ticker','series_ticker','event_title','series_title']
        try:
            event_response = exchange_client.get_event(**event_params)
            series_ticker = event_response['event']['series_ticker']
            event_title = event_response['event']['title']
            try:
                series_response = exchange_client.get_series(series_ticker=series_ticker)
                series_title = series_response['series']['title']
                return pd.Series([event_ticker, series_ticker, event_title, series_title], index=index)
            except:
                return pd.Series([event_ticker, series_ticker, event_title, None], index=index)
        except:  
            return pd.Series([event_ticker, None, None, None], index=index)

    series_data = []
    event_tickers = full_market_data['event_ticker'].dropna().unique()
    for event_ticker in event_tickers:
        series_data.append(get_series_info(event_ticker))
    series_df = pd.DataFrame(series_data) 

    full_market_data = full_market_data.merge(series_df, on='event_ticker', how='left')
    full_market_data.to_csv("cache/full_market_data.csv", index=False)

def get_return_series_for_existing_index(index_ticker):
    ## just run evaluate_expression for that index's expression
    pass

def get_return_series_for_series(series_ticker):
    all_market_data = pd.read_csv("cache/full_market_data.csv")
    series_data = all_market_data[all_market_data['series_ticker'] == series_ticker].drop_duplicates(subset=['event_ticker'])
    if series_data.shape[0] == 0:
        raise Exception("Series not found")
    elif series_data.shape[0] == 1:
        return get_return_series_for_event(series_data['event_ticker'].unique()[0])
    else:
        all_return_series = []
        for event_ticker in series_data['event_ticker'].unique():
            return_series = get_return_series_for_event(event_ticker)
            return_series.name = event_ticker
            all_return_series.append(return_series)
        event_returns_df = pd.concat(all_return_series, axis=1)
        # event_returns_df = event_returns_df.fillna(0)

        ## create a dataframe over time with a column for each event. 
        ## the values will be if the event contract is opened during that day
        contract_open = pd.DataFrame(0, index=event_returns_df.index, columns=event_returns_df.columns)
        for event_ticker in contract_open.columns:
            event_data = series_data[series_data['event_ticker'] == event_ticker]
            open_date = pd.to_datetime(event_data['open_time'].unique()[0]).date()
            close_date = pd.to_datetime(event_data['close_time'].unique()[0]).date()
            while open_date < close_date:
                contract_open.loc[open_date, event_ticker] = 1
                open_date += dt.timedelta(days=1)

        ## normalize each row in contract_open to sum to 1
        contract_open = contract_open.div(contract_open.sum(axis=1), axis=0)

        ## multiply each column in event_returns_df by the corresponding column in contract_open
        ## then sum the columns to get the return series for the series
        return_series = (event_returns_df * contract_open).sum(axis=1)

        return return_series

def extract_number_from_string(string):
  # Use a regular expression to search for a sequence of one or more digits
  # followed by a decimal point and zero or more digits at the end of the string
  match = re.search(r'\d+\.\d*$', string)
  if match:
    # If a match is found, return the matched digits as a float
    return float(match.group())
  else:
    # If no match is found, return None
    return 0

def get_return_series_for_event(event_ticker):
    all_market_data = pd.read_csv("cache/full_market_data.csv")
    event_data = all_market_data[all_market_data['event_ticker'] == event_ticker]
    if event_data.shape[0] == 0:
        raise Exception("Event not found")
    elif event_data.shape[0] == 1:
        return get_return_series_for_ticker(event_data['ticker'].iloc[0])
    else:
        ## sort the tickers by the number at the end of the ticker
        event_data['ticker_number'] = event_data['ticker'].apply(extract_number_from_string)
        event_data = event_data.sort_values('ticker_number')

        all_ticker_return_data = []
        for ticker in event_data['ticker']:
            return_series = get_return_series_for_ticker(ticker)
            return_series.name = ticker
            all_ticker_return_data.append(return_series)

        all_ticker_return_data = pd.concat(all_ticker_return_data, axis=1)
        ## fill in missing values with the last value
        # all_ticker_return_df = all_ticker_return_data.fillna(0)

        ## now I want to return a weighted sum of each tickers return series where the weights 
        ## are linearly interporlated between -1 to 1, and then normalized such that the 
        ## absolute value of the weights sum to 1
        weights = np.linspace(-1, 1, all_ticker_return_data.shape[1])
        weights = weights / np.abs(weights).sum()
        weight_series = pd.Series(weights, index=all_ticker_return_data.columns)
        weighted_return_series = all_ticker_return_data.dot(weight_series)
        return weighted_return_series

def get_return_series_for_instrument(instrument_name):

    all_market_data = pd.read_csv("cache/full_market_data.csv")

    ## TODO: add existing indices
    normal_tickers = list(all_market_data['ticker'].dropna().unique())
    event_tickers = list(all_market_data['event_ticker'].dropna().unique()) 
    series_tickers = list(all_market_data['series_ticker'].dropna().unique())
    
    if instrument_name in normal_tickers:
        return get_return_series_for_ticker(instrument_name)
    elif instrument_name in event_tickers:
        return get_return_series_for_event(instrument_name)
    elif instrument_name in series_tickers:
        return get_return_series_for_series(instrument_name)
    else:
        raise Exception("Instrument not found {}".format(instrument_name))

def variable_name_generator():
    letters = 'abcdefghijklmnopqrstuvwxyz'
    for c1 in letters:
        yield c1
    for c1 in letters:
        for c2 in letters:
            yield c1 + c2

def remove_leading_trailing_zeros(series):
    # Remove leading zeros
    while len(series) > 0 and series[0] == 0:
        series = series[1:]
    # Remove trailing zeros
    while len(series) > 0 and series[-1] == 0:
        series = series[:-1]
    
    return series


def evaluate_expression(expression):
    ## TODO: validate the absolute sum of the ticker weights is 1

    ## pull all variables from the expression
    new_expression = expression
    all_market_data = pd.read_csv("cache/full_market_data.csv")

    all_instruments = list(set(all_market_data['ticker'].dropna().tolist() + all_market_data['event_ticker'].dropna().tolist() + all_market_data['series_ticker'].dropna().tolist()))
    # sort instruments by string length so that we replace the longer ones first
    all_instruments.sort(key=len, reverse=True)

    ## get the values of all variables from the expression, make into a df and fill in missing values
    all_return_data = []
    varname_generator = variable_name_generator()
    for instrument in all_instruments:
        if instrument in new_expression:
            var = next(varname_generator)
            new_expression = new_expression.replace(instrument, var)
            return_series = get_return_series_for_instrument(instrument)
            return_series.name = var
            all_return_data.append(return_series)

    ## put then in a df into a dictionary of series representation .to_dict(orient='series')
    # instrument_returns = pd.concat(all_return_data, axis=1).fillna(0)
    instrument_returns = pd.concat(all_return_data, axis=1)
    variable_dictionary = instrument_returns.to_dict(orient='series')

    ## use eval() to evaluate the expression and add the dictionary as an argument
    index_return_series = eval(new_expression, variable_dictionary)

    ## remove leading and trailing zeros
    index_return_series = remove_leading_trailing_zeros(index_return_series.dropna())

    return index_return_series


def main():
    # series_value = evaluate_expression(".5*CASESURGE-23FEB01-A300 -.5*ACPI")
    # series_value = evaluate_expression("ACPI")
    # print(series_value.dropna())
    # series_value.to_csv("investigation.csv")
    # print(get_return_series_for_ticker('ACPI-22-B5.5'))
    download_all_kalshi_market_info()
    print(pd.read_csv("cache/full_market_data.csv").head())


if __name__ == "__main__":
    main()