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
import asyncio
import json
import time
import datetime
import pytz
import copy
import traceback
import logging

# Global variables
config = None
last_stats = {
    "time": "",
    "latest_message_timestamp": 0,
    "last_reported_time": 0,
    "handwash_stands": [
    ]
}
current_stats = last_stats

# Update each handwash stand status with the given message which includes touch event
def update_handwash_stand_status(message):
    global last_stats
    global current_stats
    
    try:
        # Detect handwash activity for each washstand
        for washstand_conf in config['handwash_stands']:
            washstand_stat = {
                "id": washstand_conf['id'],
                "last_detection_time": 0,
                "accumulated_handwash_count": 0
            }

            # Get last status of the washstand.
            for stat in last_stats['handwash_stands']:
                if washstand_conf['id'] == stat['id']:
                    washstand_stat = stat
                    break

            # Inspect reported touch events
            touch_event = json.loads(message)
            detected_time = datetime.datetime.strptime(touch_event['Time'], '%Y/%m/%d %H:%M:%S.%f')
            detected_time = detected_time.astimezone(pytz.timezone(config['timezone']))
            touched_grid = {
                "x": touch_event["GridX"],
                "y": touch_event["GridY"],
            }

            # Ignore if the timestamp of the message is older than last processed one
            if detected_time.timestamp() < last_stats['latest_message_timestamp'] or detected_time.timestamp() < datetime.datetime.now().timestamp() - 10:
                logging.warning('Ignored a too old message.')
                return

            # Update the timestamp of last processed message
            current_stats['latest_message_timestamp'] = detected_time.timestamp()

            # Check the event is like handwash activity or not by area based matching
            for touched_grid in washstand_conf['grids']:
                if touched_grid['x'] == touched_grid['x'] and touched_grid['y'] == touched_grid['y']:
                    if washstand_stat['last_detection_time'] + 2.0 < detected_time.timestamp():
                        washstand_stat['last_detection_time'] =  detected_time.timestamp()
                        washstand_stat['accumulated_handwash_count'] += 1
                    break
            #logging.info(str(washstand_stat['accumulated_handwash_count']) + '\n')

            # Get last status of the washstand.
            is_exists = False
            for i in range(len(current_stats['handwash_stands'])):
                if washstand_conf['id'] == current_stats['handwash_stands'][i]['id']:
                    current_stats['handwash_stands'][i] = washstand_stat
                    is_exists = True
                    break
            
            if not is_exists:
                current_stats['handwash_stands'].append(washstand_stat)

        # Save the last staus
        last_stats = current_stats
        logging.info(json.dumps(current_stats))
    except Exception as e:
        raise(e)
        
# Reads messages asynchronously sent from Fluend via stdin.
async def input_message(loop):
    try:
        while True:
            message = await loop.run_in_executor(None, sys.stdin.readline)
            message = message.strip()
            if message == '':
                continue

            logging.info('Received message: ' + message + '\n')

            update_handwash_stand_status(message)
            
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
    except Exception as e:
        raise(e)

# Outputs a handwash activity report to stdout for Fluentd futher process
async def output_report(output_file):
    global config
    global last_stats

    try:
        while True:
            # Wait for a certain period
            logging.info('Wait for ' + str(config['monitoring_period']) + 's for next reporting action...')
            await asyncio.sleep(config['monitoring_period'])
            logging.info('End for waiting')

            # Output report
            now = datetime.datetime.now(pytz.timezone(config['timezone']))
            last_stats['last_reported_time'] = now.timestamp()
            now = now.replace(microsecond=0)
            last_stats['time'] = now.isoformat()

            # Output a status report for futher Fluentd actions
            report = {
                "deviceType": "handwash_monitor",
                "deviceId":   config['id'],
                "eventType":  "send_data",
                "data": {
                    "time": last_stats['time'],
                    "payload": {
                        "handwashStand": "",
                        "count": 0,
                        "period": config['monitoring_period'] * 1000
                    }
                }
            }

            for handwash_stand in last_stats['handwash_stands']:
                report['data']['payload']['handwashStand'] = handwash_stand['id']
                report['data']['payload']['count']         = handwash_stand['accumulated_handwash_count']

                # Output reports for further process
                #print(json.dumps(report), flush=True)
                #sys.stdout.write(json.dumps(report))
                #sys.stdout.flush()

                with open(output_file, 'a') as f:
                    f.write(json.dumps(report) + '\n')

            logging.info("Report:" + json.dumps(last_stats))

            # Rest accumulated count of handwash activities for all handwash stands
            for handwash_stand in last_stats['handwash_stands']:
                handwash_stand['accumulated_handwash_count'] = 0

    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
    except Exception as e:
        raise(e)

# main
def main():
    global config
    global last_stats

    # Args
    device_conf_file = sys.argv[1]
    output_file      = sys.argv[2]
    log_file         = sys.argv[3]

    # Settings for logging
    logging.basicConfig(level = logging.DEBUG, filename = log_file, format = "%(asctime)s %(levelname)-7s %(message)s")

    logging.info('Script has been hard (re)started.')

    while True:
        logging.info('Script has been soft (re)started.')

        try:
            # Load sensor configuration
            with open(device_conf_file, 'r') as f:
                config = json.load(f)

            # Create status objects for each handwash stand
            for washstand_conf in config['handwash_stands']:
                washstand_stat = {
                    "id": washstand_conf['id'],
                    "last_detection_time": 0,
                    "accumulated_handwash_count": 0
                }

                last_stats['handwash_stands'].append(washstand_stat)

            # Set up async events
            loop = asyncio.get_event_loop()
            tasks = asyncio.gather(
                input_message(loop),
                output_report(output_file)
            )

            loop.run_until_complete(tasks)
        except KeyboardInterrupt:
            #tasks.cancel()
            #loop.run_forever()
            #tasks.exception()
            time.sleep(0.5) # Wait for tasks shutdown
            break
        except Exception as e:
            logging.error(traceback.format_exc())
        finally:
            loop.close()
        
        # If some exception happens, wait for 1min to restart
        logging.info('Unexpected exception has occurred. Wait for 60s to soft restart.')
        time.sleep(60)

if __name__ == "__main__":
    main()