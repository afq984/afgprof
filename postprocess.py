#!/usr/bin/env python3

import argparse
import bisect
import functools
import subprocess
import collections
import re
import os
import functools


if False:
    # Show an error message on python 2
    *Please, Use = "Python 3"


mcount_pattern = re.compile(r'LR = ([a-f0-9]+) ; PC = ([a-f0-9]+)')


int16 = functools.partial(int, base=16)


def str16(v):
    return format(v, 'x')


Map = collections.namedtuple(
    'Map',
    ('low_address', 'high_address', 'perms', 'object_name')
)


_map_pattern = re.compile(
    r'(?P<low_address>[\da-f]+)-(?P<high_address>[\da-f]+)\s+'
    r'(?P<perms>[rwxps-]{4})\s+'
    r'[\da-f]+\s+'
    r'[\da-f]{2}:[\da-f]{2}\s+'
    r'\d+\s+'
    r'(?P<object_name>.*)\s*'
)


class MapMismatch(Exception):
    pass


def tomap(line):
    match = _map_pattern.match(line)
    if match is None:
        raise MapMismatch(line)
    group = match.groupdict()
    return Map(
        low_address=int16(group['low_address']),
        high_address=int16(group['high_address']),
        perms=group['perms'],
        object_name=group['object_name']
    )


def address_to_file_offset(maps, address):
    for map_ in maps:
        if map_.low_address <= address < map_.high_address:
            return (map_.object_name, address - map_.low_address)
    return None  # just to explicit


def file_offset_to_function(symbols, file_offset):
    if file_offset is None:
        return '?'
    path, offset = file_offset
    filename = os.path.basename(path)
    if filename in symbols:
        for low, size, name in symbols[filename]:
            if low <= offset < low + size:
                return name
    return '?'


def symbols_from_file(filename='a.out'):
    symbols = []
    with subprocess.Popen(
        ['arm-linux-androideabi-nm', '--print-size', filename],
        stdout=subprocess.PIPE,
        universal_newlines=True
    ) as process:
        for line in process.stdout:
            *range_, type_, name = line.split()
            if len(range_) == 2:
                symbols.append(
                    (int(range_[0], 16), int(range_[1], 16), name)
                )
    return symbols


def main(filename):
    with open(filename) as file:
        assert next(file) == '=== start of monstartup() ===\n'

        maps = []

        for line in file:
            if '=== end of monstartup() ===\n' == line:
                break
            mapline = tomap(line)
            if 'x' in mapline.perms:
                maps.append(mapline)

        calls = []

        for line in file:
            if line == '=== _mcleanup() invoked ===\n':
                break

            lr, pc = map(
                int16,
                mcount_pattern.match(line).groups())

            calls.append((
                address_to_file_offset(maps, lr),
                address_to_file_offset(maps, pc)
            ))
        else:
            assert False

        symbols = {}

        symbols['a.out'] = symbols_from_file('a.out')

        for lrof, pcof in calls:
            print(
                file_offset_to_function(symbols, lrof),
                '->',
                file_offset_to_function(symbols, pcof)
            )



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('filename', default='gmon.out.txt', nargs='?')

    args = parser.parse_args()

    main(**vars(args))
