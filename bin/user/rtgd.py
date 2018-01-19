# rtgd.py
#
# A weeWX service to generate a loop based gauge-data.txt.
#
# Copyright (C) 2017 Gary Roderick                  gjroderick<at>gmail.com
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see http://www.gnu.org/licenses/.
#
# Version: 0.3.0                                      Date: 4 September 2017
#
# Revision History
#   4 September 2017    v0.3.0
#       - added ability to include Weather Underground forecast text
#   8 July 2017         v0.2.14
#       - changed default decimal places for foot, inHg, km_per_hour and
#         mile_per_hour
#       - reformatted change summary
#       - minor refactoring of RtgdBuffer class
#   6 May 2017          v0.2.13
#       - unnecessary whitespace removed from JSON output(issue #2)
#       - JSON output now sorted alphabetically by key (issue #2)
#       - Revised debug logging. Now supports debug=0,1,2 and 3: (issue #7)
#         0 - standard weeWX output, no debug info
#         1 - as per debug=0, advises whether Zambretti is available, logs
#             minor non-fatal errors (eg posting)
#         2 - as per debug=1, logs events that occur, eg packets queued,
#             packets processed, output generated
#         3   as per debug=2, logs packet/record contents
#       - gauge-data.txt destination directory tree is created if it does not
#         exist(issue #8)
#   27 March 2017       v0.2.12(never released)
#       - fixed empty sequence ValueError associated with BearingRangeFrom10
#         and BearingRangeTo10
#       - fixed division by zero error in windrun calculations for first
#         archive period of the day
#   22 March 2017       v0.2.11
#       - can now include local date/time in scroller text by including
#         strftime() format directives in the scroller text
#       - gauge-data.txt content can now be sent to a remote URL via HTTP POST.
#         Thanks to Alec Bennett for his idea.
#   17 March 2017       v0.2.10
#       - now supports reading scroller text from a text file specified by the
#         scroller_text config option in [RealtimeGaugeData]
#   7 March 2017        v0.2.9
#       - reworked ten minute gust calculation to fix problem where red gust
#         'wedge' would occasionally temporarily disappear from wind speed
#         gauge
#   28 February 2017    v0.2.8
#       - Reworked day max/min calculations to better handle missing historical
#         data. If historical max/min data is missing day max/min will default
#         to the current value for the obs concerned.
#   26 February 2017    v0.2.7
#       - loop packets are now cached to support stations that emit partial
#         packets
#       - windSpeed obtained from archive is now only handled as a ValueTuple
#         to avoid units issues
#   22 February 2017    v0.2.6
#       - updated docstring config options to reflect current library of
#         available options
#       - 'latest' and 'avgbearing' wind directions now return the last
#         non-None wind direction respectively when their feeder direction is
#         None
#       - implemented optional scroller_text config option allowing fixed
#         scroller text to be specified in lieu of Zambretti forecast text
#       - renamed rtgd thread and queue variables
#       - no longer reads unit group config options that have only one possible
#         unit
#       - use of mmHg, knot or cm units reverts to hPa, mile_per_hour and mm
#         respectively due to weeWX or SteelSeries Gauges not understanding the
#         unit (or derived unit)
#       - made gauge-data.txt unit code determination more robust
#       - reworked code that formats gauge-data.txt field data to better handle
#         None values
#   21 February 2017    v0.2.5
#       - fixed error where altitude units could not be changed from meter
#       - rainrate and windrun unit groups are now derived from rain and speed
#         units groups respectively
#       - solar calc config options no longer searched for in [StdWXCalculate]
#   20 February 2017    v0.2.4
#       - fixed error where rain units could not be changed from mm
#       - pressures now formats to correct number of decimal places
#       - reworked temp and pressure trend formatting
#   20 February 2017    v0.2.3
#       - Fixed logic error in windrose calculations. Minor tweaking of
#         windrose processing.
#   19 February 2017    v0.2.2
#       - Added config option apptemp_binding specifying a binding containing
#         appTemp data. apptempTL and apptempTH default to apptemp if binding
#         not specified or it does not contain appTemp data.
#   15 February 2017    v0.2.1
#       - fixed error that resulted in incorrect pressL and pressH values
#   24 January 2017     v0.2.0
#       - now runs in a thread to eliminate blocking impact on weeWX
#       - now calculates WindRoseData
#       - now calculates pressL and pressH
#       - frequency of generation is now specified by a single config option
#         min_interval
#       - gauge-data.txt output path is now specified by rtgd_path config
#         option
#       - added config options for windrose period and number of compass points
#         to be generated
#   19 January 2017     v0.1.2
#       - fix error that occurred when stations do not emit radiation
#   18 January 2017     v0.1.1
#       - better handles loop observations that are None
#   3 January 2017      v0.1.0
#       - initial release
#
"""A weeWX service to generate a loop based gauge-data.txt.

Used to update the SteelSeries Weather Gauges in near real time.

Inspired by crt.py v0.5 by Matthew Wall, a weeWX service to emit loop data to
file in Cumulus realtime format. Refer http://wiki.sandaysoft.com/a/Realtime.txt

Use of HTTP POST to send gauge-data.txt content to a remote URL inspired by
work by Alec Bennett. Refer https://github.com/wrybread/weewx-realtime_gauge-data.

Abbreviated instructions for use:

1.  Install the SteelSeries Weather Gauges for weeWX and confirm correct
operation of the gauges with weeWX. Refer to
https://github.com/mcrossley/SteelSeries-Weather-Gauges/tree/master/weather_server/WeeWX

2.  Put this file in $BIN_ROOT/user.

3.  Add the following stanza to weewx.conf:

[RealtimeGaugeData]
    # Date format to be used in gauge-data.txt. Default is %Y.%m.%d %H:%M
    date_format = %Y.%m.%d %H:%M

    # Path to gauge-data.txt. Relative paths are relative to HTML_ROOT. If
    # empty default is HTML_ROOT. If setting omitted altogether default is
    # /var/tmp
    rtgd_path = /home/weewx/public_html

    # File name (only) of file produced by rtgd. Optional, default is
    # gauge-data.txt.
    rtgd_file_name = gauge-data.txt

    # Remote URL to which the gauge-data.txt data will be posted via HTTP POST.
    # Optional, omit to disable HTTP POST.
    remote_server_url = http://remote/address
    # timeout in seconds for remote URL posts. Optional, default is 2
    timeout = 1
    # Text returned from remote URL indicating success. Optional, default is no
    # response text.
    response_text = success

    # Minimum interval (seconds) between file generation. Ideally
    # gauge-data.txt would be generated on receipt of every loop packet (there
    # is no point in generating more frequently than this); however, in some
    # cases the user may wish to generate gauge-data.txt less frequently. The
    # min_interval option sets the minimum time between successive
    # gauge-data.txt generations. Generation will be skipped on arrival of a
    # loop packet if min_interval seconds have NOT elapsed since the last
    # generation. If min_interval is 0 or omitted generation will occur on
    # every loop packet (as will be the case if min_interval < station loop
    # period). Optional, default is 0.
    min_interval =

    # Number of compass points to include in WindRoseData, normally
    # 8 or 16. Optional, default 16.
    windrose_points = 16

    # Period over which to calculate WindRoseData in seconds. Optional, default
    # is 86400 (24 hours).
    windrose_period = 86400

    # Binding to use for appTemp data. Optional, default 'wx_binding'.
    apptemp_binding = wx_binding

    # The SteelSeries Weather Gauges displays the content of the gauge-data.txt
    # 'forecast' field in the scrolling text display. The RTGD service can
    # populate the 'forecast' field in a number of ways. The RTGD service works
    # through the following sources, in order, and the first options that
    # provides valid data (ie non-None) is used to populate the 'forecast'
    # field:
    #
    # 1. text at [RealtimeGaugeData] scroller_text option
    # 2. file specified at [RealtimeGaugeData] scroller_file option
    # 3. Weather Underground API sourced forecast text for location specified
    #    at [RealtimeGaugeData] [[WU]]
    # 4. Zambretti forecast if weeWX Forecast extension is installed
    #
    # If none of the above are set/installed or provide a non-None result the,
    # forecast field is set to '' (empty string).

    # Text to display on the scroller. Must be enclosed in quotes if spaces
    # included. Python strftime format codes may be embedded in the string to
    # display the current time/date. Optional, omit to disable.
    scroller_text = 'some text'

    # File to use as source for the scroller text. File must be a text file,
    # first line only of file is read. Only used if scroller_text is blank or
    # omitted. Optional, omit to disable.
    scroller_file = /var/tmp/scroller.txt

    # Update windrun value each loop period or just on each archive period.
    # Optional, default is False.
    windrun_loop = false

    # Stations that provide partial packets are supported through a cache that
    # caches packet data. max_cache_age is the maximum age  in seconds for
    # which cached data is retained. Optional, default is 600 seconds.
    max_cache_age = 600

    # Parameters used in/required by rtgd calculations
    [[Calculate]]
        # Atmospheric transmission coefficient [0.7-0.91]. Optional, default
        # is 0.8
        atc = 0.8
        # Atmospheric turbidity (2=clear, 4-5=smoggy). Optional, default is 2.
        nfac = 2
        [[[Algorithm]]]
            # Theoretical max solar radiation algorithm to use, must be RS or
            # Bras. optional, default is RS
            maxSolarRad = RS

    [[StringFormats]]
        # String formats. Optional.
        degree_C = %.1f
        degree_F = %.1f
        degree_compass = %.0f
        hPa = %.1f
        inHg = %.2f
        inch = %.2f
        inch_per_hour = %.2f
        km_per_hour = %.1f
        km = %.1f
        mbar = %.1f
        meter = %.0f
        meter_per_second = %.1f
        mile_per_hour = %.1f
        mile = %.1f
        mm = %.1f
        mm_per_hour = %.1f
        percent = %.0f
        uv_index = %.1f
        watt_per_meter_squared = %.0f

    [[Groups]]
        # Groups. Optional. Note not all available weeWX units are supported
        # for each group.
        group_altitude = foot        # Options are 'meter' or 'foot'
        group_pressure = hPa         # Options are 'inHg', 'mbar', or 'hPa'
        group_rain = mm              # Options are 'inch' or 'mm'
        group_speed = km_per_hour    # Options are 'mile_per_hour',
                                       'km_per_hour' or 'meter_per_second'
        group_temperature = degree_C # Options are 'degree_F' or 'degree_C'

    # Specify settings to be used to obtain WU forecast text to display in the
    # 'forecast' field. Optional.
    [[WU]]
        # Enable/disable WU forecast text
        enable = true

        # WU API key to be used when calling the WU API
        api_key = xxxxxxxxxxxxxxxx

        # Interval (in seconds) between forecast downloads. Default
        # is 1800.
        interval = 1800

        # Minimum period (in seconds) between  API calls. This prevents
        # conditions where a misbehaving program could call the WU API
        # repeatedly thus violating the API usage conditions.
        # Default is 60.
        api_lockout_period = 60

        # Maximum number attempts to obtain an API response. Default is 3.
        max_WU_tries = 3

        # The location for the forecast and current conditions can be one
        # of the following:
        #   CA/San_Francisco     - US state/city
        #   60290                - US zip code
        #   Australia/Sydney     - Country/City
        #   37.8,-122.4          - latitude,longitude
        #   KJFK                 - airport code
        #   pws:KCASANFR70       - PWS id
        #   autoip               - AutoIP address location
        #   autoip.json?geo_ip=38.102.136.138 - specific IP address
        #                                       location
        # If no location is specified, station latitude and longitude are
        # used
        location = enter location here

        # The forecast text can be presented using either US imperial or Metric
        # units. Optional string 'US' or 'Metric', default is 'Metric'
        units =

4.  Add the RealtimeGaugeData service to the list of report services under
[Engines] [[WxEngine]] in weewx.conf:

[Engines]
    [[WxEngine]]
        report_services = ..., user.rtgd.RealtimeGaugeData

5.  If you intend to save the realtime generated gauge-data.txt in the same
location as the ss skin generated gauge-data.txt then you must disable the
skin generated gauge-data.txt by commenting out the [[[data]]] entry and all
subordinate settings under [CheetahGenerator] [[ToDate]] in
$SKIN_ROOT/ss/skin.conf:

[CheetahGenerator]
    encoding = html_entities
    [[ToDate]]
        [[[index]]]
            template = index.html.tmpl
        # [[[data]]]
        #     template = gauge-data.txt.tmpl

6.  Edit $SKIN_ROOT/ss/scripts/gauges.js and change the realTimeURL_weewx
setting (circa line 68) to refer to the location of the realtime generated
gauge-data.txt. Change the realtimeInterval setting (circa line 37) to reflect
the update period of the realtime gauge-data.txt in seconds. This setting
controls the count down timer and update frequency of the SteelSeries Weather
Gauges.

7.  Delete the file $HTML_ROOT/ss/scripts/gauges.js.

8.  Stop/start weeWX

9.  Confirm that gauge-data.txt is being generated regularly as per the period
and nth_loop settings under [RealtimeGaugeData] in weewx.conf.

10.  Confirm the SteelSeries Weather Gauges are being updated each time
gauge-data.txt is generated.

To do:
    - hourlyrainTH, ThourlyrainTH and LastRainTipISO. Need to populate these
      fields, presently set to 0.0, 00:00 and 00:00 respectively.
    - Lost contact with station sensors is implemented for Vantage and
      Simulator stations only. Need to extend current code to cater for the
      weeWX supported stations. Current code assume that contact is there
      unless told otherwise.
    - consolidate wind lists into a single list.
    - add windTM to loop packet (a la appTemp in wd.py). windTM is
      calculated as the greater of either (1) max windAv value for the day to
      date (from stats db)or (2) calcFiveMinuteAverageWind which calculates
      average wind speed over the 5 minutes preceding the latest loop packet.
      Should calcFiveMinuteAverageWind produce a max average wind speed then
      this may not be reflected in the stats database as the average wind max
      recorded in stats db is based on archive records only. This is because
      windAv is in an archive record but not in a loop packet. This can be
      remedied by adding the calculated average to the loop packet. weeWX
      normal archive processing will then take care of updating stats db.

Handy things/conditions noted from analysis of SteelSeries Weather Gauges:
    - wind direction is from 1 to 360, 0 is treated as calm ie no wind
    - trend periods are assumed to be one hour except for barometer which is
      taken as three hours
    - wspeed is 10 minute average wind speed (refer to wind speed gauge hover
      and gauges.js
"""

