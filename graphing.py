import csv
import os
from datetime import datetime
from operator import itemgetter
from pathlib import Path

import plotly.graph_objects as go

import plotly.io.orca

plotly.io.orca.config.server_url = 'http://127.0.0.1:9091'

countries = {
    'UK': {
        'country': ['UK', 'United Kingdom'],
        'state': ['', 'UK', 'United Kingdom']
    },
    'Italy': {
        'country': ['Italy'],
        'state': [''],
    }
}
active_country = 'UK'


def row_filter(active_country: str, row: dict) -> bool:
    country = countries[active_country]
    if 'Country_Region' in row:
        return row['Country_Region'] in country['country'] and row['Province_State'] in country['state']

    if 'Country/Region' in row:
        return row['Country/Region'] in country['country'] and row['Province/State'] in country['state']

    raise Exception(f'Unable to process row, available keys: {row.keys()}')


def process_file(filename):
    date = datetime.strptime(filename.name.rstrip('.csv'), '%m-%d-%Y')
    confirmed = deaths = recovered = 0

    # Pull out the United Kingdom data for this day.
    with open(filename, encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        try:
            data = next(row for row in reader if row_filter(active_country, row))
            confirmed, deaths, recovered = int(data['Confirmed'] or 0), int(data['Deaths'] or 0), int(
                data['Recovered'] or 0)
        except StopIteration:
            print(f'No {active_country} data in {filename}')

    return date, confirmed, deaths, recovered


def get_data():
    # Pull the data from each CSV file.
    directory = Path('.') / 'COVID-19' / 'csse_covid_19_data' / 'csse_covid_19_daily_reports'
    files = directory.glob('*.csv')
    time_series = list(map(process_file, files))
    time_series.sort(key=itemgetter(0))

    return time_series


def generate_basic_data_graph(time_series):
    time_shift = 14
    write_graph(
        time_series,
        f"{active_country}-{f'shifted-{time_shift}-days' if time_shift else 'unshifted'}.png",
        title=f'COVID-19 cases in {active_country}, with the deaths shifted by {time_shift} days',
        log_scale=False,
        time_shift=time_shift,
        truncate_x_axis=False,
    )


def generate_rate_delta_graph(time_series):
    """How are the numbers changing each day?"""
    deltas = []
    p_date = p_confirmed = p_deaths = p_recovered = None
    for index, data in enumerate(time_series):
        if not p_date:
            p_date, p_confirmed, p_deaths, p_recovered = data
            continue

        date, confirmed, deaths, recovered = data
        deltas.append((date, confirmed - p_confirmed, deaths - p_deaths))
        p_date, p_confirmed, p_deaths, p_recovered = data

    time_shift = 14
    write_graph(
        deltas,
        f"{active_country}-deltas-{f'shifted-{time_shift}-days' if time_shift else 'unshifted'}.png",
        title=f'Deltas in confirmed and deaths, with the deaths shifted by {time_shift} days',
        time_shift=14,
    )


def write_graph(
    time_series,
    output_filename, *,
    title: str = None,
    log_scale: bool = False,
    time_shift: int = None,
    truncate_x_axis: bool = False
):
    if not time_shift:
        time_shift = 0

    x = [t[0] for t in time_series]
    if time_shift and truncate_x_axis:
        x = x[:-time_shift]

    confirmed = [t[1] for t in time_series]
    deaths = [t[2] for t in time_series]

    fig = go.Figure(data=[
        go.Bar(name='Confirmed Cases', x=x, y=confirmed),
        go.Bar(name='Deaths', x=x, y=deaths[time_shift:]),
    ])

    if log_scale:
        fig.update_layout(yaxis_type='log')

    if title:
        fig.update_layout(title=title)

    fig.write_image(f'images/{output_filename}', width=1100, height=628, scale=2)


if __name__ == '__main__':
    data = get_data()
    # generate_basic_data_graph(data)
    generate_rate_delta_graph(data)
