// fabrika.ino — TCL fabrika IR aticisi (kosk fazı, 3 Kas 2026)
// Seri komutlar (115200):
//   H XXXXXX  → 24-bit RCA kelimesi 2 kez (normal kumanda davranisi)
//   G XXXXXX  → 24-bit RCA kelimesi 1 kez (hizli)
//   N XXYYZZ  → NEC frame [XX][YY][ZZ][~ZZ] 2 kez (LSB-ilk, 9000/4500, 560/560-1690)
//   M XXYYZZ  → NEC frame 1 kez (hizli)
//   B W1,W2,… → toplu RCA: her kelime 1 kez, 12ms arayla
//   C F1,F2,… → toplu NEC (6 haneli c1,c2,data gruplari), 12ms arayla
//   P         → PONG
// RCA frame: 56 kHz, baslik 4000/4000, 24 bit MSB-ilk ADDR|CMD|~ADDR|~CMD,
//        bit 500 isik + 2000='1'/1000='0', son 500 kapanis. (kumanda.ino ile ayni)
#include <IRremote.hpp>
const uint8_t KHZ = 56;
uint16_t ham[51];

void kur(uint32_t tum) {
  uint8_t i = 0;
  ham[i++] = 4000; ham[i++] = 4000;
  for (int8_t b = 23; b >= 0; b--) { ham[i++] = 500; ham[i++] = (tum >> b) & 1 ? 2000 : 1000; }
  ham[i++] = 500;
}

uint16_t nec[69];
void kurNEC4(uint32_t baytlar, uint8_t msbIlk) {
  uint8_t i = 0;
  nec[i++] = 9000; nec[i++] = 4500;
  uint8_t bayt[4] = { (uint8_t)(baytlar >> 24), (uint8_t)(baytlar >> 16), (uint8_t)(baytlar >> 8), (uint8_t)baytlar };
  for (uint8_t byt = 0; byt < 4; byt++)
    for (uint8_t b = 0; b < 8; b++) {
      uint8_t bit = msbIlk ? (7 - b) : b;
      nec[i++] = 560;
      nec[i++] = ((bayt[byt] >> bit) & 1) ? 1690 : 560;
    }
  nec[i++] = 560;                                // kapanis
}

void gonderNEC4(uint32_t baytlar, uint8_t msbIlk, uint8_t adet) {
  kurNEC4(baytlar, msbIlk);
  for (uint8_t k = 0; k < adet; k++) { IrSender.sendRaw(nec, 69, KHZ); delay(12); }
}

void kurNEC(uint8_t c1, uint8_t c2, uint8_t data) { kurNEC4(((uint32_t)c1 << 24) | ((uint32_t)c2 << 16) | ((uint32_t)data << 8) | (uint8_t)~data, 0); }

void gonderNEC(uint8_t c1, uint8_t c2, uint8_t data, uint8_t adet) {
  gonderNEC4(((uint32_t)c1 << 24) | ((uint32_t)c2 << 16) | ((uint32_t)data << 8) | (uint8_t)~data, 0, adet);
}

void gonder(uint32_t tum, uint8_t adet) {
  kur(tum);
  for (uint8_t k = 0; k < adet; k++) { IrSender.sendRaw(ham, 51, KHZ); delay(8); }
}

uint32_t okuHex6(const char* s) {          // tam 6 hex haneli kelime oku
  uint32_t v = 0;
  for (uint8_t k = 0; k < 6; k++) {
    char c = s[k];
    uint8_t h = (c >= '0' && c <= '9') ? c - '0' : (c >= 'A' && c <= 'F') ? c - 'A' + 10
            : (c >= 'a' && c <= 'f') ? c - 'a' + 10 : 0xFF;
    if (h == 0xFF) return 0xFFFFFFFF;
    v = (v << 4) | h;
  }
  return v;
}

char satir[96]; uint8_t uz = 0;

void setup() {
  Serial.begin(115200);
  IrSender.begin(3);
  Serial.println(F("FABRIKA-READY"));
}

void loop() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (uz == 0) continue;
      satir[uz] = 0; uz = 0;
      isle(satir);
    } else if (uz < sizeof(satir) - 1) {
      satir[uz++] = c;
    }
  }
}

void isle(char* s) {
  if (s[0] == 'P' && s[1] == 0) { Serial.println(F("PONG")); return; }
  if ((s[0] == 'H' || s[0] == 'G') && s[1] == ' ') {
    uint32_t w = okuHex6(s + 2);
    if (w == 0xFFFFFFFF) { Serial.println(F("ERR-HEX")); return; }
    gonder(w, s[0] == 'H' ? 2 : 1);
    Serial.print(F("SENT-OK ")); Serial.println(w, HEX);
    return;
  }
  if ((s[0] == 'M' || s[0] == 'O') && s[1] == ' ') {
    // M/O XXXXXXXX = 4 bayt ham (verildigi sirada), M=LSB-ilk, O=MSB-ilk
    uint32_t w = 0; const char* p = s + 2;
    for (uint8_t k = 0; k < 8; k++) {
      char c = p[k];
      uint8_t h = (c >= '0' && c <= '9') ? c - '0' : (c >= 'A' && c <= 'F') ? c - 'A' + 10
              : (c >= 'a' && c <= 'f') ? c - 'a' + 10 : 0xFF;
      if (h == 0xFF) { Serial.println(F("ERR-HEX")); return; }
      w = (w << 4) | h;
    }
    gonderNEC4(w, s[0] == 'M' ? 1 : 0, 2);
    Serial.print(F("NEC-OK ")); Serial.println(w, HEX);
    return;
  }
  if ((s[0] == 'N') && s[1] == ' ') {
    uint32_t w = okuHex6(s + 2);
    if (w == 0xFFFFFFFF) { Serial.println(F("ERR-HEX")); return; }
    gonderNEC((w >> 16) & 0xFF, (w >> 8) & 0xFF, w & 0xFF, 2);
    Serial.print(F("NEC-OK ")); Serial.println(w, HEX);
    return;
  }
  if (s[0] == 'B' && s[1] == ' ') {
    uint8_t n = 0; char* p = s + 2;
    while (*p && n < 16) {
      uint32_t w = okuHex6(p);
      if (w == 0xFFFFFFFF) { Serial.println(F("ERR-HEX")); return; }
      gonder(w, 1);
      n++;
      p += 6;
      if (*p == ',') p++;
      Serial.print(F("B ")); Serial.print(n); Serial.print(F(" ")); Serial.println(w, HEX);
    }
    Serial.print(F("BULK-OK ")); Serial.println(n);
    return;
  }
  if (s[0] == 'C' && s[1] == ' ') {              // toplu NEC: C 6699FF,6699FD,...
    uint8_t n = 0; char* p = s + 2;
    while (*p && n < 16) {
      uint32_t w = okuHex6(p);
      if (w == 0xFFFFFFFF) { Serial.println(F("ERR-HEX")); return; }
      gonderNEC((w >> 16) & 0xFF, (w >> 8) & 0xFF, w & 0xFF, 1);
      n++;
      p += 6;
      if (*p == ',') p++;
      Serial.print(F("C ")); Serial.print(n); Serial.print(F(" ")); Serial.println(w, HEX);
    }
    Serial.print(F("CBULK-OK ")); Serial.println(n);
    return;
  }
  Serial.println(F("ERR-CMD"));
}
