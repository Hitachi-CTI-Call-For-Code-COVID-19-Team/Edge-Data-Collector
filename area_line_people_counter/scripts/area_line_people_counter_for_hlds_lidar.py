#!/usr/bin/env python
# -*- coding: utf-8 -*-
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
import sys
import time
import json
import csv
import datetime
import pytz

# Args
DEVICE_CONF   = sys.argv[1]
OUTPUT_FILE   = sys.argv[2]
MESSAGE_FILE  = sys.argv[3]

# Load device conf file
with open(DEVICE_CONF, 'r') as f:
    config = json.load(f)

# Open input/output message files
out_file = open(OUTPUT_FILE,  'a')
mes_file = open(MESSAGE_FILE, 'r') 

# Mode detection (area or line counter)
if config['type'] != 'area' and config['type'] != 'line':
    raise('Error: Unexpected parse mode (' + config['type'] +') was specified.')

# Read, parse and transform (into JSON) input people counter messages
messageList = mes_file.readlines()
for message in messageList:
    jsonMessage = json.loads(message)

    # Data manupulation
    csvData = list(csv.reader([jsonMessage['message']]))
    if csvData[0][0] == 'TimeStamp':
        continue # Skip if it's a header

    # Parse HDLS People tracking software's log. Because it includes multiple zone (area) or line information in one line
    for i in range(int(csvData[0][1])): # csvData[0][1] indicates # of zones (area) or lines
        # Convert the timestamp to ISO8601 and cut milliseconds to fit this RFC3339
        timestamp = datetime.datetime.strptime(csvData[0][0], '%Y/%m/%d %H:%M:%S.%f').replace(microsecond=0)
        timestamp = timestamp.astimezone(pytz.timezone(config['timezone']))

        report = {
            "deviceType": "handwash_monitor",
            "deviceId":   config['id'],
            "eventType":  "send_data",
            "data": {
                "time": timestamp.isoformat(),
                "period": config['monitoring_period']
            }
        }

        if config['type'] == 'area':
            report['data']["payload"] = {
                "area":   csvData[0][4 + (i * 3) + 0],
                "count":  int(csvData[0][4 + (i * 3) + 1])
            }
        elif config['type'] == 'line':
            report['data']["payload"] = {
                "area":   csvData[0][5 + (i * 4) + 0],
                "count":  int(csvData[0][5 + (i * 4) + 1])
            }
        else:
            raise('Error: Unexpected parse mode (' + config['type'] +') was specified.')

        out_file.write(json.dumps(report) + '\n')

