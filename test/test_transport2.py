# This file is Copyright (c) 2016-2019 Florent Kermarrec <florent@enjoy-digital.fr>
# License: BSD

import unittest
import sys
from math import ceil
from random import randint

from migen import *

from litejesd204b.common import *
from litejesd204b.transport import LiteJESD204BTransportTX
from test.model.transport import TransportLayer

sys.path.append('/home/michael/fpga_wsp/litex_test_project/vc707_gt_test/spi')
from ad9174 import Ad9174Settings


def flatten_results(res):
    ''' dont care about frame grouping '''
    for i, ll in enumerate(res):
        res[i] = [item for sublist in ll for item in sublist]
    return res


def hex_str(val):
    return ' '.join('{:02x}'.format(v) for v in val)


class TestTransport(unittest.TestCase):
    def transport_tx_test(self, settings):
        transport = LiteJESD204BTransportTX(settings)

        # generate random test data:  samples[converter][sample]
        input_samples = []
        for m in range(settings.M):
            # input_samples.append([randint(0, 2**settings.N - 1) for _ in range(32)])
            input_samples.append([(0x0A + m << 8) | i for i in range(16)])  # index values

        # Get reference output
        tl = TransportLayer(settings)

        # reference_lanes[lane][octet]
        reference_lanes = flatten_results(tl.encode(input_samples))

        # output_lanes[lane][octet]
        output_lanes = [[] for i in range(settings.L)]

        def generator(dut):
            while len(input_samples[0]) > 0:
                for m, (converter, _) in enumerate(dut.sink.iter_flat()):
                    temp = 0
                    # There might be multiple samples per clock
                    for s in range(len(converter) // settings.N):
                        temp |= (input_samples[m].pop(0)) << (settings.N * s)
                    conv_bytes = temp.to_bytes(len(converter) // 8, 'little')
                    print('conv {:d}: {:}'.format(m, hex_str(conv_bytes)))
                    yield converter.eq(temp)
                yield
                # print()

                for l, (lane, _) in enumerate(dut.source.iter_flat()):
                    lane_data = (yield lane)
                    # Need to split lane_data up into octets
                    lane_bytes = lane_data.to_bytes(len(lane) // 8, 'little')
                    print('lane {:d}: {:}'.format(l, hex_str(lane_bytes)))
                    output_lanes[l].extend(lane_bytes)
                print()

        run_simulation(transport, [generator(transport)])
        return reference_lanes, output_lanes

    def test_transport_tx(self):
        print('--------------------------------')
        print(' JESD transport layer test')
        print('--------------------------------')
        print('Specific to the supported AD9174 JESD modes.')
        print('  `conv X:` data from application fed into LiteJESD204BTransportTX.sink')
        print('  `lane X:` output data going to the link layer')
        print('  data format is LSB first: <octet0> <octet1> etc.')
        print('  data is grouped by clock cycle')
        for m in [*range(13), *range(18, 23)]:
            try:
                settings = Ad9174Settings(m)
            except ValueError:
                print('skipping mode', m)
                continue
            print('\n----------------')
            print(' mode', m)
            print('----------------')
            print(settings)

            reference, output = self.transport_tx_test(settings)
            self.assertEqual(reference, output)
