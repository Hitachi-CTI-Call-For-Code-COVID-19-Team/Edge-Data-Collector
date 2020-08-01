# Hand wash activity monitor with HLDS LiDAR (ToF) 
This is a sensor data collector of a hand wash activity monitor which detects people's hand wash activities at specific washstands for COVSAFE.
* We use HLDS LiDAR (ToF) to detect hand wash activities.
* HLDS touch detection software manages all LiDARs and outputs logs including when and where people touches specific area with JSON format.
* To gather the logs in realtime, we use Fluentd.
* In the Fluentd, a python script will be called to normalize and send the data to [IBM Cloud Event Streams](https://www.ibm.com/cloud/event-streams).

<img src=./img/overview.png width=70%>

# Prerequisite
Credentials for IBM Cloud Event Streams and asset information are required during the following installation process. Thus please, check and accomplish the COVSAFE [delivery step](https://github.com/Hitachi-CTI-Call-For-Code-COVID-19-Team/delivery/) before hand.

# Requirements
* LiDAR Sensor: [HLDS 3D LiDAR (ToF)](http://hlds.co.jp/product-eng/?ckattempt=1)
* Edge server:
    * OS: Windows 10 (32/64-bits)
    * CPUs: Depends on the number of ToFs. HLDS says 2 LiDARs/core.
    * MEMs: 8 GB
    * Disk: Depends on how long you want to keep people trucking logs. Over 1 TB is recommended.

# Installation
## Install ToF SDK on management server
1. Download LiDAR SDK from;  
[http://hlds.co.jp/product-eng/tofsdk](http://hlds.co.jp/product-eng/tofsdk).
    * We tested v2.3.0 with VisualStudio2015 libraries.

2. Install LiDARs (ToF) driver from `\HldsTofSdk.2.3.0vs2015\x86\tofdriver\tof_driver_x86_v2.3.0_Installer.exe` according to the manual 
    * Note that we have to use x86 (NOT x64) driver even if we have x64 OS/CPU.

## Install HLDS People tracking software
1. Download People tracking software (including touch detection software) from;
[http://hlds.co.jp/product-eng/tofsdk/peopletrack](http://hlds.co.jp/product-eng/tofsdk/peopletrack).

1. Install software according to the manual.
    * All you have to do is copy the downloaded and extracted files to anywhere you want. We suppose that you placed it in `C:\opt\ToF\PeopleTracking_v200_for_TouchDetection` and the path of the software is `C:\opt\ToF\PeopleTracking_v200_for_TouchDetection\PeopleTracking\TouchDetect.exe`.

## Calibration of LiDARs and monitoring settings
1. According to the manual, you have to calibrate LiDARs for your environments using `C:\opt\ToF\PeopleTracking_v200_for_TouchDetection\PeopleTracking\TofStitcher.exe`.
    * You can specify map image of your store or something. 
1. Launch up `TouchDetect.exe` and configure where you want to detect touch actions according to the manual. We assumed when people touches around faucets in a specific hand washstand, it could be supposed that he/she washed their hands. 


## Install Python 3.x for Windows
1. Download Python 3.x installer from;
[https://www.python.org/downloads/windows/](https://www.python.org/downloads/windows/).
    * We use `Windows x86-64 executable installer` at this moment.

2. Install Python with downloaded `python-3.8.3-amd64.exe`.
    * Note that you should turn the check box on for `Add Python 3.X to Path`. 

## Install Fluentd and scripts for IBM Cloud Event Streams
### Download and install Fluentd (td-agent)
1. Download td-agent for Windows (td-agent is a distribution package of Fluentd + Ruby environment provided by Treasure Data, Inc.) from;
[https://td-agent-package-browser.herokuapp.com/3/windows](https://td-agent-package-browser.herokuapp.com/3/windows)
    * We use `td-agent-3.7.1-0-x64.msi` at this moment.

1. Install Fluentd with setup wizard (td-agent-*.msi)

### Clone this project
* Open `Td-agent` -> `Td-agent Command Prompt` from Windows menu.
  ```powershell
  C:\opt\td-agent> git clone https://github.com/Hitachi-CTI-Call-For-Code-COVID-19-Team/edge-data-collector.git
  ```

### Fluentd configuration
1. Add an include operation at the end of `td-agent.conf`
    ```powershell
    C:\opt\td-agent> echo "@include config.d/*.conf" >> etc\td-agent\td-agent.conf
    ```

1. Copy the configuration file for td-agent.
    ```powershell
    C:\opt\td-agent> mkdir etc\td-agent\config.d
    C:\opt\td-agent> copy edge-data-collector\handwash_monitor\conf\td-agent\config.d\handwash_monitor.conf etc\td-agent\config.d\
    ```
1. Modify kafka settings in the td-agent configuration file to produce hand wash activities data to IBM Event Stream.
    1. Acquire credential information from `.credentials` file which you have created in [delivery step](https://github.com/Hitachi-CTI-Call-For-Code-COVID-19-Team/delivery). 
    1. Check `EVENT_STREAMS_WRITER_CREDENTIALS` parameter in `.credentials` 
    1. Open C:\opt\td-agent\etc\td-agent\config.d\handwash_monitor.conf
    1. Find the kafka (Event Streams) settings in the `<match covsafe.report.*>/type kafka2` directive and replace the followings to suitable values.
         * BROKERS_ADDRESS: Concatenate broker addresses in `kafka_brokers_sasl` array with comma.
            * ex. `brokers broker-0-xxxx.kafka.svc01.jp-tok.eventstreams.cloud.ibm.com:9093,broker-1-yyyy.kafka.svc01.jp-tok.eventstreams.cloud.ibm.com:9093`
        * USERNAME: Replace with the value of `user`.
            * ex. `user token`
        * PASSWORD: Replace with the value of `password`.
            * ex. `password xxxxxxxxxxxx`
        ```xml
        <match covsafe.report.*>
        @type kafka2
        brokers BROKERS_ADDRESS # Edit this one
        use_event_time true
        default_topic covsafe
        required_acks -1

        <format>
            @type json
        </format>

        username USERNAME # Edit this one
        password PASSWORD # Edit this one
        sasl_over_ssl true
        ssl_ca_certs_from_system true

        <buffer>
            @type file
            path C:/var/run/kafka.buffer
            chunk_limit_size 8m
            queue_limit_length 256
            flush_at_shutdown true
            flush_interval 1s
            retry_wait 10s
            retry_max_times 10
        </buffer>  
        </match>
        ```

### Scripts for HLDS LiDAR
* Copy [scripts/*](scripts/) to `C:/opt/td-agent/bin/`.
  ```powershell
  C:\opt\td-agent> copy edge-data-collector\handwash_monitor\scripts\* bin\
  ```

## Sensor configurations
1. Copy a sample sensor configuration files from below to (handwash_monitor-0001.conf) to `C:/opt/td-agent/etc/sensors/`.
      ```powershell
      C:\opt\td-agent> mkdir etc\td-agent\sensors
      C:\opt\td-agent> copy edge-data-collector\handwash_monitor\conf\sensors\* etc\td-agent\sensors\
      ```
1. Modify sensor settings.
    * Open C:\opt\td-agent\etc\sensor
    * Editt \<Sensor ID\>.conf
    * Parameters are as follows;
        * id: ID of the sensor. You can find this from [asset.json in the delivery repository](https://github.com/Hitachi-CTI-Call-For-Code-COVID-19-Team/delivery/blob/master/data/tenants/c4c/cloudant/assets.json)

        * monitoring_period: Period of monitoring and normalizing in msec.
        * timezone: Timezone string where the sensor is located ([pytz style](https://pypi.org/project/pytz/))
        * handwash_stands: Information for hand washstands to detect hand wash activities. `id` is an identifier of the targeted hand washstand. You can find this form [asset.json in the delivery repository](https://github.com/Hitachi-CTI-Call-For-Code-COVID-19-Team/delivery/blob/master/data/tenants/c4c/cloudant/assets.json). `grids` indicates areas around the faucets according to the TouchDetect.exe setting where the touch actions could be assumed as hand wash activities.
        ```json
        {
            "id": "handwash_monitor-0001",
            "monitoring_period": 10,
            "timezone": "Asia/Tokyo",
            "handwash_stands" : [
                {
                    "id": "handwash_stand-0001",
                    "grids": [
                        {"x": 8, "y": 1},
                        {"x": 8, "y": 2},
                        {"x": 8, "y": 3}
                    ]
                }
            ]
        }
        ```
1. Repeat the step 1 and 2 for all sensors.

## Make Fluentd as a Windows service
1. Open `Td-agent` -> `Td-agent Command Prompt` from Windows menu **AS AN ADMINISTRATOR**, and register td-agent as a Windows service.
    ```powershell
    C:\Windows\system32> fluentd --reg-winsvc i
    C:\Windows\system32> fluentd --reg-winsvc-fluentdopt '-v -c C:\opt\td-agent\etc\td-agent\td-agent.conf -o C:\opt\td-agent\log\td-agent.log'
    ```

1. Start the Fluentd service
    ```powershell
    C:\Windows\system32> sc start "fluentdwinsvc"
    ```

1. Make the service starts automatically.
    * Note that to use above python scripts in Fluentd, we need to run the service with a user account who installed Python 3.X. Please specify `<Account Name>` and `<Password>` options.
      ```powershell
      C:\Windows\system32> sc config "fluentdwinsvc" start= auto obj= .\<Account Name> password= <Password>
      C:\Windows\system32> sc qc "fluentdwinsvc"
      ```

## Start touch detection software when logon
1. Create a shortcut of `C:\opt\ToF\PeopleTracking_v200_for_TouchDetection\PeopleTracking\TouchDetect.exe`.
1. Open Explorer and enter `shell:startup` in address bar.
1. Put the above shortcut in the shown startup folder.

# Usage
## Run Fluentd and HLDS touch detection software.
1. Run Fluentd
    *  As a foreground process
        1. Open `Td-agent` -> `Td-agent Command Prompt` from Windows menu.

        1. Type the following command to start Fluentd.
            ```
            > fluentd -v -c etc\td-agent\td-agent.conf
            ```
    *  As a service
        * Open `Td-agent` -> `Td-agent Command Prompt` from Windows menu **AS AN ADMINISTRATOR** and execute the following commands.
          ```
          C:\Windows\system32> sc start "fluentdwinsvc"
          ```

1. Launch up the touch detection software
    * Open `C:\opt\ToF\PeopleTracking_v200_for_TouchDetection\PeopleTracking\TouchDetect.exe`.


## Logs
* Fluentd logs
  * If you want check Fluentd logs, you can get it from the following file.
    ```
    C:\opt\td-agent\log\td-agent.log
    ```


## Some useful service management commands on Windows.
* Open `Td-agent` -> `Td-agent Command Prompt` from Windows menu **AS AN ADMINISTRATOR** and execute the following commands.
  ```powershell
  C:\Windows\system32> sc query state=all # Show status of all services
  C:\Windows\system32> sc query fluentdwinsvc # Show status of the Fluentd service
  C:\Windows\system32> sc start "fluentdwinsvc" # Start the Fluentd service
  C:\Windows\system32> sc stop "fluentdwinsvc" # Stop the Fluentd service
  C:\Windows\system32> sc config "fluentdwinsvc" start= auto # Make the service starts automatically
  C:\Windows\system32> sc config "fluentdwinsvc" start= demand # Make the service starts manually
  C:\Windows\system32> sc qc "fluentdwinsvc" # Show the service configurations including startup settings



