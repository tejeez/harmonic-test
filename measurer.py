#!/usr/bin/env python3
"""Module to control an SDR and perform measurements using it."""
import SoapySDR
from SoapySDR import *
import numpy as np
import math

default_settings = {
    'device_args': {'driver': 'lime'},

    'rx_channel': 0,
    'tx_channel': 0,
    'rx_antenna': 'LNAH',
    'tx_antenna': 'BAND2',
    'rx_gains': (
        ('LNA', 20),   # 0 to 30
        ('TIA', 9),   # 0 to 12
        ('PGA', 12),   # -12 to 19
    ),
    'tx_gains': (
        ('PAD', 40),  # 0 to 52
        ('IAMP', 12), # -12 to 12
    ),

    'samplerate': 0.96e6,

    'tx_amplitude': 1.0, # Value of I/Q samples written to TX

    # How much into future TX burst is timed (nanoseconds), needed to deal with latency:
    'tx_time': int(15e6),

    # Length of measurement interval in samples.
    # This also becomes the size of the FFT used to find harmonics:
    'samples_meas': 2048,
    # Extra samples to transmit before the measurement interval,
    # maybe useful to let all the filters settle first:
    'samples_begin': 500,
    # Extra samples to transmit after the measurement interval:
    'samples_end': 500,
    # Number of samples received. It should be enough to fit the transmit
    # burst within the buffer, considering tx_time as well:
    'samples_rx': 200000,

    # How many frequency bins TX is offset from RX:
    'offset': 20,
}

class Measurer:
    def __init__(self, settings):
        # Some general setup

        self.settings = settings

        self.rx_freq_offset = -settings['samplerate'] * settings['offset'] / settings['samples_meas']
        print(self.rx_freq_offset)

        # Generate the TX buffer
        samples_tx = settings['samples_begin'] + settings['samples_meas'] + settings['samples_end']
        self.txburst = np.ones(samples_tx, dtype=np.complex64) * settings['tx_amplitude']
        # Preallocate the RX buffer too
        self.rxbuffer = np.zeros(settings['samples_rx'], dtype=np.complex64)

        # Initialize the SDR

        self.sdr = SoapySDR.Device(settings['device_args'])
        self.sdr.setSampleRate(SOAPY_SDR_RX, settings['rx_channel'], settings['samplerate'])
        self.sdr.setSampleRate(SOAPY_SDR_TX, settings['tx_channel'], settings['samplerate'])

        self.sdr.setAntenna(SOAPY_SDR_RX, settings['rx_channel'], settings['rx_antenna'])
        self.sdr.setAntenna(SOAPY_SDR_TX, settings['tx_channel'], settings['tx_antenna'])

        for g in self.sdr.listGains(SOAPY_SDR_RX, settings['rx_channel']):
            print('RX gain range:', g, self.sdr.getGainRange(SOAPY_SDR_RX, settings['rx_channel'], g))
        for g in self.sdr.listGains(SOAPY_SDR_TX, settings['tx_channel']):
            print('TX gain range:', g, self.sdr.getGainRange(SOAPY_SDR_TX, settings['tx_channel'], g))

        # In gain settings, use the combined gain if a single-element tuple.
        # If there are two, the first element is the name of the gain and the second is the value.
        self.sdr.setGain(SOAPY_SDR_RX, 0, 'LNA', 0.0)
        for g in settings['rx_gains']:
            self.sdr.setGain(SOAPY_SDR_RX, settings['rx_channel'], *g)
        for g in settings['tx_gains']:
            self.sdr.setGain(SOAPY_SDR_TX, settings['tx_channel'], *g)

        self.rxstream = self.sdr.setupStream(SOAPY_SDR_RX, SOAPY_SDR_CF32)
        self.txstream = self.sdr.setupStream(SOAPY_SDR_TX, SOAPY_SDR_CF32)

    def measure(self, freq):
        """Perform a measurement on a given frequency.

        Transmitter LO is tuned to the frequency, and burst of the LO
        frequency is transmitted.

        Receiver LO is tuned to some offset from this frequency, which should
        result in each harmonic being on a different "intermediate frequency".

        Return the received signal during the measurement interval.
        """
        self.sdr.setFrequency(SOAPY_SDR_RX, self.settings['rx_channel'], freq + self.rx_freq_offset)
        self.sdr.setFrequency(SOAPY_SDR_TX, self.settings['tx_channel'], freq * 3 / 5)

        self.sdr.activateStream(self.txstream)
        self.sdr.activateStream(self.rxstream)
        time_now = self.sdr.getHardwareTime()
        tx_time = time_now + self.settings['tx_time']

        rt = self.sdr.writeStream(
            self.txstream,
            (self.txburst,), len(self.txburst),
            flags = SOAPY_SDR_END_BURST | SOAPY_SDR_HAS_TIME,
            timeNs = tx_time)
        print("TX:", rt)

        rr = self.sdr.readStream(self.rxstream, (self.rxbuffer,), len(self.rxbuffer))
        print("RX:", rr)

        self.sdr.deactivateStream(self.txstream)
        self.sdr.deactivateStream(self.rxstream)

        # Use timestamps to calculate where in the RX buffer the measurement interval is.
        samples_per_ns = self.settings['samplerate'] * 1e-9
        burst_begin = int((tx_time - rr.timeNs) * samples_per_ns)
        meas_begin = burst_begin + self.settings['samples_begin']
        meas_end = meas_begin + self.settings['samples_meas']
        if meas_begin < 0:
            raise ValueError("RX buffer was too late")
        if meas_end > rr.ret:
            raise ValueError("RX buffer was too short")
        #print(meas_begin)
        return self.rxbuffer[meas_begin : meas_end]

    def measure_harmonics(self, freq):
        return calculate_harmonics(self.measure(freq), self.settings['offset'])


