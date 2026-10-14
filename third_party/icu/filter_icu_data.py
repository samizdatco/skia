#!/usr/bin/env python

'''
Write a copy of an ICU common data package (icudtl.dat) that keeps only the items
skunicode can load, laid out the way `icupkg -r` writes it.
'''

import fnmatch
import struct
import sys

KEEP = [
  'brkitr/*',          # break rules, dictionaries, and their locale bundles
  'nfkc.nrm',          # required by the CJK dictionary engine
  'uemoji.icu',        # emoji properties
  'keyTypeData.res',   # resolves `-u-` keywords in locale tags
  'timezoneTypes.res', # referenced by keyTypeData's type map
]
DROP = [
  'brkitr/jaml.res',      # Skia disables ML phrase breaking
  'brkitr/res_index.res', # only serves locale enumeration
  'brkitr/sent*.brk',     # no Skia module requests sentence breaks
]


def main(src, dst):
  with open(src, 'rb') as f:
    data = f.read()
  if data[12:16] != b'CmnD' or data[8] != 0:
    sys.exit('%s is not a little-endian ICU common data package' % src)

  toc = struct.unpack_from('<H', data, 0)[0]
  count = struct.unpack_from('<I', data, toc)[0]
  entries = [struct.unpack_from('<II', data, toc + 4 + 8 * i) for i in range(count)]

  def matches(name, patterns):
    name = name.decode('ascii').split('/', 1)[1]
    return any(fnmatch.fnmatchcase(name, p) for p in patterns)

  def name(i):
    start = toc + entries[i][0]
    return data[start:data.index(b'\0', start)]

  def item(i):
    end = toc + entries[i + 1][1] if i + 1 < count else len(data)
    return data[toc + entries[i][1]:end]

  kept = [i for i in range(count) if matches(name(i), KEEP) and not matches(name(i), DROP)]
  names = b''.join(name(i) + b'\0' for i in kept)
  name_offset = 4 + 8 * len(kept)
  padding = -(name_offset + len(names)) % 16
  data_offset = name_offset + len(names) + padding

  out = [data[:toc], struct.pack('<I', len(kept))]
  for i in kept:
    out.append(struct.pack('<II', name_offset, data_offset))
    name_offset += len(name(i)) + 1
    data_offset += len(item(i))
  out += [names, b'\xaa' * padding] + [item(i) for i in kept]

  with open(dst, 'wb') as f:
    f.write(b''.join(out))


if __name__ == '__main__':
  main(*sys.argv[1:])
