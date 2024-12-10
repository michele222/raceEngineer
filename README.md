# raceEngineer

raceEngineer is an interactive dashboard displaying historical and live data related to open wheel racing, implemented in Python with support of Dash and Plotly.

![raceEngineer](raceEngineer.jpg?raw=true)

## Usage

Clone repository and run file main.py.

By default, the instance is accessible at http://localhost:8050.

## Docker

Docker can also be used to run the application in a container.

Start the server instance with the following command:
```
docker compose up -d
```
Stop the server instance with the following command:
```
docker compose down
```

## API Data

raceEngineer currently relies on API data provided by [OpenF1](https://github.com/br-g/openf1).
Please consider donating to support the long-term sustainability of their project.
