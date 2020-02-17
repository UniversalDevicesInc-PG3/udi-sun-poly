#!/usr/bin/env python3

import polyinterface
import sys
from astral.location import Location
from tzlocal import get_localzone
import datetime

LOGGER = polyinterface.LOGGER


class Controller(polyinterface.Controller):
    def __init__(self, polyglot):
        super().__init__(polyglot)
        self.name = 'Sun Position'
        self.address = 'sunctrl'
        self.primary = self.address
        self.location = None
        self.tz = None
        self.today = None
        self.sunrise = None
        self.sunset = None
        self.sun_above_horizon = False

    def start(self):
        LOGGER.info('Started Sun Position')
        if not 'longitude' in self.polyConfig['customParams'] or not 'latitude' in self.polyConfig['customParams']:
            LOGGER.error('Please specify latitude and longitude configuration parameters')
        else:
            self.tz = get_localzone()
            self.today = datetime.date.today()
            self.location = Location()
            self.location.timezone = str(self.tz)
            self.location.longitude = float(self.polyConfig['customParams']['longitude'])
            self.location.latitude = float(self.polyConfig['customParams']['latitude'])
            if 'elevation' in self.polyConfig['customParams']:
                self.location.elevation = int(self.polyConfig['customParams']['elevation'])
            self.sunrise = self.location.sunrise()
            self.sunset = self.location.sunset()
            ts_now = datetime.datetime.now(self.tz)
            if self.sunrise < ts_now < self.sunset:
                self.sun_above_horizon = True
            self.updateInfo()

    def stop(self):
        LOGGER.info('Sun Position is stopping')

    def shortPoll(self):
        self.updateInfo()
            
    def updateInfo(self):
        if self.location is None:
            return
        ts_now = datetime.datetime.now(self.tz)
        self.setDriver('GV0', round(self.location.solar_azimuth(), 2))
        self.setDriver('GV1', round(self.location.solar_elevation(), 2))
        self.setDriver('GV2', round(self.location.solar_zenith(ts_now), 2))
        self.setDriver('GV3', round(self.location.moon_phase(), 2))
        date_now = datetime.date.today()
        if date_now != self.today:
            LOGGER.debug('It\'s a new day! Calculating sunrise and sunset...')
            self.today = date_now
            self.sunrise = self.location.sunrise()
            self.sunset = self.location.sunset()
        ts_now = datetime.datetime.now(self.tz)
        if self.sunrise < ts_now < self.sunset:
            if not self.sun_above_horizon:
                LOGGER.info('Sunrise')
                self.reportCmd('DOF')
                self.sun_above_horizon = True
        else:
            if self.sun_above_horizon:
                LOGGER.info('Sunset')
                self.reportCmd('DON')
                self.sun_above_horizon = False

    def query(self):
        for node in self.nodes:
            self.nodes[node].reportDrivers()

    id = 'SUNCTRL'
    commands = {'QUERY': query}
    drivers = [{'driver': 'ST', 'value': 1, 'uom': 2},
               {'driver': 'GV0', 'value': 0, 'uom': 14},
               {'driver': 'GV1', 'value': 0, 'uom': 14},
               {'driver': 'GV2', 'value': 0, 'uom': 14},
               {'driver': 'GV3', 'value': 0, 'uom': 56}
              ]


if __name__ == "__main__":
    try:
        polyglot = polyinterface.Interface('Sun')
        polyglot.start()
        control = Controller(polyglot)
        control.runForever()
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
