#!/usr/bin/env python3

import udi_interface
import sys
from astral.location import Location
from tzlocal import get_localzone
import datetime

LOGGER = udi_interface.LOGGER


class Controller(udi_interface.Node ):
    def __init__(self, polyglot, primary, address, name):
        super().__init__(polyglot, primary, address, name)
        self.poly = polyglot
        self.name = name
        self.address = address
        self.primary = primary
        self.location = None
        self.tz = None
        self.today = None
        self.sunrise = None
        self.sunset = None
        self.sun_above_horizon = False
        self.configured = False

        polyglot.subscribe(polyglot.START, self.start, address)
        polyglot.subscribe(polyglot.CUSTOMPARAMS, self.parameterHandler)
        polyglot.subscribe(polyglot.POLL, self.poll)

        polyglot.ready()
        polyglot.addNode(self, conn_status="ST")


    def parameterHandler(self, params):
        self.poly.Notices.clear()
        self.configured = False
        valid = True

        if 'longitude' in params:
            if params['longitude'] == '':
                valid = False
                self.poly.Notices['long'] = 'Please specify longitude in configuraton parameters'
            else:
                self.location.longitude = float(params['longitude'])
        else:
            self.poly.Notices['long'] = 'Please specify longitude in configuraton parameters'
            valid = False

        if 'latitude' in params:
            if params['latitude'] == '':
                valid = False
                self.poly.Notices['lat'] = 'Please specify latitude in configuraton parameters'
            else:
                self.location.latitude = float(params['latitude'])
        else:
            self.poly.Notices['lat'] = 'Please specify latitude in configuraton parameters'
            valid = False

        if 'elevation' in params:
            self.location.elevation = int(params['elevation'])
        else:
            self.location.elevation = 0

        if valid:
            self.tz = get_localzone()
            self.today = datetime.date.today()
            self.location = Location()
            self.location.timezone = str(self.tz)
            self.sunrise = self.location.sunrise()
            self.sunset = self.location.sunset()
            ts_now = datetime.datetime.now(self.tz)
            if self.sunrise < ts_now < self.sunset:
                self.sun_above_horizon = True
            self.configured = True

    def start(self):
        LOGGER.info('Started Sun Position')

        while not self.configured:
            sleep(1000)

       self.updateInfo()

    def stop(self):
        LOGGER.info('Sun Position is stopping')

    def poll(self, pollflag):
        if pollflag == 'shortPoll':
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
        self.reportDrivers()

    id = 'SUNCTRL'
    commands = {'QUERY': query}
    drivers = [{'driver': 'ST', 'value': 0, 'uom': 25},
               {'driver': 'GV0', 'value': 0, 'uom': 14},
               {'driver': 'GV1', 'value': 0, 'uom': 14},
               {'driver': 'GV2', 'value': 0, 'uom': 14},
               {'driver': 'GV3', 'value': 0, 'uom': 56}
              ]


if __name__ == "__main__":
    try:
        polyglot = udi_interface.Interface([])
        polyglot.start('0.0.3')
        Controller(polyglot, 'sunctrl', 'sunctrl', 'Sun Position')
        polyglot.runForever()
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
