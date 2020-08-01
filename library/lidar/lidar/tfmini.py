#!/usr/bin/python3
# -*- coding: utf-8 -*
"""
Copyright 2020 Hitachi Ltd.
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
  http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import serial
import time
import statistics
import math


class TFmini:
    TTY                = '/dev/ttyUSB0'
    BAURATE            = 115200
    ENABLE_RETRY       = True
    MIN_DISTANCE       = 10    # 10 cm
    MAX_DISTANCE       = 12000 # 12 m
    ABNORMAL_THRESHOLD = 12000 # 12 m
    HISTORY_SIZE       = 5

    ser                = None
    tty                = TTY
    baurate            = BAURATE
    onObservedCallback = None

    def __init__(self, tty = TTY, baurate = BAURATE, history_num = HISTORY_SIZE):
        self.setSerial(tty, baurate)

    def setSerial(self, tty, baurate):
        self.tty     = tty
        self.baurate = baurate

    def open(self):
        self.ser = serial.Serial(self.tty, self.baurate)

    def getRawDistance(self):
        while True:
            count = self.ser.in_waiting
            if count > 8:
                recv = self.ser.read(9)
                self.ser.reset_input_buffer()

                if recv[0] == 0x59 and recv[1] == 0x59:     #python3
                    distance = recv[2] + recv[3] * 256
                    strength = recv[4] + recv[5] * 256

                    return distance

    def startMeasuring(self, onObservedCallback):
        self.onObservedCallback = onObservedCallback
        distanceHistory = []

        while True:
            rowDistance = self.getRawDistance()

            # Avoid abnormal value
            if rowDistance > self.ABNORMAL_THRESHOLD:
                continue
            elif rowDistance < self.MIN_DISTANCE:
                rowDistance = self.MIN_DISTANCE
            elif rowDistance > self.MAX_DISTANCE:
                rowDistance = self.MAX_DISTANCE

            # Delete oldest one and add the raw distance valuet to the history
            distanceHistory.append(rowDistance)
            if len(distanceHistory) > self.HISTORY_SIZE:
                del distanceHistory[0]

            # Calculate normalized distance 
            medianDistance = statistics.median(distanceHistory)

            # Call a callback function
            onObservedCallback(medianDistance)

if __name__ == '__main__':
    try:
        rangeSensor = TFmini()
        rangeSensor.open()
        
        def onObserved(distance):
            print(distance)

        rangeSensor.getDistance(onObserved)


    except KeyboardInterrupt:   # Ctrl+C
        if ser != None:
            ser.close()
