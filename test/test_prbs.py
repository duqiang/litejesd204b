#!/usr/bin/env python3
from litex.gen import *

from litejesd204b.phy.prbs import PRBS7Generator
from litejesd204b.phy.prbs import PRBS15Generator
from litejesd204b.phy.prbs import PRBS31Generator

from model.phy import PRBS


def main_generator(dut, prbs, dw, cycles=1024):
    errors = 0
    yield
    for i in range(cycles):
        if (yield dut.o) != prbs.getbits(dw):
            errors += 1
        yield
    print("errors: {:d}".format(errors))


if __name__ == "__main__":
    duts = {
        "prbs7":  PRBS7Generator(8),
        "prbs15": PRBS15Generator(16),
        "prbs31": PRBS31Generator(32)
    }
    models = {
        "prbs7":  PRBS(n_state=7,  taps=[5, 6]),
        "prbs15": PRBS(n_state=15, taps=[13, 14]),
        "prbs31": PRBS(n_state=31, taps=[27, 30])
    }
    for test in ["prbs7", "prbs15", "prbs31"]:
        print(test)
        dut = duts[test]
        model = models[test]
        generators = {"sys" :   [main_generator(dut, model, len(dut.o))]}
        clocks = {"sys": 10}
        run_simulation(dut, generators, clocks)
