## What is
* Controller for 1D LiDAR (ToF) baed range sensors.
  * Seeed TFmini [https://www.seeedstudio.com/Seeedstudio-Grove-TF-Mini-LiDAR.html](https://www.seeedstudio.com/Seeedstudio-Grove-TF-Mini-LiDAR.html)
  * Seeed TFmini Plus [https://www.seeedstudio.com/TFmini-Plus-LIDAR-Range-Finder-based-on-ToF-p-3222.html](https://www.seeedstudio.com/TFmini-Plus-LIDAR-Range-Finder-based-on-ToF-p-3222.html)

## Requirements
* python 3.x

## Installation
```bash
$ pip3 install .
```

## Usage
```python
import lidar

try:
    rangeSensor = TFmini()
    rangeSensor.open()
    
    def onObserved(distance):
        print(distance)

    rangeSensor.getDistance(onObserved)

except KeyboardInterrupt:   # Ctrl+C
    if ser != None:
        ser.close()
```
