from base64 import b64encode
from engine import evaluate_expression
from flask import Flask, request, render_template
import pandas as pd
import datetime as dt

import os
from dotenv import load_dotenv
load_dotenv()

# Create the Flask app
app = Flask(__name__)

app.config['TEMPLATES_AUTO_RELOAD'] = True

def get_records():
    market_info = pd.read_csv("cache/full_market_data.csv")
    etfs_created = pd.read_csv("cache/etfs_created.csv")

    records = []

    for i, row in market_info[['ticker','subtitle']].dropna().drop_duplicates().iterrows():
        record = {}
        record['ticker'] = row['ticker']
        record['user'] = "Kalshi" 
        record['description'] = row['subtitle']
        records.append(record)

    for i, row in market_info[['event_ticker','event_title']].dropna().drop_duplicates().iterrows():
        record = {}
        record['ticker'] = row['event_ticker']
        record['user'] = "Kalshi" 
        record['description'] = row['event_title']
        records.append(record)

    for i, row in market_info[['series_ticker','series_title']].dropna().drop_duplicates().iterrows():
        record = {}
        record['ticker'] = row['series_ticker']
        record['user'] = "Kalshi"
        record['description'] = row['series_title']
        records.append(record)

    for i, row in etfs_created.iterrows():
        record = {}
        record['ticker'] = row['ticker']
        record['user'] = row['user']
        record['description'] = row['expression']
        records.append(record)

    return records

records = get_records()

def remove_comments(code):
    # Split the code into a list of lines
    lines = code.split("\n")

    # Initialize an empty list to store the non-commented lines
    cleaned_lines = []

    # Iterate over the lines of code
    for line in lines:
        # If the line does not start with a comment character, add it to the cleaned_lines list
        if not line.strip().startswith("#"):
            cleaned_lines.append(line)

    # Join the cleaned lines into a single string and return it
    return "\n".join(cleaned_lines)

def graph_expression(expression):
    # Evaluate the expression and get the series of numbers
    returns = evaluate_expression(expression).sort_index()
    prices = 100 * (1 + returns).cumprod()
    x_values = returns.index.astype(str).tolist()
    y_values = list(map(lambda x: round(x, 2), prices))

    if len(x_values) > 0:
        starting_x_value = str(returns.index[0] - dt.timedelta(days=1))
        starting_y_value = 100
        x_values = [starting_x_value] + x_values
        y_values = [starting_y_value] + y_values

    APY = round(100 * (1 + returns.mean()) ** 252 - 100, 2)
    annualized_volatility = round(100 * returns.std() * 252 ** 0.5, 2)
    sharpe_ratio = round(returns.mean() / returns.std() * 252 ** 0.5, 2)
    max_drawdown = round(100 * (1 - prices.div(prices.cummax()).min()), 2)

    new_expression = expression
    new_expression += "\n\n## APY: " + str(APY) + "%"
    new_expression += "\n## Annualized Volatility: " + str(annualized_volatility) + "%"
    new_expression += "\n## Sharpe Ratio: " + str(sharpe_ratio)
    new_expression += "\n## Max Drawdown: " + str(max_drawdown) + "%"

    return render_template('home_test.html', plot_labels=x_values, plot_values=y_values, expression=new_expression, table_data=records)

def upload_expression(expression, ticker):
    expression_to_upload = remove_comments(expression)

    ## add to etfs_created.csv
    etfs_created = pd.read_csv("cache/etfs_created.csv")
    etfs_created = etfs_created.append({'ticker': ticker, 'expression': expression_to_upload, 'user': os.environ['KALSHI_PROD_EMAIL']}, ignore_index=True)
    etfs_created.to_csv("cache/etfs_created.csv", index=False)

    ## add to records
    records.append({'ticker': ticker, 'user': os.environ['KALSHI_PROD_EMAIL'], 'description': expression_to_upload})

    return render_template('home_test.html', plot_labels=[], plot_values=[], expression=expression, table_data=records)


# Set the route for the home page
@app.route('/', methods=['GET', 'POST'])
def home():
  if request.method == 'POST':
        # Get the expression from the text box
        expression = request.form['expression']
        if 'evaluate-button' in request.form:
            return graph_expression(expression)
        elif 'upload-button' in request.form:
            etf_name = 'ETF_' + str(abs(hash(expression)))[:6]
            return upload_expression(expression, etf_name)
        else:
            return render_template('home_test.html',plot_labels=[], plot_values=[], expression = '## Write some ETF-LANG here...', table_data=records)
    
  else:
    # Render the home page template
    return render_template('home_test.html',plot_labels=[], plot_values=[], expression = '## Write some ETF-LANG here...', table_data=records)

# Run the app
if __name__ == '__main__':
  app.run()
