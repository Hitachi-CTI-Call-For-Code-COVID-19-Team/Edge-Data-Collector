# Garbage bin monitor with Seeed TFmini series 
* This is a sensor data collector which monitors the distance from the ceiling of a garbage bin to the top of the accumulated garbages inside.
* This indicates how much amount of the garbages are accumulated and cloud side service can report when should the garbage bin cleaned. 
* We use Fluentd to send the data to [IBM Cloud Event Streams](https://www.ibm.com/cloud/event-streams).

<img src=./img/overview.png width=70%>

# Prerequisite
Credentials for IBM Cloud Event Streams and asset information are required during the following installation process. Thus, please check and accomplish the COVSAFE [delivery step](https://github.com/Hitachi-CTI-Call-For-Code-COVID-19-Team/delivery/) before hand.

# Requirements
* Range sensor: [Seeed TFmini series](https://wiki.seeedstudio.com/Grove-TF_Mini_LiDAR/) (We used TFmini Plus)
  * via FTDI USB-to-TTL converter (ex. [Disifen USB-6P-3V3](https://www.amazon.co.jp/3-3V%E3%82%B7%E3%83%AA%E3%82%A2%E3%83%ABUART%E3%82%B3%E3%83%B3%E3%83%90%E3%83%BC%E3%82%BF%E3%82%B1%E3%83%BC%E3%83%96%E3%83%AB%E3%80%816%E3%82%A6%E3%82%A7%E3%82%A4%E3%83%98%E3%83%83%E3%83%80%E3%81%A7%E7%B5%82%E7%AB%AF%E3%81%95%E3%82%8C%E3%81%9FFTDI%E3%83%81%E3%83%83%E3%83%97%E4%BB%98%E3%81%8D%E3%80%81Galileo-Gen2%E3%83%9C%E3%83%BC%E3%83%89-BeagleBone-Black-Minnowboard%E3%81%A7%E5%8B%95%E4%BD%9C/dp/B0742CBHKK)).
* Edge server:
    * HW: Raspberry Pi 4 Model B
    * OS: Raspberry Pi OS 
        * We have tested on Raspberry Pi OS (32-bit) Lite (ver. 2020-05-27, kernel 4.19)
        * Probably compatible with all Linux distributions.
        * Python 3.x

# Installation
### Install garbage bin monitor scripts
1. Clone this project
    ```bash
    $ git clone https://github.com/Hitachi-CTI-Call-For-Code-COVID-19-Team/edge-data-collector.git
    $ cd ./edge-data-collector
    ```

1. Install dependencies
    ```bash
    $ sudo pip3 install wheel
    $ sudo pip3 install edge-data-collector/library/lidar
    ```

1. Copy the garbage bin monitoring script
    ```bash
    $ sudo cp garbage_bin_monitor/src/garbage_bin_monitor.py /usr/local/bin
    ```

1. Edit the configuration file for the sensor device    
    * Open and edit the configuration file
        ```
        sudo mkdir /etc/garbage_bin_monitor
        sudo cp ./garbage_bin_monitor/conf/device.conf /etc/garbage_bin_monitor/
        ```
    * Parameters are as follows;
        * id: ID of the sensor. You can find this from [asset.json in the delivery repository](https://github.com/Hitachi-CTI-Call-For-Code-COVID-19-Team/delivery/blob/master/data/tenants/c4c/cloudant/assets.json)
        * target: An identifier of the targeted garbage bin. You can find this form [asset.json in the delivery repository](https://github.com/Hitachi-CTI-Call-For-Code-COVID-19-Team/delivery/blob/master/data/tenants/c4c/cloudant/assets.json).
        * empty_depth: A distance from the ceiling of the garbage bin to the bottom in cm.
        * output_file: A path of the output file which includes measured distances.

            ```json
            {
                "id": "garbage_bin_monitor-0001",
                "target": "garbage_bin-0001",
                "empty_depth": 100,
                "output_file": "/var/log/garbage_bin_monitor_event.log"
            }
            ```
1. Make the sensor management script as a service via systemd
    ```bash
    sudo cp systemd/garbage_bin_monitor.service /etc/systemd/system/
    sudo systemctl list-unit-files --type=service | grep garbage_bin_monitor.service
    sudo systemctl enable garbage_bin_monitor
    sudo systemctl start garbage_bin_monitor
    sudo systemctl status garbage_bin_monitor
    ```

## Install fluentd
* Install ruby and fluentd packages to produce monitored data to IBM Cloud Event Streams.
    ```
    sudo apt-get update
    sudo apt-get install -y ruby-dev libssl-dev
    sudo gem install fluentd --no-ri --no-rdoc -V
    sudo fluent-gem install fluent-plugin-kafka --no-rdoc --no-ri
    ```

* Create an initial fluent.conf.
    ```
    cd /etc
    sudo fluentd --setup ./fluent
    ```

* Add an include operation to fluent.conf
    ```
    sudo vi /etc/fluent/fluent.conf
    +
    +@include config.d/*.conf
    ```

* Create configurations for garbage bin monitor.
    ```
    sudo mkdir /etc/fluent/config.d
    sudo cp ./garbage_bin_monitor/conf/fluentd/garbage_bin_monitor.conf /etc/fluent/config.d/
    ```

* Modify kafka settings in the fluentd configuration file to produce monitored data to IBM Event Stream.
    1. Acquire credential information from `.credentials` file which you have created in [delivery step](https://github.com/Hitachi-CTI-Call-For-Code-COVID-19-Team/delivery). 
    1. Check `EVENT_STREAMS_WRITER_CREDENTIALS` parameter in `.credentials` 
    1. Open the configuration file
        ```
        sudo vi /etc/fluent/config.d/garbage_bin_monitor.conf
        ```
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

* Make fluentd as a daemon service
    ```
    sudo cp ./garbage_bin_monitor/systemd/fluentd.service /etc/systemd/system/
    sudo systemctl enable fluentd
    sudo service fluentd start
    ```

## Usage
* Run the garbage bin monitoring as a foreground service for test.
    ```bash
    $ /usr/local/bin/garbage_bin_monitor.py -c /etc/garbage_bin_monitor/device.conf
    ```

* Start/Stop the garbage bin monitoring service
    ```bash
    sudo systemctl start garbage_bin_monitor
    sudo systemctl stop garbage_bin_monitor
    ```