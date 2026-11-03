// TCL kumandasi tus kaydedici: her tusu RCA tarzi 12 bit (4 adres + 8 komut) olarak cozer.
// Cikti satiri: TUS <sira> adres=0x? komut=0x?? bitler=<24 bit> ters=OK/HATA
#include <IRremote.hpp>
uint16_t sira = 0;
void setup() {
  Serial.begin(115200);
  IrReceiver.begin(2, ENABLE_LED_FEEDBACK);
  Serial.println(F("Hazir. Tuslara sirayla, birer kez, araliklarla bas."));
}
void loop() {
  if (!IrReceiver.decode()) return;
  auto &ip = IrReceiver.irparams;
  if (ip.rawlen >= 52) {
    uint32_t tum = 0;
    for (uint8_t i = 0; i < 24; i++) {
      uint32_t bosluk = (uint32_t)ip.rawbuf[4 + 2 * i] * MICROS_PER_TICK;
      tum = (tum << 1) | (bosluk > 1500 ? 1 : 0);
    }
    uint16_t veri = tum >> 12, ters = tum & 0xFFF;
    sira++;
    Serial.print(F("TUS ")); Serial.print(sira);
    Serial.print(F(" adres=0x")); Serial.print(veri >> 8, HEX);
    Serial.print(F(" komut=0x")); if ((veri & 0xFF) < 16) Serial.print('0'); Serial.print(veri & 0xFF, HEX);
    Serial.print(F(" bitler="));
    for (int8_t b = 23; b >= 0; b--) { Serial.print((tum >> b) & 1); if (b == 12) Serial.print(' '); }
    Serial.println(((veri ^ ters) == 0xFFF) ? F(" ters=OK") : F(" ters=HATA"));
  }
  IrReceiver.resume();
}
