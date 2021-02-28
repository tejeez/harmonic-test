#!/usr/bin/env python3
import SoapySDR
from SoapySDR import *

default_settings = {
    'device_args': {'driver': 'lime'},
    'rx_channel': 0,
    'tx_channel': 0,
    'rx_antenna': 'LNAH',
    'tx_antenna': 'BAND1',
    'rx_gains': (40,),
    'tx_gains': (40,),
    'samplerate': 1e6,
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

def test():
    measurer = Measurer(default_settings)

if __name__ == '__main__':
    test()
