#!/usr/bin/env python

# pywws - Python software for USB Wireless Weather Stations
# http://github.com/3v1n0/pywws
# Copyright (C) 2013 Marco Trevisan <mail@3v1n0.net>

# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

__usage__ = """
 usage: python bulk_metoffice_generator.py [options] data_dir out_file.csv
 options are:
  -h | --help     display this help
  -v | --verbose  increase number of informative messages
 data_dir is the root directory of the weather data
"""

import csv
import sys
import getopt
from datetime import datetime, timedelta
from pywws import DataStore
from pywws import conversions
from pywws.Logger import ApplicationLogger
from pywws.TimeZone import Local, utc

HOUR = timedelta(hours=1)
DAY = timedelta(hours=24)
REPORTS_MAXIMUM_FREQUENCY = timedelta(minutes=3)

FIELDS = ['Id', 'Report Date / Time', 'Concrete Temp.', 'Day of Gales',
          'Soil Temp. (at 10cm)', 'Wet Bulb', 'Soil Temp. (at 30cm)',
          'Max. Temp. (last 24hr)', 'Total Cloud Cover', 'Wind Gust',
          'Day of Hail', 'Wind Gust Direction', 'Present Weather',
          'Ground State', 'Soil Temp. (at 100cm)', 'Grass Temp.', 'Sunshine',
          'Day of Snow', 'Mean Sea-Level Pressure', 'Pressure (At Station)',
          'Relative Humidity', 'Weather Diary', 'Rainfall Accumulation',
          'Visibility', 'Min. Temp. (last 24hr)', 'Wind Direction', 'Wind Speed',
          'Air Temperature', 'Snow Depth', 'Soil Moisture', 'Dew Point',
          'Day of Thunder', 'Rainfall Rate', 'Flood Impacts', 'Wind Impacts',
          'Coastal Impacts', 'Wild Fire Impacts', 'Land Slide Impacts',
          'Poor Visibility Impacts', 'Snow Impacts', 'Ice Impacts',
          'Lightning Impacts', 'Other Impacts']

def GenerateBulk(data_dir, out_file_path):
    calib_data = DataStore.calib_store(data_dir)
    out_file = open(out_file_path, 'wb')

    # Adjust these values to proper datetime values if you want to port only a slice
    start = datetime.min
    stop = datetime.max

    csv_writer = csv.DictWriter(out_file, FIELDS)
    prev_idx = datetime.min

    for report in calib_data[start:stop]:
        if (report['idx'] - prev_idx) < REPORTS_MAXIMUM_FREQUENCY:
            continue

        csv_report = {}
        csv_report['Report Date / Time'] = report['idx'].strftime('%d/%m/%Y %H:%M')
        csv_report['Max. Temp. (last 24hr)'] = safe_format("%.2f", max_temp24(calib_data, report))
        csv_report['Air Temperature'] = safe_format("%.2f", report['temp_out'])
        csv_report['Dew Point'] = safe_format("%.2f", conversions.dew_point(report['temp_out'], report['hum_out']))
        csv_report['Rainfall Rate'] = safe_format("%.2f", max(0.0, report['rain'] - calib_data[calib_data.nearest(report['idx'] - HOUR)]['rain']))
        csv_report['Rainfall Accumulation'] = safe_format("%.2f", rain_day(calib_data, report))
        csv_report['Wind Speed'] = safe_format("%.2f", report['wind_ave'])
        csv_report['Wind Gust'] = safe_format("%.2f", report['wind_gust'])
        csv_report['Wind Direction'] = safe_format("%d", conversions.winddir_degrees(report['wind_dir']))
        csv_report['Relative Humidity'] = report['hum_out']
        # csv_report['Mean Sea-Level Pressure'] = "%.2f" % report['rel_pressure']
        csv_report['Pressure (At Station)'] = "%.2f" % report['abs_pressure']
        print "Processing "+str(csv_report['Report Date / Time'])+"..."
        csv_writer.writerow(csv_report)
        prev_idx = report['idx']

    return 0


def rain_day(calib_data, report):
    midnight = datetime.utcnow().replace(tzinfo=utc).astimezone(
            Local).replace(hour=0, minute=0, second=0).astimezone(
                utc).replace(tzinfo=None)
    while report['idx'] < midnight:
        midnight -= DAY
        rain_midnight = None
    while report['idx'] >= midnight + DAY:
        midnight += DAY
        rain_midnight = None
    if rain_midnight is None:
        rain_midnight = calib_data[calib_data.nearest(midnight)]['rain']
    return max(0.0, report['rain'] - rain_midnight)


def max_temp24(calib_data, report):
    start = calib_data[calib_data.nearest(report['idx'] - DAY)]
    max_temp = report['temp_out']
    for r in calib_data[start['idx']:report['idx']]:
        max_temp = max(max_temp, r['temp_out'])
    return max_temp


def safe_format(format, value):
    return format % value if value else None


def main(argv=None):
    if argv is None:
        argv = sys.argv
    try:
        opts, args = getopt.getopt(argv[1:], "hv", ['help', 'verbose'])
    except getopt.error, msg:
        print >>sys.stderr, 'Error: %s\n' % msg
        print >>sys.stderr, __usage__.strip()
        return 1
    # process options
    verbose = 0
    for o, a in opts:
        if o in ('-h', '--help'):
            print __usage__.strip()
            return 0
        elif o in ('-v', '--verbose'):
            verbose += 1
    # check arguments
    if len(args) != 2:
        print >>sys.stderr, 'Error: 2 argument required\n'
        print >>sys.stderr, __usage__.strip()
        return 2
    logger = ApplicationLogger(verbose)
    (data_dir, out_file) = args;
    return GenerateBulk(data_dir, out_file)

if __name__ == "__main__":
    sys.exit(main())
