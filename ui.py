#!/usr/bin/env python3
import measurer
import matplotlib.pyplot as plt
import numpy as np

settings = measurer.default_settings

meas = measurer.Measurer(settings)

freqs = np.arange(100e6, 2000e6, 3e6)
results = list(meas.measure_harmonics(freq) for freq in freqs)

freqs_MHz = freqs * 1e-6

sp1 = plt.subplot(2,1,1)
sp2 = plt.subplot(2,1,2)

legends1, legends2 = [], []
#for hi, hn in enumerate(results[0][0]):  # Loop through harmonic numbers
for hi, hn in enumerate(results[0][0][0:5]):  # Or maybe only the first few
    # One harmonic as a function of frequency:
    harmonic_dB = list(results[i][1][hi] for i in range(len(freqs)))
    # Image frequencies:
    image_dB =    list(results[i][2][hi] for i in range(len(freqs)))

    sp1.plot(freqs_MHz, harmonic_dB)
    legends1.append('%d' % hn)
    sp2.plot(freqs_MHz, image_dB)
    legends2.append('%d' % hn)

plt.subplot(2,1,1)
plt.title('Harmonics')
plt.legend(legends1)
plt.xlabel('Frequency (MHz)')
plt.ylabel('Received (dBFS)')
plt.grid()

plt.subplot(2,1,2)
plt.title('Image frequencies')
plt.legend(legends2)
plt.xlabel('Frequency (MHz)')
plt.ylabel('Received (dBFS)')
plt.grid()

plt.show()
