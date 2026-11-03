#!/usr/bin/env python3
# RCU dizisi aticisi — ARM penceresi 3000ms: 14 frame sik zamanlamayla gider.
# ir.py'nin 'seq' modu cok yavas (frame basina ~0.65sn) -> 3sn penceresine sigmaz.
# Kullanim:
#   python3 rcu_atess.py "WORD1,WORD2,..."   (rcu_hesap.py ciktisini oldugu gibi ver)
#   python3 rcu_atess.py --test              # tek frame + P (LED TV'ye tutmadan Guvenli test)
import os, sys, time, termios, select

PORT = '/dev/cu.usbmodem1101'

def ac():
    fd = os.open(PORT, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    a = termios.tcgetattr(fd)
    a[0]=0; a[1]=0; a[2]=termios.CS8|termios.CLOCAL|termios.CREAD; a[3]=0
    a[4]=termios.B115200; a[5]=termios.B115200
    termios.tcsetattr(fd, termios.TCSANOW, a)
    return fd

def bekle(fd, token, timeout):
    """Token'i iceren satir gelene kadar oku; hepsini dondur."""
    buf = b''; t0 = time.time()
    while time.time() - t0 < timeout:
        r,_,_ = select.select([fd],[],[],0.02)
        if r:
            try: buf += os.read(fd, 256)
            except BlockingIOError: pass
            if token in buf:
                return buf.decode(errors='replace').strip()
    return (buf.decode(errors='replace').strip() or "(zaman asimi)")

def gonder(fd, word, timeout=0.45):
    t0 = time.time()
    os.write(fd, ('S %08X\n' % word).encode())
    yanit = bekle(fd, b'SENT-OK', timeout)
    dt = (time.time() - t0) * 1000
    return yanit, dt

fd = ac()
print("ACILIS:", bekle(fd, b'IR-READY', 6.0))

if '--test' in sys.argv:
    os.write(fd, b'P\n'); print("P   :", bekle(fd, b'PONG', 1.0))
    y, dt = gonder(fd, 0xAB54CD32)
    print("TEST:", y, "%.0fms" % dt)
    os.write(fd, b'P\n'); print("P   :", bekle(fd, b'PONG', 1.0))
    os.close(fd); sys.exit(0)

words = [int(w, 16) for w in sys.argv[1].split(',')]
toplam = time.time()
for i, w in enumerate(words):
    y, dt = gonder(fd, w)
    etiket = "ARM " if i == 0 else "D%02d " % i
    print("%s %08X  %.0fms  %s" % (etiket, w, dt, y.replace('\n', ' | ')))
print("TOPLAM: %.2f sn (pencere 3.0 sn)" % (time.time() - toplam))
os.write(fd, b'P\n'); print("SON P:", bekle(fd, b'PONG', 1.0))
os.close(fd)
