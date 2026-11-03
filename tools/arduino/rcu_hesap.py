# !!! DİKKAT — YAYIN NOTU !!!
# Bu araç proje sırasında yazıldı; coz_kuyruk() (CRC16-CCITT-FALSE tail çözümü) ve
# haneler_uret() şablonu DOĞRUDUR. Ancak içindeki 32-bit "kelime kurulumu" (hedef_word)
# bu TV'nin GERÇEK kernel formatına göre ESKİ varsayıma dayanır — gerçek format için
# docs/04-kok-fazi-kernel-kanitlari.md içindeki w19 dönüşümünü kullanın.
# Ayrıca gerçek cihazda bu dizinin GÖNDERİLEMEMESİnin nedeni (tablo keycode kısıtı)
# aynı dokümanda kanıtlıdır: bu betik yalnızca matematiğin doğru olduğunu gösterir.
#!/usr/bin/env python3
# RCU p2p dizisi hesaplayici — check_p2p_debug_ir_cmd tam RE'ye dayanir (29 Eki)
#
# Daemon mantigi (kanitli, r2):
#   ARM   : cmd=5, arg=0x50            -> 3000ms user_timer baslar, tampon sifirlanir
#   DIGIT : cmd=0xd, arg=hane_degeri   -> 13 baytlik shift register'a push (yeni hane buf[12]'ye)
#           push sonrasi buf[0]==0x01 && buf[1]==0x0C ise CRC kontrolu:
#           CRC16-CCITT-FALSE(buf[1..12], init 0xFFFF) == 0 -> COMMIT
#   Yerlesim: buf[0]=0x01(isaret) buf[1]=0x0C(isaret)
#             buf[2..5]=IP octet'leri  ("%d.%d.%d.%d" ile formatlanir)
#             buf[6..7]=port  (big-endian, rev ile cevrilir)
#             buf[8..9]=random(big-endian, RCU.RandomCode + ts_set_sourceId)
#             buf[10]=serbest            buf[11..12]=CRC cozum baytlari
#   COMMIT -> memory.factory.RCU.IPAddr / RCU.RandomCode / p2p.sinPort yazilir
#            + "factor_p2p" thread'i dogar (0.0.0.0:port dinler)
#   IP ozel durumlari: "0.0.0.0", "255.255.255.255", "255.255.255.0" farkli dala gider -> kullanma
#
# cmd/arg cikarimi (remote_thread_cb, kanitli): cmd=(scan>>16)&0xf, arg=(scan>>8)&0xff
# Ayni tusa ~15sn dedupe VAR -> tum frameler benzersiz olmali (addr yuksek nibble'i frame
# basina artar; cmd/arg bozulmaz).
#
# Kullanim:
#   python3 rcu_hesap.py                       # varsayilanlar (IP=TV, port=40000)
#   python3 rcu_hesap.py --ip 192.168.1.20 --port 40000 --random 5678 --free 00
#   python3 rcu_hesap.py --kal 32CD54AB        # kalibrasyon: AB54CD32 gonderince logda
#                                              # gorulen key_code -> sozlesme modunu yazdirir
import sys

