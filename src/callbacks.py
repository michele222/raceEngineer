import dash
import dash_bootstrap_components as dbc
from dash import Output, Input, State, ALL, html, no_update
from numpy import cumsum
from plotly import graph_objs as go

from src import utils
from src.app import app
from src.enums import DataInterval
from src.race_data import RaceData
from src.utils import is_float


@app.callback(Output('drivers-data-store', 'data'),
              Output('race-data-store', 'data'),
              Input('race-select', 'value'),
              State('race-select', 'options'),
              prevent_initial_call=True
              )
def change_race(selected_race, races):
    """
    Loads the drivers set and race title when the race is changed
    :param selected_race: id of the selected race
    :param races: race titles from the race selection dropdown
    :return: drivers data, race title
    """
    race_title = ""
    for race in races:
        if str(race['value']) == selected_race:
            race_title = race['label']
            break

    race = RaceData(selected_race)
    drivers = race.get_drivers()

    return drivers if drivers else no_update, race_title


@app.callback(Output('race-trace-graph', 'figure'),
              Output('last-update-p1-text', 'children'),
              Output("main-fade", "is_in"),
              Output("refresh-button-fade", "is_in"),
              Output("live-update-checkbox-fade", "is_in"),
              Input('refresh-timer', 'n_intervals'),
              Input("refresh-button", "n_clicks"),
              Input('drivers-data-store', 'data'),
              State('race-select', 'value'),
              State('race-data-store', 'data'),
              State('race-trace-graph', 'figure'),
              running=[(Output("loading_indicator", "display"), "show", "hide")],
              prevent_initial_call=True
              )
def update_race_trace_page(_refresh_timer,
                           _refresh_btn,
                           stored_drivers_data,
                           selected_race,
                           selected_race_title,
                           race_trace_graph):
    """
    Loads the race trace page
    :param _refresh_timer: (trigger only) timer of the live auto refresh
    :param _refresh_btn: (trigger only) refresh button
    :param stored_drivers_data: drivers data
    :param selected_race: id of the selected race
    :param selected_race_title: title of the selected race
    :param race_trace_graph: figure of the race trace graph
    :return: updated race_trace_graph, last update text, fades
    """
    race = RaceData(selected_race)
    race_trace_data = race.get_driver_diff_laps()
    drivers = {int(i): v for i, v in stored_drivers_data.items()}
    race_trace_graph = go.Figure(race_trace_graph)
    last_update_text = f"Last updated on {utils.timestamp_formatted()}"
    activator = dash.ctx.triggered_id
    if activator in ('drivers-data-store', 'refresh-button'):
        # If the drivers data is changed (new race selected), the graph title and traces are reloaded
        race_trace_graph.layout.title = selected_race_title
        race_trace_graph.data = []
        for driver in drivers.values():
            race_trace_graph.add_trace(go.Scattergl(
                x=[0],  # x-axis: lap numbers
                y=[0],  # y-axis: cumulated lap times
                mode='lines+markers',
                name=driver['name_acronym'],
                line_color=driver['team_colour']
            ))
    # Update the traces of the race trace graph
    if race_trace_data:
        for driver_id, lap_times in race_trace_data.items():
            race_trace_graph.update_traces(dict(x=list(lap_times.keys()),
                                                y=cumsum(list(lap_times.values()))),
                                           selector=({'name': drivers[driver_id]['name_acronym']}))
    else:
        last_update_text += " (no trace)"

    return (race_trace_graph if race_trace_data else no_update,
            last_update_text,
            True,  # Show the fades
            True,
            True)


@app.callback(Output('live-gaps-graph', 'figure'),
              Output('live-gaps-table', 'children'),
              Output('last-update-p2-text', 'children'),
              Input('refresh-timer', 'n_intervals'),
              Input("filter-drivers-button", "n_clicks"),
              Input("refresh-button", "n_clicks"),
              Input('drivers-data-store', 'data'),
              State('race-select', 'value'),
              State('race-data-store', 'data'),
              State('live-gaps-graph', 'figure'),
              State('data-interval-select', 'value'),
              State({"type": "drivers-checkbox", "number": ALL}, "id"),
              State({"type": "drivers-checkbox", "number": ALL}, "value"),
              running=[(Output("loading_indicator", "display"), "show", "hide")],
              prevent_initial_call=True
              )
