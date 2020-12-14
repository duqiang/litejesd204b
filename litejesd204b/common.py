#
# This file is part of LiteJESD204B
#
# This file is Copyright (c) 2020 Michael Betz <michibetz@gmail.com>
# This file is Copyright (c) 2016-2019 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause

from math import ceil
import json

# Control characters -------------------------------------------------------------------------------

control_characters = {
    "R": 0b00011100, # K28.0, Start of multi-frame
    "A": 0b01111100, # K28.3, Lane alignment
    "Q": 0b10011100, # K28.4, Start of configuration data
    "K": 0b10111100, # K28.5, Group synchronization
    "F": 0b11111100, # K28.7, Frame alignment
}


class JESD204BSettings():
    ''' Manage all JESD related configuration settings '''
    FIELDS = {
        # fld_name:  [octet index, bit offset, field width, isZeroBased]
        "ADJCNT":    [1,  4, 4, False],  # Number of adjustment resolution steps to adjust DAC LMFC. Subclass 2 only.
        "ADJDIR":    [2,  6, 1, False],  # Direction to adjust DAC LMFC 0: Advance, 1: Delay. Subclass 2 only.
        "BID":       [1,  0, 4, False],  # Bank ID
        "CF":        [10, 0, 5, False],  # No. of control words per frame duration per link
        "CS":        [7,  6, 2, False],  # No. of control bits / sample
        "DID":       [0,  0, 8, False],  # Device ID
        "F":         [4,  0, 8, True ],  # No. of octets / frame
        "HD":        [10, 7, 1, False],  # High density format
        "JESDV":     [9,  5, 3, False],  # Jesd204 version
        "K":         [5,  0, 8, True ],  # No. of frames / multiframe
        "L":         [3,  0, 5, True ],  # No. of lanes
        "LID":       [2,  0, 5, False],  # Lane ID
        "M":         [6,  0, 8, True ],  # No. of converters
        "N":         [7,  0, 5, True ],  # Converter resolution
        "NP":        [8,  0, 5, True ],  # Total no. of bits / sample
        "PHADJ":     [2,  5, 1, False],  # Phase adjustment request to DAC Subclass 2 only
        "S":         [9,  0, 5, True ],  # No. of samples per converter per frame cycle
        "SCR":       [3,  7, 1, False],  # Scrambling enable
        "SUBCLASSV": [8,  5, 3, False],  # Device subclass version
        "RES1":      [11, 0, 8, False],  # Reserved field 1
        "RES2":      [12, 0, 8, False],  # Reserved field 2
        "FCHK":      [13, 0, 8, False]   # Checksum
    }
    LEN = 14

    def __init__(
        self, FCHK_OVER_OCTETS=False, LINK_DW=32, json_file=None, **kwargs
    ):
        '''
            Holds all JESD parameter fields in a byte-array according to spec.

            FCHK_OVER_OCTETS:
                true = calc. checksum as sum over all octets (Analog Devices)
                false = sum over all fields (JESD standard)

            LINK_DW:
                number of bits the transceivers (gtx / gth) put out per clock
                cycle. Without 8b10b encoding.

            kwargs are taken as field names for initialization

            field names can also be get / set as class attributes

            parameters counting items like L, M, K are handled naturally (>= 1)

            json_file:
                .json file to import jesd parameters from.
                If this is given all other init parameters are ignored.
        '''
        self.octets = bytearray(JESD204BSettings.LEN)

        if json_file is not None:
            self.import_constants(json_file)
            return

        self.LINK_DW = LINK_DW
        self.FR_CLK = None
        self.FCHK_OVER_OCTETS = FCHK_OVER_OCTETS
        self.set_field('SCR', 1)
        self.set_field('JESDV', 1)
        self.set_field('SUBCLASSV', 1)
        for k, v in kwargs.items():
            self.set_field(k, v)
        # self.calc_fchk()

    def calc_fchk(self):
        ''' needs to be called manually after all values have been set '''
        if self.FCHK_OVER_OCTETS:
            val = sum(self.octets[:11])
        else:
            # The checksum shall be calculated based on the 21 fields (not
            # including the FCHK field) contained within the link configuration
            # octets, and all bits not belonging to one of the 21 fields shall
            # be ignored when calculating the checksum.
            val = 0
            for name in JESD204BSettings.FIELDS:
                if name == 'FCHK':
                    continue
                val += self.get_field(name)
        self.set_field('FCHK', val & 0xFF)

        # --------------------
        #  Sanity checks
        # --------------------
        F_temp = (self.M * self.S * self.NP) / 8 / self.L
        if self.F != F_temp:
            print(self)
            raise ValueError('F = {} is inconsistent! Should be {}'.format(
                self.F, F_temp
            ))
        if self.F not in (1, 2, 4):
            raise ValueError('Only F = 1, 2 or 4 is supported right now')

        # How many jesd frames are processed in one clock cycle
        self.FR_CLK = self.LINK_DW // 8 // self.F

    def set_field(self, name, val, encode=True):
        # print('setting:', name, val)
        index, offset, width, is_zb = JESD204BSettings.FIELDS[name]
        if encode and is_zb:
            val -= 1
        if val >= 2**width:
            raise ValueError(
                'value {:x} for {:s} is larger than {:d} bits'.format(
                    val, name, width
                )
            )
        mask = (2**width - 1) << offset
        self.octets[index] &= ~mask
        self.octets[index] |= val << offset

    def get_field(self, name, decode=True):
        ''' decode: when true return actual 1 based count values '''
        index, offset, width, is_zb = JESD204BSettings.FIELDS[name]
        val = (self.octets[index] >> offset) & (2**width - 1)
        if decode and is_zb:
            val += 1
        return val

    def get_dsp_layout(self):
        cw = self.FR_CLK * self.S * self.N
        return [("converter" + str(m), cw) for m in range(self.M)]

    def __getattr__(self, name):
        if name in JESD204BSettings.FIELDS:
            return self.get_field(name)
        raise AttributeError

    def __setattr__(self, name, value):
        if name in JESD204BSettings.FIELDS:
            self.set_field(name, value)
        else:
            self.__dict__[name] = value

    def __repr__(self):
        s = "JESD204BSettings(): "
        for o in self.octets:
            s += '{:02x} '.format(o)
        s += '\n  '
        for i, (name, _) in enumerate(sorted(
            JESD204BSettings.FIELDS.items(),
            key=lambda x: x[1][0] * 8 + x[1][1]
        )):
            s += '{:>10s}: {:3d} '.format(name, self.get_field(name))
            if ((i + 1) % 4) == 0:
                s += '\n  '
        s += '\n  {:>10s}: {:3d} '.format('[ LINK_DW', self.LINK_DW)
        s += '{:>10s}: {:3d} ]'.format('FR_CLK', self.FR_CLK)
        return s

    def export_constants(self, soc):
        '''
        export all settings as litex constants, which will be written to
        csr.csv / csr.json
        '''
        for name in JESD204BSettings.FIELDS:
            val = self.get_field(name)
            soc.add_constant('JESD_{:}'.format(name), val)

        soc.add_constant('JESD_FCHK_OVER_OCTETS', self.FCHK_OVER_OCTETS)
        soc.add_constant('JESD_LINK_DW', self.LINK_DW)
        soc.add_constant('JESD_FR_CLK', self.FR_CLK)

    def import_constants(self, json_file):
        ''' quick and dirty! assumes all class parameters are upper case '''
        with open(json_file, 'r') as f:
            j = json.load(f)
        for con, val in j['constants'].items():
            if not con.startswith('jesd_'):
                    continue
            par_name = con[5:].upper()
            # print('jesd_import', par_name, val)
            setattr(self, par_name, val)

        # re-calculate the checksum, hopefully it does not change
        import_chk = self.FCHK
        self.calc_fchk()
        if import_chk != self.FCHK:
            raise RuntimeError('imported FCHK does not match calculated one')
