import unittest
from math import ceil

from migen import *

from litejesd204b.common import *
from litejesd204b.transport import LiteJESD204BTransportTX, LiteJESD204BTransportRX

from test.model.transport import samples_to_lanes, lanes_to_samples


class TestTransport(unittest.TestCase):
    def transport_tx_test(self, nlanes, nconverters, converter_data_width):
        ps = JESD204BPhysicalSettings(l=nlanes, m=nconverters, n=16, np=16)
        ts = JESD204BTransportSettings(f=2, s=1, k=16, cs=1)
        jesd_settings = JESD204BSettings(ps, ts, did=0x5a, bid=0x5)

        transport = LiteJESD204BTransportTX(jesd_settings,
                                            converter_data_width)

        input_samples = [[j+i*256 for j in range(16)]
            for i in range(nconverters)]
        reference_lanes = samples_to_lanes(samples_per_frame=1,
                                           nlanes=nlanes,
                                           nconverters=nconverters,
                                           nbits=16,
                                           samples=input_samples)

        output_lanes = [[] for i in range(nlanes)]

        octets_per_lane = jesd_settings.octets_per_lane
        lane_data_width = len(transport.source.lane0)

        def generator(dut):
            for i in range(5):
                if i < 4:
                    for c in range(nconverters):
                        converter_data = getattr(dut.sink, "converter"+str(c))
                        for j in range(nconverters):
                            yield converter_data[16*j:16*(j+1)].eq(input_samples[c][4*i+j])
                if i > 0:
                    for l in range(nlanes):
                        lane_data = (yield getattr(dut.source, "lane"+str(l)))
                        for f in range(lane_data_width//(octets_per_lane*8)):
                            frame = [(lane_data >> (f*8*octets_per_lane)+8*i) & 0xff
                                for i in range(octets_per_lane)]
                            output_lanes[l].append(frame)
                yield

        run_simulation(transport, generator(transport))
        return reference_lanes, output_lanes

    def test_transport_tx(self):
        for nlanes in [1, 2, 4, 8]:
            reference, output = self.transport_tx_test(nlanes, 4, 64)
            self.assertEqual(reference, output)

    def transport_loopback_test(self, nlanes, nconverters, converter_data_width):
        ps = JESD204BPhysicalSettings(l=nlanes, m=nconverters, n=16, np=16)
        ts = JESD204BTransportSettings(f=2, s=1, k=16, cs=1)
        jesd_settings = JESD204BSettings(ps, ts, did=0x5a, bid=0x5)

        class DUT(Module):
            def __init__(self):
                transport_tx = LiteJESD204BTransportTX(jesd_settings, converter_data_width)
                transport_rx = LiteJESD204BTransportRX(jesd_settings, converter_data_width)
                self.comb += transport_rx.sink.eq(transport_tx.source)
                self.submodules += transport_tx, transport_rx
                self.sink, self.source = transport_tx.sink, transport_rx.source

        dut = DUT()
        input_samples  = [[j+i*256 for j in range(16)] for i in range(nconverters)]
        output_samples = [[] for i in range(nconverters)]

        def generator(dut):
            for i in range(5):
                if i < 4:
                    for c in range(nconverters):
                        converter_data = getattr(dut.sink, "converter"+str(c))
                        for j in range(nconverters):
                            yield converter_data[16*j:16*(j+1)].eq(input_samples[c][4*i+j])
                if i > 0:
                    for c in range(nconverters):
                        converter_data = (yield getattr(dut.source, "converter"+str(c)))
                        for j in range(nconverters):
                            sample = (converter_data >> 16*j) & 0xffff
                            output_samples[c].append(sample)
                yield

        run_simulation(dut, generator(dut))
        return input_samples, output_samples

    def test_transport_loopback(self):
        for nlanes in [1, 2, 4, 8]:
            reference, output = self.transport_loopback_test(nlanes, 4, 64)
            self.assertEqual(reference, output)
