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
    y_values = prices.tolist()

    starting_x_value = str(returns.index[0] - dt.timedelta(days=1))
    starting_y_value = 100
    x_values = [starting_x_value] + x_values
    y_values = [starting_y_value] + y_values

    return render_template('home.html', plot_labels=x_values, plot_values=y_values)
  else:
    # Render the home page template
    return render_template('home.html',plot_labels=[], plot_values=[])

# Run the app
if __name__ == '__main__':
  app.run()
