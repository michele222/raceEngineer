import dash
from dash import dcc, html
from dash.dependencies import Output, Input
import plotly.graph_objs as go
import requests
import json
import time
from numpy import cumsum

# Initialize the Dash app
app = dash.Dash(__name__)

# Layout of the app
app.layout = html.Div([
    html.H1("Live Lap Time Data"),
    html.Div([
        dcc.Graph(id='live-lap-time-graph'),
        dcc.Interval(
            id='interval-component',
            interval=20000,  # Update every 10 seconds
            n_intervals=0
        ),
        dcc.Slider(
            1, #@TODO: change all these values based on race laps
            80,
            step=None,
            value=3,
            id='lap-slider'
        )
    ])
])

def is_float(element: any) -> bool:
    #If you expect None to be passed:
    if element is None:
        return False
    try:
        float(element)
        return True
    except ValueError:
        return False

def get_driver_laps(data_in):
    driver_laps = {}
    #print(data_in)
    for lap_item in data_in:
        #print(lap_item['driver_number'])
        if lap_item['driver_number'] not in driver_laps:
            #print(f"There is no {lap_item['driver_number']}in the dictionary\n")
            driver_laps[lap_item['driver_number']] = {}
        if is_float(lap_item['lap_duration']):
            driver_laps[lap_item['driver_number']][lap_item['lap_number']] = lap_item['lap_duration']
        #print(f"Adding lap duration {lap_item['lap_duration']} for driver {lap_item['driver_number']} at lap number {lap_item['lap_number']}\n")
    return driver_laps

# Opening JSON file
with open('baku.json') as json_file:
    mock_data = json.load(json_file)

# Callback to update the graph
@app.callback(
    Output('live-lap-time-graph', 'figure'),
            Output('lap-slider', 'value'),
    Input('interval-component', 'n_intervals'),
    Input('lap-slider', 'value')
)
def update_graph_live(n, counter):
    #Perform GET request to get the latest data from the local server
    try:
        response = requests.get(f'https://api.openf1.org/v1/laps?session_key=latest')
        #response = requests.get(f'https://api.openf1.org/v1/laps?session_key=9598&lap_number<{counter}')
        #print(f'https://api.openf1.org/v1/laps?session_key=9598&lap_number<{counter}')
        if response.status_code == 200:
            data = response.json()
        else:
            data = {}
    except Exception as e:
        print(f"Error retrieving data: {e}")
        data = {}
    #data = mock_data

    #counter += 1


    laps_data = get_driver_laps(data)

    # Prepare the traces for the line plot
    traces = []
    for driver, lap_times in laps_data.items():
        #print(f"Driver: {driver} Lap times: {lap_times}/n")
        traces.append(go.Scatter(
            x=list(lap_times.keys()),  # X-axis: lap numbers
            #y=list(lap_times.values()),  # Y-axis: lap times
            y=cumsum(list(lap_times.values())),
            mode='lines+markers',
            name=driver
        ))

    # Create the figure
    fig = go.Figure(
        data=traces,
        layout=go.Layout(
            title='Live Lap Times',
            xaxis={'title': 'Lap Number'},
            yaxis={'title': 'Lap Time (seconds)'},
            hovermode='closest'
        )
    )

    return fig, counter

# Run the Dash app
if __name__ == '__main__':
    app.run_server(debug=True)

    # counter = 10
    # try:
    #     response = requests.get(f'https://api.openf1.org/v1/laps?session_key=9598&lap_number<{counter}')
    #     if response.status_code == 200:
    #         data = response.json()
    #     else:
    #         data = {}
    #     print(response.status_code)
    # except Exception as e:
    # # print(f"Error retrieving data: {e}")
    #     data = {}
    #     print('exception')
    # # data = mock_data
    # print(data)

