```
                             __   _ __         _____________  ___  ___  ____ ___
                            / /  (_) /____ __ / / __/ __/ _ \|_  |/ _ \/ / // _ )
                           / /__/ / __/ -_) // / _/_\ \/ // / __// // /_  _/ _  |
                          /____/_/\__/\__/\___/___/___/____/____/\___/ /_//____/

                                     Copyright      2020 / M. Betz
                                     Copyright 2016-2020 / EnjoyDigital
                                     Copyright 2016-2018 / M-Labs Ltd

                            A small footprint and configurable JESD204B core
                                        powered by Migen & LiteX
```

[![](https://travis-ci.com/enjoy-digital/litejesd204b.svg?branch=master)](https://travis-ci.com/enjoy-digital/litejesd204b) ![License](https://img.shields.io/badge/License-BSD%202--Clause-orange.svg)

# Fork
Most changes in this fork are related to how the JESD parameters are handled. I introduced a new [`JESD204BSettings()`](litejesd204b/common.py) class which manages all configurable parameters of this library.

Otherwise the goal is to understand the limitations and make it work with an AD9174 DAC.

__Lessons learned so far__

  * No re-configuration during run-time
  * `F` must be 1, 2 or 4
  * That's because 4 bytes need to be fed into the GTX every cycle (all 12 bit modes of the AD9174 are out)
  * The JREF clock, providing an edge to synchronize multiple devices, must be equal to the LMFC clock divided by an __integer__
  * Being familiar with Litescope, Chipscope or another internal logic analyzer is absolutely necessary for board bring up
  * The GTX PHY needs a reset, __after__ bringing up all external clocks

## Testing
[Results](https://docs.google.com/spreadsheets/d/1F6s6cVM1Lo6IOUgZoq9xm0ueGYkePZFeD96N0-kPR9o/edit?usp=sharing) of JESD modes tested so far on hardware. All 16 bit modes work reliably. Tested at up to 12.8 Gbps lane rate with 8 lanes. There are comments in the `Tested OK` column.

__Hardware used__
  * AD9174-FMC-EBZ
  * VC707
  * External `f_DAC = 5.12 GHz` sample clock

[litex project for testing](https://github.com/yetifrisstlama/litex_test_project/tree/master/vc707_gt_test)

[python worksheet with testing procedure](https://github.com/yetifrisstlama/litex_test_project/blob/master/vc707_gt_test/spi/setup2.ipynb)



[> Intro
--------
LiteJESD204B provides a small footprint and configurable JESD204B core.

LiteJESD204B is part of LiteX libraries whose aims are to lower entry level of
complex FPGA cores by providing simple, elegant and efficient implementations
of components used in today's SoC such as Ethernet, SATA, PCIe, SDRAM Controller...

Using Migen to describe the HDL allows the core to be highly and easily configurable.

LiteJESD204B can be used as LiteX library or can be integrated with your standard
design flow by generating the verilog rtl that you will use as a standard core.

[> Features
-----------
PHY:
 - PRBS7/PRBS15/PRBS31 to check link integrity.
 - 8B/10B encoding
 - 32 bits interface
 - Artix7 support
 - Kintex7 support (CPLL up to 5Gbps, QPLL for higher linerates)
 - Kintex Ultrascale support (CPLL up to 6.25Gbps, QPLL for higher linerates)

Core:
 Link:
  - Scrambling to reduce EMI
  - Special characters insertion
  - CGS/ILAS
 Transport:
  - converters <--> lanes mapping

[> FPGA Proven
---------------
LiteDRAM is already used in commercial and open-source designs:
- ARTIQ: http://m-labs.hk/artiq/index.html
- and others commercial designs...

[> Possible improvements
------------------------
- add support for non scrambled mode
- add support for Altera PHYs
- add support for Lattice PHYs
- ... See below Support and consulting :)

If you want to support these features, please contact us at florent [AT]
enjoy-digital.fr.

[> Getting started
------------------
1. Install Python 3.6+ and FPGA vendor's development tools.
2. Install Migen/LiteX and the LiteX's cores:

```sh
$ wget https://raw.githubusercontent.com/enjoy-digital/litex/master/litex_setup.py
$ chmod +x litex_setup.py
$ ./litex_setup.py init install --user (--user to install to user directory)
```
  Later, if you need to update all repositories:
```sh
$ ./litex_setup.py update
```


3. TODO: add/describe examples

[> Tests
--------
Unit tests are available in ./test/.
To run all the unit tests:
```sh
$ ./setup.py test
```

Tests can also be run individually:
```sh
$ python3 -m unittest test.test_name
```

[> License
----------
LiteJESD204B is released under the very permissive two-clause BSD license. Under
the terms of this license, you are authorized to use LiteJESD204B for closed-source
proprietary designs.
Even though we do not require you to do so, those things are awesome, so please
do them if possible:
 - tell us that you are using LiteJESD204B
 - cite LiteJESD204B in publications related to research it has helped
 - send us feedback and suggestions for improvements
 - send us bug reports when something goes wrong
 - send us the modifications and improvements you have done to LiteJESD204B.

[> Support and consulting
-------------------------
We love open-source hardware and like sharing our designs with others.

LiteJESD204B is developed and maintained by EnjoyDigital.

If you would like to know more about LiteJESD204B or if you are already a happy user
and would like to extend it for your needs, EnjoyDigital can provide standard
commercial support as well as consulting services.

So feel free to contact us, we'd love to work with you! (and eventually shorten
the list of the possible improvements :)

[> Contact
----------
E-mail: florent [AT] enjoy-digital.fr
