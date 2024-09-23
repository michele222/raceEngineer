from datetime import datetime
from pickle import EMPTY_SET, EMPTY_LIST
from statistics import median
from dateutil import parser

import dash
import requests
import json
import time
import plotly.graph_objs as go
from dash import dcc, html
from dash.dependencies import Output, Input
from numpy import cumsum, divide

from src import utils

def get_drivers(data_in):
    # per driver (id is number), returns a dict with listed data
    drivers = {}
    for driver_item in data_in:
        drivers[driver_item['driver_number']] = {
            'driver_number': driver_item['driver_number'],
            'country_code': driver_item['country_code'],
            'first_name': driver_item['first_name'],
            'headshot_url': driver_item['headshot_url'],
            'last_name': driver_item['last_name'],
            'team_colour': '#' + driver_item['team_colour'].lower(),
            'team_name': driver_item['team_name'],
            'name_acronym': driver_item['name_acronym']
        }
    return drivers

with open('mock_data/drivers_baku.json') as json_file:
    mock_drivers_data = json.load(json_file)
drivers = get_drivers(mock_drivers_data)
try:
    response = requests.get(f'https://api.openf1.org/v1/drivers?session_key=latest')
    if response.status_code == 200:
        if len(response.json()) == 0:
            print(f"[{str(datetime.now())}] Server response empty")
        else:
            drivers = get_drivers(response.json())
    else:
        print(f"[{str(datetime.now())}] Server response: {response.status_code}")
except Exception as e:
    print(f"[{str(datetime.now())}] Error retrieving data: {e}")

# Opening JSON files with mock data
with open('mock_data/baku.json') as json_file:
    mock_data = json.load(json_file)
data = mock_data #TODO: data should still be initialized

# Prepare the traces for the line plot
traces = []
for driver in drivers.values():
    traces.append(go.Scatter(
        x = [0],  # X-axis: lap numbers
        y = [0], # Y-axis: cumulated lap times
        mode = 'lines+markers',
        name = driver['name_acronym'],
        line_color = driver['team_colour']
    ))

# Initialize the Dash app
app = dash.Dash(__name__)

# Layout of the app
app.layout = html.Div([
    html.H1("Live Lap Time Data"),
    html.Div([
        dcc.Graph(id = 'live-lap-time-graph',
                  figure= go.Figure(
                        data = traces,
                        layout = go.Layout(
                            title = 'Live Lap Times',
                            xaxis = {'title': 'Lap Number'},
                            yaxis = {'title': 'Lap Time (seconds)', 'autorange': 'reversed'},
                            hovermode = 'closest',
                            height = 1000
                        ))),
        dcc.Interval(
            id = 'interval-component',
            interval = 10000,  # Update every x milliseconds
            n_intervals = 0
        )
    ])
])

def get_driver_laps(data_in):
    #per driver (id is number), returns a dict with lap: lap time
    driver_laps = {}
    for lap_item in data_in:
        if lap_item['driver_number'] not in driver_laps:
            #driver_laps[lap_item['driver_number']] = {}
            if lap_item['lap_number'] == 2:
                lap_start_iso_time = parser.isoparse(lap_item['date_start'])
                driver_laps[lap_item['driver_number']] = {
                    1: float(lap_start_iso_time.strftime("%M")) * 60 + float(lap_start_iso_time.strftime("%S.%f"))
                }
        if utils.is_float(lap_item['lap_duration']):
            driver_laps[lap_item['driver_number']][lap_item['lap_number']] = lap_item['lap_duration']
    return driver_laps

def get_average_laps(data_in):
    #per lap, returns a list with lap times
    avg_laps = {}
    for lap_item in data_in:
        if utils.is_float(lap_item['lap_duration']):
            if lap_item['lap_number'] not in avg_laps:
                avg_laps[lap_item['lap_number']] = []
            avg_laps[lap_item['lap_number']].append(lap_item['lap_duration'])
    for key in avg_laps.keys():
        avg_laps[key] = round(sum(avg_laps[key]) / len(avg_laps[key]), 3)
    return avg_laps

