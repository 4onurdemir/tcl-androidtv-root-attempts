// TCL TV: kumandayi OGREN, sonra kendi IR LED'imizle GONDER
// Devre (PDF: tv-ir/TV-IR-yeni-devre-kilavuzu.pdf)
//   KY-022 alici : sana bakarken soldan - (E9) -> GND, orta + (E10) -> 5V, S (E11) -> Pin 2
//   IR LED       : Pin 3 -> 1k -> 2N2222A beyz; 5V -> 68R -> LED -> kollektor; emiter -> GND
//   Mantik duz   : Pin 3 HIGH = LED yanar (eski BC557 devresindeki ters mantik YOK)
//
// Kullanim (Seri Monitor 115200 baud, satir sonu fark etmez):
//   1) Kumandayi aliciya 5-10 cm'den tut, VOL+ bas  -> kod kaydedilir, ekrana yazilir
//   2) IR LED'i TV'ye cevir, 'g' yaz + Enter         -> kaydedilen kod 1 kez gonderilir
//      '5' yaz -> 5 kez arka arkaya gonderir (ses belirgin artsin diye)
//      'f' yaz -> taninmayan (ham) kodlarda tasiyici frekansi 38 <-> 56 kHz degistirir

#define RAW_BUFFER_LENGTH 200      // Uno'nun 2 KB RAM'i icin yeterli; TCL/NEC kodlari ~50-70 adim
#define EXCLUDE_EXOTIC_PROTOCOLS
#include <IRremote.hpp>

const uint8_t IR_ALICI_PIN = 2;    // gonderme pini Uno'da sabit: Pin 3 (timer2)

struct Kayit {
  IRData veri;
  uint8_t ham[RAW_BUFFER_LENGTH];
  uint16_t hamUzunluk;
  bool dolu;
} kayit;

uint8_t tasiyiciKHz = 38;

bool hamMi(decode_type_t p) {
  return p == UNKNOWN || p == PULSE_WIDTH || p == PULSE_DISTANCE;
}

void kodKaydet() {
  IRData &d = IrReceiver.decodedIRData;
  if (IrReceiver.irparams.rawlen < 4) return;                       // parazit
  if (d.flags & (IRDATA_FLAGS_IS_REPEAT | IRDATA_FLAGS_IS_AUTO_REPEAT)) return;  // tusa basili tutma tekrari
  if (d.flags & IRDATA_FLAGS_WAS_OVERFLOW) {
    Serial.println(F("Kod cok uzun, tampona sigmadi. Tusa kisa bas."));
    return;
  }

  kayit.veri = d;
  kayit.dolu = true;
  Serial.println(F("=============================="));
  if (hamMi(d.protocol)) {
    kayit.hamUzunluk = IrReceiver.irparams.rawlen - 1;
    IrReceiver.compensateAndStoreIRResultInArray(kayit.ham);
    Serial.print(F("Protokol taninmadi -> HAM olarak kaydedildi ("));
    Serial.print(kayit.hamUzunluk);
    Serial.println(F(" adim)."));
    IrReceiver.printIRResultRawFormatted(&Serial, true);
  } else {
    kayit.veri.flags = 0;
    IrReceiver.printIRResultShort(&Serial);
    IrReceiver.printIRSendUsage(&Serial);
  }
  Serial.println(F("KAYDEDILDI. LED'i TV'ye cevir, 'g' yaz."));
}

void kodGonder(uint8_t adet) {
  if (!kayit.dolu) {
    Serial.println(F("Once kumandadan bir tusa bas, kayitli kod yok."));
    return;
  }
  IrReceiver.stop();                      // alici ve verici ayni zamanlayiciyi kullaniyor
  for (uint8_t i = 0; i < adet; i++) {
    if (hamMi(kayit.veri.protocol)) {
      IrSender.sendRaw(kayit.ham, kayit.hamUzunluk, tasiyiciKHz);
    } else {
      IrSender.write(&kayit.veri);
    }
    delay(120);
  }
  IrReceiver.start();
  Serial.print(F("Gonderildi x"));
  Serial.print(adet);
  if (hamMi(kayit.veri.protocol)) {
    Serial.print(F(" (ham, "));
    Serial.print(tasiyiciKHz);
    Serial.print(F(" kHz)"));
  }
  Serial.println();
}

void setup() {
  Serial.begin(115200);
  IrReceiver.begin(IR_ALICI_PIN, ENABLE_LED_FEEDBACK);  // Uno'daki L ledi sinyal gelince yanip soner
  IrSender.begin(3);                                     // Uno: Pin 3 (timer2 PWM)
  Serial.println(F("Hazir. Kumandayi aliciya tutup VOL+ bas."));
}

void loop() {
  if (Serial.available()) {
    char c = Serial.read();
    if (c == 'g' || c == 'G') kodGonder(1);
    else if (c == '5') kodGonder(5);
    else if (c == 'f' || c == 'F') {
      tasiyiciKHz = (tasiyiciKHz == 38) ? 56 : 38;
      Serial.print(F("Ham kod tasiyici frekansi: "));
      Serial.print(tasiyiciKHz);
      Serial.println(F(" kHz"));
    }
  }

  if (IrReceiver.decode()) {
    kodKaydet();
    IrReceiver.resume();
  }
}
