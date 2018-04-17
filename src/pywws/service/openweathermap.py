# pywws - Python software for USB Wireless Weather Stations
# http://github.com/jim-easterbrook/pywws
# Copyright (C) 2018  pywws contributors

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

"""Upload weather data to Open Weather Map.

`Open Weather Map`_ is a Latvian based IT company seeking to provide
affordable weather data.

* Create account: http://home.openweathermap.org/users/sign_up
* API: http://openweathermap.org/stations
* Example ``weather.ini`` configuration::

    [openweathermap]
    api key = b1b15e88fa797225412429c1c50c122a1
    lat = 51.501
    long = -0.142
    alt = 10
    external id = SW1Aweather
    station name = Buck House
    station id = 583436dd9643a9000196b8d6

    [logged]
    services = ['openweathermap', 'underground']

After signing up and logging in to OpenWeatherMap visit the `API keys
page`_ and copy your default key to the ``api key`` entry in
weather.ini. ``lat`` and ``long`` should be set to the latitude and
longitude of your station (in degrees) and ``alt`` to its altitude in
metres.

The ``external id`` field is a single word name to identify your
station. You could use a name based on your post code, or maybe your id
from Weather Underground or CWOP. The ``station name`` is a longer,
human readable, name. I'm not sure what use OpenWeatherMap makes of
either of these.

After setting (or changing) the above fields you need to "register" your
station with OpenWeatherMap. This is done by running the
pywws.service.openweathermap module with the ``-r`` flag::

    python -m pywws.service.openweathermap -r -v data_dir

If this succeeds then OpenWeatherMap will have allocated a ``station
id`` value which pywws stores in weather.ini. All this complication is
to allow you to have more than one station attached to one user's
account.

.. _Open Weather Map: http://openweathermap.org/
.. _API keys page: https://home.openweathermap.org/api_keys

"""

from __future__ import absolute_import, unicode_literals

from contextlib import contextmanager
from datetime import timedelta
import json
import logging
import os
import sys

import requests

import pywws.service

__docformat__ = "restructuredtext en"
service_name = os.path.splitext(os.path.basename(__file__))[0]
logger = logging.getLogger(__name__)


class ToService(pywws.service.BaseToService):
    catchup = 7
    fixed_data = {}
    interval = timedelta(seconds=40)
    logger = logger
    service_name = service_name
    template = """
#live#
#idx          "'dt'         : %s,"#
#temp_out     "'temperature': %.1f,"#
#wind_ave     "'wind_speed' : %.1f,"#
#wind_gust    "'wind_gust'  : %.1f,"#
#wind_dir     "'wind_deg'   : %.0f," "" "winddir_degrees(x)"#
#rel_pressure "'pressure'   : %.1f,"#
#hum_out      "'humidity'   : %.d,"#
#calc "rain_hour(data)" "'rain_1h': %.1f,"#
#calc "rain_24hr(data)" "'rain_24h': %.1f,"#
#calc "dew_point(data['temp_out'], data['hum_out'])" "'dew_point': %.1f,"#
"""

    def __init__(self, context):
        # get station params
        self.params = {
            'api_key'     : context.params.get(service_name, 'api key', ''),
            'external_id' : context.params.get(service_name, 'external id', ''),
            'station_name': context.params.get(service_name, 'station name', ''),
            'lat'         : context.params.get(service_name, 'lat', ''),
            'long'        : context.params.get(service_name, 'long', ''),
            'alt'         : context.params.get(service_name, 'alt', ''),
            }
        # get configurable "fixed data"
        self.fixed_data.update({
            'station_id': context.params.get(service_name, 'station id'),
            })
        # base class init
        super(ToService, self).__init__(context)

    @contextmanager
    def session(self):
        with requests.Session() as session:
            session.headers.update({'Content-Type': 'application/json'})
            session.params.update({'appid': self.params['api_key']})
            yield session

    def upload_data(self, session, prepared_data={}, live=False):
        url = 'http://api.openweathermap.org/data/3.0/measurements'
        try:
            rsp = session.post(url, json=[prepared_data], timeout=60)
        except Exception as ex:
            return False, str(ex)
        if rsp.status_code != 204:
            return False, 'http status: {:d} {:s}'.format(
                rsp.status_code, rsp.text)
        return True, 'OK'

    def register(self):
        url = 'http://api.openweathermap.org/data/3.0/stations'
        data = {
            'external_id': self.params['external_id'],
            'name'       : self.params['station_name'],
            'latitude'   : float(self.params['lat']),
            'longitude'  : float(self.params['long']),
            'altitude'   : float(self.params['alt']),
            }
        with self.session() as session:
            if self.fixed_data['station_id']:
                # update existing station
                logger.debug(
                    'Udating station id ' + self.fixed_data['station_id'])
                url += '/' + self.fixed_data['station_id']
                try:
                    rsp = session.put(url, json=data, timeout=60)
                except Exception as ex:
                    print('exception', str(ex))
                    return
                rsp = rsp.json()
                logger.debug('response: ' + repr(rsp))
            else:
                # create new station
                logger.debug('Creating new station')
                try:
                    rsp = session.post(url, json=data, timeout=60)
                except Exception as ex:
                    print('exception', str(ex))
                    return
                rsp = rsp.json()
                logger.debug('response: ' + repr(rsp))
                self.context.params.set(
                    self.service_name, 'station id', rsp['ID'])


if __name__ == "__main__":
    sys.exit(pywws.service.main(ToService, 'Upload data to OpenWeatherMap'))
