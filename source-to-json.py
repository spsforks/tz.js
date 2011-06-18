#!/usr/bin/python

# L. David Baron <dbaron@dbaron.org>, June 2011

# This work is available under the CC0 Public Domain Dedication:
# http://creativecommons.org/publicdomain/zero/1.0/
# To the extent possible under law, L. David Baron has waived all
# copyright and related or neighboring rights to the tz.js library,
# including the JavaScript code and the tools used to generate it.  This
# work is published from the United States of America.

# This script is intended to convert the source time zone data from the
# Olson time zone database (http://www.twinsun.com/tz/tz-link.htm), that
# is, the tzdata* data, into a JSON format suitable for inclusion in the
# tz.js JavaScript library.

# It is not yet anywhere near complete, but at some point in the future
# I would like to replace the current data (generated by
# compiled-to-json.py) with a more compact data format generated here.

from optparse import OptionParser
import os.path
import re
import tarfile

op = OptionParser()
(options, args) = op.parse_args()

if len(args) == 1:
    tzdatatar = args[0]
else:
    op.error("expected a single argument (the tzdata archive)")

tzversion = re.match('tzdata(.*)\.tar\.gz$', os.path.basename(tzdatatar))
if tzversion is None:
    raise StandardError("argument must be tzdata archive")
tzversion = tzversion.groups()[0]
print "/* Time zone data version " + tzversion + ". */"

def read_lines():
    tar = tarfile.open(name=tzdatatar, mode="r:*")
    members_of_tar = {
        # We use only these members of the tar file and ignore the rest,
        # since they have information we don't want.
        "africa": True,
        "antarctica": True,
        "asia": True,
        "australasia": True,
        "europe": True,
        "northamerica": True,
        "southamerica": True
    }
    for tarinfo in tar:
        if not tarinfo.isfile() or not tarinfo.name in members_of_tar:
            continue
        # FIXME: Should set encoding on this |io| to iso-8859-1.
        io = tar.extractfile(tarinfo)
        while True:
            line = io.readline()
            if line is "":
                break
            line = line.rstrip("\n")
            line = line.partition("#")[0]
            line = line.rstrip(" \t")
            if line is "":
                continue
            yield line
        io.close()
    tar.close()

zones = {}
rules = {}

def process_time(s):
    if s == '-':
        return 0
    negate = 1
    if s[0] == '-':
        negate = -1
        s = s[1:]
    # FIXME: Do a little more validation on these integers?
    words = map(int, s.split(":"))
    value = words[0] * 3600
    if len(words) > 1:
        value = value + words[1] * 60
        if len(words) > 2:
            value = value + words[2]
            if len(words) > 3:
                raise StandardError("unexpected time " + s)
    return value * negate

def handle_zone_line(words):
    (gmtoff, rules, fmt) = words[0:3]
    until = " ".join(words[3:])
    # FIXME: process the "until" instead -- it's in LOCAL time unless suffixed
    return { "o": process_time(gmtoff), "r": rules, "f": fmt, "u": until }

ws_re = re.compile("[ \t]+")
current_zone = None
for line in read_lines():
    # For documentation, see zic(8), which is included in the tzcode*
    # distribution.
    words = ws_re.split(line)
    if words[0] == '':
        # FIXME: Check appending consistency with UNTIL value
        if current_zone is None:
           raise StandardError("continuation line when not in Zone")
        current_zone.append(handle_zone_line(words[1:]))
    elif words[0] == 'Zone':
        # FIXME: Check appending consistency with UNTIL value
        current_zone = []
        current_zone.append(handle_zone_line(words[2:]))
        name = words[1]
        if name in zones:
            raise StandardError("duplicate zone " + name)
        zones[name] = current_zone
    elif words[0] == 'Rule':
        current_zone = None
        (name_, from_, to_, type_, in_, on_, at_, save_, letter_) = words[1:]
        rule = rules.setdefault(name_, [])
        rule.append(words[2:])
    elif words[0] == 'Link':
        current_zone = None
        # ignore
    else:
        raise StandardError("unexpected line " + " ".join(words))

print zones
print rules