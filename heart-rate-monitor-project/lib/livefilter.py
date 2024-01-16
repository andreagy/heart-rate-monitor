"""
livefilter.py - digitally filter data sample-by-sample using second-order-sections

Version history:
26.2.2023, SL: Modified version from the original source. Works without numpy module. 
9.4.2023, SL: Added limit value.
School of ICT
Metropolia UAS

Modified version to work with standard Python (without numpy or ulab).

Source: https://www.samproell.io/posts/yarppg/yarppg-live-digital-filter/
"""

class LiveSosFilter:
    """Live implementation of digital filter with second-order sections.
    """
    def __init__(self, sos, limit = 5000):
        """Initialize live second-order sections filter.

        Args:
            sos (array-like): second-order sections obtained from scipy
                filter design (with output="sos").
            limit (integer):  value to use the limit high or low values.
        """
        self.sos = sos
        self.limit = limit       
        self.n_sections = len(sos)
        # initialize internal states to zeros
        self.state = [[0]*2 for i in range(self.n_sections)]
        
    def process(self, x):
        """Filter incoming data with cascaded second-order sections.
        """
        for s in range(self.n_sections):  # apply filter sections in sequence

            # compute difference equations of transposed direct form II
            b0, b1, b2, a0, a1, a2 = self.sos[s]             
            y = b0*x + self.state[s][0]
            # Limit the values between -limit and +limit
            y = max(y, -self.limit) 
            y = min(y, +self.limit)
            # compute internal states
            self.state[s][0] = b1*x - a1*y + self.state[s][1] 
            self.state[s][1] = b2*x - a2*y
            # set biquad output as input of next filter section
            x = y  

        return y