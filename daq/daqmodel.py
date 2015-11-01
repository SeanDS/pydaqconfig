#/usr/bin/env python
import re
import daqchannel
import utils

class DAQModel(object):
    def __init__(self, name, channels, header):
        self._name = name
        self._channels = channels
        self._header = header
        self._datarate = self.get_datarate_from_header()

    # ===== PROPERTIES =====

    @property
    def name(self):
        return self._name

    @property
    def datarate(self):
        return self._datarate

    @property
    def channels(self):
        return self._channels

    # ===== METHODS ======

    def get_datarate_from_header(self):
        for line in self._header:
            if line.startswith('datarate='):
                m = re.match('datarate=(\d*)', line)
                return int(m.group(1))
        return -1

    def to_ini(self, ini):
        for line in self._header:
            ini.write(line)
        for chan in self.channels:
            chan.to_ini(ini)

    @staticmethod
    def from_ini(name, ini):
        header = []
        channels = []

        # TODO: this assumes that all DQ channels appear at the end of the file.
        #       Is that guaranteed to be the case?
        while True:
            fpos = ini.tell()
            line = ini.readline()
            if not line: break
            if line.endswith('_DQ]\n'):
                ini.seek(fpos)
                break
            header.append(line)

        model = DAQModel(name, [], header)

        while True:
            channel = daqchannel.DAQChannel.from_ini(model, ini)
            if not channel: break
            channels.append(channel)

        model._channels = channels

        return model


if __name__ == '__main__':
    import sys
    import os
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = 'examples/G2SSM.ini'

    with open(filename) as ini:
        dm = DAQModel.from_ini(utils.get_model_name(filename), ini)
    
    for chan in dm.channels:
        print "{c.name}: {c.datarate}Hz, enabled={c.enabled}, acquire={c.acquire}".format(c=chan)

    with open('out.ini', 'wb') as ini:
        dm.to_ini(ini)