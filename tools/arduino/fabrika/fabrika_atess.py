#!/usr/bin/env python3
# fabrika.ino atis scripti — kos fazi (3 Kas 2026)
# Kullanim:
#   python3 fabrika_atess.py P                  # ping
#   python3 fabrika_atess.py H F2F0D0           # tek kelime (2 frame)
#   python3 fabrika_atess.py ARM                # ARM Aday-A (A0A5F5) tek frame... yok, 2 frame
#   python3 fabrika_atess.py ARMB               # ARM Aday-B (50AAF5)
#   python3 fabrika_atiss.py DIZI A|B           # ARM + 13 hane patlamasi (moda gore)
#   python3 fabrika_atess.py DENE A|B           # ARM + 13 hane, her hane sonrasi HARMLESS (0x3C Info) ayirici
#                                              # — 0x01 dedupe calismasini gormek icin
import os, sys, time, termios, select

PORT = '/dev/cu.usbmodem11101'

def ac():
    fd = os.open(PORT, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    a = termios.tcgetattr(fd)
    a[0]=0; a[1]=0; a[2]=termios.CS8|termios.CLOCAL|termios.CREAD; a[3]=0
    a[4]=termios.B115200; a[5]=termios.B115200
    termios.tcsetattr(fd, termios.TCSANOW, a)
    return fd

def bekle(fd, token, timeout):
    buf = b''; t0 = time.time()
    while time.time() - t0 < timeout:
        r,_,_ = select.select([fd],[],[],0.02)
        if r:
            try: buf += os.read(fd, 256)
            except BlockingIOError: pass
            if token in buf:
                return buf.decode(errors='replace').strip()
    return (buf.decode(errors='replace').strip() or "(zaman asimi)")

def satir(fd, cmd, token, timeout=3.0):
    t0 = time.time()
    os.write(fd, (cmd + '\n').encode())
    yanit = bekle(fd, token, timeout)
    return yanit, (time.time() - t0) * 1000

# ---- 13 hane uretici (YENI 24-bit format) ----
def crc16_ccitt_false(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if (crc & 0x8000) else (crc << 1)
            crc &= 0xFFFF
    return crc

def coz_kuyruk(bas: bytes) -> bytes:
    for i in range(0x10000):
        tail = bytes([i >> 8, i & 0xFF])
        if crc16_ccitt_false(bas + tail) == 0:
            return tail
    raise RuntimeError("CRC cozumu yok")

def bitrev8(v): return int('{:08b}'.format(v & 0xFF)[::-1], 2)
def bitrev4(v): return int('{:04b}'.format(v & 0xF)[::-1], 2)

def kelime(addr4, cmd8):
    return (addr4 << 20) | (cmd8 << 12) | ((addr4 ^ 0xF) << 8) | (cmd8 ^ 0xFF)

MAC_IP = "192.168.1.30"; PORT_NUM = 40000; RANDOM = 0x5678; FREE = 0x00

def dizi_uret(mod):
    octetler = [int(x) for x in MAC_IP.split(".")]
    parca = [0x01, 0x0C] + octetler + [(PORT_NUM >> 8) & 0xFF, PORT_NUM & 0xFF,
             (RANDOM >> 8) & 0xFF, RANDOM & 0xFF, FREE]
    kuyruk = coz_kuyruk(bytes(parca[1:11]))
    haneler = parca + list(kuyruk)
    assert len(haneler) == 13
    arm_addr = 0xA if mod == 'A' else 0x5           # custom=5: A: bitrev4(0xA)=5, B: kendisi=5
    hane_addr = 0xB if mod == 'A' else 0xD          # custom=0xD: A: bitrev4(0xB)=D, B: kendisi=D
    frameler = [kelime(arm_addr, 0x0A)]             # ARM: CMD=0x0A -> bitrev8=0x50 ('P')
    for h in haneler:
        frameler.append(kelime(hane_addr, bitrev8(h)))
    return frameler, haneler

ARM_A = 0xA0A5F5; ARM_B = 0x50AAF5

fd = ac()
print("ACILIS:", bekle(fd, b'FABRIKA-READY', 6.0))

komut = sys.argv[1].upper() if len(sys.argv) > 1 else 'P'

if komut == 'P':
    print("P  :", bekle(fd, b'PONG', 1.0))
elif komut == 'H':
    w = sys.argv[2].upper()
    print("H %s:" % w, satir(fd, 'H ' + w, b'SENT-OK'))
elif komut == 'ARM':
    print("ARM-A:", satir(fd, 'H A0A5F5', b'SENT-OK'))
elif komut == 'ARMB':
    print("ARM-B:", satir(fd, 'H 50AAF5', b'SENT-OK'))
elif komut in ('DIZI', 'DENE'):
    mod = sys.argv[2].upper() if len(sys.argv) > 2 else 'A'
    frameler, haneler = dizi_uret(mod)
    print("Mod %s | haneler: %s" % (mod, " ".join("%02X" % h for h in haneler)))
    print("CRC: %s" % hex(crc16_ccitt_false(bytes(haneler[1:13]))))
    print("Kelimeler:", ",".join("%06X" % f for f in frameler))
    if komut == 'DENE':
        # hane bazli: her hane G ile + tekrar eden deger oncesi Info (0x3C, ADDR=F) ayirici
        toplam = time.time()
        arm_addr = 0xA if mod == 'A' else 0x5
        print("ARM :", satir(fd, 'G %06X' % kelime(arm_addr, 0x0A), b'SENT-OK'))
        gecen = set()
        for i, h in enumerate(haneler):
            if h in gecen:
                print("  ayirici (Info 0xF3C0C3) ...", satir(fd, 'G F3C0C3', b'SENT-OK'))
            gecen.add(h)
            y, dt = satir(fd, 'G %06X' % kelime(0xB if mod=='A' else 0xD, bitrev8(h)), b'SENT-OK')
            print("  D%02d %02X %.0fms %s" % (i, h, dt, y.replace('\n',' | ')))
        print("TOPLAM: %.2f sn" % (time.time() - toplam))
    else:
        # ARM + toplu patlama
        bulk = ",".join("%06X" % f for f in frameler[1:])
        toplam = time.time()
        print("ARM :", satir(fd, 'G %06X' % frameler[0], b'SENT-OK'))
        print("BULK:", satir(fd, 'B ' + bulk, b'BULK-OK', 8.0))
        print("TOPLAM: %.2f sn" % (time.time() - toplam))
os.close(fd)
