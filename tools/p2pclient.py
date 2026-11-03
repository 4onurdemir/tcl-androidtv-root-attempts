#!/usr/bin/env python3
"""tclfactoryos factor_p2p (ts protokolü) istemcisi.
CRC16-CCITT-FALSE (init 0xFFFF, poly 0x1021, son 2 bayt BE).
Kısa frame: 84 83 <cmd> <data...> <crcH> <crcL>
Uzun frame: 84 FE <len:be16> <cmd> <data...> <crcH> <crcL>
El sıkışma: 84 83 7b 7c
Kullanım: p2pclient.py [port] [--send hexframe]
"""
import socket, sys, time

TV = '192.168.1.20'

def crc16(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if (crc & 0x8000) else (crc << 1)
            crc &= 0xFFFF
    return crc

def short(cmd: int, data: bytes = b'') -> bytes:
    body = bytes([0x84, 0x83, cmd]) + data
    c = crc16(body)
    return body + bytes([c >> 8, c & 0xFF])

def longframe(cmd: int, data: bytes = b'') -> bytes:
    body = bytes([0x84, 0xFE]) + len(data).to_bytes(2, 'big') + bytes([cmd]) + data
    c = crc16(body)
    return body + bytes([c >> 8, c & 0xFF])

HANDSHAKE = bytes.fromhex('84837B7C')

def recv_all(s, wait=2.0, label=''):
    s.settimeout(wait)
    out = b''
    try:
        while True:
            b = s.recv(4096)
            if not b:
                break
            out += b
    except socket.timeout:
        pass
    if out:
        print(f'<<{label}', out.hex())
    return out

def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 40000
    s = socket.create_connection((TV, port), timeout=5)
    print('connected', TV, port)
    s.sendall(HANDSHAKE)
    print('>> handshake', HANDSHAKE.hex())
    recv_all(s, 2.0, ' hs')
    # --send <hex> ile ek frame'ler
    if '--send' in sys.argv:
        for i, a in enumerate(sys.argv):
            if a == '--send':
                hx = sys.argv[i + 1].replace(' ', '')
                f = bytes.fromhex(hx)
                s.sendall(f)
                print('>>', f.hex())
                recv_all(s, 2.0, f' r{i}')
    # --probe: bilinen güvenli FCMD numaralarını tek tek dene
    if '--probe' in sys.argv:
        for cmd in [0x01, 0x02, 0x03, 0x10, 0x50]:
            f = short(cmd)
            s.sendall(f)
            print('>> probe', f.hex())
            r = recv_all(s, 1.0, f' p{cmd:02x}')
            if r:
                time.sleep(0.3)
    s.close()

if __name__ == '__main__':
    main()