# python imports
import Queue
import datetime
import errno
import httplib
import json
import math
import os.path
import socket
import syslog
import threading
import time
import urllib2
from operator import itemgetter

# weeWX imports
import weedb
import weewx
import weeutil.weeutil
import weewx.units
import weewx.wxformulas
from weewx.engine import StdService
from weewx.units import ValueTuple, convert, getStandardUnitType, ListOfDicts
from weeutil.weeutil import to_bool, to_int, startOfDay

# version number of this script
RTGD_VERSION = '0.3.0'
# version number (format) of the generated gauge-data.txt
GAUGE_DATA_VERSION = '13'

# ordinal compass points supported
COMPASS_POINTS = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
                  'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW', 'N']

# map weeWX unit names to unit names supported by the SteelSeries Weather
# Gauges
UNITS_WIND = {'mile_per_hour':      'mph',
              'meter_per_second':   'm/s',
              'km_per_hour':        'km/h'}
UNITS_TEMP = {'degree_C': 'C',
              'degree_F': 'F'}
UNITS_PRES = {'inHg': 'in',
              'mbar': 'mb',
              'hPa':  'hPa'}
UNITS_RAIN = {'inch': 'in',
              'mm':   'mm'}
UNITS_CLOUD = {'foot':  'ft',
               'meter': 'm'}
GROUP_DIST = {'mile_per_hour':      'mile',
              'meter_per_second':   'km',
              'km_per_hour':        'km'}
# the obs that we will buffer
MANIFEST = ['outTemp', 'barometer', 'outHumidity', 'rain', 'rainRate',
            'humidex', 'windchill', 'heatindex', 'windSpeed', 'inTemp',
            'appTemp', 'dewpoint', 'windDir', 'UV', 'radiation', 'wind',
            'windGust', 'windGustDir']

# obs for which we need a history
HIST_MANIFEST = ['windSpeed', 'windDir', 'windGust', 'wind']

MAX_AGE = 600

# Define station lost contact checks for supported stations. Note that at
# present only Vantage and FOUSB stations lost contact reporting is supported.
STATION_LOST_CONTACT = {'Vantage': {'field': 'rxCheckPercent', 'value': 0},
                        'FineOffsetUSB': {'field': 'status', 'value': 0x40},
                        'Ultimeter': {'field': 'rxCheckPercent', 'value': 0},
                        'WMR100': {'field': 'rxCheckPercent', 'value': 0},
                        'WMR200': {'field': 'rxCheckPercent', 'value': 0},
                        'WMR9x8': {'field': 'rxCheckPercent', 'value': 0},
                        'WS23xx': {'field': 'rxCheckPercent', 'value': 0},
                        'WS28xx': {'field': 'rxCheckPercent', 'value': 0},
                        'TE923': {'field': 'rxCheckPercent', 'value': 0},
                        'WS1': {'field': 'rxCheckPercent', 'value': 0},
                        'CC3000': {'field': 'rxCheckPercent', 'value': 0}}
# stations supporting lost contact reporting through their archive record
ARCHIVE_STATIONS = ['Vantage']
# stations supporting lost contact reporting through their loop packet
LOOP_STATIONS = ['FineOffsetUSB']


def logmsg(level, msg):
    syslog.syslog(level, msg)


def logcrit(id, msg):
    logmsg(syslog.LOG_CRIT, '%s: %s' % (id, msg))


def logdbg(id, msg):
    logmsg(syslog.LOG_DEBUG, '%s: %s' % (id, msg))


def logdbg2(id, msg):
    if weewx.debug >= 2:
        logmsg(syslog.LOG_DEBUG, '%s: %s' % (id, msg))


def logdbg3(id, msg):
    if weewx.debug >= 3:
        logmsg(syslog.LOG_DEBUG, '%s: %s' % (id, msg))


def loginf(id, msg):
    logmsg(syslog.LOG_INFO, '%s: %s' % (id, msg))


def logerr(id, msg):
    logmsg(syslog.LOG_ERR, '%s: %s' % (id, msg))


# ============================================================================
#                     Exceptions that could get thrown
# ============================================================================


class MissingApiKey(IOError):
    """Raised when a WU API key cannot be found"""


# ============================================================================
#                          class RealtimeGaugeData
# ============================================================================


class RealtimeGaugeData(StdService):
    """Service that generates gauge-data.txt in near realtime.

    The RealtimeGaugeData class creates and controls a threaded object of class
    RealtimeGaugeDataThread that generates gauge-data.txt. Class
    RealtimeGaugeData feeds the RealtimeGaugeDataThread object with data via an
    instance of Queue.Queue.
    """

    def __init__(self, engine, config_dict):
        # initialize my superclass
        super(RealtimeGaugeData, self).__init__(engine, config_dict)

        self.rtgd_ctl_queue = Queue.Queue()
        # get our RealtimeGaugeData config dictionary
        rtgd_config_dict = config_dict.get('RealtimeGaugeData', {})
        manager_dict = weewx.manager.get_manager_dict_from_config(config_dict,
                                                                  'wx_binding')
        self.db_manager = weewx.manager.open_manager(manager_dict)

        #
        wu_config_dict = rtgd_config_dict.get('WU', None)
        if wu_config_dict is not None and to_bool(wu_config_dict.get('enable', False)):
            self.wu_ctl_queue = Queue.Queue()
            self.result_queue = Queue.Queue()
            self.wu_thread = WUThread(self.wu_ctl_queue,
                                      self.result_queue,
                                      config_dict,
                                      wu_config_dict,
                                      lat=engine.stn_info.latitude_f,
                                      long=engine.stn_info.longitude_f,
                                      )
            self.wu_thread.start()
        else:
            self.wu_thread = None
            self.result_queue = None

        # get an instance of class RealtimeGaugeDataThread and start the
        # thread running
        self.rtgd_thread = RealtimeGaugeDataThread(self.rtgd_ctl_queue,
                                                   self.result_queue,
                                                   config_dict,
                                                   manager_dict,
                                                   latitude=engine.stn_info.latitude_f,
                                                   longitude=engine.stn_info.longitude_f,
                                                   altitude=convert(engine.stn_info.altitude_vt, 'meter').value)
        self.rtgd_thread.start()

        # bind ourself to the relevant weeWX events
        self.bind(weewx.NEW_LOOP_PACKET, self.new_loop_packet)
        self.bind(weewx.NEW_ARCHIVE_RECORD, self.new_archive_record)
        self.bind(weewx.END_ARCHIVE_PERIOD, self.end_archive_period)

    def new_loop_packet(self, event):
        """Puts new loop packets in the rtgd queue."""

        # package the loop packet in a dict since this is not the only data
        # we send via the queue
        _package = {'type': 'loop',
                    'payload': event.packet}
        self.rtgd_ctl_queue.put(_package)
        if weewx.debug == 2:
            logdbg("rtgd",
                   "queued loop packet (%s)" % _package['payload']['dateTime'])
        elif weewx.debug >= 3:
            logdbg("rtgd", "queued loop packet: %s" % _package['payload'])

    def new_archive_record(self, event):
        """Puts archive records in the rtgd queue."""

        # package the archive record in a dict since this is not the only data
        # we send via the queue
        _package = {'type': 'archive',
                    'payload': event.record}
        self.rtgd_ctl_queue.put(_package)
        if weewx.debug == 2:
            logdbg("rtgd",
                   "queued archive record (%s)" % _package['payload']['dateTime'])
        elif weewx.debug >= 3:
            logdbg("rtgd", "queued archive record: %s" % _package['payload'])
        # get alltime min max baro and put in the queue
        # get the min and max values (incl usUnits)
        _minmax_baro = self.get_minmax_obs('barometer')
        # if we have some data then package it in a dict since this is not the
        # only data we send via the queue
        if _minmax_baro:
            _package = {'type': 'stats',
                        'payload': _minmax_baro}
            self.rtgd_ctl_queue.put(_package)
            if weewx.debug == 2:
                logdbg("rtgd", "queued min/max barometer values")
            elif weewx.debug >= 3:
                logdbg("rtgd",
                       "queued min/max barometer values: %s" % _package['payload'])

    def end_archive_period(self, event):
        """Puts END_ARCHIVE_PERIOD event in the rtgd queue."""

        # package the event in a dict since this is not the only data we send
        # via the queue
        _package = {'type': 'event',
                    'payload': weewx.END_ARCHIVE_PERIOD}
        self.rtgd_ctl_queue.put(_package)
        logdbg2("rtgd", "queued weewx.END_ARCHIVE_PERIOD event")

    def shutDown(self):
        """Shut down any threads.

        Would normally do all of a given threads actions in one go but since
        we may have more than one thread and so that we don't have sequential
        (potential) waits of up to 15 seconds we send each thread a shutdown
        signal and then go and check that each has indeed shutdown.
        """

        if hasattr(self, 'rtgd_ctl_queue') and hasattr(self, 'rtgd_thread'):
            if self.rtgd_ctl_queue and self.rtgd_thread.isAlive():
                # Put a None in the rtgd_ctl_queue to signal the thread to
                # shutdown
                self.rtgd_ctl_queue.put(None)
        if hasattr(self, 'wu_ctl_queue') and hasattr(self, 'wu_thread'):
            if self.wu_ctl_queue and self.wu_thread.isAlive():
                # Put a None in the wu_ctl_queue to signal the thread to
                # shutdown
                self.wu_ctl_queue.put(None)
        if hasattr(self, 'rtgd_thread') and self.rtgd_thread.isAlive():
            # Wait up to 15 seconds for the thread to exit:
            self.rtgd_thread.join(15.0)
            if self.rtgd_thread.isAlive():
                logerr("rtgd",
                       "Unable to shut down %s thread" % self.rtgd_thread.name)
            else:
                logdbg("rtgd", "Shut down %s thread." % self.rtgd_thread.name)
        if hasattr(self, 'wu_thread') and self.wu_thread.isAlive():
            # Wait up to 15 seconds for the thread to exit:
            self.wu_thread.join(15.0)
            if self.wu_thread.isAlive():
                logerr("rtgd",
                       "Unable to shut down %s thread" % self.wu_thread.name)
            else:
                logdbg("rtgd", "Shut down %s thread." % self.wu_thread.name)

    def get_minmax_obs(self, obs_type):
        """Obtain the alltime max/min values for an observation."""

        # create an interpolation dict
        inter_dict = {'table_name': self.db_manager.table_name,
                      'obs_type': obs_type}
        # the query to be used
        minmax_sql = "SELECT MIN(min), MAX(max) FROM %(table_name)s_day_%(obs_type)s"
        # execute the query
        _row = self.db_manager.getSql(minmax_sql % inter_dict)
        if not _row or None in _row:
            return {'min_%s' % obs_type: None,
                    'max_%s' % obs_type: None}
        else:
            return {'min_%s' % obs_type: _row[0],
                    'max_%s' % obs_type: _row[1]}


# ============================================================================
#                       class RealtimeGaugeDataThread
# ============================================================================


