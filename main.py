import dash
import dash_bootstrap_components as dbc
import plotly.graph_objs as go

from dash import dcc, html, ALL
from dash.dependencies import Output, Input, State
from numpy import cumsum

from src import utils
from src.race_data import RaceData
from src.utils import current_year, is_float

interval = 30 #update every x seconds

# with open('mock_data/drivers_baku.json') as json_file:
#     mock_drivers_data = json.load(json_file)
# drivers = get_drivers(mock_drivers_data)

# Initialize the Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.SLATE])#, update_title=None)

tab1_content = html.Div([
                dcc.Graph(id='race-trace-graph',
                          figure=go.Figure(
                              layout=go.Layout(
                                  xaxis={'title': 'Lap Number',
                                         'minallowed': 0,
                                         'tick0': 0,
                                         'dtick': 5,
                                         'zeroline': False,
                                         'gridcolor':'#333333',
                                         'minor': {'ticklen': 3,
                                                   'dtick': 1,
                                                   'showgrid': True}},
                                  yaxis={'title': 'Gap (seconds)',
                                         'autorange': 'reversed',
                                         'zeroline': False,
                                         'gridcolor':'#333333'},
                                  hovermode='closest',
                                  height=1000,
                                  plot_bgcolor='#111111',
                                  paper_bgcolor='rgba(0,0,0,0)',
                                  font_color='#999999'
                              ))),
                dcc.Interval(
                    id='interval-component',
                    interval=interval * 1000,  # Update every x milliseconds
                    n_intervals=0,
                    disabled=True
                ),
                dcc.Store(id='drivers-data', data={})
            ])


tab2_content = html.Div([
                dbc.Row([
                    dbc.Col([dbc.Table([html.Thead(html.Tr([html.Th("Pos"),
                                                           html.Th("Driver"),
                                                           html.Th("Gap (Leader)"),
                                                           html.Th("Gap (Interval)"),
                                                            html.Th(dbc.Checkbox(
                                                id="check-all-drivers",
                                                value=True,
                                            ))])),
                                      html.Tbody(id='live-gaps-table')],
                                      striped=True, bordered=True, hover=True),
                            dbc.Button("Filter drivers", id="btn-filter-drivers", size="sm")],
                            width = 2),
                    dbc.Col(
                        dcc.Graph(id='live-gaps-graph',
                                  figure=go.Figure(
                                      layout=go.Layout(
                                          xaxis={'title': 'Time',
                                                 'zeroline': False,
                                                 'gridcolor': '#333333'},
                                          yaxis={'title': 'Gap (seconds)',
                                                 'autorange': 'reversed',
                                                 'zeroline': False,
                                                 'gridcolor': '#333333'},
                                          hovermode='closest',
                                          height=1000,
                                          plot_bgcolor='#111111',
                                          paper_bgcolor='rgba(0,0,0,0)',
                                          font_color='#999999'
                                      ))), width = 10
                    )
                ])
            ],className="mt-3")

tabs = dbc.Tabs(
    [
        dbc.Tab(tab1_content, label="Race Trace"),
        dbc.Tab(tab2_content, label="Live Gaps"),
    ]
)

