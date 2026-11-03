> Depo notu: aşağıdaki sketch'ler `tools/arduino/` klasöründedir; alıcı bağlantısı için `assets/3-alici-ve-TV.pdf`.

# TCL 65T61C kumanda IR kodları

Ölçüm: 3 Kasım 2026, KY-022 + Arduino Uno (`tus_kaydet.ino`), ham kayıt `tus_kaydi_ham.log`.

## Protokol (RCA tarzı)

- Taşıyıcı: **56 kHz** (38 kHz alıcı yakından yakalıyor; gönderimde 56 kHz ile TV'de doğrulandı)
- Başlık: **4000 µs ışık + 4000 µs boşluk**
- 24 bit, en anlamlı bit önce: **4 bit adres + 8 bit komut**, ardından aynı 12 bitin **tersi** (hata kontrolü)
- Her bit: **500 µs ışık**, ardından boşluk **2000 µs = 1**, **1000 µs = 0**; en sonda 500 µs kapanış ışığı
- Adres bu TV için her tuşta **0xF**. Kumanda her basışta çerçeveyi iki kez gönderir.

## Tuş tablosu

| # | Tuş | Komut | Veri (adres+komut) | Ters | Kontrol |
|---|---|---|---|---|---|
| 1 | Power | `0x2A` | `111100101010` | `000011010101` | OK |
| 2 | Sessiz (Mute) | `0x3F` | `111100111111` | `000011000000` | OK |
| 3 | 3 | `0x33` | `111100110011` | `000011001100` | OK |
| 4 | 2 | `0x32` | `111100110010` | `000011001101` | OK |
| 5 | 1 | `0x31` | `111100110001` | `000011001110` | OK |
| 6 | 6 | `0x36` | `111100110110` | `000011001001` | OK |
| 7 | 5 | `0x35` | `111100110101` | `000011001010` | OK |
| 8 | 4 | `0x34` | `111100110100` | `000011001011` | OK |
| 9 | 9 | `0x39` | `111100111001` | `000011000110` | OK |
| 10 | 8 | `0x38` | `111100111000` | `000011000111` | OK |
| 11 | 7 | `0x37` | `111100110111` | `000011001000` | OK |
| 12 | Menü (≡) | `0xEC` | `111111101100` | `000000010011` | OK |
| 13 | 0 | `0x30` | `111100110000` | `000011001111` | OK |
| 14 | Kaynak (Input) | `0xA3` | `111110100011` | `000001011100` | OK |
| 15 | Mavi (B) | `0xD8` | `111111011000` | `000000100111` | OK |
| 16 | Sarı (Y) | `0xE4` | `111111100100` | `000000011011` | OK |
| 17 | Yeşil (G) | `0xE8` | `111111101000` | `000000010111` | OK |
| 18 | Kırmızı (R) | `0x00` | `111100000000` | `000011111111` | OK |
| 19 | Yukarı ▲ | `0x59` | `111101011001` | `000010100110` | OK |
| 20 | Sağ ▶ | `0x57` | `111101010111` | `000010101000` | OK |
| 21 | OK (orta) | `0xF4` | `111111110100` | `000000001011` | OK |
| 22 | Sol ◀ | `0x56` | `111101010110` | `000010101001` | OK |
| 23 | Aşağı ▼ | `0x58` | `111101011000` | `000010100111` | OK |
| 24 | Home | `0x08` | `111100001000` | `000011110111` | OK |
| 25 | Geri (←) | `0x27` | `111100100111` | `000011011000` | OK |
| 26 | Mikrofon | `0x5C` | `111101011100` | `000010100011` | OK |
| 27 | TV (📺) | `0x1A` | `111100011010` | `000011100101` | OK |
| 28 | Ayarlar (⚙) | `0xCF` | `111111001111` | `000000110000` | OK |
| 29 | CH ▲ | `0x2D` | `111100101101` | `000011010010` | OK |
| 30 | 123 | `0xCD` | `111111001101` | `000000110010` | OK |
| 31 | VOL + | `0x2F` | `111100101111` | `000011010000` | OK |
| 32 | CH ▼ | `0x2C` | `111100101100` | `000011010011` | OK |
| 33 | Info (ⓘ) | `0x3C` | `111100111100` | `000011000011` | OK |
| 34 | VOL − | `0x2E` | `111100101110` | `000011010001` | OK |
| 35 | YouTube | `0xE2` | `111111100010` | `000000011101` | OK |
| 36 | Prime Video | `0xC1` | `111111000001` | `000000111110` | OK |
| 37 | Netflix | `0xEF` | `111111101111` | `000000010000` | OK |
| 38 | Disney+ | `0x9A` | `111110011010` | `000001100101` | OK |
| 39 | TCL Channel | `0xE3` | `111111100011` | `000000011100` | OK |
| 40 | Video | `0x02` | `111100000010` | `000011111101` | OK |

Doğrulama: rakamlar 0x30–0x39 sırasında, VOL+ = 0x2F (TV'de test edildi), yön tuşları 0x56–0x59 — sıralama tutarlı.
## TV'de doğrulanan tuşlar (3 Kasım 2026)

VOL+ (0x2F), VOL− (0x2E), Sessiz aç/kapa (0x3F) — kendi devremizle (`kumanda/kumanda.ino`, 56 kHz) gönderildi, TV tepki verdi.

## Dosyalar

| Dosya | Ne işe yarar |
|---|---|
| `tus_kaydet/tus_kaydet.ino` | Kumanda tuşlarını okuyup adres/komut/bit olarak yazar |
| `kumanda/kumanda.ino` | Seri porttan harf alıp TV'ye tuş gönderir (`+ - m p u d l r o h b c v i s k 0-9`) |
| `ses_ac_oto/ses_ac_oto.ino` | Her 1 sn VOL+ gönderir |
| `ogren_gonder/ogren_gonder.ino` | Herhangi bir kumandayı öğrenip ham olarak geri gönderir |
| `led_tek_kaynak.py`, `transistor_adim_kaynak.py`, `alici_adim_kaynak.py` | Adım 1–3 PDF'lerinin kaynakları |

## Devre notu (düzeltme)

Bu projedeki 2N2222A'nın bacak sırası, düz yüz sana bakarken **C – B – E**. `TV-IR-yeni-devre-kilavuzu.pdf` ve `Adim2-transistor.pdf` içinde E – B – C yazıyor; bu yanlış. Çalışan devrede transistör o çizime göre 180° çevrik takılı. Başka bir 2N2222A kullanırken multimetrenin hFE yuvasıyla sırayı kontrol et.