class RealtimeGaugeDataThread(threading.Thread):
    """Thread that generates gauge-data.txt in near realtime."""

    def __init__(self, control_queue, result_queue, config_dict, manager_dict,
                 latitude, longitude, altitude):
        # Initialize my superclass:
        threading.Thread.__init__(self)

        # setup a few thread things
        self.setName('RtgdThread')
        self.setDaemon(True)

        self.control_queue = control_queue
        self.result_queue = result_queue
        self.config_dict = config_dict
        self.manager_dict = manager_dict

        # get our RealtimeGaugeData config dictionary
        rtgd_config_dict = config_dict.get('RealtimeGaugeData', {})

        # setup file generation timing
        self.min_interval = rtgd_config_dict.get('min_interval', None)
        self.last_write = 0  # ts (actual) of last generation

        # get our file paths and names
        _path = rtgd_config_dict.get('rtgd_path', '/var/tmp')
        _html_root = os.path.join(config_dict['WEEWX_ROOT'],
                                  config_dict['StdReport'].get('HTML_ROOT', ''))

        self.rtgd_path = os.path.join(_html_root, _path)
        self.rtgd_path_file = os.path.join(self.rtgd_path,
                                           rtgd_config_dict.get('rtgd_file_name',
                                                                'gauge-data.txt'))

        # get the remote server URL if it exists, if it doesn't set it to None
        self.remote_server_url = rtgd_config_dict.get('remote_server_url', None)
        # timeout to be used for remote URL posts
        self.timeout = to_int(rtgd_config_dict.get('timeout', 2))
        # response text from remote URL if post was successful
        self.response = rtgd_config_dict.get('response_text', None)

        # get scroller text if there is any
        self.scroller_text = rtgd_config_dict.get('scroller_text', None)
        if self.scroller_text is not None and self.scroller_text.strip() == '':
            self.scroller_text = None
        # get scroller file if specified, check it refers to a file
        self.scroller_file = rtgd_config_dict.get('scroller_file', None)
        if self.scroller_file is not None and not os.path.isfile(self.scroller_file):
            self.scroller_file = None

        # get windrose settings
        try:
            self.wr_period = int(rtgd_config_dict.get('windrose_period',
                                                      86400))
        except ValueError:
            self.wr_period = 86400
        try:
            self.wr_points = int(rtgd_config_dict.get('windrose_points', 16))
        except ValueError:
            self.wr_points = 16

        # setup max solar rad calcs
        # do we have any?
        calc_dict = config_dict.get('Calculate', {})
        # algorithm
        algo_dict = calc_dict.get('Algorithm', {})
        self.solar_algorithm = algo_dict.get('maxSolarRad', 'RS')
        # atmospheric transmission coefficient [0.7-0.91]
        self.atc = float(calc_dict.get('atc', 0.8))
        # Fail hard if out of range:
        if not 0.7 <= self.atc <= 0.91:
            raise weewx.ViolatedPrecondition("Atmospheric transmission "
                                             "coefficient (%f) out of "
                                             "range [.7-.91]" % self.atc)
        # atmospheric turbidity (2=clear, 4-5=smoggy)
        self.nfac = float(calc_dict.get('nfac', 2))
        # Fail hard if out of range:
        if not 2 <= self.nfac <= 5:
            raise weewx.ViolatedPrecondition("Atmospheric turbidity (%d) "
                                             "out of range (2-5)" % self.nfac)

        # Get our groups and format strings
        self.date_format = rtgd_config_dict.get('date_format',
                                                '%Y.%m.%d %H:%M')
        self.time_format = '%H:%M'
        self.temp_group = rtgd_config_dict['Groups'].get('group_temperature',
                                                         'degree_C')
        self.temp_format = rtgd_config_dict['StringFormats'].get(self.temp_group,
                                                                 '%.1f')
        self.hum_group = 'percent'
        self.hum_format = rtgd_config_dict['StringFormats'].get(self.hum_group,
                                                                '%.0f')
        self.pres_group = rtgd_config_dict['Groups'].get('group_pressure',
                                                         'hPa')
        # SteelSeries Weather Gauges don't understand mmHg so default to hPa
        # if we have been told to use mmHg
        if self.pres_group == 'mmHg':
            self.pres_group = 'hPa'
        self.pres_format = rtgd_config_dict['StringFormats'].get(self.pres_group,
                                                                 '%.1f')
        self.wind_group = rtgd_config_dict['Groups'].get('group_speed',
                                                         'km_per_hour')
        # Since the SteelSeries Weather Gauges derives distance units from wind
        # speed units we cannot use knots because weeWX does not know how to
        # use distance in nautical miles. If we have been told to use knot then
        # default to mile_per_hour.
        if self.wind_group == 'knot':
            self.wind_group = 'mile_per_hour'
        self.wind_format = rtgd_config_dict['StringFormats'].get(self.wind_group,
                                                                 '%.1f')
        self.rain_group = rtgd_config_dict['Groups'].get('group_rain',
                                                         'mm')
        # SteelSeries Weather Gauges don't understand cm so default to mm if we
        # have been told to use cm
        if self.rain_group == 'cm':
            self.rain_group = 'mm'
        self.rain_format = rtgd_config_dict['StringFormats'].get(self.rain_group,
                                                                 '%.1f')
        # SteelSeries Weather gauges derives rain rate units from rain units,
        # so must we
        self.rainrate_group = ''.join([self.rain_group, '_per_hour'])
        self.rainrate_format = rtgd_config_dict['StringFormats'].get(self.rainrate_group,
                                                                     '%.1f')
        self.dir_group = 'degree_compass'
        self.dir_format = rtgd_config_dict['StringFormats'].get(self.dir_group,
                                                                '%.1f')
        self.rad_group = 'watt_per_meter_squared'
        self.rad_format = rtgd_config_dict['StringFormats'].get(self.rad_group,
                                                                '%.0f')
        self.uv_group = 'uv_index'
        self.uv_format = rtgd_config_dict['StringFormats'].get(self.uv_group,
                                                               '%.1f')
        # SteelSeries Weather gauges derives windrun units from wind speed
        # units, so must we
        self.dist_group = GROUP_DIST[self.wind_group]
        self.dist_format = rtgd_config_dict['StringFormats'].get(self.dist_group,
                                                                 '%.1f')
        self.alt_group = rtgd_config_dict['Groups'].get('group_altitude',
                                                        'meter')
        self.alt_format = rtgd_config_dict['StringFormats'].get(self.alt_group,
                                                                '%.1f')
        self.flag_format = '%.0f'

        # what units are incoming packets using
        self.packet_units = None

        # get max cache age
        self.max_cache_age = rtgd_config_dict.get('max_cache_age', 600)

        # initialise last wind directions for use when respective direction is
        # None. We need latest and average
        self.last_dir = 0
        self.last_average_dir = 0

        # Are we updating windrun using archive data only or archive and loop
        # data?
        self.windrun_loop = to_bool(rtgd_config_dict.get('windrun_loop',
                                                         False))

        # weeWX does not normally archive appTemp so day stats are not usually
        # available; however, if the user does have appTemp in a database then
        # if we have a binding we can use it. Check if an appTemp binding was
        # specified, if so use it, otherwise default to 'wx_binding'. We will
        # check for data existence before using it.
        self.apptemp_binding = rtgd_config_dict.get('apptemp_binding',
                                                    'wx_binding')

#        # create a Buffer object to hold our loop 'stats'
#        self.buffer = Buffer(MANIFEST)

        # Set our lost contact flag. Assume we start off with contact
        self.lost_contact_flag = False

        # initialise some properties used to hold archive period wind data
        self.windSpeedAvg_vt = ValueTuple(None, 'km_per_hour', 'group_speed')
        self.windDirAvg = None
        self.min_barometer = None
        self.max_barometer = None

        # initialise forecast text
        self.forecast_text = None

        # get some station info
        self.latitude = latitude
        self.longitude = longitude
        self.altitude_m = altitude
        self.station_type = config_dict['Station']['station_type']

        # gauge-data.txt version
        self.version = str(GAUGE_DATA_VERSION)

        if self.min_interval is None:
            _msg = "RealTimeGaugeData will generate gauge-data.txt. "\
                       "min_interval is None"
        elif self.min_interval == 1:
            _msg = "RealTimeGaugeData will generate gauge-data.txt. "\
                       "min_interval is 1 second"
        else:
            _msg = "RealTimeGaugeData will generate gauge-data.txt. min_interval is %s seconds" % self.min_interval
        loginf("engine", _msg)

    def run(self):
        """Collect packets from the rtgd queue and manage their processing.

        Now that we are in a thread get a manager for our db so we can
        initialise our forecast and day stats. Once this is done we wait for
        something in the rtgd queue.
        """

        # would normally do this in our objects __init__ but since we are are
        # running in a thread we need to wait until the thread is actually
        # running before getting db managers

        try:
            # get a db manager
            self.db_manager = weewx.manager.open_manager(self.manager_dict)
            # get a db manager for appTemp
            self.apptemp_manager = weewx.manager.open_manager_with_config(self.config_dict,
                                                                          self.apptemp_binding)
            # get a Zambretti forecast objects
            self.forecast = ZambrettiForecast(self.config_dict)
            logdbg("rtgdthread",
                   "Zambretti is installed: %s" % self.forecast.is_installed())
            # initialise our day stats
            self.day_stats = self.db_manager._get_day_summary(time.time())
            # set the unit system for our day stats
            self.day_stats.unit_system = self.db_manager.std_unit_system
            # initialise our day stats from our appTemp source
            self.apptemp_day_stats = self.apptemp_manager._get_day_summary(time.time())
            # get a Buffer object
            self.buffer = Buffer(MANIFEST,
                                 day_stats=self.day_stats,
                                 additional_day_stats=self.apptemp_day_stats)

            # get a windrose to start with since it is only on receipt of an
            # archive record
            self.rose = calc_windrose(int(time.time()),
                                      self.db_manager,
                                      self.wr_period,
                                      self.wr_points)
            if weewx.debug == 2:
                logdbg("rtgdthread", "windrose data calculated")
            elif weewx.debug >= 3:
                logdbg("rtgdthread", "windrose data calculated: %s" % (self.rose,))
            # setup our loop cache and set some starting wind values
            _ts = self.db_manager.lastGoodStamp()
            if _ts is not None:
                _rec = self.db_manager.getRecord(_ts)
            else:
                _rec = {'usUnits': None}
            # get a CachedPacket object as our loop packet cache and prime it with
            # values from the last good archive record if available
            self.packet_cache = CachedPacket(_rec)
            logdbg2("rtgdthread", "loop packet cache initialised")
            # save the windSpeed value to use as our archive period average, this
            # needs to be a ValueTuple since we may need to convert units
            if 'windSpeed' in _rec:
                self.windSpeedAvg_vt = weewx.units.as_value_tuple(_rec, 'windSpeed')
            # save the windDir value to use as our archive period average
            if 'windDir' in _rec:
                self.windDirAvg = _rec['windDir']

            # now run a continuous loop, waiting for records to appear in the rtgd
            # queue then processing them.
            while True:
                # inner loop to monitor the queues
                while True:
                    # If we have a result queue check to see if we have received
                    # any forecast data. Use get_nowait() so we don't block the
                    # rtgd control queue. Wrap in a try..except to catch the error
                    # if there is nothing in the queue.
                    if self.result_queue:
                        try:
                            # use nowait() so we don't block
                            _package = self.result_queue.get_nowait()
                        except Queue.Empty:
                            # nothing in the queue so continue
                            pass
                        else:
                            # we did get something in the queue but was it a
                            # 'forecast' package
                            if isinstance(_package, dict):
                                if 'type' in _package and _package['type'] == 'forecast':
                                    # we have forecast text so log and save it
                                    logdbg2("rtgdthread",
                                            "received forecast text: %s" % _package['payload'])
                                    self.forecast_text = _package['payload']
                    # now deal with the control queue
                    try:
                        _package = self.control_queue.get_nowait()
                    except Queue.Empty:
                        # nothing in the queue so continue
                        pass
                    else:
                        # a None record is our signal to exit
                        if _package is None:
                            return
                        elif _package['type'] == 'archive':
                            if weewx.debug == 2:
                                logdbg("rtgdthread",
                                       "received archive record (%s)" % _package['payload']['dateTime'])
                            elif weewx.debug >= 3:
                                logdbg("rtgdthread",
                                       "received archive record: %s" % _package['payload'])
                            self.new_archive_record(_package['payload'])
                            self.rose = calc_windrose(_package['payload']['dateTime'],
                                                      self.db_manager,
                                                      self.wr_period,
                                                      self.wr_points)
                            if weewx.debug == 2:
                                logdbg("rtgdthread", "windrose data calculated")
                            elif weewx.debug >= 3:
                                logdbg("rtgdthread",
                                       "windrose data calculated: %s" % (self.rose,))
                            continue
                        elif _package['type'] == 'event':
### FIX ME - do we need this event?
                            if _package['payload'] == weewx.END_ARCHIVE_PERIOD:
                                logdbg2("rtgdthread",
                                        "received event - END_ARCHIVE_PERIOD")
                                # self.end_archive_period()
                            continue
                        elif _package['type'] == 'stats':
                            if weewx.debug == 2:
                                logdbg("rtgdthread",
                                       "received stats package")
                            elif weewx.debug >= 3:
                                logdbg("rtgdthread",
                                       "received stats package: %s" % _package['payload'])
                            self.process_stats(_package['payload'])
                            continue
                        elif _package['type'] == 'loop':
                            # we now have a packet to process, wrap in a
                            # try..except so we can catch any errors
                            try:
                                if weewx.debug == 2:
                                    logdbg("rtgdthread",
                                           "received loop packet (%s)" % _package['payload']['dateTime'])
                                elif weewx.debug >= 3:
                                    logdbg("rtgdthread",
                                           "received loop packet: %s" % _package['payload'])
                                self.process_packet(_package['payload'])
                                continue
                            except Exception, e:
                                # Some unknown exception occurred. This is probably
                                # a serious problem. Exit.
                                logcrit("rtgdthread",
                                        "Unexpected exception of type %s" % (type(e), ))
                                weeutil.weeutil.log_traceback('*** ',
                                                              syslog.LOG_DEBUG)
                                logcrit("rtgdthread",
                                        "Thread exiting. Reason: %s" % (e, ))
                                return
                    # if packets have backed up in the control queue, trim it until
                    # it's no bigger than the max allowed backlog
                    while self.control_queue.qsize() > 5:
                        self.control_queue.get()
        except Exception, e:
            # Some unknown exception occurred. This is probably
            # a serious problem. Exit.
            logcrit("rtgdthread run",
                    "Unexpected exception of type %s" % (type(e), ))
            weeutil.weeutil.log_traceback('*** ',
                                          syslog.LOG_DEBUG)
            logcrit("rtgdthread run",
                    "Thread exiting. Reason: %s" % (e, ))
            return

    def process_packet(self, packet):
        """Process incoming loop packets and generate gauge-data.txt.

        Input:
            packet: dict containing the loop packet to be processed
        """

        # get time for debug timing
        t1 = time.time()
        # convert our incoming packet
        loginf("rtgdthread", "1")
        loginf("rtgdthread", "packet=%s" % (packet,))
        loginf("rtgdthread", "self.day_stats.unit_system=%s" % (self.day_stats.unit_system,))
        _conv_packet = weewx.units.to_std_system(packet,
                                                 self.day_stats.unit_system)
        # update the packet cache with this packet
        loginf("rtgdthread", "2")
        self.packet_cache.update(_conv_packet, _conv_packet['dateTime'])
        # update the buffer with the converted packet
        loginf("rtgdthread", "3")
        self.buffer.add_packet(_conv_packet)

        # generate if we have no minimum interval setting or if minimum
        # interval seconds have elapsed since our last generation
        loginf("rtgdthread", "4")
        if self.min_interval is None or (self.last_write + float(self.min_interval)) < time.time():
            try:
                # get a cached packet
                cached_packet = self.packet_cache.get_packet(_conv_packet['dateTime'],
                                                             self.max_cache_age)
                if weewx.debug == 2:
                    logdbg("rtgdthread",
                           "created cached loop packet (%s)" % cached_packet['dateTime'])
                elif weewx.debug >= 3:
                    logdbg("rtgdthread",
                           "created cached loop packet: %s" % (cached_packet,))
                # set our lost contact flag if applicable
                if self.station_type in LOOP_STATIONS:
                    self.lost_contact_flag = cached_packet[STATION_LOST_CONTACT[self.station_type]['field']] == STATION_LOST_CONTACT[self.station_type]['value']
                # get a data dict from which to construct our file
                data = self.calculate(cached_packet)
                # write to our file
                self.write_data(data)
                # set our write time
                self.last_write = time.time()
                # if required send the data to a remote URL via HTTP POST
                if self.remote_server_url is not None:
                    # post the data
                    self.post_data(data)
                # log the generation