def get_median_laps(data_in):
    #per lap, returns a list with lap times
    avg_laps = {}
    for lap_item in data_in:
        if utils.is_float(lap_item['lap_duration']):
            if lap_item['lap_number'] not in avg_laps:
                avg_laps[lap_item['lap_number']] = []
            if lap_item['lap_number'] == 2:
                if 1 not in avg_laps:
                    avg_laps[1] = []
                lap_start_iso_time = parser.isoparse(lap_item['date_start'])
                avg_laps[1].append(float(lap_start_iso_time.strftime("%M")) * 60
                                   + float(lap_start_iso_time.strftime("%S.%f")))
            avg_laps[lap_item['lap_number']].append(lap_item['lap_duration'])
    for key in avg_laps.keys():
        avg_laps[key] = round(median(avg_laps[key]), 3)
    return avg_laps

def get_moving_average_laps(data_in):
    #per lap, returns a list with lap times
    avg_laps = {}
    for lap_item in data_in:
        if utils.is_float(lap_item['lap_duration']):
            if lap_item['lap_number'] not in avg_laps:
                if lap_item['lap_number'] - 1 in avg_laps:
                    avg_laps[lap_item['lap_number']] = avg_laps[lap_item['lap_number'] - 1].copy()
                else:
                    avg_laps[lap_item['lap_number']] = []
            avg_laps[lap_item['lap_number']].append(lap_item['lap_duration'])
    for key in avg_laps.keys():
        avg_laps[key] = round(sum(avg_laps[key]) / len(avg_laps[key]), 3)
    return avg_laps

def get_driver_diff_avg_laps(data_in):
    # per driver (id is number), returns a dict with lap: lap time - avg(lap time)
    avg_laps = get_average_laps(data_in)
    driver_laps = get_driver_laps(data_in)
    for driver, lap_times in driver_laps.items():
        for lap in lap_times:
            driver_laps[driver][lap] = driver_laps[driver][lap] - avg_laps[lap]
    return driver_laps

def get_driver_diff_moving_avg_laps(data_in):
    # per driver (id is number), returns a dict with lap: lap time - avg(all lap times so far)
    avg_laps = get_moving_average_laps(data_in)
    driver_laps = get_driver_laps(data_in)
    for driver, lap_times in driver_laps.items():
        for lap in lap_times:
            driver_laps[driver][lap] = driver_laps[driver][lap] - avg_laps[lap]
    return driver_laps

def get_driver_diff_median_laps(data_in):
    # per driver (id is number), returns a dict with lap: lap time - median(lap time)
    avg_laps = get_median_laps(data_in)
    driver_laps = get_driver_laps(data_in)
    for driver, lap_times in driver_laps.items():
        for lap in lap_times:
            driver_laps[driver][lap] = driver_laps[driver][lap] - avg_laps[lap]
    return driver_laps

def get_driver_diff_std_laps(data_in, std_lap_time):
    # per driver (id is number), returns a dict with lap: lap time - standard fixed time
    driver_laps = get_driver_laps(data_in)
    for driver, lap_times in driver_laps.items():
        for lap in lap_times:
            driver_laps[driver][lap] = driver_laps[driver][lap] - std_lap_time
    return driver_laps

# Callback to update the graph
@app.callback(Output('live-lap-time-graph', 'figure'),
              Input('interval-component', 'n_intervals'),
              Input('live-lap-time-graph', 'figure')
)
def update_graph_live(n, fig):
    live_data = []
    #Perform GET request to get the latest data from the local server
    try:
        response = requests.get(f'https://api.openf1.org/v1/laps?session_key=latest')
        if response.status_code == 200:
            if len(response.json()) == 0:
                print(f"[{str(datetime.now())}] Server response empty")
            else:
                live_data = response.json()
                #print(data)
        else:
            #data = {}
            print(f"[{str(datetime.now())}] Server response: {response.status_code}")
    except Exception as e:
        print(f"[{str(datetime.now())}] Error retrieving data: {e}")
        #data = {}

    out_figure = fig
    if len(live_data) > 0:
        laps_data = get_driver_diff_median_laps(live_data)

        # Update the traces for the line plot
        out_figure = go.Figure(fig)
        for driver, lap_times in laps_data.items():
            out_figure.update_traces(dict(x=list(lap_times.keys()),
                                          y=cumsum(list(lap_times.values()))),
                                     selector=({'name':drivers[driver]['name_acronym']}))

    return out_figure

# Run the Dash app
if __name__ == '__main__':
    app.run(debug=True)
    #app.run_server(host = '0.0.0.0', debug = False)