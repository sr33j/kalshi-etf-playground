from base64 import b64encode
from engine import evaluate_expression
import flask
from flask import Flask, request, render_template
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg
from io import BytesIO

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
    returns = evaluate_expression(expression)
    prices = 100 * (1 + returns).cumprod()

    # # Plot the numbers
    # fig, ax = plt.subplots()
    # plt.figure(facecolor='#797979')
    # plt.figure(figsize=(2, 1), dpi=80)
    # ax.set_facecolor('#333333')

    # for tick in ax.xaxis.get_ticklabels():
    #     tick.set_rotation(45)

    # ax.set_title("Index Price Time Series Starting with $100")
    # ax.set_xlabel("Date")
    # ax.set_ylabel("Price (USD)")

    # ax.plot(prices, color='green')


    # # Render the plot as a png image
    # output = BytesIO()
    # FigureCanvasAgg(fig).print_png(output)
    
    # # Encode the image as a base64 string
    # plot_data = "data:image/png;base64," + b64encode(output.getvalue()).decode()
    
    # Return the image as the response
    return render_template('home.html', plot_labels=returns.index.tolist(), plot_values=prices.tolist())
  else:
    # Render the home page template
    return render_template('home.html',plot_labels=[], plot_values=[])

# Run the app
if __name__ == '__main__':
  app.run()