### FIX ME - revert to logdbg2
                loginf("rtgdthread",
                       "gauge-data.txt (%s) generated in %.5f seconds" % (cached_packet['dateTime'],
                                                                          (self.last_write-t1)))
            except Exception, e:
                weeutil.weeutil.log_traceback('rtgdthread: **** ')
        else:
            # we skipped this packet so log it
            logdbg2("rtgdthread", "packet (%s) skipped" % _conv_packet['dateTime'])

    def process_stats(self, package):
        """Process a stats package.

        Input:
            package: dict containing the stats data to process
        """

        if package is not None:
            for key, value in package.iteritems():
                setattr(self, key, value)

    def post_data(self, data):
        """Post data to a remote URL via HTTP POST.

        This code is modelled on the weeWX restFUL API, but rather then
        retrying a failed post the failure is logged and then ignored. If
        remote posts are not working then the user should set debug=1 and
        restart weeWX to see what the log says.

        The data to be posted is sent as a JSON string.

        Inputs:
            data: dict to sent as JSON string
        """

        # get a Request object
        req = urllib2.Request(self.remote_server_url)
        # set our content type to json
        req.add_header('Content-Type', 'application/json')
        # POST the data but wrap in a try..except so we can trap any errors
        try:
            response = self.post_request(req, json.dumps(data,
                                                         separators=(',', ':'),
                                                         sort_keys=True))
            if 200 <= response.code <= 299:
                # No exception thrown and we got a good response code, but did
                # we get self.response back in a return message? Check for
                # self.response, if its there then we can return. If it's
                # not there then log it and return.
                if self.response is not None and self.response not in response:
                    # didn't get 'success' so log it and continue
                    logdbg("rtgdthread",
                           "Failed to post data: Unexpected response")
                return
            # we received a bad response code, log it and continue
            logdbg("rtgdthread",
                   "Failed to post data: Code %s" % response.code())
        except (urllib2.URLError, socket.error,
                httplib.BadStatusLine, httplib.IncompleteRead), e:
            # an exception was thrown, log it and continue
            logdbg("rtgdthread", "Failed to post data: %s" % e)

    def post_request(self, request, payload):
        """Post a Request object.

        Inputs:
            request: urllib2 Request object
            payload: the data to sent

        Returns:
            The urllib2.urlopen() response
        """

        try:
            # Python 2.5 and earlier do not have a "timeout" parameter.
            # Including one could cause a TypeError exception. Be prepared
            # to catch it.
            _response = urllib2.urlopen(request,
                                        data=payload,
                                        timeout=self.timeout)
        except TypeError:
            # Must be Python 2.5 or early. Use a simple, unadorned request
            _response = urllib2.urlopen(request, data=payload)
        return _response

    def write_data(self, data):
        """Write the gauge-data.txt file.

        Takes dictionary of data elements, converts them to JSON format and
        writes them to file. JSON output is sorted by key and any non-critical
        whitespace removed before being written to file. Destination directory
        is created if it does not exist.

        Inputs:
            data: dictionary of gauge-data.txt data elements
        """

        # make the destination directory, wrapping it in a try block to catch
        # any errors
        try:
            os.makedirs(self.rtgd_path)
        except OSError as error:
            # raise if the error is anything other than the dir already exists
            if error.errno != errno.EEXIST:
                raise
        # now write to file
        with open(self.rtgd_path_file, 'w') as f:
            json.dump(data, f, separators=(',', ':'), sort_keys=True)

    def get_scroller_text(self):
        """Obtain the text string to be used in the scroller.

        Scroller text may come from any one of four sources, each is checked in
        the following order and the first non-zero length string result found
        is used:
        - string in weewx.conf [RealtimeGaugeData]
        - string in a text file
        - WU API forecast text
        - Zambretti forecast

        If nothing is found then a zero length string is returned.
        """

        # first look for a string in weewx.conf
        if self.scroller_text is not None:
            _scroller = self.scroller_text
        # if nothing then look for a file
        elif self.scroller_file is not None:
            with open(self.scroller_file, 'r') as f:
                _scroller = f.readline().strip()
        # if nothing look for a WU forecast
        elif self.forecast_text is not None:
            _scroller = self.forecast_text
        # if nothing look for a Zambretti forecast
        elif self.forecast.is_installed():
            _scroller = self.forecast.get_zambretti_text()
        # finally there is nothing so return a 0 length string
        else:
            _scroller = ''
        return _scroller

    def calculate(self, packet):
        """Construct a data dict for gauge-data.txt.

        Input:
            packet: loop data packet

        Returns:
            Dictionary of gauge-data.txt data elements.
        """

        ts = packet['dateTime']
        if self.packet_units is None or self.packet_units != packet['usUnits']:
            self.packet_units = packet['usUnits']
            (self.p_temp_type, self.p_temp_group) = getStandardUnitType(self.packet_units,
                                                                        'outTemp')
            (self.p_wind_type, self.p_wind_group) = getStandardUnitType(self.packet_units,
                                                                        'windSpeed')
            (self.p_baro_type, self.p_baro_group) = getStandardUnitType(self.packet_units,
                                                                        'barometer')
            (self.p_rain_type, self.p_rain_group) = getStandardUnitType(self.packet_units,
                                                                        'rain')
            (self.p_rainr_type, self.p_rainr_group) = getStandardUnitType(self.packet_units,
                                                                          'rainRate')
            (self.p_alt_type, self.p_alt_group) = getStandardUnitType(self.packet_units,
                                                                      'altitude')
        data = {}
        # timeUTC - UTC date/time in format YYYY,mm,dd,HH,MM,SS
        data['timeUTC'] = datetime.datetime.utcfromtimestamp(ts).strftime("%Y,%m,%d,%H,%M,%S")
        # date - date in (default) format Y.m.d HH:MM
        data['date'] = time.strftime(self.date_format, time.localtime(ts))
        # dateFormat - date format
        data['dateFormat'] = self.date_format.replace('%','')
        # SensorContactLost - 1 if the station has lost contact with its remote
        # sensors "Fine Offset only" 0 if contact has been established
        data['SensorContactLost'] = self.flag_format % self.lost_contact_flag
        # tempunit - temperature units - C, F
        data['tempunit'] = UNITS_TEMP[self.temp_group]
        # windunit -wind units - m/s, mph, km/h, kts
        data['windunit'] = UNITS_WIND[self.wind_group]
        # pressunit - pressure units - mb, hPa, in
        data['pressunit'] = UNITS_PRES[self.pres_group]
        # rainunit - rain units - mm, in
        data['rainunit'] = UNITS_RAIN[self.rain_group]
        # cloudbaseunit - cloud base units - m, ft
        data['cloudbaseunit'] = UNITS_CLOUD[self.alt_group]
        # temp - outside temperature
        temp_vt = ValueTuple(packet['outTemp'],
                             self.p_temp_type,
                             self.p_temp_group)
        temp = convert(temp_vt, self.temp_group).value
        temp = temp if temp is not None else convert(ValueTuple(0.0, 'degree_C', 'group_temperature'),
                                                     self.temp_group).value
        data['temp'] = self.temp_format % temp
        # tempTL - today's low temperature
        tempTL_vt = ValueTuple(self.buffer['outTemp'].min,
                               self.p_temp_type,
                               self.p_temp_group)
        tempTL = convert(tempTL_vt, self.temp_group).value
        tempTL = tempTL if tempTL is not None else temp
        data['tempTL'] = self.temp_format % tempTL
        # tempTH - today's high temperature
        tempTH_vt = ValueTuple(self.buffer['outTemp'].max,
                               self.p_temp_type,
                               self.p_temp_group)
        tempTH = convert(tempTH_vt, self.temp_group).value
        tempTH = tempTH if tempTH is not None else temp
        data['tempTH'] = self.temp_format % tempTH
        # TtempTL - time of today's low temp (hh:mm)
        TtempTL = time.localtime(self.buffer['outTemp'].mintime)
        data['TtempTL'] = time.strftime(self.time_format, TtempTL)
        # TtempTH - time of today's high temp (hh:mm)
        TtempTH = time.localtime(self.buffer['outTemp'].maxtime)
        data['TtempTH'] = time.strftime(self.time_format, TtempTH)
        # temptrend - temperature trend value
        _temp_trend_val = calc_trend('outTemp', temp_vt, self.temp_group,
                                     self.db_manager, ts - 3600, 300)
        temp_trend = _temp_trend_val if _temp_trend_val is not None else 0.0
        data['temptrend'] = self.temp_format % temp_trend
        # intemp - inside temperature
        intemp_vt = ValueTuple(packet['inTemp'],
                               self.p_temp_type,
                               self.p_temp_group)
        intemp = convert(intemp_vt, self.temp_group).value
        intemp = intemp if intemp is not None else convert(ValueTuple(0.0, 'degree_C', 'group_temperature'),
                                                           self.temp_group).value
        data['intemp'] = self.temp_format % intemp
        # hum - relative humidity
        hum = packet['outHumidity'] if packet['outHumidity'] is not None else 0.0
        data['hum'] = self.hum_format % hum
        # humTL - today's low relative humidity
        humTL = self.buffer['outHumidity'].min
        humTL = humTL if humTL is not None else hum
        data['humTL'] = self.hum_format % humTL
        # humTH - today's high relative humidity
        humTH = self.buffer['outHumidity'].max
        humTH = humTH if humTH is not None else hum
        data['humTH'] = self.hum_format % humTH
        # ThumTL - time of today's low relative humidity (hh:mm)
        ThumTL = time.localtime(self.buffer['outHumidity'].mintime)
        data['ThumTL'] = time.strftime(self.time_format, ThumTL)
        # ThumTH - time of today's high relative humidity (hh:mm)
        ThumTH = time.localtime(self.buffer['outHumidity'].maxtime)
        data['ThumTH'] = time.strftime(self.time_format, ThumTH)
        # inhum - inside humidity
        if 'inHumidity' not in packet:
            data['inhum'] = self.hum_format % 0.0
        else:
            inhum = packet['inHumidity'] if packet['inHumidity'] is not None else 0.0
            data['inhum'] = self.hum_format % inhum
        # dew - dew point
        dew_vt = ValueTuple(packet['dewpoint'],
                            self.p_temp_type,
                            self.p_temp_group)
        dew = convert(dew_vt, self.temp_group).value
        dew = dew if dew is not None else convert(ValueTuple(0.0, 'degree_C', 'group_temperature'),
                                                  self.temp_group).value
        data['dew'] = self.temp_format % dew
        # dewpointTL - today's low dew point
        dewpointTL_vt = ValueTuple(self.buffer['dewpoint'].min,
                                   self.p_temp_type,
                                   self.p_temp_group)
        dewpointTL = convert(dewpointTL_vt, self.temp_group).value
        dewpointTL = dewpointTL if dewpointTL is not None else dew
        data['dewpointTL'] = self.temp_format % dewpointTL
        # dewpointTH - today's high dew point
        dewpointTH_vt = ValueTuple(self.buffer['dewpoint'].max,
                                   self.p_temp_type,
                                   self.p_temp_group)
        dewpointTH = convert(dewpointTH_vt, self.temp_group).value
        dewpointTH = dewpointTH if dewpointTH is not None else dew
        data['dewpointTH'] = self.temp_format % dewpointTH
        # TdewpointTL - time of today's low dew point (hh:mm)
        TdewpointTL = time.localtime(self.buffer['dewpoint'].mintime)
        data['TdewpointTL'] = time.strftime(self.time_format, TdewpointTL)
        # TdewpointTH - time of today's high dew point (hh:mm)
        TdewpointTH = time.localtime(self.buffer['dewpoint'].maxtime)
        data['TdewpointTH'] = time.strftime(self.time_format, TdewpointTH)
        # wchill - wind chill
        wchill_vt = ValueTuple(packet['windchill'],
                               self.p_temp_type,
                               self.p_temp_group)
        wchill = convert(wchill_vt, self.temp_group).value
        wchill = wchill if wchill is not None else convert(ValueTuple(0.0, 'degree_C', 'group_temperature'),
                                                           self.temp_group).value
        data['wchill'] = self.temp_format % wchill
        # wchillTL - today's low wind chill
        wchillTL_vt = ValueTuple(self.buffer['windchill'].min,
                                 self.p_temp_type,
                                 self.p_temp_group)
        wchillTL = convert(wchillTL_vt, self.temp_group).value
        wchillTL = wchillTL if wchillTL is not None else wchill
        data['wchillTL'] = self.temp_format % wchillTL
        # TwchillTL - time of today's low wind chill (hh:mm)
        TwchillTL = time.localtime(self.buffer['windchill'].mintime)
        data['TwchillTL'] = time.strftime(self.time_format, TwchillTL)
        # heatindex - heat index
        heatindex_vt = ValueTuple(packet['heatindex'],
                                  self.p_temp_type,
                                  self.p_temp_group)
        heatindex = convert(heatindex_vt, self.temp_group).value
        heatindex = heatindex if heatindex is not None else convert(ValueTuple(0.0, 'degree_C', 'group_temperature'),
                                                                    self.temp_group).value
        data['heatindex'] = self.temp_format % heatindex
        # heatindexTH - today's high heat index
        heatindexTH_vt = ValueTuple(self.buffer['heatindex'].max,
                                    self.p_temp_type,
                                    self.p_temp_group)
        heatindexTH = convert(heatindexTH_vt, self.temp_group).value
        heatindexTH = heatindexTH if heatindexTH is not None else heatindex
        data['heatindexTH'] = self.temp_format % heatindexTH
        # TheatindexTH - time of today's high heat index (hh:mm)
        TheatindexTH = time.localtime(self.buffer['heatindex'].maxtime)
        data['TheatindexTH'] = time.strftime(self.time_format, TheatindexTH)
        # apptemp - apparent temperature
        if 'appTemp' in packet:
            # appTemp has been calculated for us so use it
            apptemp_vt = ValueTuple(packet['appTemp'],
                                    self.p_temp_type,
                                    self.p_temp_group)
        else:
            # apptemp not available so calculate it
            # first get the arguments for the calculation, if any of our
            # pre-reqs are missing or None the calculated app temp will be None
            temp_C = convert(temp_vt, 'degree_C').value
            windspeed_vt = ValueTuple(packet.get('windSpeed', None),
                                      self.p_wind_type,
                                      self.p_wind_group)
            windspeed_ms = convert(windspeed_vt, 'meter_per_second').value
            # now calculate it
            apptemp_C = weewx.wxformulas.apptempC(temp_C,
                                                  packet.get('outHumidity', None),
                                                  windspeed_ms)
            apptemp_vt = ValueTuple(apptemp_C, 'degree_C', 'group_temperature')

        apptemp = convert(apptemp_vt, self.temp_group).value
        apptemp = apptemp if apptemp is not None else convert(ValueTuple(0.0, 'degree_C', 'group_temperature'),
                                                              self.temp_group).value
        data['apptemp'] = self.temp_format % apptemp
        # apptempTL - today's low apparent temperature
        # apptempTH - today's high apparent temperature
        # TapptempTL - time of today's low apparent temperature (hh:mm)
        # TapptempTH - time of today's high apparent temperature (hh:mm)
        if 'appTemp' in self.buffer:
            # we have day stats for appTemp
            apptempTL_vt = ValueTuple(self.buffer['appTemp'].min,
                                      self.p_temp_type,
                                      self.p_temp_group)
            apptempTL = convert(apptempTL_vt, self.temp_group).value
            apptempTH_vt = ValueTuple(self.buffer['appTemp'].max,
                                      self.p_temp_type,
                                      self.p_temp_group)
            apptempTH = convert(apptempTH_vt, self.temp_group).value
            apptempTH = apptempTH if apptempTH is not None else convert(ValueTuple(0.0, 'degree_C', 'group_temperature'),
                                                                        self.temp_group).value
            TapptempTL = time.localtime(self.buffer['appTemp'].mintime)
            TapptempTH = time.localtime(self.buffer['appTemp'].maxtime)
        else:
            # There are no appTemp day stats. Normally we would return None but
            # the SteelSeries Gauges do not like None/null. Return the current
            # appTemp value so as to not upset the gauge auto scaling. The day
            # apptemp range wedge will not show, and the mouse-over low/highs
            # will be wrong but it is the best we can do.
            apptempTL = apptemp
            apptempTH = apptemp
            TapptempTL = datetime.date.today().timetuple()
            TapptempTH = datetime.date.today().timetuple()
        apptempTL = apptempTL if apptempTL is not None else convert(ValueTuple(0.0, 'degree_C', 'group_temperature'),
                                                                    self.temp_group).value
        data['apptempTL'] = self.temp_format % apptempTL
        apptempTH = apptempTH if apptempTH is not None else convert(ValueTuple(0.0, 'degree_C', 'group_temperature'),
                                                                    self.temp_group).value
        data['apptempTH'] = self.temp_format % apptempTH
        data['TapptempTL'] = time.strftime(self.time_format, TapptempTL)
        data['TapptempTH'] = time.strftime(self.time_format, TapptempTH)
        # humidex - humidex
        if 'humidex' in packet:
            # humidex is in the packet so use it
            humidex_vt = ValueTuple(packet['humidex'],
                                    self.p_temp_type,
                                    self.p_temp_group)
            humidex = convert(humidex_vt, self.temp_group).value
        else:
            # humidex is not in the packet so calculate it
            temp_C = convert(temp_vt, 'degree_C').value
            dewpoint_C = convert(dew_vt, 'degree_C').value
            humidex_C = weewx.wxformulas.humidexC(temp_C,
                                                  packet.get('outHumidity', None))
            humidex_vt = ValueTuple(humidex_C, 'degree_C', 'group_temperature')
            humidex = convert(humidex_vt, self.temp_group).value
        humidex = humidex if humidex is not None else convert(ValueTuple(0.0, 'degree_C', 'group_temperature'),
                                                              self.temp_group).value
        data['humidex'] = self.temp_format % humidex
        # press - barometer
        press_vt = ValueTuple(packet['barometer'],
                              self.p_baro_type,
                              self.p_baro_group)
        press = convert(press_vt, self.pres_group).value
        press = press if press is not None else 0.0
        data['press'] = self.pres_format % press
        # pressTL - today's low barometer
        # pressTH - today's high barometer
        # TpressTL - time of today's low barometer (hh:mm)
        # TpressTH - time of today's high barometer (hh:mm)
        if 'barometer' in self.buffer:
            pressTL_vt = ValueTuple(self.buffer['barometer'].min,
                                    self.p_baro_type,
                                    self.p_baro_group)
            pressTL = convert(pressTL_vt, self.pres_group).value
            pressTL = pressTL if pressTL is not None else press
            data['pressTL'] = self.pres_format % pressTL
            pressTH_vt = ValueTuple(self.buffer['barometer'].max,
                                    self.p_baro_type,
                                    self.p_baro_group)
            pressTH = convert(pressTH_vt, self.pres_group).value
            pressTH = pressTH if pressTH is not None else press
            data['pressTH'] = self.pres_format % pressTH
            TpressTL = time.localtime(self.buffer['barometer'].mintime)
            data['TpressTL'] = time.strftime(self.time_format, TpressTL)
            TpressTH = time.localtime(self.buffer['barometer'].maxtime)
            data['TpressTH'] = time.strftime(self.time_format, TpressTH)
        else:
            data['pressTL'] = self.pres_format % 0.0
            data['pressTH'] = self.pres_format % 0.0
            data['TpressTL'] = None
            data['TpressTH'] = None
        # pressL - all time low barometer
        if self.min_barometer is not None:
            pressL_vt = ValueTuple(self.min_barometer,
                                   self.p_baro_type,
                                   self.p_baro_group)
        else:
            pressL_vt = ValueTuple(850, 'hPa', self.p_baro_group)
        pressL = convert(pressL_vt, self.pres_group).value
        data['pressL'] = self.pres_format % pressL
        # pressH - all time high barometer
        if self.max_barometer is not None:
            pressH_vt = ValueTuple(self.max_barometer,
                                   self.p_baro_type,
                                   self.p_baro_group)
        else:
            pressH_vt = ValueTuple(1100, 'hPa', self.p_baro_group)
        pressH = convert(pressH_vt, self.pres_group).value
        data['pressH'] = self.pres_format % pressH
        # presstrendval -  pressure trend value
        _p_trend_val = calc_trend('barometer', press_vt, self.pres_group,
                                  self.db_manager, ts - 3600, 300)
        presstrendval = _p_trend_val if _p_trend_val is not None else 0.0
        data['presstrendval'] = self.pres_format % presstrendval
        # rfall - rain today
        rainDay = self.buffer['rain'].sum
        rainT_vt = ValueTuple(rainDay, self.p_rain_type, self.p_rain_group)
        rainT = convert(rainT_vt, self.rain_group).value
        rainT = rainT if rainT is not None else 0.0
        data['rfall'] = self.rain_format % rainT
        # rrate - current rain rate (per hour)
        if 'rainRate' in packet:
            rrate_vt = ValueTuple(packet['rainRate'],
                                  self.p_rainr_type,
                                  self.p_rainr_group)
            rrate = convert(rrate_vt, self.rainrate_group).value
            rrate = rrate if rrate is not None else 0.0
        else:
            rrate = 0.0
        data['rrate'] = self.rainrate_format % rrate
        # rrateTM - today's maximum rain rate (per hour)
        if 'rainRate' in self.buffer:
            rrateTM_vt = ValueTuple(self.buffer['rainRate'].max,
                                    self.p_rainr_type,
                                    self.p_rainr_group)
            rrateTM = convert(rrateTM_vt, self.rainrate_group).value
        else:
            rrateTM = 0
        rrateTM = rrateTM if rrateTM is not None else 0.0
        data['rrateTM'] = self.rainrate_format % rrateTM
        # TrrateTM - time of today's maximum rain rate (per hour)
        if 'rainRate' in self.buffer:
            TrrateTM = time.localtime(self.buffer['rainRate'].maxtime)
            data['TrrateTM'] = time.strftime(self.time_format, TrrateTM)
        else:
            data['TrrateTM'] = '00:00'
        # hourlyrainTH - Today's highest hourly rain
        # ###FIX ME - need to determine hourlyrainTH
        data['hourlyrainTH'] = "0.0"
        # ThourlyrainTH - time of Today's highest hourly rain
        # ###FIX ME - need to determine ThourlyrainTH
        data['ThourlyrainTH'] = "00:00"
        # LastRainTipISO -
        # ###FIX ME - need to determine LastRainTipISO
        data['LastRainTipISO'] = "00:00"
        # wlatest - latest wind speed reading
        wlatest_vt = ValueTuple(packet['windSpeed'],
                                self.p_wind_type,
                                self.p_wind_group)
        wlatest = convert(wlatest_vt, self.wind_group).value
        wlatest = wlatest if wlatest is not None else 0.0
        data['wlatest'] = self.wind_format % wlatest
        # wspeed - wind speed (average)
        wspeed = convert(self.windSpeedAvg_vt, self.wind_group).value
        wspeed = wspeed if wspeed is not None else 0.0
        data['wspeed'] = self.wind_format % wspeed
        # windTM - today's high wind speed (average)
        windTM_vt = ValueTuple(self.buffer['windSpeed'].max,
                               self.p_wind_type,
                               self.p_wind_group)
        windTM = convert(windTM_vt, self.wind_group).value
        windTM = windTM if windTM is not None else 0.0
        data['windTM'] = self.wind_format % windTM
