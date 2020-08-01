#!/usr/bin/python3
# -*- coding: utf-8 -*

import sys
import os
import time
import datetime
import math
import statistics
import json
import argparse
import traceback
import logging

# If you did not install lidar package yet, enable the following line.
#sys.path.append(os.path.join(os.path.dirname(__file__), '../../library'))
import lidar

formatter = '%(levelname)s: %(message)s'
logging.basicConfig(level=logging.DEBUG, format=formatter)
log = logging.getLogger('garbage_bin_monitor')

# Garbage bin monitor with range sensors
class GarbageBinMonitor:
    MONITORING_PERIOD  = 10.0 # sec
    REPORT_PERIOD      = 10.0 # sec

    sensor             = None
    distanceHistory    = None
    lastMedianDistance = -1
    monitoringPeriod   = 0
    lastMeasuredTime   = 0
    isReported         = False
    lastMonitoredTime  = 0
    lastReportedTime   = 0
    confPath           = 0
    conf               = None

    def __init__(self, confPath, sensor = None, monitoringPeriod = MONITORING_PERIOD, reportPeriod = REPORT_PERIOD):
        self.sensor            = sensor
        self.monitoringPeriod  = monitoringPeriod
        self.reportPeriod      = reportPeriod
        self.confPath          = confPath

        with open(self.confPath) as f:
            self.conf = json.load(f)

    def start(self):
        self.isReported        = False
        self.lastMonitoredTime = time.time()
        self.lastMeasuredTime  = self.lastMonitoredTime
        self.lastReportedTime  = self.lastMonitoredTime
        self.distanceHistory   = {
            'time': [],
            'distance': []
        }

        # Setup and start range sensor
        if self.sensor == None:
            self.sensor = lidar.TFmini()
        self.sensor.open()
        self.sensor.startMeasuring(self.onMeasured) 
    
    def onMeasured(self, distance):
        currentTime = time.time()
        measuringTimeDiff = currentTime - self.lastMeasuredTime
        # log.debug(measuringTimeDiff)

        # Add the measured distance and current time to the history array
        self.distanceHistory['time'].append(currentTime)
        self.distanceHistory['distance'].append(distance)

        # Revmove old data from the history array
        for i in range(0, len(self.distanceHistory['time'])):
            if self.distanceHistory['time'][i] < currentTime - self.monitoringPeriod:
                del(self.distanceHistory['time'][:i + 1])
                del(self.distanceHistory['distance'][:i + 1])
                break

        # print(len(self.distanceHistory['time']), len(self.distanceHistory['distance']))

        # If the time elapelapsed exceeds the monitoring period
        if self.monitoringPeriod < currentTime - self.lastMonitoredTime:
            # Calculate normalized distance 
            self.lastMedianDistance = statistics.median(self.distanceHistory['distance'])
            self.lastMonitoredTime = currentTime
            log.debug('Monitord: distance = ' + str(self.lastMedianDistance))

        # if the time elapelapsed exceeds the reporting period
        if self.reportPeriod < currentTime - self.lastReportedTime:
            self.lastReportedTime = currentTime

            amountRate = (self.conf['empty_depth'] - self.lastMedianDistance) / self.conf['empty_depth'] * 100.0
            if amountRate > 100.0:
                amountRate = 100.0
            elif amountRate < 0:
                amountRate = 0
            
            # Send data preparation
            report = {
                "deviceType": "garbage_bin_monitor",
                "deviceId":   self.conf['id'],
                "eventType":  "send_data",
                "data": {
                    "time": datetime.datetime.fromtimestamp(currentTime).replace(microsecond=0).astimezone().isoformat(),
                    "payload": {
                        "garbage_bin": self.conf['target'],
                        "distance": self.lastMedianDistance,
                        "max_depth": self.conf['empty_depth'],
                        "amount_rate": amountRate
                    }
                }
            }
        
            # Output the report with JSON
            with open(self.conf['output_file'], 'a') as f:
                f.write(json.dumps(report) + '\n')

            log.debug('Reported: distance = ' + str(self.lastMedianDistance))

        #log.debug(self.peopleCount, self.rawPeopleCount, distance, math.floor(detectedTimeDuration * 1000), math.floor((currentTime - self.lastTime) * 1000))
        self.lastMeasuredTime = currentTime 

if __name__ == '__main__':
    while True:
        try:
            # Parse auguments
            parser = argparse.ArgumentParser()
            parser.add_argument("-c", "--conf", required = False, default = '/etc/garbage_bin_monitor.conf', help = "Configuration file")
            args = parser.parse_args()
    
            # Setup and start garbage bin monitoring
            garbageBinMonitor = GarbageBinMonitor(args.conf)
            garbageBinMonitor.start()
        except KeyboardInterrupt:   # Ctrl+C
            exit()
        except Exception as e:
            log.error('Error: ' + str(e))
            log.error(traceback.format_exc())
            log.info('Wait for 60 secs to restart...')
            time.sleep(60)

