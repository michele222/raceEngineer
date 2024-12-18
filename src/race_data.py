from collections import defaultdict
from statistics import mean, median

import requests
from dateutil import parser

import src.utils as utils
from src.enums import Operation, DataInterval
from src.logger import logger
from src.utils import get_hex_color, time_iso


class RaceData:

    def __init__(self, race_id='latest'):
        self.__race_id = race_id
        self.__server = 'https://api.openf1.org/v1/'  # Data source
        # Query results are stored in the following instance variables and can be processed by other methods
        self.__data_races_year = {}
        self.__data_race_event = {}
        self.__data_drivers = {}
        self.__data_driver_laps = {}
        self.__data_driver_positions = {}
        self.__data_driver_intervals = {}

    def __api_request(self, request_text):
        """
        Perform API request to get the latest data from the server
        :param request_text: full text of the GET request, including parameters
        :return: json formatted data, False if not successful
        """
        try:
            response = requests.get(f'{self.__server}{request_text}')
            if response.status_code == 200:
                data = response.json()
                if len(data) == 0:
                    self.__log_query(request_text, 'Server response empty')
                    return False
                self.__log_query(request_text, 'Success')
                return data
            self.__log_query(request_text, f'Server response: {response.status_code}')
            return False
        except Exception as e:
            self.__log_query(request_text, f'Error retrieving data: {e}')
            return False

    def __log_query(self, request_text, text):
        """
        Prints a message in the log including the API request
        :param request_text: full text of the GET request, including parameters
        :param text: text of the log entry to be made
        """
        logger.info(f"[{self.__server}{request_text}] {text}")

    def get_races_of_year(self, year=2024):
        """
        Queries data source about races (+sprints) of a specific year
        :param year:
        :return: dict with query result
        """
        races = {}
        self.__data_races_year = self.__api_request(f'sessions?session_type=Race&year={year}')
        if self.__data_races_year:
            for race_item in self.__data_races_year:
                races[race_item['session_key']] = race_item
        return races

    def get_race_event(self):
        """
        Queries data source about a race event
        :return: dict with query result
        """
        race_event = {}
        self.__data_race_event = self.__api_request(f'sessions?session_key={self.__race_id}')
        if self.__data_race_event:
            for race_event_item in self.__data_race_event:  # using for but this should only be 1 line
                race_event = race_event_item
        return race_event

    def get_drivers(self):
        """
        Queries data source about drivers from a race event.
        Per driver (id is number), returns a dict with listed data
        :return: dict with query result
        """
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
        """
        Queries data source about driver laps from a race event.
        Per driver (id is number), returns a dict with lap: lap time
        :return: dict with query result
        """
        driver_laps = defaultdict(lambda: {0: 0.0})  # make all drivers start at 0 in lap 0
        self.__data_driver_laps = self.__api_request(f'laps?session_key={self.__race_id}')
        if self.__data_driver_laps:
            for lap_item in self.__data_driver_laps:
                if lap_item['lap_number'] == 2:
                    # Lap 1 in the dataset is not timed: generate lap 1 times from the timestamps of lap 2 start
                    lap_start_iso_time = parser.isoparse(lap_item['date_start'])
                    driver_laps[lap_item['driver_number']][1] = (float(lap_start_iso_time.strftime("%M")) * 60
                                                                 + float(lap_start_iso_time.strftime("%S.%f")))
                if utils.is_float(lap_item['lap_duration']):
                    driver_laps[lap_item['driver_number']][lap_item['lap_number']] = lap_item['lap_duration']
        return driver_laps

    def get_driver_positions(self):
        """
        Queries data source about driver positions from a race event.
        Per driver (id is number), returns a dict with positions over time, and the current position
        :return: dict with query result
        """
        driver_positions = defaultdict(dict)
        self.__data_driver_positions = self.__api_request(f'position?session_key={self.__race_id}')
        if self.__data_driver_positions:
            for position_item in self.__data_driver_positions:
                driver_positions[position_item['driver_number']]['current'] = position_item['position']
                driver_positions[position_item['driver_number']][position_item['date']] = position_item['position']
        return driver_positions

    def get_driver_intervals(self, data_filter=DataInterval.OFF.value):
        """
        Queries data source about driver intervals (gaps from leader and intervals) from a race event.
        Per driver (id is number), returns a dict with time: gap from leader, interval
        :param data_filter: if set, returns only the last x minutes of data
        :return: dict with query result
        """
        driver_intervals = defaultdict(lambda: {'leader': {}, 'interval': {}})
        if data_filter == DataInterval.OFF.value or not data_filter.isnumeric():
            param = ''
        else:
            param = f'&date>={time_iso(-int(data_filter) * 60)}'  # Filter is in minutes, API wants seconds
        self.__data_driver_intervals = self.__api_request(f'intervals?session_key={self.__race_id}{param}')
        if self.__data_driver_intervals:
            for interval_item in self.__data_driver_intervals:
                driver_intervals[interval_item['driver_number']]['leader'][interval_item['date']] = interval_item[
                    'gap_to_leader']
                driver_intervals[interval_item['driver_number']]['interval'][interval_item['date']] = interval_item[
                    'interval']
        return driver_intervals

    def __process_laps(self, operation):
        """
        Performs the selected operation on the lap times data, aggregated per lap.
        :param operation: operation from the Operations class in enums
        :return: dict with processed data, ordered per lap
        """
        unprocessed_laps = defaultdict(list)
        processed_laps = {0: 0.0} # all drivers start at 0 in lap 0
        if self.__data_driver_laps:
            for lap_item in self.__data_driver_laps:
                if utils.is_float(lap_item['lap_duration']):
                    if lap_item['lap_number'] == 2:
                        lap_start_iso_time = parser.isoparse(lap_item['date_start'])
                        # Lap 1 in the dataset is not timed: generate lap 1 times from the timestamps of lap 2 start
                        unprocessed_laps[1].append(float(lap_start_iso_time.strftime("%M")) * 60
                                           + float(lap_start_iso_time.strftime("%S.%f")))
                    unprocessed_laps[lap_item['lap_number']].append(lap_item['lap_duration'])
            match operation:
                case Operation.AVG:
                    for lap in unprocessed_laps.keys():
                        processed_laps[lap] = round(mean(unprocessed_laps[lap]), 3)
                case Operation.MEDIAN:
                    for lap in unprocessed_laps.keys():
                        processed_laps[lap] = round(median(unprocessed_laps[lap]), 3)
        return processed_laps

    def get_driver_diff_laps(self, operation=Operation.MEDIAN, fixed_lap_duration=90):
        """
        Performs the difference between lap times and the aggregated times of a lap, for all laps of all drivers.
        Per driver (id is number), returns a dict with lap: lap time - operation(lap time)
        :param operation: operation from the Operations class in enums
        :param fixed_lap_duration: if the operation is FIXED, this is the default lap time duration to perform the difference with
        :return: dict with processed driver laps
        """
        driver_laps = self.get_driver_laps()
        if operation == Operation.FIXED:
            # Difference with a fixed lap time value
            for driver, lap_times in driver_laps.items():
                for lap in lap_times:
                    driver_laps[driver][lap] = driver_laps[driver][lap] - fixed_lap_duration
        else:
            # Difference with a lap time generated by the selected operation (average lap time, median lap time, etc.)
            avg_laps = self.__process_laps(operation)
            for driver, lap_times in driver_laps.items():
                for lap in lap_times:
                    driver_laps[driver][lap] = driver_laps[driver][lap] - avg_laps[lap]
        return driver_laps
