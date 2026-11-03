// TCL TV: VOL+ kodunu (RCA tarzi, adres 0xF, komut 0x2F) her 1 sn'de bir otomatik gonderir.
// Kumandadan okunan zamanlamalar: baslik 4000/4000 us, bit 500 us isik + 2000 (1) / 1000 (0) us bosluk.
// Tasiyici 56 kHz (TCL/RCA standardi). Uno'daki L ledi her gonderimde kisa yanar.
#include <IRremote.hpp>

const uint8_t  ADRES = 0xF;
const uint8_t  KOMUT = 0x2F;   // VOL+
const uint8_t  KHZ   = 56;
uint16_t ham[2 + 24 * 2 + 1];

void kodHazirla() {
  uint32_t veri = ((uint32_t)ADRES << 8 | KOMUT);         // 12 bit
  uint32_t tum = (veri << 12) | (~veri & 0xFFF);           // 24 bit: veri + tersi
  uint8_t i = 0;
  ham[i++] = 4000; ham[i++] = 4000;
  for (int8_t b = 23; b >= 0; b--) {
    ham[i++] = 500;
    ham[i++] = (tum >> b) & 1 ? 2000 : 1000;
  }
  ham[i++] = 500;
}

void setup() {
  Serial.begin(115200);
  pinMode(13, OUTPUT);
  IrSender.begin(3);
  kodHazirla();
  Serial.println(F("VOL+ her 1 sn'de gonderiliyor (56 kHz)."));
}

void loop() {
  digitalWrite(13, HIGH);
  IrSender.sendRaw(ham, sizeof(ham) / sizeof(ham[0]), KHZ);
  delay(8);
  IrSender.sendRaw(ham, sizeof(ham) / sizeof(ham[0]), KHZ);  // kumanda gibi bir tekrar
  digitalWrite(13, LOW);
  Serial.println(F("VOL+ gonderildi"));
  delay(1000);
}
