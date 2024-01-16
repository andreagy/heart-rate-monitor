### Heart Rate Monitor
## First year Health Technology Hardware course project

![image](https://github.com/andreagy/heart-rate-monitor/assets/112083530/c1d40e20-b950-492c-9055-b04c9fe404f5)

![image](https://github.com/andreagy/heart-rate-monitor/assets/112083530/4c5c804c-3a29-4543-bb07-1c00beb64e60)

During the project, a microcontroller was used developed by lecturers at Metropolia University of Applied Sciences. The device has the following components: a Raspberry Pi Pico W attached to a protoboard, a Crowtail Pulse Sensor v2.0 attached through a Grove-connector to one of the Analog-to-Digital converters of the protoboard, an OLED display, a rotary switch and knob, three LEDs and three buttons. Most of these also serve as the user interface. 
MicroPython programming language was used in the Thonny IDE. The OLED screen uses the SSD1306 display driver, which is connected to the I2C-1 bus. The ‘machine’ library's Pin, I2C and ADC classes were used for handling the GPIO’s, the OLED screen and the sensor’s analogue signals. The ‘FIFO’ library organizes and manipulates a data buffer for the data produced by the sensor. Other libraries used are ‘piotimer’ for scheduling the ADC measurements, ‘livefilter’ for signal filtering, the ‘ssd1306_I2C’ library for the OLED display, and ‘uRequest’ to make HTTP requests. The latter is needed for the REST API communication with the Kubios Cloud Service, for further analysing measurements.