def calculate_harmonics(rx, offset):
    """Calculate the levels of harmonics from a received signal.

    Return value is a tuple with the following elements:
    * Array of harmonic numbers
    * Array of harmonic levels, in dB
    * Array of harmonic levels on the image frequency, in dB"""
    # Rectangular FFT window is OK here, since all the harmonics should
    # have an integer number of cycles within the measurement interval.
    # But let's still try a Hann window, because it might reject
    # interference from other frequencies better...
    #f = np.fft.fft(rx)  # Rectangular
    f = np.fft.fft(rx * np.hanning(len(rx)))  # Hann
    scaling_dB = math.log10(len(rx)) * -20 + 6.02   # +6 needed for Hann window
    f_dB = np.log10(f.real**2 + f.imag**2) * 10 + scaling_dB

    maxbin = len(f) / 2
    harmonic_nums = np.arange(1, maxbin // offset, 2, dtype=np.int)
    # An I/Q mixer driven by a square wave is sensitive to odd harmonics
    # of its LO frequency. For every second of these, the spectrum is
    # "inverted" because 90° phase shift becomes a -90° phase shift,
    # so we want the bins 1, -3, 5, -7...
    harmonic_bins = harmonic_nums * offset * \
        np.tile((1,-1), len(harmonic_nums))[0:len(harmonic_nums)]
    # Also return the image frequencies though
    image_bins = -harmonic_bins
    return (harmonic_nums, f_dB[harmonic_bins], f_dB[image_bins])

def test_scaling(samples_rx = 1024, offset = 10):
    """Test that scaling for a full-scale sine wave is correct.
    # It should return a value close to 0 dB on the first harmonic."""
    phase = np.linspace(0, np.pi*2 * offset, samples_rx, endpoint=False)
    print(calculate_harmonics(np.cos(phase) + np.sin(phase)*1j, offset))

def test_measurement():
    measurer = Measurer(default_settings)
    for f in np.linspace(2.4e9, 2.45e9, 50):
        print(measurer.measure_harmonics(f))

if __name__ == '__main__':
    #test_scaling()
    test_measurement()
