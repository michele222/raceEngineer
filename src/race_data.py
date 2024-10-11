import json

import requests
from dateutil import parser
from statistics import median

import src.utils as utils
from src.enums import Operation, DataInterval
from src.utils import get_hex_color, time_iso


class RaceData:

    def __init__(self, race_id = 'latest'):
        self.__race_id = race_id
        self.__server = 'https://api.openf1.org/v1/'
        self.__data_races_year = {}
        self.__data_race_event = {}
        self.__data_drivers = {}
        self.__data_driver_laps = {}
        self.__data_driver_positions = {}
        self.__data_driver_intervals = {}

    def __api_request(self, request_text):
    # Perform API request to get the latest data from the server
        try:
            response = requests.get(f'{self.__server}{request_text}')
            if response.status_code == 200:
                data = response.json()
                if len(data) == 0:
                    self.__log_entry(request_text,'Server response empty')
                    return False
                self.__log_entry(request_text,'Success')
                return data
            else:
                self.__log_entry(request_text,f'Server response: {response.status_code}')
                return False
        except Exception as e:
            self.__log_entry(request_text,f'Error retrieving data: {e}')
            return False

    def __log_entry(self, request_text, text):
    # prints a message in the log including the API request
        print(f"[{utils.timestamp_formatted()} {self.__server}{request_text}] {text}")

    def get_races_of_year(self, year = 2024):
    # returns a dict with races (+sprints) of a specific year
        races = {}
        self.__data_races_year = self.__api_request(f'sessions?session_type=Race&year={year}')
        if self.__data_races_year:
            for race_item in self.__data_races_year:
                races[race_item['session_key']] = race_item
        return races

    def get_race_event(self):
    # returns a dict with race event data
        race_event = {}
        self.__data_race_event = self.__api_request(f'sessions?session_key={self.__race_id}')
        if self.__data_race_event:
            for race_event_item in self.__data_race_event: #using for but this should only be 1 line
                race_event = race_event_item
        return race_event

    def get_drivers(self):
    # per driver (id is number), returns a dict with listed data
        drivers = {}
        self.__data_drivers = self.__api_request(f'drivers?session_key={self.__race_id}')
        if self.__data_drivers:
            for driver_item in self.__data_drivers:
                drivers[driver_item['driver_number']] = {
                    'driver_number': driver_item['driver_number'],
                    'country_code': driver_item['country_code'],
                    'first_name': driver_item['first_name'],
                    'headshot_url': driver_item['headshot_url'],
                    'last_name': driver_item['last_name'],
                    'team_colour': get_hex_color(driver_item['team_colour']),
                    'team_name': driver_item['team_name'],
                    'name_acronym': driver_item['name_acronym']
                }
        return drivers

    def get_driver_laps(self):
    # per driver (id is number), returns a dict with lap: lap time
        driver_laps = {}
        self.__data_driver_laps = self.__api_request(f'laps?session_key={self.__race_id}')
        if self.__data_driver_laps:
            for lap_item in self.__data_driver_laps:
                if lap_item['driver_number'] not in driver_laps:
                    if lap_item['lap_number'] == 2:
                        lap_start_iso_time = parser.isoparse(lap_item['date_start'])
                        driver_laps[lap_item['driver_number']] = {
                            0: 0.0,
                            1: float(lap_start_iso_time.strftime("%M")) * 60
                               + float(lap_start_iso_time.strftime("%S.%f"))
                        }
                if utils.is_float(lap_item['lap_duration']):
                    driver_laps[lap_item['driver_number']][lap_item['lap_number']] = lap_item['lap_duration']
        return driver_laps

    def get_driver_positions(self):
    # per driver (id is number), returns a dict with positions over time, and the current position
        driver_positions = {}
        self.__data_driver_positions = self.__api_request(f'position?session_key={self.__race_id}')
        if self.__data_driver_positions:
            for position_item in self.__data_driver_positions:
                if position_item['driver_number'] not in driver_positions:
                    driver_positions[position_item['driver_number']] = {}
                driver_positions[position_item['driver_number']]['current'] = position_item['position']
                driver_positions[position_item['driver_number']][position_item['date']] = position_item['position']
        return driver_positions

    def get_driver_intervals(self, data_filter = DataInterval.OFF.value):
    # per driver (id is number), returns a dict with time: gap from leader
        driver_intervals = {}
        if data_filter == DataInterval.OFF.value or not data_filter.isnumeric():
            param = ''
        else:
            param = f'&date>={time_iso(-int(data_filter) * 60)}'
        self.__data_driver_intervals = self.__api_request(f'intervals?session_key={self.__race_id}{param}')
        if self.__data_driver_intervals:
            for interval_item in self.__data_driver_intervals:
                if interval_item['driver_number'] not in driver_intervals:
                    driver_intervals[interval_item['driver_number']] = {'leader': {}, 'interval': {}}
                driver_intervals[interval_item['driver_number']]['leader'][interval_item['date']] = interval_item['gap_to_leader']
                driver_intervals[interval_item['driver_number']]['interval'][interval_item['date']] = interval_item['interval']
        return driver_intervals

    def __process_laps(self, operation):
    # per lap, returns a list with processed lap times
        avg_laps = {}
        if self.__data_driver_laps:
            for lap_item in self.__data_driver_laps:
                if utils.is_float(lap_item['lap_duration']):
                    if lap_item['lap_number'] not in avg_laps:
                        avg_laps[lap_item['lap_number']] = []
                    if lap_item['lap_number'] == 2:
                        avg_laps[0] = [0.0]
                        if 1 not in avg_laps:
                            avg_laps[1] = []
                        lap_start_iso_time = parser.isoparse(lap_item['date_start'])
                        avg_laps[1].append(float(lap_start_iso_time.strftime("%M")) * 60
                                           + float(lap_start_iso_time.strftime("%S.%f")))
                    avg_laps[lap_item['lap_number']].append(lap_item['lap_duration'])
            match operation:
                case Operation.AVG:
                    for key in avg_laps.keys():
                        avg_laps[key] = round(sum(avg_laps[key]) / len(avg_laps[key]), 3)
                case Operation.MEDIAN:
                    for key in avg_laps.keys():
                        avg_laps[key] = round(median(avg_laps[key]), 3)
        return avg_laps

    def get_driver_diff_laps(self, operation = Operation.MEDIAN, fixed_lap_duration = 90):
    # per driver (id is number), returns a dict with lap: lap time - median(lap time)
        driver_laps = self.get_driver_laps()
        if operation == Operation.FIXED:
            for driver, lap_times in driver_laps.items():
                for lap in lap_times:
                    driver_laps[driver][lap] = driver_laps[driver][lap] - fixed_lap_duration
        else:
            avg_laps = self.__process_laps(operation)
            for driver, lap_times in driver_laps.items():
                for lap in lap_times:
                    driver_laps[driver][lap] = driver_laps[driver][lap] - avg_laps[lap]
        return driver_laps
