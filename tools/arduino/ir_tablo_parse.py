import struct
d = open('../data/ir_table.bin','rb').read()
hdr = struct.unpack_from('<II', d, 0)
n = hdr[0]
bilinen = {0x73:'VOL+',0x72:'VOL-',0x71:'MUTE',0x66:'HOME',0x1c:'ENTER'}
for i in range(n):
    off = 8 + i*8
    t, kc, r1, r2 = struct.unpack_from('<HHHH', d, off)
    tag = bilinen.get(kc, '')
    print("%3d t=%04x kc=%04x raw=%08x [%s] %s" % (i, t, kc, (r2<<16)|r1, d[off+4:off+8].hex(), tag))
