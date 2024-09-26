import dash
import dash_bootstrap_components as dbc
import plotly.graph_objs as go

from datetime import datetime

from dash import dcc, html
from dash.dependencies import Output, Input, State
from numpy import cumsum

from src import utils
from src.race_data import RaceData
from src.utils import current_year

interval = 30 #update every x seconds

# with open('mock_data/drivers_baku.json') as json_file:
#     mock_drivers_data = json.load(json_file)
# drivers = get_drivers(mock_drivers_data)

race = RaceData()

drivers = race.get_drivers()

event = race.get_race_event()
event_title = f'{event["country_name"]} {event["year"]} - {event["location"]}'

# event_title = 'Grand Prix'
# try:
#     response = requests.get(f'https://api.openf1.org/v1/meetings?meeting_key=latest')
#     if response.status_code == 200:
#         if len(response.json()) == 0:
#             print(f"[{str(datetime.now())}] Server response empty")
#         else:
#             event_title = response.json()[0]['meeting_official_name']
#     else:
#         print(f"[{str(datetime.now())}] Server response: {response.status_code}")
# except Exception as e:
#     print(f"[{str(datetime.now())}] Error retrieving data: {e}")

# Opening JSON files with mock data
# with open('mock_data/baku.json') as json_file:
#     mock_data = json.load(json_file)
# data = mock_data #TODO: data should still be initialized

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
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.SLATE])#, update_title=None)

tab1_content = dbc.Card(
    dbc.CardBody(
        [
            html.Div([
                dcc.Graph(id='live-lap-time-graph',
                          figure=go.Figure(
                              data=traces,
                              layout=go.Layout(
                                  title=f'{event_title} - Race Trace',
                                  xaxis={'title': 'Lap Number'},
                                  yaxis={'title': 'Gap (seconds)', 'autorange': 'reversed'},
                                  hovermode='closest',
                                  height=1000
                              ))),
                dcc.Interval(
                    id='interval-component',
                    interval=interval * 1000,  # Update every x milliseconds
                    n_intervals=0,
                    disabled=False
                ),
                dcc.Store(id='drivers-data', data=drivers),
                html.Small(id = "last-update-text", className = "text-muted"),
                dbc.Checkbox(
                    id="live-update-checkbox",
                    label="Live updates",
                    value=True,
                ),
                dbc.Fade(
                    dbc.Card(
                        dbc.CardBody([
                            html.Label("Update interval (seconds)"),
                            dbc.Select(list(range(5, 61, 5)),
                                       interval,
                                       id="interval-select",
                                       )
                        ]),
                        style={"width": "18rem"},
                    ),
                    id="live-update-fade",
                    is_in=True,
                    appear=True,
                ),
                html.Label("Select race"),
                dbc.Select(list(range(current_year(), 2022, -1)),
                           current_year(),
                           id="year-select",
                           ),
                dbc.Select(['latest'],
                           'latest',
                           id="race-select",
                           ),
                #dbc.Button("Go", size="sm"),
            ])
        ]
    ),
    className="mt-3",
)

tab2_content = dbc.Card(
    dbc.CardBody(
        [
            html.P("Nothing to see here yet", className="card-text"),
            dbc.Button("Do nothing", color="danger"),
        ]
    ),
    className="mt-3",
)

tabs = dbc.Tabs(
    [
        dbc.Tab(tab1_content, label="Race Trace"),
        dbc.Tab(tab2_content, label="Live Gaps"),
    ]
)

# Layout of the app
app.layout = html.Div([
    html.H1("raceEngineer"),
    tabs
], className="m-4")


# Callback to update the graph
@app.callback(Output('live-lap-time-graph', 'figure'),
              Output('last-update-text', 'children'),
              Output('drivers-data', 'data'),
              Input('interval-component', 'n_intervals'),
              Input('race-select', 'value'),
              State('live-lap-time-graph', 'figure'),
              State('last-update-text', 'children'),
              State('drivers-data', 'data'),
)
def update_graph_live(n, in_race, fig, last_update_text, in_drivers):
    activator = dash.ctx.triggered_id
    out_figure = fig
    out_text = last_update_text
    out_drivers = {int(i):v for i,v in in_drivers.items()}
    live_race = RaceData(in_race)
    live_data = live_race.get_driver_diff_laps()

    if len(live_data) > 0:
        out_figure = go.Figure(fig)
        out_text = f"Last updated on {utils.timestamp()}"

        if activator == 'race-select':
            live_event = live_race.get_race_event()
            out_figure.layout.title = f'{live_event["country_name"]} {live_event["year"]} - {live_event["location"]}'
            out_figure.data = []
            out_drivers = live_race.get_drivers()
            for driver in out_drivers.values():
                out_figure.add_trace(go.Scatter(
                    x=[0],  # X-axis: lap numbers
                    y=[0],  # Y-axis: cumulated lap times
                    mode='lines+markers',
                    name=driver['name_acronym'],
                    line_color=driver['team_colour']
                ))
        # Update the traces for the line plot
        for driver_id, lap_times in live_data.items():
            out_figure.update_traces(dict(x=list(lap_times.keys()),
                                          y=cumsum(list(lap_times.values()))),
                                     selector=({'name':out_drivers[driver_id]['name_acronym']}))

    return out_figure, out_text, out_drivers

@app.callback(
    Output("live-update-fade", "is_in"),
    Output('interval-component', 'disabled'),
    Input("live-update-checkbox", "value"),
)
def toggle_fade(live_update_checked):
    return live_update_checked, not live_update_checked

@app.callback(
    Output('interval-component', 'interval'),
    Input("interval-select", "value"),
)
def change_live_interval(interval):
    return int(interval)*1000

@app.callback(
    Output('race-select', 'options'),
    Input("year-select", "value"),
)
def change_year_select(year):
    data = RaceData()
    races = data.get_races_of_year(year)
    return [{'label': f'{race_item["country_name"]} - {race_item["location"]} - {race_item["session_name"]}',
             'value': race_id}
            for (race_id, race_item) in races.items()]


# Run the Dash app
if __name__ == '__main__':
    app.run(debug=True)
    #app.run_server(host = '0.0.0.0', debug = False)