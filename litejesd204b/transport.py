# This file is Copyright (c) 2016-2019 Florent Kermarrec <florent@enjoy-digital.fr>
# License: BSD

from math import ceil

from migen import *


def seed_to_data(seed, random=True):
    return ((seed + 1)*0x31415979 + 1) & 0xffff if random else seed


class LiteJESD204BTransportTX(Module):
    def __init__(self, jesd_settings):
        """Transport TX layer
        inputs:
        - jesd_settings:        JESD204B settings
        cf section 5.1.3
        """
        samples_per_clock = jesd_settings.S * jesd_settings.FR_CLK

        # width of the application layer interface providing the sample data
        # for one converter
        converter_data_width = jesd_settings.N * samples_per_clock

        # Endpoints
        self.sink = Record([("converter"+str(i), converter_data_width)
            for i in range(jesd_settings.M)])
        self.source = Record([("lane"+str(i), jesd_settings.LINK_DW)
            for i in range(jesd_settings.L)])

        # # #

        current_sample = 0
        current_octet  = 0
        nibbles_per_word = ceil(jesd_settings.NP / 4)  # 1 word = 1 sample
        while current_sample < samples_per_clock:
            # Frame's samples
            frame_samples = []
            for j in range(jesd_settings.M):
                for i in range(jesd_settings.S):
                    converter_data = getattr(self.sink, "converter"+str(j))
                    sample = Signal(jesd_settings.N)
                    self.comb += sample.eq(
                        converter_data[(current_sample+i)*jesd_settings.N:
                        (current_sample+i+1)*jesd_settings.N])
                    frame_samples.append(sample)

            # Frame's words
            frame_words = frame_samples  # no control bits

            # Frame's nibbles
            frame_nibbles = []
            for word in frame_words:
                for i in reversed(range(nibbles_per_word)):
                    nibble = Signal(4)
                    self.comb += nibble.eq(word[4*i:4*(i+1)])
                    frame_nibbles.append(nibble)

            # Frame's octets
            frame_octets = []
            for i in range(len(frame_nibbles)//2):
                octet = Signal(8)
                self.comb += octet.eq(Cat(frame_nibbles[2*i+1],
                                          frame_nibbles[2*i]))
                frame_octets.append(octet)

            # Lanes' octets for a frame
            for i in range(jesd_settings.L):
                frame_lane_octets = frame_octets[
                    i * jesd_settings.F:
                    (i+1)*jesd_settings.F]
                lane_data = getattr(self.source, "lane"+str(i))
                for j, octet in enumerate(frame_lane_octets):
                    self.comb += lane_data[
                        8*(current_octet+j):
                        8*(current_octet+j+1)].eq(octet)

            current_sample += jesd_settings.S
            current_octet += jesd_settings.F

# Transport RX -------------------------------------------------------------------------------------

class LiteJESD204BTransportRX(Module):
    """Transport RX layer
    inputs:
    - jesd_settings:        JESD204BSettings object
    cf section 5.1.3
    """
    def __init__(self, jesd_settings):
        # Compute parameters
        samples_per_clock = jesd_settings.S * jesd_settings.FR_CLK
        converter_data_width = jesd_settings.N * samples_per_clock

        # Endpoints
        self.sink = Record([("lane"+str(i), jesd_settings.LINK_DW)
            for i in range(jesd_settings.L)])
        self.source = Record([("converter"+str(i), converter_data_width)
            for i in range(jesd_settings.M)])

        # # #

        current_sample = 0
        current_octet = 0
        nibbles_per_word = ceil(jesd_settings.NP / 4)  # 1 word = 1 sample
        while current_sample < samples_per_clock:
            # Frame's octets
            frame_octets = []
            for i in range(jesd_settings.L):
                frame_lane_octets = []
                lane_data = getattr(self.sink, "lane"+str(i))
                for j in range(jesd_settings.F):
                    frame_lane_octets.append(lane_data[
                        8*(current_octet+j):
                        8*(current_octet+j+1)])
                frame_octets += frame_lane_octets

            # Frame's nibbles
            frame_nibbles = []
            for octet in frame_octets:
                for j in reversed(range(2)):
                    frame_nibbles.append(octet[4*j:4*(j+1)])

            # Frame's words
            frame_words = []
            for j in range(jesd_settings.M):
                for i in range(jesd_settings.S):
                    word = Signal(nibbles_per_word*4)
                    for k in range(nibbles_per_word):
                        self.comb += word[4*k:4*(k+1)].eq(frame_nibbles.pop())
                    frame_words.append(word)

            # Frame's samples
            frame_samples = frame_words # no control bits

            # Converters' samples for a frame
            for j in range(jesd_settings.M):
                for i in range(jesd_settings.S):
                    converter_data = getattr(self.source, "converter"+str(j))
                    self.comb += converter_data[
                        (current_sample+i)*jesd_settings.N:
                        (current_sample+i+1)*jesd_settings.N].eq(frame_samples.pop())

            current_sample += jesd_settings.S
            current_octet  += jesd_settings.F

# STPL Generator (TX) ------------------------------------------------------------------------------

class LiteJESD204BSTPLGenerator(Module):
    """Simple Transport Layer Pattern Generator
    cf section 5.1.6.2
    """
    def __init__(self, jesd_settings, random=True):
        samples_per_clock = jesd_settings.S * jesd_settings.FR_CLK
        converter_data_width = jesd_settings.N * samples_per_clock

        self.source = Record([("converter"+str(i), converter_data_width)
            for i in range(jesd_settings.M)])
        self.errors = Signal(32) # unused

        # # #

        for i in range(jesd_settings.M):
            converter = getattr(self.source, "converter"+str(i))
            for j in range(samples_per_clock):
                data = seed_to_data((i << 8) | j%jesd_settings.S, random)
                self.comb += converter[j*jesd_settings.N:
                                       (j+1)*jesd_settings.N].eq(data)

# STPL Checker (RX) --------------------------------------------------------------------------------

class LiteJESD204BSTPLChecker(Module):
    """Simple Transport Layer Pattern Checker
    cf section 5.1.6.2
    """
    def __init__(self, jesd_settings, random=True):
        samples_per_clock = jesd_settings.S * jesd_settings.FR_CLK
        converter_data_width = jesd_settings.N * samples_per_clock

        self.sink = Record([("converter"+str(i), converter_data_width)
            for i in range(jesd_settings.M)])
        self.errors = Signal(32)

        # # #

        for i in range(jesd_settings.M):
            converter = getattr(self.sink, "converter"+str(i))
            for j in range(samples_per_clock):
                data = seed_to_data((i << 8) | j%jesd_settings.S, random)
                self.sync += [
                    If(converter[j*jesd_settings.N:(j+1)*jesd_settings.N] != data,
                        self.errors.eq(self.errors + 1)
                    )
                ]
