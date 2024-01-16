"""adcsim.py - simulates PPG signal readings from ADC
Hardware course - Project
8.4.2023, Sakari Lukkarinen
11.4.2023, SL: removed obsolete rows and polish the code
School of ICT
Metropolia UAS
"""

from utime import ticks_ms, ticks_diff

class ADC():
    def __init__(self, pin_number, filename = 'example_data.csv', fs = 250):
        # The code does not use the pin number anywhere, but let's store the value
        self.pin_number = pin_number
        self.file = open(filename, encoding = 'utf-8')
        self.fs = fs # sampling frequency
        self.start = ticks_ms() # start ticking
  
    def read_u16(self):
        # Calculate elapsed time
        now = ticks_ms()
        elapsed = int(ticks_diff(now, self.start)) 
        # Store now as new start time
        self.start = now
        # Read N rows
        N = (elapsed * self.fs // 1000)
        for n in range(N):
            str = self.file.readline()
            if len(str) <= 0: # End of the file reached
                self.file.seek(0) # Read from the beginning of the file
                str = self.file.readline()
        return int(str)
