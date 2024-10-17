import dash_bootstrap_components as dbc
from dash import html, dcc
from plotly import graph_objs as go

from src.enums import DataInterval
from src.utils import current_year
import src.callbacks

title = "raceEngineer"
default_refresh_rate = 30  # update every x seconds

race_trace_graph = dcc.Graph(id='race-trace-graph',
                             figure=go.Figure(
                                 layout=go.Layout(
                                     xaxis={'title': 'Lap Number',
                                            'minallowed': 0,
                                            'tick0': 0,
                                            'dtick': 5,
                                            'zeroline': False,
                                            'gridcolor': '#333333',
                                            'minor': {'ticklen': 3,
                                                      'dtick': 1,
                                                      'showgrid': True}},
                                     yaxis={'title': 'Gap (seconds)',
                                            'autorange': 'reversed',
                                            'zeroline': False,
                                            'gridcolor': '#333333'},
                                     hovermode='closest',
                                     height=1000,
                                     plot_bgcolor='#111111',
                                     paper_bgcolor='rgba(0,0,0,0)',
                                     font_color='#999999')))

live_gaps_graph = dcc.Graph(id='live-gaps-graph',
                            figure=go.Figure(
                                layout=go.Layout(
                                    xaxis={'title': 'Time',
                                           'zeroline': False,
                                           'gridcolor': '#333333'},
                                    yaxis={'title': 'Gap from leader (seconds)',
                                           'autorange': 'reversed',
                                           'zeroline': False,
                                           'gridcolor': '#333333'},
                                    hovermode='closest',
                                    height=1000,
                                    plot_bgcolor='#111111',
                                    paper_bgcolor='rgba(0,0,0,0)',
                                    font_color='#999999')))

refresh_timer = dcc.Interval(
    id='refresh-timer',
    interval=default_refresh_rate * 1000,  # Update every x milliseconds
    n_intervals=0,
    disabled=True
)

drivers_data_store = dcc.Store(id='drivers-data-store', data={})

all_drivers_checkbox = dbc.Checkbox(id="all-drivers-checkbox", value=True)

live_gaps_table_header = html.Tr([html.Th("Pos"),
                                  html.Th("Driver"),
                                  html.Th("Gap (Leader)"),
                                  html.Th("Gap (Interval)"),
                                  html.Th(all_drivers_checkbox)])

live_gaps_table = dbc.Table([html.Thead(live_gaps_table_header),
                             html.Tbody(id='live-gaps-table')],
                            striped=True, bordered=True, hover=True)

filter_drivers_button = dbc.Button("Filter drivers", id="filter-drivers-button", size="sm")

tab1 = html.Div([race_trace_graph,
                 refresh_timer,
                 drivers_data_store
                 ])

tab2 = [html.Div([live_gaps_table, filter_drivers_button],
                 style={'width': '25%', 'display': 'inline-block'}),
        html.Div(live_gaps_graph,
                         style={'width': '75%', 'display': 'inline-block'})]

tabs = dbc.Tabs(
    [
        dbc.Tab(tab1, label="Race Trace"),
        dbc.Tab(tab2, label="Live Gaps")
    ]
)

main_fade = dbc.Fade(dbc.Card(tabs, className="mt-3"), id="main-fade", is_in=False, appear=True)

year_select = dbc.Select(list(range(current_year(), 2022, -1)), current_year(), id="year-select", size="sm")
race_select = dbc.Select(placeholder="Select a race", id="race-select", size="sm")
refresh_button = dbc.Button("Refresh", id="refresh-button", size="sm")
refresh_button_fade = dbc.Fade(refresh_button, id="refresh-button-fade", is_in=False, appear=True)
loading_indicator = dcc.Loading(id="loading_indicator", type="circle", display="hide")
last_update_text = html.Small(id="last-update-text", className="text-muted")
live_update_checkbox = dbc.Checkbox(id="live-update-checkbox", label="Live updates", value=False)
live_update_checkbox_fade = dbc.Fade(live_update_checkbox, id="live-update-checkbox-fade", is_in=False, appear=True)
refresh_rate_label = dbc.Label("Refresh rate (seconds)")
refresh_rate_label_fade = dbc.Fade(refresh_rate_label, id="refresh-rate-label-fade", is_in=False, appear=True)
refresh_rate_select = dbc.Select(list(range(5, 61, 5)), default_refresh_rate, id="refresh-rate-select", size="sm")
refresh_rate_fade = dbc.Fade(refresh_rate_select, id="refresh-rate-fade", is_in=False, appear=True)
data_interval_label = dbc.Label("Data interval (minutes)")
data_interval_label_fade = dbc.Fade(data_interval_label, id="data-interval-label-fade", is_in=False, appear=True)
data_interval_select = dbc.Select(list(range(2, 31, 2)) + [DataInterval.OFF.value], DataInterval.OFF.value,
                                  id="data-interval-select",
                                  size="sm")
data_interval_select_fade = dbc.Fade(data_interval_select, id="data-interval-fade", is_in=False, appear=True)

top_bar_items = [year_select,
                 race_select,
                 refresh_button_fade,
                 loading_indicator,
                 last_update_text,
                 live_update_checkbox_fade,
                 refresh_rate_label_fade,
                 refresh_rate_fade,
                 data_interval_label_fade,
                 data_interval_select_fade]

app_layout = html.Div([
    html.H1(title),
    html.Div([dbc.Row([dbc.Col(item, width="auto") for item in top_bar_items], justify="start")]),
    main_fade
], className="m-4")


def get_layout():
    return app_layout