### VERIFY ME
        # wgust - 10 minute high gust
        if 'windGust' in self.buffer:
            wgust = self.buffer['windGust'].history_max(ts).value
        elif 'windSpeed' in self.buffer:
            wgust = self.buffer['windSpeed'].history_max(ts).value
        else:
            wgust = None
        wgust_vt = ValueTuple(wgust, self.p_wind_type, self.p_wind_group)
        wgust = convert(wgust_vt, self.wind_group).value
        wgust = wgust if wgust is not None else 0.0
        data['wgust'] = self.wind_format % wgust
        # wgustTM - today's high wind gust
        wgustTM_vt = ValueTuple(self.buffer['wind'].max,
                                self.p_wind_type,
                                self.p_wind_group)
        wgustTM = convert(wgustTM_vt, self.wind_group).value
        wgustTM = wgustTM if wgustTM is not None else 0.0
        data['wgustTM'] = self.wind_format % wgustTM
        # TwgustTM - time of today's high wind gust (hh:mm)
        TwgustTM = time.localtime(self.buffer['wind'].maxtime)
        data['TwgustTM'] = time.strftime(self.time_format, TwgustTM)



        # bearing - wind bearing (degrees)
        bearing = packet['windDir']
        bearing = bearing if bearing is not None else self.last_dir
        # save this bearing to use next time if there is no windDir, this way
        # our wind dir needle will always hsow the last non-None windDir rather
        # than return to 0
        self.last_dir = bearing
        data['bearing'] = self.dir_format % bearing
        # avgbearing - 10-minute average wind bearing (degrees)
        avg_bearing = self.windDirAvg
        avg_bearing = avg_bearing if avg_bearing is not None else self.last_average_dir
        # save this bearing to use next time if there is no average wind dir,
        # this way our avg dir needle will always show the last non-None avg
        # wind dir rather than return to 0
        self.last_average_dir = avg_bearing
        data['avgbearing'] = self.dir_format % avg_bearing
        # bearingTM - The wind bearing at the time of today's high gust
        # As our self.buffer is really a weeWX accumulator filled with the
        # relevant days stats we need to use .max_dir rather than .gustdir
        # to get the gust direction for the day.
        bearingTM = self.buffer['wind'].max_dir
        bearingTM = bearingTM if bearingTM is not None else 0
        data['bearingTM'] = self.dir_format % bearingTM