def update_live_gaps_page(_refresh_timer,
                          _filter_btn,
                          _refresh_btn,
                          stored_drivers_data,
                          selected_race,
                          selected_race_title,
                          live_gaps_graph,
                          selected_data_interval,
                          checkboxes,
                          checked):
    """
    Loads the live gaps page
    :param _refresh_timer: (trigger only) timer of the live auto refresh
    :param _filter_btn: (trigger only) driver filter button
    :param _refresh_btn: (trigger only) refresh button
    :param stored_drivers_data: drivers data
    :param selected_race: id of the selected race
    :param selected_race_title: title of the selected race
    :param live_gaps_graph: figure of the live gaps graph
    :param selected_data_interval: the selected interval of data (last x minutes of data)
    :param checkboxes: list of drivers checkbox ids
    :param checked: list of drivers checkbox values
    :return: updated live_gaps_graph, live_gaps_table, last update text
    """
    race = RaceData(selected_race)
    live_gaps_data = race.get_driver_intervals(selected_data_interval)
    drivers = {int(i): v for i, v in stored_drivers_data.items()}
    live_gaps_graph = go.Figure(live_gaps_graph)
    last_update_text = f"Last updated on {utils.timestamp_formatted()}"
    driver_positions = race.get_driver_positions()
    driver_positions_table = []
    if not driver_positions:
        last_update_text += " (no pos)"
    activator = dash.ctx.triggered_id
    if activator in ('drivers-data-store', 'refresh-button'):
        # If the drivers data is changed (new race selected), the graph title and traces are reloaded
        live_gaps_graph.layout.title = selected_race_title
        live_gaps_graph.data = []
        for driver in drivers.values():
            live_gaps_graph.add_trace(go.Scattergl(
                x=[],  # x-axis: lap numbers
                y=[],  # y-axis: gap from the leader
                mode='lines',
                name=driver['name_acronym'],
                line_color=driver['team_colour']
            ))
    # Update the traces of the live gaps graph
    if live_gaps_data:
        for driver_id, gaps in live_gaps_data.items():
            gap_leader = next(reversed(gaps['leader'].values()))  # last gap in the series
            gap_interval = next(reversed(gaps['interval'].values()))  # last gap in the series
            live_gaps_graph.update_traces(dict(x=list(gaps['leader'].keys()),
                                               y=list(y for y in gaps['leader'].values() if is_float(y))),
                                          selector=({'name': drivers[driver_id]['name_acronym']}))
            # Build the driver positions table
            driver_positions_table.append({
                'position': driver_positions[driver_id]['current'] if driver_positions else None,
                'last_name': drivers[driver_id]['last_name'],
                'number': driver_id,
                'gap_leader': gap_leader,
                'gap_interval': gap_interval})
        # Filter the drivers selected by their checkboxes
        filtered_drivers = [driver["number"] for driver, selected in zip(checkboxes, checked) if selected]
        # Draws the gap table, order by position if available, otherwise use the gap from leader
        live_gaps_table = draw_drivers_gap_table(driver_positions_table, filtered_drivers,
                                                 'position' if driver_positions else 'gap_leader')
    else:
        last_update_text += " (no gaps)"

    return (live_gaps_graph if live_gaps_data else no_update,
            live_gaps_table if live_gaps_data else no_update,
            last_update_text)


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
    """
    Handles the (de)activation of the live update checkbox: fades and refresh timer are (de)activated accordingly.
    The data interval dropdown value is defaulted to OFF by default when the live update is (de)activated.
    :param live_update_checked: value of the live update checkbox
    :return: fades, refresh timer, data interval dropdown value
    """
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
    """
    Changes the refresh rate based on the value of the dropdown
    :param refresh_rate: selected refresh rate
    :return: refresh timer interval
    """
    return int(refresh_rate) * 1000


