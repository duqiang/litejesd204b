# This file is Copyright (c) 2020 Michael Betz <michibetz@gmail.com>
# This file is Copyright (c) 2016-2019 Florent Kermarrec <florent@enjoy-digital.fr>
# License: BSD

from math import ceil

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
        self, fchk_over_octets=False, link_data_width=32, **kwargs
    ):
        '''
            Holds all JESD parameter fields in a byte-array according to spec.

            fchk_over_octets:
                true = calc. checksum as sum over all octets (Analog Devices)
                false = sum over all fields (JESD standard)

            link_data_width:
                number of bits the transceivers (gtx / gth) put out per clock
                cycle. Without 8b10b encoding.

            kwargs are taken as field names for initialization

            field names can also be get / set as class attributes

            parameters counting items like L, M, K are handled naturally (>= 1)
        '''
        self.link_data_width = link_data_width
        self.frames_per_clock = None
        self.fchk_over_octets = fchk_over_octets
        self.octets = bytearray(JESD204BSettings.LEN)
        self.set_field('SCR', 1)
        self.set_field('JESDV', 1)
        self.set_field('SUBCLASSV', 1)
        for k, v in kwargs.items():
            self.set_field(k, v)
        self.calc_fchk()

    def calc_fchk(self):
        ''' needs to be called manually after all values have been set '''
        if self.fchk_over_octets:
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
        self.frames_per_clock = self.link_data_width // 8 // self.F

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
        s += '\n  {:>10s}: {:3d} '.format('[ LINK DW', self.link_data_width)
        s += '{:>10s}: {:3d} ]'.format('FR / CLK', self.frames_per_clock)
        return s
