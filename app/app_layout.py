import dash

from dash import dcc
from dash import html
import plotly.graph_objs as go
import numpy as np

# Create a Dash application
app = dash.Dash(__name__)

# Sample data for the plots
x = np.linspace(0, 10, 100)
y1 = np.sin(x)
y2 = np.cos(x)
y3 = np.tan(x)
y4 = np.exp(x)
y5 = np.log(x + 1)

# Layout of the Dash application
app.layout = html.Div(children=[
    html.H1(children='Dash Plotly Example with 5 Plots'),

    html.Div(children='''
        Dash: A web application framework for Python.
    '''),

    # Plot 1
    dcc.Graph(
        id='plot-1',
        figure={
            'data': [
                go.Scatter(x=x, y=y1, mode='lines', name='Sine')
            ],
            'layout': go.Layout(
                title='Plot 1: Sine Function',
                xaxis={'title': 'x'},
                yaxis={'title': 'y'}
            )
        }
    ),

    # Plot 2
    dcc.Graph(
        id='plot-2',
        figure={
            'data': [
                go.Scatter(x=x, y=y2, mode='lines', name='Cosine')
            ],
            'layout': go.Layout(
                title='Plot 2: Cosine Function',
                xaxis={'title': 'x'},
                yaxis={'title': 'y'}
            )
        }
    ),

    # Plot 3
    dcc.Graph(
        id='plot-3',
        figure={
            'data': [
                go.Scatter(x=x, y=y3, mode='lines', name='Tangent')
            ],
            'layout': go.Layout(
                title='Plot 3: Tangent Function',
                xaxis={'title': 'x'},
                yaxis={'title': 'y'}
            )
        }
    ),

    # Plot 4
    dcc.Graph(
        id='plot-4',
        figure={
            'data': [
                go.Scatter(x=x, y=y4, mode='lines', name='Exponential')
            ],
            'layout': go.Layout(
                title='Plot 4: Exponential Function',
                xaxis={'title': 'x'},
                yaxis={'title': 'y'}
            )
        }
    ),

    # Plot 5
    dcc.Graph(
        id='plot-5',
        figure={
            'data': [
                go.Scatter(x=x, y=y5, mode='lines', name='Logarithm')
            ],
            'layout': go.Layout(
                title='Plot 5: Logarithm Function',
                xaxis={'title': 'x'},
                yaxis={'title': 'y'}
            )
        }
    ),
])

# Run the application
if __name__ == '__main__':
    app.run_server(debug=True)