@app.callback(
    Output('race-select', 'options'),
    Input("year-select", "value"),
)
def change_year(year):
    """
    Loads the dropdown with the races (and sprints) of the selected year
    :param year: selected year
    :return: list of races formatted for the dropdown
    """
    data = RaceData()
    races = data.get_races_of_year(year)
    races_list = [{'label': f'{race_item["country_name"]} - {race_item["location"]} - {race_item["session_name"]}',
                   'value': race_id}
                  for (race_id, race_item) in races.items()]
    # The value 'latest' refers to the latest session and is added to give the option to potentially load data from
    # non-race sessions (practice, qualifying)
    races_list.append({'label': 'Latest', 'value': 'latest'})

    return races_list


@app.callback(Output({"type": "drivers-checkbox", "number": ALL}, "value"),
              Input("all-drivers-checkbox", "value"),
              State({"type": "drivers-checkbox", "number": ALL}, "value"),
              prevent_initial_call=True
              )
def select_all_drivers(value, checkboxes):
    """
    Handles the (de)activation of the drivers checkboxes based on select-all-drivers checkbox
    :param value: value of the select-all-drivers checkbox
    :param checkboxes: drivers checkboxes
    :return: updated drivers checkboxes
    """
    return [value] * len(checkboxes)


def draw_drivers_gap_table(driver_positions_table, selection, sorting_key='position'):
    """
    Draws the drivers table with positions and gaps from leader and from driver ahead (interval).
    A selection of drivers can be made: in this case gaps are calculated only amongst the selected drivers
    :param driver_positions_table: dict with drivers data, position and gaps
    :param selection: list of the selected drivers (driver numbers)
    :param sorting_key: the sorting key of the table (by default is position)
    :return: the table ready for display
    """
    gaps_table = []
    # empty_selection is True if no driver is selected. In this case, all drivers are displayed
    empty_selection = len(selection) == 0
    leader_is_set = False
    gap_delta_leader = gap_delta_interval = 0
    for driver in sorted(driver_positions_table, key=lambda x: x[sorting_key]):
        if not leader_is_set:
            if empty_selection or driver['number'] in selection:
                # this is the leader of the selection
                gap_leader = gap_interval = '-'
                leader_is_set = True
                if is_float(driver['gap_leader']):
                    # leader of the selection is not the overall leader: save his gap from the overall leader
                    gap_delta_leader = driver['gap_leader']
            else:
                # driver not in selection and ahead of the selection leader, ignore
                gap_leader = gap_interval = ''
        else:
            if empty_selection or driver['number'] in selection:
                if is_float(driver['gap_leader']):
                    # driver in the same lap as the leader
                    gap_leader = f"+{(driver['gap_leader'] - gap_delta_leader):.3f}"
                else:
                    # lapped driver
                    gap_leader = f"+{driver['gap_leader']}"
                if is_float(driver['gap_interval']):
                    # driver in the same lap as the preceding driver
                    gap_interval = f"+{driver['gap_interval'] + gap_delta_interval:.3f}"
                else:
                    # lapped driver
                    gap_interval = f"+{driver['gap_interval']}"
                gap_delta_interval = 0
            else:
                # driver not in selection: add his interval to the gap delta interval
                gap_leader = gap_interval = ''
                if is_float(driver['gap_interval']):
                    gap_delta_interval += driver['gap_interval']

        gaps_table.append(html.Tr([html.Td(driver['position'] if driver['position'] is not None else ""),
                                   html.Td(driver['last_name']),
                                   html.Td(gap_leader),
                                   html.Td(gap_interval),
                                   html.Td(dbc.Checkbox(
                                       id={"type": "drivers-checkbox", "number": driver['number']},
                                       value=(driver['number'] in selection) or empty_selection,
                                   ))]))

    return gaps_table
