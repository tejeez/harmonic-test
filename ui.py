#!/usr/bin/env python3
import measurer
import matplotlib.pyplot as plt
import numpy as np

settings = measurer.default_settings

def plot_spectrum(buf):
    """Plot spectrum from a buffer of signal"""
    fft = np.fft.fftshift(np.fft.fft(buf))
    fft_dB = np.log10(fft.real**2 + fft.imag**2) * 10
    harmonic_numbers = np.fft.fftshift(
        np.fft.fftfreq(
            len(fft),
            settings['offset'] / settings['samples_meas']))
    plt.plot(harmonic_numbers, fft_dB)

meas = measurer.Measurer(settings)

rxbuf = meas.measure(432e6)

plot_spectrum(rxbuf)
plt.xlabel("Harmonic number")
plt.ylabel("Received dB")
plt.grid()
plt.show()