def crc16_ccitt_false(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if (crc & 0x8000) else (crc << 1)
            crc &= 0xFFFF
    return crc

def coz_kuyruk(bas: bytes) -> bytes:
    """bas (10 bayt: 0C + 9 veri) sonuna 2 bayt ekle ki CRC(bas+2bayt)==0"""
    for i in range(0x10000):
        tail = bytes([i >> 8, i & 0xFF])
        if crc16_ccitt_false(bas + tail) == 0:
            return tail
    raise RuntimeError("CRC cozumu bulunamadi")

def sozlesme_kalibre(gonderilen: int, gorulen: int):
    """Kalibrasyon: hangi donusum soz geciyor? (sozcuk -> driver'in bildirdigi key_code)"""
    b = lambda v: [(v >> 24) & 0xFF, (v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF]
    g, r = b(gonderilen), b(gorulen)
    if g == r:        return "std", "bildirim = gonderilen sozcuk (byte sirasi ayni)"
    if g == r[::-1]:  return "rev", "bildirim = gonderilen sozcugun byte-tersizi (standart NEC decode)"
    inv = lambda x: x ^ 0xFF
    if [inv(x) for x in g] == r: return "inv", "bildirim = gonderilenin bayt-bazli terslenmisi"
    return None, "TANINMADI — baytlar: gonderilen=%s gorulen=%s (manuel incele)" % (g, r)

def hedef_word(cmd: int, arg: int, varyasyon: int, mod: str) -> int:
    """Driver'a ulusacak degeri (cmd,arg)'ye gore kur, sonra sozlesmeye cevir.
    Deger duzeni: bits31-24=addr, 23-16=~addr, 15-8=data(arg), 7-0=~data
    cmd = (~addr)&0xf  ->  addr = (varyasyon<<4) | (~cmd & 0xF)
    """
    addr = ((varyasyon & 0xF) << 4) | ((~cmd) & 0xF)
    data = arg & 0xFF
    val = (addr << 24) | ((addr ^ 0xFF) << 16) | (data << 8) | (data ^ 0xFF)
    if mod == "std":
        return val
    elif mod == "rev":
        b = [(val >> 24) & 0xFF, (val >> 16) & 0xFF, (val >> 8) & 0xFF, val & 0xFF]
        return (b[3] << 24) | (b[2] << 16) | (b[1] << 8) | b[0]
    raise ValueError("bilinmeyen mod: %s" % mod)

def dizi_uret(ip="192.168.1.20", port=40000, random=0x5678, free=0x00, mod="std"):
    octetler = [int(x) for x in ip.split(".")]
    parca = [0x01, 0x0C] + octetler + [(port >> 8) & 0xFF, port & 0xFF,
             (random >> 8) & 0xFF, random & 0xFF, free]   # buf[0..10] (11 bayt)
    kuyruk = coz_kuyruk(bytes(parca[1:11]))               # CRC buf[1..12] uzerinde
    haneler = parca + list(kuyruk)                        # 13 hane
    assert len(haneler) == 13
    frameler = [hedef_word(5, 0x50, 0, mod)]              # ARM
    for i, h in enumerate(haneler):
        frameler.append(hedef_word(0xD, h, (i + 1) & 0xF, mod))  # DIGIT, benzersiz varyasyon
    return frameler, haneler

if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--kal":
        gonderilen, gorulen = 0xAB54CD32, int(args[1], 16)
        mod, aciklama = sozlesme_kalibre(gonderilen, gorulen)
        print("mod:", mod, "-", aciklama)
        # cmd/arg dogrulamasi da yazdir
        print("  bu gorulen degerde cmd=(v>>16)&0xf=%#x  arg=(v>>8)&0xff=%#x" %
              ((gorulen >> 16) & 0xF, (gorulen >> 8) & 0xFF))
        sys.exit(0)
    ip, port, rnd, free, mod = "192.168.1.20", 40000, 0x5678, 0x00, "std"
    if "--ip" in args:     ip = args[args.index("--ip") + 1]
    if "--port" in args:   port = int(args[args.index("--port") + 1])
    if "--random" in args: rnd = int(args[args.index("--random") + 1], 16)
    if "--free" in args:   free = int(args[args.index("--free") + 1], 16)
    if "--mod" in args:    mod = args[args.index("--mod") + 1]
    frameler, haneler = dizi_uret(ip, port, rnd, free, mod)
    print("Haneler (13):", " ".join("%02X" % h for h in haneler))
    print("CRC kontrol : CRC16-CCITT-FALSE(hane[1:13]) =", hex(crc16_ccitt_false(bytes(haneler[1:13]))))
    print("ARM  + 13 DIGIT frame sozcukleri:")
    print(",".join("%08X" % f for f in frameler))
