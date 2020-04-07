import argparse
import csv
import logging
import os
import sys
from collections import ChainMap
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

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)


class Generator:
    def __init__(self, config):
        self.config = config
        self.active_country: str = config.country
        self.data: list = self.get_data()

    def row_filter(self, row: dict) -> bool:
        country = countries[self.active_country]
        if 'Country_Region' in row:
            return row['Country_Region'] in country['country'] and row['Province_State'] in country['state']

        if 'Country/Region' in row:
            return row['Country/Region'] in country['country'] and row['Province/State'] in country['state']

        raise Exception(f'Unable to process row, available keys: {row.keys()}')

    def process_file(self, filename):
        date = datetime.strptime(filename.name.rstrip('.csv'), '%m-%d-%Y')
        confirmed = deaths = 0

        # Pull out the United Kingdom data for this day.
        with open(filename, encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)
            try:
                data = next(row for row in reader if self.row_filter(row))
                confirmed, deaths = int(data['Confirmed'] or 0), int(data['Deaths'] or 0)
            except StopIteration:
                logger.debug(f'No {self.active_country} data in {filename}')

        return date, confirmed, deaths

    def get_data(self):
        # Pull the data from each CSV file.
        directory = Path('.') / 'COVID-19' / 'csse_covid_19_data' / 'csse_covid_19_daily_reports'
        files = directory.glob('*.csv')
        time_series = list(map(self.process_file, files))
        time_series.sort(key=itemgetter(0))

        return time_series

    def generate_basic_data_graph(self):
        self.write_graph('cases', self.data)

    def generate_rate_delta_graph(self):
        """How are the numbers changing each day?"""
        deltas = []
        p_date = p_confirmed = p_deaths = None
        for index, data in enumerate(self.data):
            if not p_date:
                p_date, p_confirmed, p_deaths = data
                continue

            date, confirmed, deaths = data
            deltas.append((date, confirmed - p_confirmed, deaths - p_deaths))
            p_date, p_confirmed, p_deaths = data

        # Remove confirmed
        # deltas = [(date, 0, deaths) for date, confirmed, deaths in deltas]

        self.write_graph('deltas', deltas)

    def generate_filename(self, graph_type: str):
        return f"{self.active_country}-{graph_type}-{f'shifted-{self.config.shift}-days' if self.config.shift else 'unshifted'}{f' (log)' if self.config.log else ''}.png"

    def generate_title(self, graph_type: str):
        if self.config.shift:
            return f'{graph_type.title()} in confirmed and deaths, with the deaths shifted by {self.config.shift} days'

        return f'{graph_type.title()} in confirmed and deaths'

    def write_graph(
        self,
        graph_type,
        time_series
    ):
        time_shift = self.config.shift

        if not time_shift:
            time_shift = 0

        x = [t[0].strftime('%d %b') for t in time_series]
        confirmed = [t[1] for t in time_series]
        deaths = [t[2] for t in time_series]

        if self.config.any_case:
            # Find the first index with data in either category
            offset = next(index for index, (c, d) in enumerate(zip(confirmed, deaths)) if c + d > 0)
        else:
            # Find the first index with data in both categories
            offset = next(index for index, (c, d) in enumerate(zip(confirmed, deaths)) if c > 0 and d > 0)

        x = x[offset:]
        confirmed = confirmed[offset:]
        deaths = deaths[offset:]

        fig = go.Figure(data=[
            go.Bar(name='Confirmed Cases', x=x, y=confirmed),
            go.Bar(name='Deaths', x=x, y=deaths[time_shift:]),
        ], layout=go.Layout(
            title=self.generate_title(graph_type),
            yaxis=dict(
                type='log' if self.config.log else 'linear',
            ),
            xaxis=dict(
                # showgrid=True,
                # type='category',
            ),
        ))

        output_filename = self.generate_filename(graph_type)
        logger.info(f'Wrote images/{output_filename}')
        fig.write_image(f'images/{output_filename}', width=1100, height=628, scale=2)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate COVID-19 graphs.')
    parser.add_argument("-s", "--shift", default=14, type=int, help="Number of days to shift deaths by.")
    parser.add_argument("-l", "--log", action='store_true', help="Whether to use a log-scale.")
    parser.add_argument("-c", "--country", default='UK', type=str, choices=countries.keys(), help="Which country to render data for.")
    parser.add_argument("-a", "--any-case", action='store_true', help="Show columns where there are _any_ cases, rather than needing at least one confirmed case and one death.")

    parser.add_argument('-b', '--basic', action='append_const', dest='graphs', const='basic', help='Generate the basic data graph.')
    parser.add_argument('-d', '--delta', action='append_const', dest='graphs', const='delta', help='Generate the delta trends graph.')

    parser.add_argument('-v', '--verbose', action='store_true')

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.NOTSET)

    if args.graphs is None:
        args.graphs = ['basic']

    logger.info(f'Starting graphing with args: {args}')

    generator = Generator(args)

    if 'basic' in args.graphs:
        generator.generate_basic_data_graph()

    if 'delta' in args.graphs:
        generator.generate_rate_delta_graph()