### FIX ME
#        # BearingRangeFrom10 - The 'lowest' bearing in the last 10 minutes
#        # (or as configured using AvgBearingMinutes in cumulus.ini), rounded
#        # down to nearest 10 degrees
#        if self.windDirAvg is not None:
#            try:
#                fromBearing = max((self.windDirAvg-d) if ((d-self.windDirAvg) < 0 < s) else None for x, y, s, d, t in self.buffer.wind_dir_list)
#            except (TypeError, ValueError):
#                fromBearing = None
#            BearingRangeFrom10 = self.windDirAvg - fromBearing if fromBearing is not None else 0.0
#            if BearingRangeFrom10 < 0:
#                BearingRangeFrom10 += 360
#            elif BearingRangeFrom10 > 360:
#                BearingRangeFrom10 -= 360
#        else:
#            BearingRangeFrom10 = 0.0
#        data['BearingRangeFrom10'] = self.dir_format % BearingRangeFrom10
### FIX ME
#        # BearingRangeTo10 - The 'highest' bearing in the last 10 minutes
#        # (or as configured using AvgBearingMinutes in cumulus.ini), rounded
#        # up to the nearest 10 degrees
#        if self.windDirAvg is not None:
#            try:
#                toBearing = max((d-self.windDirAvg) if ((d-self.windDirAvg) > 0 and s > 0) else None for x, y, s, d, t in self.buffer.wind_dir_list)
#            except (TypeError, ValueError):
#                toBearing = None
#            BearingRangeTo10 = self.windDirAvg + toBearing if toBearing is not None else 0.0
#            if BearingRangeTo10 < 0:
#                BearingRangeTo10 += 360
#            elif BearingRangeTo10 > 360:
#                BearingRangeTo10 -= 360
#        else:
#            BearingRangeTo10 = 0.0
#        data['BearingRangeTo10'] = self.dir_format % BearingRangeTo10
        # domwinddir - Today's dominant wind direction as compass point
        deg = 90.0 - math.degrees(math.atan2(self.buffer['wind'].ysum,
                                  self.buffer['wind'].xsum))
        dom_dir = deg if deg >= 0 else deg + 360.0
        data['domwinddir'] = degreeToCompass(dom_dir)
        # WindRoseData -
        data['WindRoseData'] = self.rose
### FIX ME
#        # windrun - wind run (today)
#        last_ts = self.db_manager.lastGoodStamp()
#        try:
#            wind_sum_vt = ValueTuple(self.buffer['wind'].sum,
#                                     self.p_wind_type,
#                                     self.p_wind_group)
#            windrun_day_average = (last_ts - startOfDay(ts))/3600.0 * convert(wind_sum_vt,
#                                                                              self.wind_group).value/self.buffer['wind'].count
#        except (ValueError, TypeError, ZeroDivisionError):
#            windrun_day_average = 0.0
#        if self.windrun_loop:   # is loop/realtime estimate
#            loop_hours = (ts - last_ts)/3600.0
#            try:
#                windrun = windrun_day_average + loop_hours * convert((self.buffer.windsum,
#                                                                      self.p_wind_type,
#                                                                      self.p_wind_group),
#                                                                     self.wind_group).value/self.buffer.windcount
#            except (ValueError, TypeError):
#                windrun = windrun_day_average
#        else:
#            windrun = windrun_day_average
#        data['windrun'] = self.dist_format % windrun
        # Tbeaufort - wind speed (Beaufort)
        if packet['windSpeed'] is not None:
            data['Tbeaufort'] = str(weewx.wxformulas.beaufort(convert(wlatest_vt,
                                                                      'knot').value))
        else:
            data['Tbeaufort'] = "0"
        # UV - UV index
        if 'UV' not in packet:
            UV = 0.0
        else:
            UV = packet['UV'] if packet['UV'] is not None else 0.0
        data['UV'] = self.uv_format % UV
        # UVTH - today's high UV index
        if 'UV' not in self.buffer:
            UVTH = UV
        else:
            UVTH = self.buffer['UV'].max
        UVTH = UVTH if UVTH is not None else 0.0
        data['UVTH'] = self.uv_format % UVTH
        # SolarRad - solar radiation W/m2
        if 'radiation' not in packet:
            SolarRad = 0.0
        else:
            SolarRad = packet['radiation']
        SolarRad = SolarRad if SolarRad is not None else 0.0
        data['SolarRad'] = self.rad_format % SolarRad
        # SolarTM - today's maximum solar radiation W/m2
        if 'radiation' not in self.buffer:
            SolarTM = 0.0
        else:
            SolarTM = self.buffer['radiation'].max
        SolarTM = SolarTM if SolarTM is not None else 0.0
        data['SolarTM'] = self.rad_format % SolarTM
        # CurrentSolarMax - Current theoretical maximum solar radiation
        if self.solar_algorithm == 'Bras':
            curr_solar_max = weewx.wxformulas.solar_rad_Bras(self.latitude,
                                                             self.longitude,
                                                             self.altitude_m,
                                                             ts,
                                                             self.nfac)
        else:
            curr_solar_max = weewx.wxformulas.solar_rad_RS(self.latitude,
                                                           self.longitude,
                                                           self.altitude_m,
                                                           ts,
                                                           self.atc)
        curr_solar_max = curr_solar_max if curr_solar_max is not None else 0.0
        data['CurrentSolarMax'] = self.rad_format % curr_solar_max
        if 'cloudbase' in packet:
            cb = packet['cloudbase']
            cb_vt = ValueTuple(cb, self.p_alt_type, self.p_alt_group)
        else:
            temp_C = convert(temp_vt, 'degree_C').value
            cb = weewx.wxformulas.cloudbase_Metric(temp_C,
                                                   packet['outHumidity'],
                                                   self.altitude_m)
            cb_vt = ValueTuple(cb, 'meter', self.p_alt_group)
        cloudbase = convert(cb_vt, self.alt_group).value
        cloudbase = cloudbase if cloudbase is not None else 0.0
        data['cloudbasevalue'] = self.alt_format % cloudbase
        # forecast - forecast text
        _text = self.get_scroller_text()
        data['forecast'] = time.strftime(_text, time.localtime(ts))
        # version - weather software version
        data['version'] = '%s' % weewx.__version__
        # build -
        data['build'] = ''
        # ver - gauge-data.txt version number
        data['ver'] = self.version
        return data

    def new_archive_record(self, record):
        """Control processing when new a archive record is presented."""

        # set our lost contact flag if applicable
        if self.station_type in ARCHIVE_STATIONS:
            self.lost_contact_flag = record[STATION_LOST_CONTACT[self.station_type]['field']] == STATION_LOST_CONTACT[self.station_type]['value']
        # save the windSpeed value to use as our archive period average
        if 'windSpeed' in record:
            self.windSpeedAvg_vt = weewx.units.as_value_tuple(record, 'windSpeed')
        else:
            self.windSpeedAvg_vt = ValueTuple(None, 'km_per_hour', 'group_speed')
        # save the windDir value to use as our archive period average
        if 'windDir' in record:
            self.windDirAvg = record['windDir']
        else:
            self.windDirAvg = None
        # refresh our day (archive record based) stats to date in case we have
        # jumped to the next day
        self.day_stats = self.db_manager._get_day_summary(record['dateTime'])
        self.apptemp_day_stats = self.apptemp_manager._get_day_summary(record['dateTime'])

#    def end_archive_period(self):
#        """Control processing at the end of each archive period."""
#
#        # Reset our loop stats.
#        self.buffer.reset_loop_stats()
#
    def parse_field_map(self, rtgd_config_dict):
        """Parse the field map."""

        _field_map = rtgd_config_dict.get("FieldMap", None)


# ============================================================================
#                           class ObsBuffer
# ============================================================================


class ObsBuffer(object):
    """Base class to buffer an obs."""

    def __init__(self, stats, units=None, history=False):
        self.units = units
        self.last = None
        self.lasttime = None
        if history:
            self.use_history = True
            self.history_full = False
            self.history = []
        else:
            self.use_history = False

    def add_value(self, val, ts, hilo=True):
        """Add a value to my hilo and history stats as required."""

        pass

    def day_reset(self):
        """Reset the vector obs buffer."""

        pass

    def trim_history(self, ts):
        """Trim any old data from the history list."""

        # calc ts of oldest sample we want to retain
        oldest_ts = ts - MAX_AGE
        # set history_full
        self.history_full = min([a.ts for a in self.history if a.ts is not None]) <= oldest_ts
        # remove any values older than oldest_ts
        self.history = [s for s in self.history if s.ts > oldest_ts]

    def history_max(self, ts, age=MAX_AGE):
        """Return the max value in my history.

        Search the last age seconds of my history for the max value and the
        corresponding timestamp.

        Inputs:
            ts:  the timestamp to start searching back from
            age: the max age of the records being searched

        Returns:
            An object of type ObsTuple where value is a 3 way tuple of
            (value, x component, y component) and ts is the timestamp when
            it occurred.
        """

        born = ts - age
        snapshot = [a for a in self.history if a.ts >= born]
        if len(snapshot) > 0:
            _max = max(snapshot, key=itemgetter(1))
            return ObsTuple(_max[0], _max[1])
        else:
            return None

    def history_avg(self, ts, age=MAX_AGE):
        """Return the average value in my history.

        Search the last age seconds of my history for the max value and the
        corresponding timestamp.

        Inputs:
            ts:  the timestamp to start searching back from
            age: the max age of the records being searched

        Returns:
            An object of type ObsTuple where value is a 3 way tuple of
            (value, x component, y component) and ts is the timestamp when
            it occurred.
        """

        born = ts - age
        snapshot = [a.value[0] for a in self.history if a.ts >= born]
        if len(snapshot) > 0:
            return float(sum(snapshot)/len(snapshot))
        else:
            return None


# ============================================================================
#                             class VectorBuffer
# ============================================================================


class VectorBuffer(ObsBuffer):
    """Class to buffer vector obs."""

    default_init = (None, None, None, None, None)

    def __init__(self, stats, units=None, history=False):
        # initialize my superclass
        super(VectorBuffer, self).__init__(stats, units=units, history=history)

        if stats:
            self.min = stats.min
            self.mintime = stats.mintime
            self.max = stats.max
            self.max_dir = stats.max_dir
            self.maxtime = stats.maxtime
            self.sum = stats.sum
            self.xsum = stats.xsum
            self.ysum = stats.ysum
            self.sumtime = stats.sumtime
        else:
            (self.min, self.mintime,
             self.max, self.max_dir, self.maxtime) = VectorBuffer.default_init
            self.sum = 0.0
            self.xsum = 0.0
            self.ysum = 0.0
            self.sumtime = 0.0

    def add_value(self, val, ts, hilo=True):
        """Add a value to my hilo and history stats as required."""

        (w_speed, w_dir) = val
        if w_speed is not None:
            if hilo:
                if self.min is None or w_speed < self.min:
                    self.min = w_speed
                    self.mintime = ts
                if self.max is None or w_speed > self.max:
                    self.max = w_speed
                    self.max_dir = w_dir
                    self.maxtime = ts
            self.sum += w_speed
            if self.lasttime:
                self.sumtime += ts - self.lasttime
            if w_dir is not None:
                self.xsum += w_speed * math.cos(math.radians(90.0 - w_dir))
                self.ysum += w_speed * math.sin(math.radians(90.0 - w_dir))
            if self.lasttime is None or ts >= self.lasttime:
                self.last = (w_speed, w_dir)
                self.lasttime = ts
            if self.use_history and w_dir is not None:
                self.history.append(ObsTuple((w_speed,
                                              math.cos(math.radians(90.0 - w_dir)),
                                              math.sin(math.radians(90.0 - w_dir))), ts))
                self.trim_history(ts)

    def day_reset(self):
        """Reset the vector obs buffer."""

        (self.min, self.mintime,
         self.max, self.max_dir, self.maxtime) = VectorBuffer.default_init
        try:
            self.sum = 0.0
        except AttributeError:
            pass

    @property
    def vec_avg(self):
        """The day vector average value."""

        return math.sqrt((self.xsum**2 + self.ysum**2) / self.sumtime**2)

    @property
    def vec_dir(self):
        """The day vector average direction."""

        _dir = 90.0 - math.degrees(math.atan2(self.ysum, self.xsum))
        if _dir < 0.0:
            _dir += 360.0
        return _dir


# ============================================================================
#                             class ScalarBuffer
# ============================================================================


class ScalarBuffer(ObsBuffer):
    """Class to buffer scalar obs."""

    default_init = (None, None, None, None, 0.0)

    def __init__(self, stats, units=None, history=False):
        # initialize my superclass
        super(ScalarBuffer, self).__init__(stats, units=units, history=history)

        if stats:
            self.min = stats.min
            self.mintime = stats.mintime
            self.max = stats.max
            self.maxtime = stats.maxtime
            self.sum = stats.sum
        else:
            (self.min, self.mintime,
             self.max, self.maxtime, self.sum) = ScalarBuffer.default_init

    def add_value(self, val, ts):
        """Add a value to my stats as required."""

        if val is not None:
            if self.lasttime is None or ts >= self.lasttime:
                self.last = val
                self.lasttime = ts
            if self.min is None or val < self.min:
                self.min = val
                self.mintime = ts
            if self.max is None or val > self.max:
                self.max = val
                self.maxtime = ts
            self.sum += val
            if self.use_history:
                self.history.append(ObsTuple(val, ts))
                self.trim_history(ts)

    def day_reset(self):
        """Reset the scalar obs buffer."""

        (self.min, self.mintime,
         self.max, self.maxtime) = ScalarBuffer.default_init
        try:
            self.sum = 0.0
        except AttributeError:
            pass


# ============================================================================
#                               class Buffer
# ============================================================================


