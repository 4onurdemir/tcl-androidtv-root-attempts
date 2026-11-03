#!/usr/bin/env python3
"""tclfactoryos TCP 27856 istemcisi — 144 baytlık frame protokolü.

Frame: id:i32, fun:i32, intAttr:i32, strKey[64], intValue:i32, strValue[64]
fun: 0=SET_PROP 1=GET_PROP 2=GET_ATTR 3=SET_ATTR 4=DO_FUNCTION 6=GET_INFO 7=EVENT
Kullanım (adb forward tcp:19999 tcp:27856 yapıldıktan sonra):
  factorysock.py get  <key>
  factorysock.py set  <key> <value>
  factorysock.py aget <key>
  factorysock.py aset <key> <value>
  factorysock.py func <intAttrHex> [strKey] [strValue]
  factorysock.py info
  factorysock.py raw  <hex>
"""
import socket, struct, sys, time

HOST, PORT = '127.0.0.1', 19999

def frame(fid, fun, attr, key=b'', val=b'', intval=0):
    k = key.encode() if isinstance(key, str) else key
    v = val.encode() if isinstance(val, str) else val
    return (struct.pack('<iii', fid, fun, attr)
            + k[:64].ljust(64, b'\0')
            + struct.pack('<i', intval)
            + v[:64].ljust(64, b'\0'))

def parse(buf):
    r = {'len': len(buf), 'raw': buf.hex()}
    if len(buf) >= 12:
        r['id'], r['fun'], r['attr'] = struct.unpack_from('<iii', buf, 0)
    if len(buf) >= 76:
        r['key'] = buf[12:76].split(b'\0')[0].decode('utf-8', 'replace')
    if len(buf) >= 80:
        r['intval'] = struct.unpack_from('<i', buf, 76)[0]
    if len(buf) > 80:
        r['val'] = buf[80:144].split(b'\0')[0].decode('utf-8', 'replace')
    # kısa yanit: string dogrudan gövdede olabilir
    r['ascii'] = ''.join(chr(b) if 32 <= b < 127 else '.' for b in buf)
    return r

def xchg(data, wait=1.5):
    s = socket.create_connection((HOST, PORT), timeout=4)
    s.sendall(data)
    s.settimeout(wait)
    out = b''
    try:
        while len(out) < 144:
            b = s.recv(4096)
            if not b:
                break
            out += b
    except socket.timeout:
        pass
    s.close()
    return out

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    fid = int(time.time()) % 100000
    if cmd == 'get':
        data = frame(fid, 1, 0, sys.argv[2])
    elif cmd == 'set':
        data = frame(fid, 0, 0, sys.argv[2], sys.argv[3])
    elif cmd == 'aget':
        data = frame(fid, 2, 0, sys.argv[2])
    elif cmd == 'aset':
        data = frame(fid, 3, 0, sys.argv[2], sys.argv[3])
    elif cmd == 'func':
        attr = int(sys.argv[2], 0)
        k = sys.argv[3] if len(sys.argv) > 3 else ''
        v = sys.argv[4] if len(sys.argv) > 4 else ''
        data = frame(fid, 4, attr, k, v)
    elif cmd == 'info':
        data = frame(fid, 6, 0)
    elif cmd == 'raw':
        data = bytes.fromhex(sys.argv[2].replace(' ', ''))
    else:
        print(__doc__); return
    print('>>', data[:144].hex())
    out = xchg(data)
    print('<<', parse(out))

if __name__ == '__main__':
    main()