# Layout of the app
app.layout = html.Div([
    html.H1("raceEngineer"),
    html.Div([
        dbc.Row([
            dbc.Col(dbc.Select(list(range(current_year(), 2022, -1)),
                       current_year(),
                       id="year-select",
                       size="sm",
                       ), width = "auto"),
            dbc.Col(dbc.Select(placeholder="Select a race",
                       id="race-select",
                       size="sm",
                       ), width = "auto"),
            dbc.Col(
                dbc.Fade(
                    dbc.Button("Refresh", id="btn-refresh", size="sm"),
                    id="btn-refresh-fade",
                    is_in=False,
                    appear=True
                ), width = "auto"),
            dbc.Col(html.Small(id = "last-update-text", className = "text-muted"), width = "auto"),
            dbc.Col(
                dbc.Fade(
                    dbc.Checkbox(
                        id="live-update-checkbox",
                        label="Live updates",
                        value=False
                    ),
                    id="live-update-checkbox-fade",
                    is_in=False,
                    appear=True
                ), width = "auto"),
            dbc.Col(
                dbc.Fade(
                    dbc.Label("Refresh rate (seconds)"),
                    id="live-update-label-fade",
                    is_in=False,
                    appear=True
                ), width = "auto"),
            dbc.Col(
                dbc.Fade(
                    dbc.Select(list(range(5, 61, 5)),
                               interval,
                               id="interval-select",
                               size="sm"
                               ),
                    id="live-update-fade",
                    is_in=False,
                    appear=True,
                ), width = "auto"),
            dbc.Col(
                dbc.Fade(
                    dbc.Label("Data interval (minutes)"),
                    id="live-interval-label-fade",
                    is_in=False,
                    appear=True
                ), width = "auto"),
            dbc.Col(
                dbc.Fade(
                    dbc.Select(list(range(2, 31, 2)),
                               2,
                               id="live-interval-select",
                               size="sm"
                               ),
                    id="live-interval-fade",
                    is_in=False,
                    appear=True,
                ), width = "auto")
        ], justify="start"),
    ]),
    dbc.Fade(
        dbc.Card(tabs,
                 className="mt-3"),
        id="main-fade",
        is_in=False,
        appear=True
    )
], className="m-4")


def draw_drivers_gap_table(driver_positions_table, selection):
    gaps_table = []
    empty_selection = len(selection) == 0
    leader_is_set = False
    gap_delta_leader = gap_delta_interval = 0
    for position, driver in sorted(driver_positions_table.items()):
        if not leader_is_set:
            if empty_selection or driver['number'] in selection:
                gap_leader = gap_interval = '-'
                leader_is_set = True
                if is_float(driver['gap_leader']):
                    gap_delta_leader = driver['gap_leader']
            else:
                gap_leader = gap_interval = ''
        else:
            if empty_selection or driver['number'] in selection:
                if is_float(driver['gap_leader']):
                    gap_leader = f"+{(driver['gap_leader'] - gap_delta_leader):.3f}"
                else:
                    gap_leader = f"+{driver['gap_leader']}"
                if is_float(driver['gap_interval']):
                    gap_interval = f"+{driver['gap_interval'] + gap_delta_interval:.3f}"
                else:
                    gap_interval = f"+{driver['gap_interval']}"
                gap_delta_interval = 0
            else:
                gap_leader = gap_interval = ''
                if is_float(driver['gap_interval']):
                    gap_delta_interval += driver['gap_interval']
        gaps_table.append(html.Tr([html.Td(position),
                                        html.Td(driver['last_name']),
                                        html.Td(gap_leader),
                                        html.Td(gap_interval),
                                        html.Td(dbc.Checkbox(
                                                id={"type": "drivers-checkbox", "number": driver['number']},
                                                #name="drivers-checkbox",
                                                value=(driver['number'] in selection) or empty_selection,
                                            ))]))
    return gaps_table