class Buffer(dict):
    """Class to buffer various loop packet obs.

    If archive based stats are an efficient means of getting stats for today.
    However, their use would mean that any daily stat (eg today's max outTemp)
    that 'occurs' after the most recent archive record but before the next
    archive record is written to archive will not be captured. For this reason
    selected loop data is buffered to ensure that such stats are correctly
    reflected.
    """



    def __init__(self, manifest, day_stats, additional_day_stats):
        """Initialise an instance of our class."""

        self.manifest = manifest
        # seed our buffer objects from day_stats
        for obs in [f for f in day_stats if f in self.manifest]:
            seed_func = seed_functions.get(obs, Buffer.seed_scalar)
            seed_func(self, day_stats, obs, history=obs in HIST_MANIFEST)
        # seed our buffer objects from additional_day_stats
        if additional_day_stats:
            for obs in [f for f in additional_day_stats if f in self.manifest]:
                if obs not in self:
                    seed_func = seed_functions.get(obs, Buffer.seed_scalar)
                    seed_func(self, additional_day_stats, obs,
                              history=obs in HIST_MANIFEST)
        self.primary_unit_system = day_stats.unit_system
        self.last_windSpeed_ts = None
        self.windrun = self.seed_windrun(day_stats)

    def seed_scalar(self, stats, obs_type, history):
        """Seed a scalar buffer."""

        self[obs_type] = init_dict.get(obs_type, ScalarBuffer)(stats=stats[obs_type],
                                                               units=stats.unit_system,
                                                               history=history)

    def seed_vector(self, stats, obs_type, history):
        """Seed a vector buffer."""

        self[obs_type] = init_dict.get(obs_type, VectorBuffer)(stats=stats[obs_type],
                                                               units=stats.unit_system,
                                                               history=history)

    def seed_windrun(self, day_stats):
        """Seed day windrun."""

        if 'windSpeed' in day_stats:
            # The wsum field hold the sum of (windSpeed * interval in seconds)
            # for today so we can calculate windrun from wsum - just need to
            # do a little unit conversion and scaling

            # The day_stats units may be different to our buffer unit system so
            # first convert the wsum value to a km_per_hour based value (the
            # wsum 'units' are a distance but we can use the group_speed
            # conversion to convert to a km_per_hour based value)
            # first get the day_stats windSpeed unit and unit group
            (unit, group) = weewx.units.getStandardUnitType(day_stats.unit_system,
                                                            'windSpeed')
            # now express wsum as a 'group_speed' ValueTuple
            _wr_vt = ValueTuple(day_stats['windSpeed'].wsum, unit, group)
            # convert it to a 'km_per_hour' based value
            _wr_km = convert(_wr_vt, 'km_per_hour').value
            # but _wr_km was based on wsum which was based on seconds not hours
            # so we need to divide by 3600 to get our real windrun in km
            windrun = _wr_km/3600.0
        else:
            windrun = 0.0
        return windrun

    def add_packet(self, packet):
        """Add a packet to the buffer."""

#        packet = weewx.units.to_std_system(packet, self.primary_unit_system)
        if packet['dateTime'] is not None:
            for obs in [f for f in packet if f in self.manifest]:
                add_func = add_functions.get(obs, Buffer.add_value)
                add_func(self, packet, obs)

    def add_value(self, packet, obs):
        """Add a value to the buffer."""

        # if we haven't seen this obs before add it to our buffer
        if obs not in self:
            self[obs] = init_dict.get(obs, ScalarBuffer)(stats=None,
                                                         units=packet['usUnits'],
                                                         history=obs in HIST_MANIFEST)
        if self[obs].units == packet['usUnits']:
            _value = packet[obs]
        else:
            (unit, group) = getStandardUnitType(packet['usUnits'], obs)
            _vt = ValueTuple(packet[obs], unit, group)
            _value = weewx.units.convertStd(_vt, self[obs].units).value
        self[obs].add_value(_value, packet['dateTime'])

    def add_wind_value(self, packet, obs):
        """Add a wind value to the buffer."""

        # first add it as 'windSpeed' the scalar
        self.add_value(packet, obs)

        # update today's windrun
        if 'windSpeed' in packet:
            try:
                self.windrun += packet['windSpeed'] * (packet['dateTime'] - self.last_windSpeed_ts)/1000.0
            except TypeError:
                pass
            self.last_windSpeed_ts = packet['dateTime']

        # now add it as the special vector 'wind'
        if 'wind' not in self:
            self['wind'] = VectorBuffer(stats=None, units=packet['usUnits'])
        if self['wind'].units == packet['usUnits']:
            _value = packet['windSpeed']
        else:
            (unit, group) = getStandardUnitType(packet['usUnits'], 'windSpeed')
            _vt = ValueTuple(packet['windSpeed'], unit, group)
            _value = weewx.units.convertStd(_vt, self['wind'].units).value
        self['wind'].add_value((_value, packet.get('windDir')),
                               packet['dateTime'])

    def start_of_day_reset(self):
        """Reset our buffer stats at the end of an archive period.

        Reset our hi/lo data but don't touch the history, it might need to be
        kept longer than the end of the archive period.
        """

        for obs in self.manifest:
            self[obs].day_reset()


# ============================================================================
#                            Configuration dictionaries
# ============================================================================

init_dict = ListOfDicts({'wind': VectorBuffer})
add_functions = ListOfDicts({'windSpeed': Buffer.add_wind_value})
seed_functions = ListOfDicts({'wind': Buffer.seed_vector})


# ============================================================================
#                              class ObsTuple
# ============================================================================


# A observation during some period can be represented by the value of the
# observation and the time at which it was observed. This can be represented
# in a 2 way tuple called an obs tuple. An obs tuple is useful because its
# contents can be accessed using named attributes.
#
# Item   attribute   Meaning
#    0    value      The observed value eg 19.5
#    1    ts         The epoch timestamp that the value was observed
#                    eg 1488245400
#
# It is valid to have an observed value of None.
#
# It is also valid to have a ts of None (meaning there is no information about
# the time the was was observed.

class ObsTuple(tuple):

    def __new__(cls, *args):
        return tuple.__new__(cls, args)

    @property
    def value(self):
        return self[0]

    @property
    def ts(self):
        return self[1]


# ============================================================================
#                            Class CachedPacket
# ============================================================================


class CachedPacket():
    """Class to cache loop packets.

    The purpose of the cache is to ensure that necessary fields for the
    generation of gauge-data.txt are continuously available on systems whose
    station emits partial packets. The key requirement is that the field
    exists, the value (numerical or None) is handled by method calculate().
    Method calculate() could be refactored to deal with missing fields, but
    this would either result in the gauges dials oscillating when a loop packet
    is missing an essential field, or overly complex code in method calculate()
    if field caching was to occur.

    The cache consists of a dictionary of value, timestamp pairs where
    timestamp is the timestamp of the packet when obs was last seen and value
    is the value of the obs at that time. None values may be cached.

    A cached loop packet may be obtained by calling the get_packet() method.
    """

    # These fields must be available in every loop packet read from the
    # cache.
    OBS = ["cloudbase", "windDir", "windrun", "inHumidity", "outHumidity",
           "barometer", "radiation", "rain", "rainRate", "windSpeed",
           "appTemp", "dewpoint", "heatindex", "humidex", "inTemp",
           "outTemp", "windchill", "UV"]

    def __init__(self, rec):
        """Initialise our cache object.

        The cache needs to be initialised to include all of the fields required
        by method calculate(). We could initialise all field values to None
        (method calculate() will interpret the None values to be '0' in most
        cases). The result on the gauge display may be misleading. We can get
        ballpark values for all fields by priming them with values from the
        last archive record. As the archive may have many more fields than rtgd
        requires, only prime those fields that rtgd requires.

        This approach does have the drawback that in situations where the
        archive unit system is different to the loop packet unit system the
        entire loop packet will be converted each time the cache is updated.
        This is inefficient.
        """

        self.cache = dict()
        # if we have a dateTime field in our record source use that otherwise
        # use the current system time
        _ts = rec['dateTime'] if 'dateTime' in rec else int(time.time() + 0.5)
        # only prime those fields in CachedPacket.OBS
        for _obs in CachedPacket.OBS:
            if _obs in rec and 'usUnits' in rec:
                # only add a value if it exists and we know what units its in
                self.cache[_obs] = {'value': rec[_obs], 'ts': _ts}
            else:
                # otherwise set it to None
                self.cache[_obs] = {'value': None, 'ts': _ts}
        # set the cache unit system if known
        self.unit_system = rec['usUnits'] if 'usUnits' in rec else None

    def update(self, packet, ts):
        """Update the cache from a loop packet.

        If the loop packet uses a different unit system to that of the cache
        then convert the loop packet before adding it to the cache. Update any
        previously seen cache fields and add any loop fields that have not been
        seen before.
        """

        if self.unit_system is None:
            self.unit_system = packet['usUnits']
        elif self.unit_system != packet['usUnits']:
            packet = weewx.units.to_std_system(packet, self.unit_system)
        for obs in [x for x in packet if x not in ['dateTime', 'usUnits']]:
            if packet[obs] is not None:
                self.cache[obs] = {'value': packet[obs], 'ts': ts}

    def get_value(self, obs, ts, max_age):
        """Get an obs value from the cache.

        Return a value for a given obs from the cache. If the value is older
        than max_age then None is returned.
        """

        if obs in self.cache and ts - self.cache[obs]['ts'] <= max_age:
            return self.cache[obs]['value']
        return None

    def get_packet(self, ts=None, max_age=600):
        """Get a loop packet from the cache.

        Resulting packet may contain None values.
        """

        if ts is None:
            ts = int(time.time() + 0.5)
        packet = {'dateTime': ts, 'usUnits': self.unit_system}
        for obs in self.cache:
            packet[obs] = self.get_value(obs, ts, max_age)
        return packet


# ============================================================================
#                            Utility Functions
# ============================================================================


def degreeToCompass(x):
    """Convert degrees to ordinal compass point.

    Input:
        x: degrees

    Returns:
        Corresponding ordinal compass point from COMPASS_POINTS. Can return
        None.
    """

    if x is None:
        return None
    idx = int((x + 11.25) / 22.5)
    return COMPASS_POINTS[idx]


def calc_trend(obs_type, now_vt, group, db_manager, then_ts, grace=0):
    """ Calculate change in an observation over a specified period.

    Inputs:
        obs_type:   database field name of observation concerned
        now_vt:     value of observation now (ie the finishing value)
        group:      group our returned value must be in
        db_manager: manager to be used
        then_ts:    timestamp of start of trend period
        grace:      the largest difference in time when finding the then_ts
                    record that is acceptable

    Returns:
        Change in value over trend period. Can be positive, 0, negative or
        None. Result will be in 'group' units.
    """

    if now_vt.value is None:
        return None
    then_record = db_manager.getRecord(then_ts, grace)
    if then_record is None:
        return None
    else:
        if obs_type not in then_record or then_record[obs_type] is None:
            return None
        else:
            then_vt = weewx.units.as_value_tuple(then_record, obs_type)
            now = convert(now_vt, group).value
            then = convert(then_vt, group).value
            return now - then


def calc_windrose(now, db_manager, period, points):
    """Calculate a SteelSeries Weather Gauges windrose array.

    Calculate an array representing the 'amount of wind' from each of the 8 or
    16 compass points. The value for each compass point is determined by
    summing the archive windSpeed values for wind from that compass point over
    the period concerned. Resulting values are rounded to one decimal point.

    Inputs:
        db_manager: A manager object for the database to be used.
        period:     Calculate the windrose using the last period (in
                    seconds) of data in the archive.
        points:     The number of compass points to use, normally 8 or 16.

    Return:
        List containing windrose data with 'points' elements.
    """

    # initialise our result
    rose = [0.0 for x in range(points)]
    # get the earliest ts we will use
    ts = now - period
    # determine the factor to be used to divide numerical windDir into
    # cardinal/ordinal compass points
    angle = 360.0/points
    # create an interpolation dict for our query
    inter_dict = {'table_name': db_manager.table_name,
                  'ts': ts,
                  'angle': angle}
    # the query to be used
    windrose_sql = "SELECT ROUND(windDir/%(angle)s),sum(windSpeed) "\
                   "FROM %(table_name)s WHERE dateTime>%(ts)s "\
                   "GROUP BY ROUND(windDir/%(angle)s)"

    # we expect at least 'points' rows in our result so use genSql
    for _row in db_manager.genSql(windrose_sql % inter_dict):
        # for windDir==None we expect some results with None, we can ignore
        # those
        if _row is None or None in _row:
            pass
        else:
            # Because of the structure of the compass and the limitations in
            # SQL maths our 'North' result will be returned in 2 parts. It will
            # be the sum of the '0' group and the 'points' group.
            if int(_row[0]) != int(points):
                rose[int(_row[0])] += _row[1]
            else:
                rose[0] += _row[1]
    # now  round our results and return
    return [round(x, 1) for x in rose]


# ============================================================================
#                              class WUThread
# ============================================================================


