#!/usr/bin/env python3
import SoapySDR
from SoapySDR import *
import numpy as np

default_settings = {
    'device_args': {'driver': 'lime'},

    'rx_channel': 0,
    'tx_channel': 0,
    'rx_antenna': 'LNAH',
    'tx_antenna': 'BAND1',
    'rx_gains': (40,),
    'tx_gains': (60,),

    'samplerate': 1e5,

    'rx_offset': 10000,  # RX frequency offset from TX

    'burst_samples': 100,  # TX burst length in samples
    'tx_amplitude': 1.0,
    'tx_time': int(10e6), # How much into future TX burst is timed (nanoseconds), needed to deal with latency
    'rx_samples': 2000,
}

class Measurer:
    def __init__(self, settings):
        self.settings = settings
        self.sdr = SoapySDR.Device(settings['device_args'])
        self.sdr.setSampleRate(SOAPY_SDR_RX, settings['rx_channel'], settings['samplerate'])
        self.sdr.setSampleRate(SOAPY_SDR_TX, settings['tx_channel'], settings['samplerate'])

        self.sdr.setAntenna(SOAPY_SDR_RX, settings['rx_channel'], settings['rx_antenna'])
        self.sdr.setAntenna(SOAPY_SDR_TX, settings['tx_channel'], settings['tx_antenna'])

        # In gain settings, use the combined gain if the value is not a tuple.
        # If it is, the first element is the name of the gain and the second is the value.
        for g in settings['rx_gains']:
            if g is tuple:
                self.sdr.setGain(SOAPY_SDR_RX, settings['rx_channel'], g[0], g[1])
            else:
                self.sdr.setGain(SOAPY_SDR_RX, settings['rx_channel'], g)
        for g in settings['tx_gains']:
            if g is tuple:
                self.sdr.setGain(SOAPY_SDR_TX, settings['tx_channel'], g[0], g[1])
            else:
                self.sdr.setGain(SOAPY_SDR_TX, settings['tx_channel'], g)

        self.rxstream = self.sdr.setupStream(SOAPY_SDR_RX, SOAPY_SDR_CF32)
        self.txstream = self.sdr.setupStream(SOAPY_SDR_TX, SOAPY_SDR_CF32)

        self.txburst = np.ones(settings['burst_samples'], dtype=np.complex64) * settings['tx_amplitude']

    def measure(self, freq):
        """Perform a measurement on a given frequency.

        Transmitter LO is tuned to the frequency, and burst of the LO
        frequency is transmitted.

        Receiver LO is tuned to some offset from this frequency, which should
        result in each harmonic being on a different "intermediate frequency".
        """
        self.sdr.setFrequency(SOAPY_SDR_RX, self.settings['rx_channel'], freq + self.settings['rx_offset'])
        self.sdr.setFrequency(SOAPY_SDR_TX, self.settings['tx_channel'], freq)

        self.sdr.activateStream(self.txstream)
        self.sdr.activateStream(self.rxstream)
        tnow = self.sdr.getHardwareTime()

        rt = self.sdr.writeStream(
            self.txstream,
            (self.txburst,), len(self.txburst),
            flags = SOAPY_SDR_END_BURST | SOAPY_SDR_HAS_TIME,
            timeNs = tnow + self.settings['tx_time'])
        print("TX:", rt)

        rxbuf = np.zeros(self.settings['rx_samples'], dtype=np.complex64)
        rr = self.sdr.readStream(self.rxstream, (rxbuf,), len(rxbuf))
        print("RX:", rr)
        print(np.mean(np.abs(rxbuf).reshape(-1, 100), axis=1))

        self.sdr.deactivateStream(self.txstream)
        self.sdr.deactivateStream(self.rxstream)


def test():
    measurer = Measurer(default_settings)
    for f in np.linspace(2.4e9, 2.45e9, 50):
        measurer.measure(f)

if __name__ == '__main__':
    test()
