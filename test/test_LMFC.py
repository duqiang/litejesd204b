from migen import *
from litejesd204b.core import LMFC
from litejesd204b.common import JESD204BSettings

s = JESD204BSettings(
    S=1,
    K=32
)
s.FR_CLK = 2

dut = LMFC(s, 5)

def gen(dut):
    yield dut.load.eq(16)
    for i in range(3):
        yield
    for j in range(3):
        yield dut.jref.eq(1)
        for i in range(8):
            yield
        yield dut.jref.eq(0)
        for i in range(8):
            yield

run_simulation(dut, gen(dut), vcd_name='out.vcd')
