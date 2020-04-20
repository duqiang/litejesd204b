from migen import *

from litejesd204b.common import *
from litejesd204b.phy.gtx import GTXTransmitter
from litejesd204b.phy.gth import GTHTransmitter

from litex.soc.interconnect import stream
from litex.soc.interconnect.csr import *


class JESD204BPhyTX(Module, AutoCSR):
    def __init__(self, pll, tx_pads, sys_clk_freq, transceiver="gtx", **kwargs):
        self.sink = sink = stream.Endpoint([("data", 32), ("ctrl", 4)])

        # self.data = Signal(32)
        # self.ctrl = Signal(32//8)

        # # #

        transmitters = {
            "gtx": GTXTransmitter,
            "gth": GTHTransmitter
        }
        self.submodules.transmitter = transmitters[transceiver](
            pll=pll,
            tx_pads=tx_pads,
            sys_clk_freq=sys_clk_freq,
            **kwargs
        )
        for i in range(32//8):
            self.comb += [
                self.transmitter.encoder.d[i].eq(sink.data[8*i:8*(i+1)]),
                self.transmitter.encoder.k[i].eq(sink.ctrl[i])
            ]
