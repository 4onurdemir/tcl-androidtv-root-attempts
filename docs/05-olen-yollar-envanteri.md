# 05 — Ölen Yollar Envanteri

> Proje boyunca kapatılan her vektör, "neden öldü" gerekçesiyle. Başka bir araştırmacı
> aynı cihaza saldırırsa bu liste saatler kazandırır. Hepsi kanıtlı; "muhtemelen"
> yazan yer yok.

## Daemon'a kanal açma girişimleri

| Yol | Neden öldü |
|---|---|
| IR RCU dizisi → commit → p2p | Ana imkansızlık ispatı — doküman 04 (tablo marker eksikliği + report-mode kilidi) |
| p2p'yi DB yazarak doğurmak | Thread yalnız IR-commit'te doğar; DB yazımı canlı test edildi, thread doğmadı |
| Reboot / daemon-restart ile p2p | thread_init p2p yaratmıyor (disasm + canlı thread listesi) |
| UART yazılımsal (/dev/ttyS0 TIOCSTI, TIOCM_LOOP) | SELinux serial_device: system_app/shell open denied (avc kanıtı) |
| /dev/input/* ve /dev/uinput ile sahte IR olayı | root:input 660 — shell yazamıyor; uhid aynı |
| Bluetooth kumanda taklidi (HID ile fabrika dizisi) | Daemon sadece venus_IR_input cihazını işliyor; BT HID input-core'a başka cihaz olarak düşüyor, type-0x19 üretilemiyor |
| NEC protokol frame'leri (3 müşteri ailesi × bit/bayt sırası varyantları) | Bu ünitede protokol deaktif — 8 varyant denendi, tek event yok; açan sysfs root-only |

## HAL / HIDL yüzeyi

| Yol | Neden öldü |
|---|---|
| ITclUbootEnv (setUbootEnv = root env yazımı) | SELinux `find` yalnız system_server domainine; system_app'ten NoSuchElementException + avc denied. system_server'a geçiş vektörü yok |
| ITclDevManager upgradeFirmware | Bağlı TCL cihazı yok; çöp dosyayla erken-ret (retval=1), yol cihazsız ölü |
| HAL debug(NativeHandle, options) | Override yok — IBase default dprintf |
| RKP/CSR komut enjeksiyonu (fun=4 attr=0x8b, `system("%s > %s")`) | Çağrılan amzn_dha_tool/dhaprov-tool bu firmware'de YOK (exit 32512 — Amazon varyantı değil); ayrıca impdata yolu config katmanından okunuyor |
| wcl_generate tek-tırnak enjeksiyonu (memory.factory.cpu.number kaynağı) | Aynı akış: dak_provision önce koşuyor ve ölüyor — enjeksiyon hiç ateşlenmiyor (test edilmiş payload'lar: `x';sh /tmp/x.sh;#` vb.) |
| preset_keys thread (`fpi_system_shell_cmd` çağırıyor!) | `/impdata` root:root 755 — dosya konamıyor; shell çağrısından ÖNCE key-burn var (anahtar yazma zaten etik dışı) |
| monitord (root) | Yalnız watchdog reboot (persist.vendor.rtk.monitord_enabled=1 → 5sn'de reboot) — exec yok |
| doconfig_create (json_dom_list_save) | retval=1 ama readback değişmiyor — in-memory override yok / başka katman |
| doCmdCopyFile (M5 matrisi, 10 kombinasyon) | access(src)+access(dst) ikisi de VAR olmalı; tırnaklı `cp` — enjeksiyon kapalı; 10/10 false |
| /tmp/ota staging | system:system 770; vendor binary'lerinde tüketici yok |

## Property/config katmanları

| Yol | Neden öldü |
|---|---|
| DB'ye config etkisi beklemek | db katmanı ≠ config katmanı: okumalar /tclconfig/json_sys.ini (RO) üzerinden; DB yazımı yansımıyor (canlı test) |
| odm.tcl.factory.* property'lerini shell'den setlemek | SELinux property-context — shell domaini yazamıyor (yazım yalnız HAL/root) |

## Kernel / sistem düzeyi

| Yol | Neden öldü |
|---|---|
| /sys/venus_ir/* (protocol switch, report mode) | Düğümler SELinux'suz-etiketli (?????????) — shell/system_app erişemiyor |
| SICK-2020-012 (TCL 2020 public root, chmod 0777 vendor deseni) | Bu firmware'de yamalı |
| Kernel 5.4 genel LPE'leri, Android 12 bilinen istismarları | Güvenlik yaması 2025-12-05 — kapalı |
| Boot partition değiştirme (Magisk/AVB) | İmza + brick riski + fiziksel erişim sınırlı — fiilen kapalı, kapsam dışı |
| USB'den güncelleme paketi | İmza duvarı (OTACERT) + proje kuralları gereği yasak |
| FOTA paket imzası (HUAN-Sign/MD5 damarı) | Çözüldü ama paket kabulünü geçmedi — ilginç bulgu, yol değil |

## Donanım-özel

| Yol | Neden öldü |
|---|---|
| Telefon IR blaster (Redmi) | HAL'de transmit OK; hedef 38 kHz'te hiç dekode yok (dönemin taşıyıcı hatası) — 56 kHz bulununca donanım zaten sökülmüştü |
| LED fotodiyotla kayıt/doğrulama | 50 Hz şebeke flicker'ına boğuluyor (106 kayıt, hepsi şebeke) |
| Fiziksel UART / kapak içi pinler | Cihaz ailenin — kapak açılamıyor (proje sınırı, teknik engel değil) |
| Harici servis/RS232 jakı | Arka panel incelendi: HDMI×3, anten, LAN, USB, küçük jak (etiketi okunamadı) — **açık soru**, otel modeli değilse yok |

## Socket 27856 parser (özel not)

`recvfrom` sabit 144B + `recv==144` denetimi + `fun<=7` denetimi + SQLite parameterized.
strKey/strValue 64B dolduğunda strlen'in komşu alana taşması **kağıt üzerinde** var;
somut zarar kanıtı yok. Kör fuzzing = her crash daemon ölümü = yalnız reboot ile geri
dönüş (ve fabrika ekranı kazası emsali) — kötü takas, denenmedi.
