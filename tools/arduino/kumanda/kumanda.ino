// TCL TV kumandasi: seri porttan gelen harfe gore tus gonderir (RCA tarzi, adres 0xF, 56 kHz).
// Kodlar: tv-ir/TCL-kumanda-kodlari.md
#include <IRremote.hpp>
const uint8_t ADRES = 0xF, KHZ = 56;
uint16_t ham[51];

uint8_t harfToKomut(char c) {
  if (c >= '0' && c <= '9') return 0x30 + (c - '0');
  switch (c) {
    case '+': return 0x2F; case '-': return 0x2E; case 'm': return 0x3F; case 'p': return 0x2A;
    case 'u': return 0x59; case 'd': return 0x58; case 'l': return 0x56; case 'r': return 0x57;
    case 'o': return 0xF4; case 'h': return 0x08; case 'b': return 0x27; case 'c': return 0x2D;
    case 'v': return 0x2C; case 'i': return 0x3C; case 's': return 0xCF; case 'k': return 0xA3;
  }
  return 0xFF;  // bilinmiyor
}

void gonder(uint8_t komut) {
  uint32_t veri = ((uint32_t)ADRES << 8) | komut;
  uint32_t tum = (veri << 12) | (~veri & 0xFFF);
  uint8_t i = 0;
  ham[i++] = 4000; ham[i++] = 4000;
  for (int8_t b = 23; b >= 0; b--) { ham[i++] = 500; ham[i++] = (tum >> b) & 1 ? 2000 : 1000; }
  ham[i++] = 500;
  IrSender.sendRaw(ham, 51, KHZ); delay(8); IrSender.sendRaw(ham, 51, KHZ);
}

void setup() {
  Serial.begin(115200);
  IrSender.begin(3);
  Serial.println(F("Kumanda hazir: + - m p u d l r o h b c v i s k 0-9"));
}

void loop() {
  if (!Serial.available()) return;
  char c = Serial.read();
  uint8_t k = harfToKomut(c);
  if (k == 0xFF) return;
  gonder(k);
  Serial.print(F("Gonderildi '")); Serial.print(c); Serial.print(F("' komut=0x")); Serial.println(k, HEX);
}
