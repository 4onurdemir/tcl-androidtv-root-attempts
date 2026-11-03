# 01 — Keşif ve Erişim Kapıları

> Faz: gün 1–2. Cihaz kimliği, firmware'in ele geçişi, saldırı yüzeyi haritası ve
> **uid-1000 kod koşturma kapısının** bulunması.

## 1. Cihaz kimliği ve ilkeler

- TCL 65T61C — Android TV 12, Realtek RTD2875P/rtd6748, kernel 5.4.284+,
  güvenlik yaması 2025-12-05 (yani: bilinen genel LPE'ler kapalı).
- Kumanda RC833A **dual-mode**: Bluetooth açıkken HID olarak bağlanır (`BT_RC833A_...`),
  Bluetooth kapalıyken IR'a döner. Bu ayrım IR fazında kritik oldu: **IR testleri öncesi
  Bluetooth her seferinde kapatıldı** (yoksa testler anlamsızlaşır; ve dikkat — TV her
  yeniden başlatmada Bluetooth'u rastgele durumda geri getiriyordu).
- Çalışma ilkeleri baştan kondu: kendi cihazı, kendi ağı; kalıcı flag/reboot ancak sahibi
  onayla; MID/SN/anahtar yazımı hiç yok; her adım geri alınabilir olacak.

## 2. Firmware'in ele geçişi

TCL'nin güncelleme sunucusundan cihaza uygun tam OTA paketi (**V8-R75PT01-LF1V618.zip**, ~2 GB)
indirildi. İçinden çıkanlar çalışmanın omurgası oldu:

- `boot.img` → kernel Image (48,7 MB, ARM64) — gün 8'de IR sürücüsünü çözmekte kullanıldı
- `factory_ro.img` → **ir_table.bin** (kernel IR tuş tablosu!) + ir_table_rtk_bt.bin
- `vendor.img` → tclfactoryos daemon'u, HAL servisleri, TCL framework jar'ları
- `bootloader.img`, `dtbo.img`, `Auxcode.bin` — arşivde

**Ders:** OTA paketini indirmeden önce hiçbir derin analiz yapılmadı — statik RE'nin
tamamı bu damar üzerinden yürüdü. Canlı cihazda denemekten önce kâğıtta çözmek,
yeniden başlatma riskini sıfırladı.

## 3. Saldırı yüzeyi haritası (özet)

Erişilebilen katmanlar ve kimlikleri:

| Katman | Kim | Ne |
|---|---|---|
| Adb (ağ) | shell uid 2000 | Giriş noktası |
| `com.tcl.ttvs` uygulaması | system_app uid 1000 | TCL'ın sistem uygulaması — içinde kapı var (aşağıda) |
| `tclfactoryos` | **root** | Fabrika daemon'u — hedef (doküman 02) |
| `vendor.tcl.factory@1.0-service` | root | HAL arakatman |
| ITclDevManager / ITclUbootEnv | root | Ek HIDL yüzeyleri (ikisi de öldü — doküman 05) |

## 4. uid-1000 kod koşturma kapısı (buluş #1)

TCL'ın servis altyapısında bir "teşhis komutu çalıştırıcı" kapı bulundu ve çalıştığı
canlı kanıtlandı:

```
settings put global tcl_diagnostic_status 1
dumpsys activity service com.tcl.ttvs/com.tcl.guard.onlinesupport.service.OnlineSupportService \
  --i 3 "CLASSPATH=/system/framework/tcl-service.jar:/data/data/com.tcl.ttvs/files/M4.jar \
         app_process / M <mod> [args] > /data/data/com.tcl.ttvs/files/m4out.txt 2>&1"
```

- `--i 3` argümanı servisi "harici komut çalıştır" moduna sokuyor; komut
  **system_app (uid 1000)** olarak koşuyor — root değil ama shell'den çok daha yetkili.
- Uzun işler için `&` ile arka plana atıp çıktıyı sonra okuma deseni gerekiyor
  (servis ~4 sn'de foreground penceresini kapatıyor).

### M-jar harness ailesi

Bu kapıdan çağrılmak üzere, tcl-service.jar'ın HIDL arayüzlerini **reflection ile** çağıran
küçük Java harness'ları yazıldı (derleme: `javac --release 8` + `d8 --min-api 30`; HIDL
jar'ı DEX olduğundan derleme anında kullanılamıyor — reflection şart):

| Harness | Yetenekler |
|---|---|
| M / M2 | pg (durum okuma), uartw (UART yazma denemesi) |
| M3 | pmon/pmoff (P-mode aç/kapa), pg, pmrd |
| M4 | + cfgw (doSet_property), cfgcreate/cfgdel, cmdcopy, **rootloop** (root komut kanalı denemesi) |
| M5–M9 | HAL probe matrisleri: doCmdCopyFile kombinasyonları, doconfig_create, Demura yolları... |

Kritik kazanımlar:
- **pmon**: daemon'u **yeniden başlatmadan** canlı başlatır (init trigger'ı `pmode=1 &&
  halready=1` → `start tclfactoryos`; `disabled oneshot` servis). Bu, tüm çalışma boyunca
  TV'yi asla yeniden başlatmadan root daemon'una sahip olmamızı sağladı.
- **pmoff**: flag'i kapatır ama daemon'u öldürmez (canlı kanıt) — yani pmode toggle ile
  yaşayan daemon yeniden doğmaz; bu ayrıntı gün 8'de "reboot işe yaramaz" ispatının parçası oldu.

**Önemli ders (jar isimlendirmesi):** jar dosyası `M3.jar` olsa bile **sınıf adı `M`** —
`app_process / M3 pmon` yazmak ClassNotFoundException ile sessizce ölüyor. Boş çıktı
görülünce önce sınıf adını kontrol et.

## 5. Property katmanları ve ilk hayal kırıklığı

Fabrika konfigürasyonunun iki ayrı katmanı olduğu canlı testle anlaşıldı:

- **DB katmanı:** `/userdata/factory_property.db` (SQLite). 27856 socket'ten (doküman 02)
  **whitelist'siz** yazılıyor (`memory.factory.*` ve hatta `sys.System.*`) — yazım+geri okuma kanıtlı.
- **Config katmanı:** daemon'un okuduğu birçok değer `doconfig_get_str` → `/tclconfig/json_sys.ini`
  (salt-okunur mount) üzerinden geliyor. **DB'ye yazmak config'e yansımıyor** (impdata path
  testiyle kanıtlandı).

Yani "DB'de her şeyi yazabiliyorum" görüntüsü aldatıcıydı: config'ten okunan hiçbir şey
bu yolla değiştirilemiyor. Bu ayrım, RKP enjeksiyonu gibi kimi umut verici yolları baştan
öldürdü (doküman 05).

## 6. Bu fazın çıktıları

- uid-1000'de istediğimiz kod koşuyor (reflection harness ailesi)
- Daemon'u reboot'suz istediğimiz an canlı başlatabiliyoruz (pmon)
- Property DB'sine serbest yazış (sınırlı etkisi olsa da)
- Firmware damarı tamamen açık: kernel, vendor, factory_ro elimizde

Sıradaki soru: **root daemon'unun içi nasıl?** → doküman 02.
