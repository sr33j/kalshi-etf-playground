from base64 import b64encode
from engine import evaluate_expression
from flask import Flask, request, render_template
import pandas as pd
import matplotlib.pyplot as plt
import datetime as dt


plt.switch_backend('Agg') 


# Create the Flask app
app = Flask(__name__)

app.config['TEMPLATES_AUTO_RELOAD'] = True

market_info = pd.read_csv("cache/full_market_data.csv").head(20)

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


# Set the route for the home page
@app.route('/', methods=['GET', 'POST'])
def home():
  if request.method == 'POST':
    # Get the expression from the text box
    expression = request.form['expression']
    
    # Evaluate the expression and get the series of numbers
    returns = evaluate_expression(expression).sort_index()
    prices = 100 * (1 + returns).cumprod()
    x_values = returns.index.astype(str).tolist()
    y_values = list(map(lambda x: round(x, 2), prices))

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

    return render_template('home.html', plot_labels=x_values, plot_values=y_values, expression=new_expression, table_data=records)
  else:
    # Render the home page template
    return render_template('home.html',plot_labels=[], plot_values=[], expression = '## Write some ETF-LANG here...', table_data=records)

# Run the app
if __name__ == '__main__':
  app.run()