# Callback to update the graph
@app.callback(Output('race-trace-graph', 'figure'),
              Output('live-gaps-graph', 'figure'),
              Output('live-gaps-table', 'children'),
              Output('last-update-text', 'children'),
              Output('drivers-data', 'data'),
              Output("main-fade", "is_in"),
              Output("btn-refresh-fade", "is_in"),
              Output("live-update-checkbox-fade", "is_in"),
              Input('interval-component', 'n_intervals'),
              Input("btn-filter-drivers", "n_clicks"),
              Input("btn-refresh", "n_clicks"),
              Input('race-select', 'value'),
              State('race-trace-graph', 'figure'),
              State('live-gaps-graph', 'figure'),
              State('live-gaps-table', 'children'),
              State('last-update-text', 'children'),
              State('drivers-data', 'data'),
              State({"type": "drivers-checkbox", "number": ALL}, "id"),
              State({"type": "drivers-checkbox", "number": ALL}, "value")

)
def update_graphs(_, _btn1, _btn2, in_race, race_trace_graph, live_gaps_graph, live_gaps_table, last_update_text, in_drivers, checkboxes, checked):
    show_graph = False
    if in_race is None:
        out_drivers = in_drivers
    else:
        activator = dash.ctx.triggered_id
        out_drivers = {int(i):v for i,v in in_drivers.items()}
        race = RaceData(in_race)
        race_trace_data = race.get_driver_diff_laps()
        live_gaps_data = race.get_driver_intervals()
        if len(race_trace_data) > 0:
            race_trace_graph = go.Figure(race_trace_graph)
            live_gaps_graph = go.Figure(live_gaps_graph)
            last_update_text = f"Last updated on {utils.timestamp()}"
            show_graph = True
            driver_positions = race.get_driver_positions()
            driver_positions_table = {}

            if activator == 'race-select':
                event = race.get_race_event()
                race_trace_graph.layout.title = f'{event["country_name"]} {event["year"]} - {event["location"]}'
                live_gaps_graph.layout.title = race_trace_graph.layout.title
                race_trace_graph.data = []
                live_gaps_graph.data = []
                out_drivers = race.get_drivers()
                for driver in out_drivers.values():
                    race_trace_graph.add_trace(go.Scattergl(
                        x=[0],  # X-axis: lap numbers
                        y=[0],  # Y-axis: cumulated lap times
                        mode='lines+markers',
                        name=driver['name_acronym'],
                        line_color=driver['team_colour']
                    ))
                    live_gaps_graph.add_trace(go.Scattergl(
                        x=[],  # X-axis: lap numbers
                        y=[],  # Y-axis: cumulated lap times
                        mode='lines',
                        name=driver['name_acronym'],
                        line_color=driver['team_colour']
                    ))

            # Update the traces for the line plot
            for driver_id, lap_times in race_trace_data.items():
                race_trace_graph.update_traces(dict(x=list(lap_times.keys()),
                                                    y=cumsum(list(lap_times.values()))),
                                               selector=({'name':out_drivers[driver_id]['name_acronym']}))

            for driver_id, gaps in live_gaps_data.items():
                gap_leader = next(reversed(gaps['leader'].values())) #last gap in the series
                gap_interval = next(reversed(gaps['interval'].values())) #last gap in the series
                live_gaps_graph.update_traces(dict(x=list(gaps['leader'].keys()),
                                                   y=list(y for y in gaps['leader'].values() if is_float(y))),
                                              selector=({'name':out_drivers[driver_id]['name_acronym']}))
                driver_positions_table[driver_positions[driver_id]['current']] = {
                    'last_name': out_drivers[driver_id]['last_name'],
                    'number': driver_id,
                    'gap_leader': gap_leader,
                    'gap_interval': gap_interval}

            filtered_drivers = [driver["number"] for driver, selected in zip(checkboxes, checked) if selected]
            live_gaps_table = draw_drivers_gap_table(driver_positions_table, filtered_drivers)

    return race_trace_graph, live_gaps_graph, live_gaps_table, last_update_text, out_drivers, show_graph, show_graph, show_graph

@app.callback(
    Output("live-update-fade", "is_in"),
    Output("live-update-label-fade", "is_in"),
    Output("live-interval-fade", "is_in"),
    Output("live-interval-label-fade", "is_in"),
    Output('interval-component', 'disabled'),
    Input("live-update-checkbox", "value"),
)
def toggle_fade(live_update_checked):
    return live_update_checked, live_update_checked, live_update_checked, live_update_checked, not live_update_checked

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

@app.callback(Output({"type": "drivers-checkbox", "number": ALL}, "value"),
    Input("check-all-drivers", "value"),
    State({"type": "drivers-checkbox", "number": ALL}, "value")
)
def select_all_drivers(value, checkboxes):
    if dash.ctx.triggered_id is None:
        return checkboxes
    return [value] * len(checkboxes)

# Run the Dash app
if __name__ == '__main__':
    app.run(debug=True)
    #app.run_server(host = '0.0.0.0', debug = False)