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
        # fld_name:  [octet index, bit offset, field width, is zero based count]
        "DID":       [0,  0, 8, False], # device id
        "BID":       [1,  0, 4, False], # bank id
        "ADJCNT":    [1,  4, 4, False], # N/A (subclass 2 only)
        "LID":       [2,  0, 5, False], # lane id
        "PHADJ":     [2,  5, 1, False], # N/A (subclass 2 only)
        "ADJDIR":    [2,  6, 1, False], # N/A (subclass 2 only)
        "L":         [3,  0, 5, True],
        "SCR":       [3,  7, 1, False], # scrambling enable
        "F":         [4,  0, 8, True],
        "K":         [5,  0, 8, True],
        "M":         [6,  0, 8, True],
        "N":         [7,  0, 5, True],
        "CS":        [7,  6, 2, False],
        "NP":        [8,  0, 5, True],
        "SUBCLASSV": [8,  5, 3, False], # device subclass version
        "S":         [9,  0, 5, True],
        "JESDV":     [9,  5, 3, False], # jesd204 version
        "CF":        [10, 0, 5, False],
        "HD":        [10, 7, 1, False],
        "RES1":      [11, 0, 8, False],
        "RES2":      [12, 0, 8, False],
        "FCHK":      [13, 0, 8, False]
    }
    LEN = 14

    def __init__(self, fchk_over_octets=False, **kwargs):
        '''
            Holds all JESD parameter fields in a byte-array according to spec.

            fchk_over_octets:
                true = calc. checksum as sum over all octets (Analog Devices)
                false = sum over all fields (JESD standard)

            kwargs are taken as field names for initialization

            parameters like L, M, K are zero based, add 1 to get the count
        '''
        self.fchk_over_octets = fchk_over_octets
        self.octets = bytearray(JESD204BSettings.LEN)
        self.set_field('JESDV', 1)
        self.set_field('SUBCLASSV', 1)
        for k, v in kwargs.items():
            self.set_field(k, v)

    def calc_fchk(self):
        ''' called on each field value change '''
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

        # compute internal settings
        self.nibbles_per_word = ceil(self.NP // 4)
        self.octets_per_frame = (self.S * self.nibbles_per_word) // 2
        self.octets_per_lane = (self.octets_per_frame * self.M) // self.L
        self.lmfc_cycles = int(self.octets_per_frame * self.K // 4)

    def set_field(self, name, val, encode=True):
#         print('setting:', name, val)
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
        if name != 'FCHK':
            self.calc_fchk()

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

    def __setattr__(self, name, value):
        if name in JESD204BSettings.FIELDS:
            self.set_field(name, value)
        else:
            self.__dict__[name] = value

    def __repr__(self):
        s = "JESD204BSettings(): "
        for o in self.octets:
            s += '{:02x} '.format(o)
        s += '\n'
        for name, _ in sorted(
            JESD204BSettings.FIELDS.items(),
            key=lambda x: x[1][0] * 8 + x[1][1]
        ):
            s += '  {:>16s}: {:3d}\n'.format(name, self.get_field(name))
        return s
