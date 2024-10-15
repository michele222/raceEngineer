import dash
import dash_bootstrap_components as dbc
from dash import Output, Input, State, ALL, html
from numpy import cumsum
from plotly import graph_objs as go

from src import utils
from src.app import app
from src.enums import DataInterval
from src.race_data import RaceData
from src.utils import is_float


@app.callback(Output('race-trace-graph', 'figure'),
              Output('live-gaps-graph', 'figure'),
              Output('live-gaps-table', 'children'),
              Output('last-update-text', 'children'),
              Output('drivers-data-store', 'data'),
              Output("main-fade", "is_in"),
              Output("refresh-button-fade", "is_in"),
              Output("live-update-checkbox-fade", "is_in"),
              Input('refresh-timer', 'n_intervals'),
              Input("filter-drivers-button", "n_clicks"),
              Input("refresh-button", "n_clicks"),
              Input('race-select', 'value'),
              State('race-trace-graph', 'figure'),
              State('live-gaps-graph', 'figure'),
              State('data-interval-select', 'value'),
              State('drivers-data-store', 'data'),
              State({"type": "drivers-checkbox", "number": ALL}, "id"),
              State({"type": "drivers-checkbox", "number": ALL}, "value"),
              prevent_initial_call=True
              )
def update_graphs(_refresh_timer,
                  _filter_btn,
                  _refresh_btn,
                  selected_race,
                  race_trace_graph,
                  live_gaps_graph,
                  selected_data_interval,
                  stored_drivers_data,
                  checkboxes,
                  checked):
    race = RaceData(selected_race)
    race_trace_data = race.get_driver_diff_laps()
    if not race_trace_data:
        raise dash.exceptions.PreventUpdate
    live_gaps_data = race.get_driver_intervals(selected_data_interval)
    if not live_gaps_data:
        raise dash.exceptions.PreventUpdate
    drivers = {int(i): v for i, v in stored_drivers_data.items()}
    race_trace_graph = go.Figure(race_trace_graph)
    live_gaps_graph = go.Figure(live_gaps_graph)
    last_update_text = f"Last updated on {utils.timestamp_formatted()}"
    driver_positions = race.get_driver_positions()
    driver_positions_table = {}
    activator = dash.ctx.triggered_id
    if activator == 'race-select':
        event = race.get_race_event()
        race_trace_graph.layout.title = f'{event["country_name"]} {event["year"]} - {event["location"]}'
        live_gaps_graph.layout.title = race_trace_graph.layout.title
        race_trace_graph.data = []
        live_gaps_graph.data = []
        drivers = race.get_drivers()
        for driver in drivers.values():
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
                                       selector=({'name': drivers[driver_id]['name_acronym']}))

    for driver_id, gaps in live_gaps_data.items():
        gap_leader = next(reversed(gaps['leader'].values()))  # last gap in the series
        gap_interval = next(reversed(gaps['interval'].values()))  # last gap in the series
        live_gaps_graph.update_traces(dict(x=list(gaps['leader'].keys()),
                                           y=list(y for y in gaps['leader'].values() if is_float(y))),
                                      selector=({'name': drivers[driver_id]['name_acronym']}))
        driver_positions_table[driver_positions[driver_id]['current']] = {
            'last_name': drivers[driver_id]['last_name'],
            'number': driver_id,
            'gap_leader': gap_leader,
            'gap_interval': gap_interval}

    filtered_drivers = [driver["number"] for driver, selected in zip(checkboxes, checked) if selected]
    live_gaps_table = draw_drivers_gap_table(driver_positions_table, filtered_drivers)

    return race_trace_graph, live_gaps_graph, live_gaps_table, last_update_text, drivers, True, True, True


@app.callback(
    Output("refresh-rate-fade", "is_in"),
    Output("refresh-rate-label-fade", "is_in"),
    Output("data-interval-fade", "is_in"),
    Output("data-interval-label-fade", "is_in"),
    Output('refresh-timer', 'disabled'),
    Output('data-interval-select', 'value'),
    Input("live-update-checkbox", "value"),
    prevent_initial_call=True
)
def toggle_live_update(live_update_checked):
    return (live_update_checked,
            live_update_checked,
            live_update_checked,
            live_update_checked,
            not live_update_checked,
            DataInterval.OFF.value)


@app.callback(
    Output('refresh-timer', 'interval'),
    Input("refresh-rate-select", "value"),
    prevent_initial_call=True
)
def change_refresh_rate(refresh_rate):
    return int(refresh_rate) * 1000


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
              Input("all-drivers-checkbox", "value"),
              State({"type": "drivers-checkbox", "number": ALL}, "value"),
              prevent_initial_call=True
              )
def select_all_drivers(value, checkboxes):
    return [value] * len(checkboxes)


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
                                       # name="drivers-checkbox",
                                       value=(driver['number'] in selection) or empty_selection,
                                   ))]))
    return gaps_table
