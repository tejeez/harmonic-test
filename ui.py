#!/usr/bin/env python3
import measurer
import matplotlib.pyplot as plt
import numpy as np

settings = measurer.default_settings

meas = measurer.Measurer(settings)

freqs = np.arange(100e6, 3.4e9, 100e6)
results = list(meas.measure_harmonics(freq) for freq in freqs)

plt.xlabel('TX frequency (MHz)')
plt.ylabel('Received (dB)')
legends = []
#for hi, hn in enumerate(results[0][0]):  # Loop through harmonic numbers
for hi, hn in enumerate(results[0][0][0:4]):  # Or maybe only the first few
    # One harmonic as a function of frequency:
    harmonic_dB = list(results[i][1][hi] for i in range(len(freqs)))
    # Image frequencies:
    image_dB =    list(results[i][2][hi] for i in range(len(freqs)))

    plt.plot(freqs, harmonic_dB)
    legends.append('Harmonic %d' % hn)
    plt.plot(freqs, image_dB)
    legends.append('Image of harmonic %d' % hn)
plt.legend(legends)
plt.grid()
plt.show()