class WUThread(threading.Thread):
    """Thread that obtains WU API forecast data and places it in a queue.

    The WUThread class queries the WU API and places selected forecast data in
    JSON format in a queue used by the data consumer. The WU API is called at a
    user selectable frequency. The thread listens for a shutdown signal from
    its parent.

    WUThread constructor parameters:

        control_queue:  A Queue object used by our parent to control (shutdown)
                        this thread.
        result_queue:   A Queue object used to pass forecast data to the
                        destination
        config_dict:    A weeWX config dictionary.
        wu_config_dict: A config dictionary for the WUThread.
        lat:            Station latitude in decimal degrees.
        long:           Station longitude in decimal degrees.

    WUThread methods:

        run.               Control querying of the API and monitor the control
                           queue.
        query_wu.          Query the API and put selected forecast data in the
                           result queue.
        parse_wu_response. Parse a WU API response and return selected data.
    """

    def __init__(self, control_queue, result_queue, config_dict,
                 wu_config_dict, lat, long):

        # Initialize my superclass
        threading.Thread.__init__(self)

        # setup a few thread things
        self.setName('RtgdWuThread')
        self.setDaemon(True)

        # save the queues we will use
        self.control_queue = control_queue
        self.result_queue = result_queue

        # the WU API 'feature' to be used for the forecast data
        self.feature = 'forecast'
        # interval between API calls
        self.interval = to_int(wu_config_dict.get('interval', 1800))
        # max no of tries we will make in any one attempt to contact WU via API
        self.max_WU_tries = to_int(wu_config_dict.get('max_WU_tries', 3))
        # Get API call lockout period. This is the minimum period between API
        # calls for the same feature. This prevents an error condition making
        # multiple rapid API calls and thus breac the API usage conditions.
        self.lockout_period = to_int(wu_config_dict.get('api_lockout_period',
                                                        60))
        # initialise container for timestamp of last WU api call
        self.last_call_ts = None
        # Get our API key from weewx.conf, first look in [RealtimeGaugeData]
        # [[WU]] and if no luck try [Forecast] if it exists. Wrap in a
        # try..except loop to catch exceptions (ie one or both don't exist.
        try:
            if wu_config_dict.get('api_key') is not None:
                api_key = wu_config_dict.get('api_key')
            elif config_dict['Forecast']['WU'].get('api_key', None) is not None:
                api_key = config_dict['Forecast']['WU'].get('api_key')
            else:
                raise MissingApiKey("Cannot find valid Weather Underground API key")
        except:
            raise MissingApiKey("Cannot find Weather Underground API key")
        # Get 'query' (ie the location) to be used for use in WU API calls.
        # Refer weewx.conf for details.
        self.query = wu_config_dict.get('location', (lat, long))
        # get a WeatherUndergroundAPI object to handle the API calls
        self.api = WeatherUndergroundAPI(api_key)
        # get units to be used in forecast text
        self.units = wu_config_dict.get('units', 'METRIC').upper()

        # log what we will do
        loginf("engine",
               "RealTimeGaugeData will download forecast data from Weather Underground")

    def run(self):
        """Control the querying of the API and the shutdown of the thread.

        Run a continuous loop querying the API, queuing the resulting forecast
        data and checking for the shutdown signal. Since subsequent API queries
        are triggered by an elapsed period of time rather than an external
        event (eg recipt of archive record) it makes sense to sleep for a
        period before checking if it is time to query. However, this limits the
        responsiveness of the thread to the shutdown singal unless the sleep
        period is very short (seconds). An alternative is to use the blocking
        feature of Queue.get() to spend time blocking rather than sleeping. If
        the blocking period is greater than the API lockout period then we can
        avoid activating the API blockout period.
        """

        # since we are in a thread some additional try..except clauses will
        # help give additional output in case of an error rather than having
        # the thread die silently
        try:
            # Run a continuous loop, obtaining WU data as required and
            # monitoring the control queue for the shutdown signal. Only break
            # out if we receive the shutdown signal (None) from our parent.
            while True:
                # run an inner loop querying the API and checking for the
                # shutdown signal
                # first up query the API
                _response = self.query_wu()
                # if we have a non-None response then we have data from WU,
                # parse the response, gather the required data and put it in
                # the result queue
                if _response is not None:
                    # parse the WU response and extract the forecast text
                    _data = self.parse_wu_response(_response)
                    # if we have some data then place it in the result queue
                    if _data is not None:
                        # construct our data dict for the queue
                        _package = {'type': 'forecast',
                                    'payload': _data}
                        self.result_queue.put(_package)
                # now check to see if we have a shutdown signal
                try:
                    # Try to get data from the queue, block for up to 60
                    # seconds. If nothing is there an empty queue exception
                    # will be thrown after 60 seconds
                    _package = self.control_queue.get(block=True, timeout=60)
                except Queue.Empty:
                    # nothing in the queue so continue
                    pass
                else:
                    # somethign was in the queue, if it is the shutdown signal
                    # then return otherwise continue
                    if _package is None:
                        # we have a shutdown signal so return to exit
                        return
        except Exception, e:
            # Some unknown exception occurred. This is probably a serious
            # problem. Exit with some notification.
            logcrit("WUThread",
                    "Unexpected exception of type %s" % (type(e), ))
            weeutil.weeutil.log_traceback('WUThread: **** ')
            logcrit("WUThread", "Thread exiting. Reason: %s" % (e, ))

    def query_wu(self):
        """If required query the WU API and return the response.

        Checks to see if it is time to query the API, if so queries the API
        and returns the raw response in JSON format. To prevent the user
        exceeding their API call limit the query is only made if at least
        self.lockout_period seconds have elapsed since the last call.

        Inputs:
            None.

        Returns:
            The raw WU API response in JSON format.
        """

        # get the current time
        now = time.time()
        logdbg2("WUThread",
                "Last Weather Underground API call at %s" % self.last_call_ts)
        # has the lockout period passed since the last call
        if self.last_call_ts is None or ((now + 1 - self.lockout_period) >= self.last_call_ts):
            # If we haven't made an API call previously or if its been too long
            # since the last call then make the call
            if (self.last_call_ts is None) or ((now + 1 - self.interval) >= self.last_call_ts):
                # Make the call, wrap in a try..except just in case
                try:
                    _response = self.api.data_request(features=self.feature,
                                                      query=self.query,
                                                      resp_format='json',
                                                      max_tries=self.max_WU_tries)
                    logdbg("WUThread",
                           "Downloaded updated Weather Underground %s information" % self.feature)
                except Exception, e:
                    # Some unknown exception occurred. Log it and continue.
                    loginf("WUThread",
                           "Unexpected exception of type %s" % (type(e), ))
                    weeutil.weeutil.log_traceback('WUThread: **** ')
                    loginf("WUThread",
                           "Unexpected exception of type %s" % (type(e), ))
                    loginf("WUThread",
                           "Weather Underground '%s' API query failed" % self.feature)
                # if we got something back then reset our last call timestamp
                if _response is not None:
                    self.last_call_ts = now
                return _response
        else:
            # API call limiter kicked in so say so
            loginf("WUThread",
                   "Tried to make an API call within %d sec of the previous call." % (self.lockout_period, ))
            loginf("        ",
                   "API call limit reached. API call skipped.")
        return None

    def parse_wu_response(self, response):
        """ Validate/parse a WU response and return the required fields.

        Take a WU API response, check for (WU defined) errors then extract and
        return the forecast text and Metric forecast text fields for period 0.

        Input:
            response: A WU API response in JSON format.

        Returns:
            A dictionary containing the fields of interest from the WU API
            response.
        """

        # deserialize the response
        _response_json = json.loads(response)
        # check for recognised format
        if 'response' not in _response_json:
            loginf("WUThread",
                   "Unknown format in Weather Underground '%s'" % (self.feature, ))
            return None
        _response = _response_json['response']
        # check for WU provided error else start pulling in the data we want
        if 'error' in _response:
            loginf("WUThread",
                   "Error in Weather Underground '%s' response" % (self.feature, ))
            return None
        # we have forecast data so return the data we want
        _fcast = _response_json['forecast']['txt_forecast']['forecastday']
        # select which forecast we want
        if self.units == 'METRIC':
            return _fcast[0]['fcttext_metric']
        else:
            return _fcast[0]['fcttext']


# ============================================================================
#                        class WeatherUndergroundAPI
# ============================================================================


class WeatherUndergroundAPI(object):
    """Query the Weather Underground API and return the API response.

    The WU API is accessed by calling one or more features. These features can
    be grouped into two groups, WunderMap layers and data features. This class
    supports access to the API data features only.

    WeatherUndergroundAPI constructor parameters:

        api_key: WeatherUnderground API key to be used.

    WeatherUndergroundAPI methods:

        data_request. Submit a data feature request to the WeatherUnderground
                      API and return the response.
    """

    BASE_URL = 'http://api.wunderground.com/api'

    def __init__(self, api_key):
        # initialise a WeatherUndergroundAPI object

        # save the API key to be used
        self.api_key = api_key

    def data_request(self, features, query, settings=None,
                     resp_format='json', max_tries=3):
        """Make a data feature request via the API and return the results.

        Construct an API call URL, make the call and return the response.

        Parameters:
            features:    One or more WU API data features. String or list/tuple
                         of strings.
            query:       The location for which the information is sought.
                         Refer usage comments at start of this file. String.
            settings:    Optional settings to be included in the API call
                         eg lang:FR for French, pws:1 to use PWS for
                         conditions. String or list/tuple of strings. Default
                         is 'pws:1'
            resp_format: The output format of the data returned by the WU API.
                         String, either 'json' or 'xml' for JSON or XML
                         respectively. Default is JSON.
            max_tries:   The maximum number of attempts to be made to obtain a
                         response from the WU API. Default is 3.

        Returns:
            The WU API response in JSON or XML format.
        """

        # there may be multiple features so if features is a list create a
        # string delimiting the features with a solidus
        if features is not None and hasattr(features, '__iter__'):
            features_str = '/'.join(features)
        else:
            features_str = features

        # Are there any settings parameters? If so construct a query string
        if hasattr(settings, '__iter__'):
            # we have more than one setting
            settings_str = '/'.join(settings)
        elif settings is not None:
            # we have a single setting
            settings_str = settings
        else:
            # we have no setting, use the default pws:1 to make life easier
            # when assembling the URL to be used
            settings_str = 'pws:1'

        # construct the API call URL to be used
        partial_url = '/'.join([self.BASE_URL,
                                self.api_key,
                                features_str,
                                settings_str,
                                'q',
                                query])
        url = '.'.join([partial_url, resp_format])
        # if debug >=1 log the URL used but obfuscate the API key
        if weewx.debug >= 1:
            _obf_api_key = '*'*(len(self.api_key) - 4) + self.api_key[-4:]
            _obf = '/'.join([self.BASE_URL,
                             _obf_api_key,
                             features_str,
                             settings_str,
                             'q',
                             query])
            _obf_url = '.'.join([_obf, resp_format])
            logdbg("weatherundergroundapi",
                   "Submitting API call using URL: %s" % (_obf_url, ))
        # we will attempt the call max_tries times
        for count in range(max_tries):
            # attempt the call
            try:
                w = urllib2.urlopen(url)
                _response = w.read()
                w.close()
                return _response
            except (urllib2.URLError, socket.timeout), e:
                logerr("weatherundergroundapi",
                       "Failed to get '%s' on attempt %d" % (query, count+1))
                logerr("weatherundergroundapi", "   **** %s" % e)
        else:
            logerr("weatherundergroundapi",
                   "Failed to get Weather Underground '%s'" % (query, ))
        return None


# ============================================================================
#                          class ZambrettiForecast
# ============================================================================


class ZambrettiForecast(object):
    """Class to extract Zambretti forecast text.

    Requires the weeWX forecast extension to be installed and configured to
    provide the Zambretti forecast otherwise 'Forecast not available' will be
    returned."""

    DEFAULT_FORECAST_BINDING = 'forecast_binding'
    DEFAULT_BINDING_DICT = {'database': 'forecast_sqlite',
                            'manager': 'weewx.manager.Manager',
                            'table_name': 'archive',
                            'schema': 'user.forecast.schema'}

    def __init__(self, config_dict):
        """Initialise the ZambrettiForecast object."""

        # flag as to whether the weeWX forecasting extension is installed
        self.forecasting_installed = False
        # set some forecast db access parameters
        self.db_max_tries = 3
        self.db_retry_wait = 3
        # Get a db manager for the forecast database and import the Zambretti
        # label lookup dict. If an exception is raised then we can assume the
        # forecast extension is not installed.
        try:
            # create a db manager config dict
            dbm_dict = weewx.manager.get_manager_dict(config_dict['DataBindings'],
                                                      config_dict['Databases'],
                                                      ZambrettiForecast.DEFAULT_FORECAST_BINDING,
                                                      default_binding_dict=ZambrettiForecast.DEFAULT_BINDING_DICT)
            # get a db manager for the forecast database
            self.dbm = weewx.manager.open_manager(dbm_dict)
            # import the Zambretti forecast text
            from user.forecast import zambretti_label_dict
            self.zambretti_label_dict = zambretti_label_dict
            # if we made it this far the forecast extension is installed and we
            # can do business
            self.forecasting_installed = True
        except (weewx.UnknownBinding, weedb.DatabaseError,
                weewx.UnsupportedFeature, KeyError, ImportError):
            # something went wrong, our forecasting_installed flag will not
            # have been set so we can just continue on
            pass

    def is_installed(self):
        """Is the forecasting extension installed."""

        return self.forecasting_installed

    def get_zambretti_text(self):
        """Return the current Zambretti forecast text."""

        # if the forecast extension is not installed then return an appropriate
        # message
        if not self.forecasting_installed:
            return 'Forecast not available'

        # SQL query to get the latest Zambretti forecast code
        sql = "SELECT dateTime,zcode FROM %s WHERE method = 'Zambretti' ORDER BY dateTime DESC LIMIT 1" % self.dbm.table_name
        # try to execute the query
        for count in range(self.db_max_tries):
            try:
                record = self.dbm.getSql(sql)
                # if we get a non-None response then return the decoded
                # forecast text
                if record is not None:
                    return self.zambretti_label_dict[record[1]]
            except Exception, e:
                logerr('rtgdthread: zambretti:', 'get zambretti failed (attempt %d of %d): %s' %
                       ((count + 1), self.db_max_tries, e))
                logdbg('rtgdthread: zambretti', 'waiting %d seconds before retry' %
                       self.db_retry_wait)
                time.sleep(self.db_retry_wait)
        # if we made it here we have been unable to get a response from the
        # forecast db so return a suitable message
        return 'Forecast not available'
