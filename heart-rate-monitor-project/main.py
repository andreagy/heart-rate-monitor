#Library setup
from ssd1306 import SSD1306_I2C
from machine import Pin, I2C, ADC
from fifo import Fifo
from piotimer import Piotimer as Timer #use hardware timer instead of Timer from machine
from led import Led
from utime import sleep_ms
import time
from livefilter import LiveSosFilter # Real-time filtering implementation
import math
import urequests as requests
import ujson
import network

#WLAN connection
ssid = 'Insert_wifi_joke'
password = 'tisztaforras'

def connect():
    #Connect to WLAN
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)
    #Loop until connection handshake happens
    while wlan.isconnected() == False:
        print('Waiting for connection...')
        sleep(1)
    ip = wlan.ifconfig()[0]
    print(f'Connected on {ip}')
    return ip

#Hardware setup
adc = ADC(26)
fs = 250 #sampling frequency (sample/s)
N = fs // 25 # Display every Nth sample
fifo = Fifo(fs * 2)  # size of the buffer
i2c = I2C(1, scl = Pin(15), sda = Pin(14))
oled = SSD1306_I2C(128, 64, i2c)
pico_led = Pin("LED", Pin.OUT)
button_pin = Pin(12, Pin.IN, Pin.PULL_UP)

#Rotary button push handler
def rotary_button_push(pin):
    global restart
    debounce_time_rot = 0
    if (time.ticks_ms()-debounce_time_rot) > 500:
        debounce_time1=time.ticks_ms()
        restart = True

#Data aquisition handler
def adc_read(tim):
    x = adc.read_u16()
    fifo.put(x)

#HRV analysis (PPI, HR, SDNN, RMSSD)
def hrv_analysis(ppi_set):
    N = len(ppi_set)
    if N == 0 or N == 1: #preventing devision by 0
        return 0, 0, 0, 0
    ppi_mean = sum(ppi_set) / N
    hr_mean = 60 / (ppi_mean / 1000)
    # SDNN
    inner_sum = 0
    for ppi_value in ppi_set:
        inner_sum += (ppi_value - ppi_mean) ** 2
    sdnn = math.sqrt(1 / (N - 1) * inner_sum)

    # RMSSD
    inner_sum2 = 0
    prev_ppi_value = ppi_set[0]
    ppi_set.pop(0)
    for ppi_value in ppi_set:
        inner_sum2 += (ppi_value - prev_ppi_value) ** 2
        prev_ppi_value = ppi_value
    rmssd = math.sqrt(1 / (N - 1) * inner_sum2)
    return ppi_mean, hr_mean, sdnn, rmssd

#Show start message on OLED
oled.fill(0)
oled.text('Hardware Project', 1, 10, 1)
oled.text('HEART HACKER', 15, 25, 1)
oled.text('Group 1', 35, 55, 1)
oled.show()
sleep_ms(4000)
oled.fill(0)
oled.show()


#Rotary button push interrupt
button_pin.irq(handler = rotary_button_push, trigger = button_pin.IRQ_FALLING)

#Run
L = 15 #max sample
x1 = -1
y1 = 32
m0 = 28621 #moving average
a = 1/25 #weight for adding new data to moving average, bigger the denominator is the longer time it takes for sampling

# Filter settings, the filter coefficient have been copied
sos =  [[ 0.99375596, -0.99375596,  0.        ,  1.        , -0.98751193, 0.        ],
        [ 0.009477  , -0.01795636,  0.009477  ,  1.        , -1.87609963,  0.88074724],
        [ 1.        , -1.98153609,  1.        ,  1.        , -1.95391259,  0.95787597]]
sosfilter = LiveSosFilter(sos, 5000) # Initialize the real-time filter



b2b_intervals = []

#Trying to connect to internet
try:
    ip = connect()
except KeyboardInterrupt:
    machine.reset()
    
    
#Run
restart = True #flag for restarting loop

while True:
    # starting collecting data
    timer = Timer(freq=fs, callback=adc_read)
    count = 0
    last_beat_count = 0
    max_x = 1
    min_x = 65000
    last_x = 0
    in_beat = False
    b2b_intervals = []
    restart = False
    while count < L * fs:
        if not fifo.empty():
            count += 1
            x_unfiltered = fifo.get()  # get data from the buffer
            x = sosfilter.process(x_unfiltered - 33000)
            if x > max_x:
                max_x = x
            if x < min_x:
                min_x = x
            if not in_beat and x > (max_x * 2) // 5:  # if x is above the threshold we get a peak. threshold is 2/5 of the max amplitude
                in_beat = True  # we have a peak
                diff = (count - last_beat_count) / fs  # calculating beat-to-beat interval, diff/fs, converting the beat-to-beat interval from the number of samples between peaks to a time value in seconds
                last_beat_count = count
                hr = 60 / diff
                print(f'heart rate: {hr:.0f}')
                pico_led.value(1) #led lights up in peak
                if hr < 200 and hr > 43:  # append only reasonable values
                    b2b_intervals.append(diff * 1000)
            if in_beat and x < (
                    max_x + min_x) // 2:  # peak is finished: setting threshold, which is the halfway point between the maximum and minimum values
                in_beat = False
                pico_led.value(0)
            if count % N == 0:
                m0 = (1 - a) * m0 + a * x  # calculate moving average
                y2 = int(32 * x / max_x + 32)  # scale the plotting to fit into OLED
                # y2 = int(64 - (x/65535)*64) #alternative scaling without moving average
                y2 = max(0, min(64, y2))  # limit the values between 0-64
                x2 = x1 + 1  # drawing the graph
                oled.line(x2, 0, x2, 64, 0)  # clean up one line on OLED
                oled.line(x1, y1, x2, y2, 1)  # show plotting on OLED
                oled.show()
                x1 = x2
                if x1 > 127:  # start over when we reach the end of the display
                    x1 = -1
                y1 = y2
                last_x = x

    # Calculate average
    b2b_intervals.pop(0) #first measurement is always invalid
    ppi_mean, hr_mean, sdnn, rmssd = hrv_analysis(b2b_intervals)

    timer.deinit()  # close the timer

    # Kubios analysis

    APIKEY = "pbZRUi49X48I56oL1Lq8y8NDjq6rPfzX3AQeNo3a"
    CLIENT_ID = "3pjgjdmamlj759te85icf0lucv"
    CLIENT_SECRET = "111fqsli1eo7mejcrlffbklvftcnfl4keoadrdv1o45vt9pndlef"

    LOGIN_URL = "https://kubioscloud.auth.eu-west-1.amazoncognito.com/login"
    TOKEN_URL = "https://kubioscloud.auth.eu-west-1.amazoncognito.com/oauth2/token"
    REDIRECT_URI = "https://analysis.kubioscloud.com/v1/portal/login"

    response = requests.post(
        url=TOKEN_URL,
        data='grant_type=client_credentials&client_id={}'.format(CLIENT_ID),
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        auth=(CLIENT_ID, CLIENT_SECRET))

    response = response.json()  # Parse JSON response into a python dictionary
    access_token = response["access_token"]  # Parse access token out of the response dictionary

    # creating dataset
    data_set = {
        "type": "RRI",
        "data": b2b_intervals,
        "analysis": {
            "type": "readiness"
        }
    }

    # analyze given data

    response = requests.post(
        url="https://analysis.kubioscloud.com/v2/analytics/analyze",
        headers={"Authorization": "Bearer {}".format(access_token),
                 # use access token to access KubiosCloud analysis session
                 "X-Api-Key": APIKEY},
        json=data_set)  # convert dataset to JSON format
    response = response.json()
    print(response)
    
    
    if response['status'] == 'error':
        print('Measurment invalid. Start over.')
        oled.fill(0)
        oled.text('Measurment',20, 10, 1)
        oled.text('invalid.',30, 20, 1)
        oled.text('Start over.', 20, 40, 1)
        oled.show()
    else:
        sns = response['analysis']['sns_index']
        pns = response['analysis']['pns_index']
        

        # Print algorithm analysis
        print(f'PPI mean: {ppi_mean:.0f}')
        print(f'heart rate: {hr_mean:.0f}')
        print(f'SDNN: {sdnn:.2f} ms')
        print(f'RMSSD: {rmssd:.2f} ms')
        # Print Kubios analysis
        print(f'SNS: {sns}')
        print(f'PNS: {pns}')
        print('Done!')

        # Show mean value on OLED
        oled.fill(0)
        oled.text(f'PPI mean: {ppi_mean:.0f}', 1, 0, 1)
        oled.text(f'HR mean: {hr_mean:.1f}', 1, 10, 1)
        oled.text(f'SDNN: {sdnn:.2f} ms', 1, 20, 1)
        oled.text(f'RMSSD: {rmssd:.2f} ms', 1, 30, 1)
        oled.text(f'SNS: {sns}', 1, 40, 1)
        oled.text(f'PNS: {pns}', 1, 50, 1)
        oled.text(f'PPI mean: {ppi_mean:.0f}', 1, 0, 1)
        oled.show()

    restart = False

    while not fifo.empty():
        temp = fifo.get()
    while True:
        if restart == True:
            oled.fill(0)
            oled.text('Restarting in', 13, 10, 1)
            oled.show()
            sleep_ms(1000)
            oled.text('3', 35, 25, 1)
            oled.show()
            sleep_ms(1000)
            oled.text('3  2', 35, 25, 1)
            oled.show()
            sleep_ms(1000)
            oled.text('3  2  1', 35, 25, 1)
            oled.show()
            sleep_ms(1000)
            oled.fill(0)
            break

