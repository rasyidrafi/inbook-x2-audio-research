# Riset ES8326 pada Infinix INBOOK X2

Tanggal: 22 Oktober 2026. Sasaran: board `EM_IC325_200B_V1.0 20211012`,
vendor DMI `Infinix`, Intel i3-1005G1, codec ACPI `ESSX8326`, subsystem
`2782:1a21`. Temuan ini tidak otomatis berlaku pada semua laptop bernama INBOOK X2.

## Jawaban: mengapa Windows normal tetapi Linux bermasalah?

Chip yang sama tetap memerlukan urutan pengaturan daya dan jalur speaker yang
benar. Paket Windows memiliki konfigurasi khusus untuk hardware ID laptop ini,
sedangkan driver machine Linux yang diperiksa belum mempunyai pengecualian
board Infinix tersebut. Selain perbedaan pengaturan GPIO, ada bug Linux yang
berhasil direproduksi: STOP mematikan amplifier, lalu START tidak memulihkannya
ketika pengelola daya audio (DAPM) masih menganggap jalur speaker menyala.

Ini menjelaskan **salah satu penyebab speaker diam** dengan bukti pada laptop
ini. Belum menjelaskan seluruh kejadian kresek atau PCM macet. Kemampuan Windows
memutar audio merupakan petunjuk bahwa hardware mampu bekerja, bukan bukti
bahwa semua masalah Linux berasal dari satu register tertentu.

Linux sudah memiliki driver codec ES8326 buatan **Everest Semiconductor**,
ditulis David Yang, serta driver machine Intel. Jadi pekerjaan yang tepat adalah
memperbaiki integrasi board dan transisi playback yang salah. Menulis ulang
seluruh driver akan menduplikasi kode yang sudah ada tanpa menyelesaikan
perbedaan konfigurasi secara otomatis.

## Bahan dan metode

- Binary Windows `ESAuDriverTDMMode.sys`, PE32+ x86-64, 150736 byte; INF
  `DriverVer=12/04/2021,3.0.1.1`. Source C asli Windows tidak tersedia.
- INF bagian `ESAuDriver_Device_Emdoor_27821A21_RegAdd`, cocok dengan
  `ACPI\VEN_ESSX&DEV_8326&SUBSYS_27821A21`.
- Ekstrak ACPI `_CRS`, `_DSM`, pemetaan GPIO, dan NHLT dari mesin ini.
- Linux upstream tag **v7.3**, commit
  `c03c1a14507dfaf8b856c2608f9ac216021fc222`, sebagai basis patch.
- Source DKMS lokal 1.0.1 sebagai baseline kompatibilitas kernel 6.18.
- Bukti GPIO dan raw ALSA sebelum/sesudah patch 1.0.1 dari tahap sebelumnya.

Ghidra 12.2 dengan Java 25 dijalankan di `build-host`. Skrip
`scripts/ghidra/ExportAudio.java` mengekspor fungsi C hasil dekompilasi,
assembly, call graph, dan referensi string. Diperoleh **179 fungsi**, tanpa
kegagalan decompiler yang dilaporkan. Itu tidak menjamin semua tipe atau
control flow hasil dekompilasi benar. Indirect call WDF melewati Windows CFG;
beberapa return value dan loop terlihat tidak masuk akal. Cabang polaritas dan
pemetaan `_DSM 0x5B` juga diperiksa di assembly.

`scripts/analyze-driver.py` menghasilkan konfigurasi board dan inventaris
**223 callsite penulisan register**, di antaranya **132** dengan argumen register
dan nilai berupa literal. Angka ini menghitung lokasi kode, bukan jumlah write
saat boot. Cabang runtime, kondisi jack, stream, dan model codec belum seluruhnya
dipecahkan. CSV tersebut **bukan urutan init yang boleh diputar ulang**.

Hash input Linux dan binary/INF Windows tersimpan di `analysis/input-sha256.txt`.
Dump firmware dan hash-nya tidak disertakan dalam repo publik. Binary Windows dan
hasil dekompilasi lengkap disimpan dalam workspace riset privat dan tidak
disertakan dalam arsip kode untuk dibagikan. Implementasi Linux memakai source
GPL Linux dan perubahan kecil berdasarkan perilaku yang diamati; tidak menyalin
fungsi dekompilasi Windows ke modul Linux. Ini bukan klaim proses clean-room
dengan peneliti dan implementer terpisah.

## Peta fungsi Windows yang ditemukan

Alamat berikut adalah virtual address dari binary yang dianalisis; nama peran
adalah hasil interpretasi, bukan simbol vendor.

| Alamat fungsi | Peran yang didukung bukti | Batas interpretasi |
| --- | --- | --- |
| `0x140007bac` | Membaca array 74 nama setting dari registry `ESAuDsetting` | Nilai runtime dapat diubah registry |
| `0x14000817c` | Memetakan setting ke field konteks perangkat | Tipe konteks direkonstruksi parsial |
| `0x14000f274` | Menyusun request `_DSM`, memetakan return menurut selector | Tidak semua selector dianalisis |
| `0x14001ddf0` | Enumerasi resource connection GPIO I/O dan pembuatan handle | WDF call melalui CFG; urutan resource Windows belum direkam langsung |
| `0x140009ecc` | Membuka resource GPIO melalui `RESOURCE_HUB` | Nama WDF spesifik belum seluruhnya dipulihkan |
| `0x140009a44` | I/O GPIO via handle `ctx+0x238+8*index`; read `0x480000`, write `0x480004` | Return C `unaff_ESI` merupakan artefak decompiler |
| `0x14000a214` | Memilih nilai output GPIO, mode steady/pulse, menyimpan state speaker | Mode pulse tidak digunakan INF board ini |
| `0x14000b26c` | Mengirim pasangan byte register/nilai, dilindungi mutex | Cabang pemanggil menentukan apakah write relevan untuk board |
| `0x14000b0c8` | Menulis alamat register lalu membaca satu byte | Bukan trace I2C fisik |
| `0x14000c0bc` | Handler state stream; cabang state 2 mematikan output, state 3 mengatur playback | Nama state eksternal dan seluruh callback chain belum dipastikan |
| `0x14000cefc` | Menerapkan ulang output berdasarkan stream dan mute tersimpan | Dipanggil melalui fungsi `0x14001f750`; timing belum diverifikasi langsung |
| `0x14001fe70` | Memulihkan GPIO speaker sesuai mute/multistream | Terdaftar sebagai callback; jenis timer/timing belum dipastikan |
| `0x14001d2d0`, `0x14001d530` | Jalur mirip power entry/exit, menonaktifkan GPIO dan memulihkan/menyimpan setting | Nama callback WDF masih interpretasi |

## Konfigurasi board Windows dan firmware

| Setting | Nilai INF board | Field konteks yang ditemukan |
| --- | --- | --- |
| `Platform_With_Oscillator` | 0 | `+0x51` |
| `Platform_SpkGpio_ControlMode` | 0 (steady) | `+0x53` |
| `Spk_Mute` | 0 | `+0x344` |
| `Hp_Mute` | 0 | `+0x348` |
| `Headphone_GMS01_Type` | 3 | `+0x417` |
| `MultiStream_Mode` | 0 | low nibble `+0x68`, high nibble `+0x69` |
| `ES8326_TDM_OutSel` | 1 | `+0x468` |
| `PDMMainMicIOMAP` | 1 | `+0x2ca` |

Bagian INF generic mempunyai nilai lain. Parser sengaja membaca section hardware
yang cocok, bukan mengambil kemunculan pertama setting dari seluruh INF.

Firmware `_DSM` selector **0x5B mengembalikan 1**. Fungsi `0x14000f274`
membatasi return menjadi 0 atau 1 dan menyimpannya pada `ctx+0x32b`.
Di assembly: cabang selector pada `0x140010747`, penulisan field pada
`0x140010a7b`. Fungsi GPIO `0x14000a214` membaca field tersebut pada
`0x14000a38f`: nilai 1 memilih output speaker dengan polaritas langsung.

GUID request Windows pada VA `0x140017340` juga dicocokkan byte demi byte dengan
buffer `Arg0` firmware: `04 0c 80 a9 16 e0 3e 34 41 f4 6b cc e7 0f 43 32`,
atau `a9800c04-e016-343e-41f4-6bcce70f4332` dalam notasi GUID Windows.
Jadi selector tersebut ditelusuri pada namespace `_DSM` yang sama.

Ini berbeda dari register codec alamat **0x5B**, yang oleh header Linux dinamai
`ES8326_SDINOUT23_IO`. Kesamaan angka tidak berarti selector firmware adalah
alamat register. Menulis nilai `_DSM` langsung ke register berpotensi mengubah
routing yang tidak dimaksudkan.

`_CRS` menggabungkan I2C, GPIO I/O pertama, GPIO I/O kedua, lalu interrupt.
Pemetaan firmware menghasilkan pin controller-relative **130**, **145**, lalu
interrupt **129**. Enumerasi binary menerima resource type `0x84`, class 1,
type 2, menyimpan connection ID ke `ctx+0x220+8*i` dan handle ke
`ctx+0x238+8*i`, sambil menaikkan indeks. Ini mendukung indeks Windows 0 dan 1
mengikuti urutan GPIO I/O firmware. Pengurutan resource hasil translasi Windows
belum dibuktikan dengan trace langsung.

## GPIO: apa yang setara, apa yang belum

Untuk mode steady dan flag polaritas 1, helper Windows menghasilkan:

| Permintaan helper | Byte output |
| --- | --- |
| selector 0, speaker enable | 1 |
| selector 0, speaker disable | 0 |
| selector 1, secondary enable | 0 |
| selector 1, secondary disable | 1 |

Dengan speaker diaktifkan dan secondary dinonaktifkan, pasangan byte adalah
**1/1**. Ini konsisten dengan pengamatan Linux bahwa speaker bekerja ketika kedua
pin fisik **hi/hi**. Namun byte API Windows bukan nilai logical GPIO Linux.
Linux mendaftarkan dua descriptor sebagai **active-low**, sehingga write logical
0 menghasilkan pin fisik high. Variabel Linux `speaker_en` juga bernilai **false
ketika DAPM speaker menyala**.

Dengan quirk 128, Linux memakai urutan nama yang terbalik: `gpio_speakers`
menunjuk pin145, `gpio_headphone` menunjuk pin130. Patch mempertahankan pemetaan
yang sebelumnya diuji pada laptop, mengubah secondary agar mengikuti logical
speaker state. Tidak mengasumsikan nama descriptor sama dengan nama jalur Windows.

**Batas penting:** saat kedua jalur Windows diminta disable, tabel helper memberi
0/1; patch lokal saat DAPM speaker mati memberi fisik 0/0. Jadi patch ini bukan
emulasi lengkap state machine Windows. Hasil speaker playback yang konsisten
tidak membuktikan idle, headphone, atau seluruh suspend sequence identik.
Mengubah semua transisi berdasarkan satu tabel helper belum dibenarkan tanpa
trace jack/power dan pengujian perangkat.

Register `0x14` pada Windows disentuh fungsi `0x140006c90`; header Linux
menamainya `ES8326_DAC_MUTE`. Fungsi itu mempertahankan nibble rendah dan
mengubah bit tinggi menurut field routing. Linux juga memiliki pengaturan clock,
mute, jack detection, dan kalibrasi pada `es8326.c`. Tidak ditemukan bukti cukup
bahwa menyalin satu urutan register Windows akan memperbaiki PCM yang macet.
Karena itu kandidat tidak mengubah clock, topology, atau register codec secara
spekulatif.

## Bug Linux yang telah dibuktikan

Urutan uji terdahulu memakai data hening dan PCM yang tetap terbuka:

1. Playback pertama: pin130/145 = hi/hi, penghitung PCM maju.
2. STOP → prepare → START pada kode sebelum fix restart: hi/lo, PCM tetap maju.
3. Pada DKMS 1.0.1, tiga restart dengan urutan sama: hi/hi, PCM tetap maju.
4. Pengguna mengonfirmasi lagu terdengar normal setelah patch.

`sof_8336_trigger()` mematikan GPIO pada STOP, SUSPEND, PAUSE_PUSH tetapi
upstream v7.3 tidak melakukan apa pun pada START, RESUME, PAUSE_RELEASE.
Callback DAPM tidak harus terpanggil jika jalur belum power-cycle. Kandidat
mengantrikan kembali pekerjaan GPIO dengan delay existing 70 ms pada tiga
transisi mulai, hanya untuk playback board yang cocok ketika speaker powered.

Bug serupa dilaporkan pada mesin ES8336 lain di issue SOF #5967. Itu bukti
pendukung, bukan pengganti reproduksi pada laptop ini. Perbaikan sengaja belum
diperluas ke semua board tanpa pengujian tambahan.

Pernah pula teramati PCM `RUNNING` dengan `hw_ptr=96`, `appl_ptr=2584` tidak
bergerak, pulih setelah sink suspend/resume. Bug GPIO tidak menjelaskan berhentinya
penghitung data tersebut. Belum ada trace yang cukup untuk menentukan apakah
penyebabnya SOF IPC/firmware, clock, ALSA, atau interaksi server audio. Kandidat
tidak diklaim menyelesaikan gejala ini maupun seluruh suara kresek.

## Kontribusi Linux

Dua patch disiapkan terhadap source upstream v7.3: pengecualian board/polaritas
dan pemulihan GPIO saat restart. Ini kandidat review, belum dikirim ke maintainer.
Kernel adalah tempat tepat untuk dua perubahan tersebut; pemilihan profil dan
volume UCM tetap ranah `alsa-ucm-conf`. Workaround WirePlumber bukan pengganti
perbaikan kernel.

Sebelum pengajuan: uji kandidat pada boot dingin, restart berulang, headphone,
mic, suspend/resume laptop, dan pemakaian lama; periksa juga kemungkinan race
workqueue STOP versus pekerjaan yang sudah berjalan. Test tiruan saat ini
menguji transisi sekuensial, tidak membuktikan bebas race. Maintainer mungkin
meminta solusi restart yang umum untuk semua board atau representasi polaritas
yang berbeda. Patch belum memiliki Signed-off-by manusia; jangan mengarang
identitas atau DCO atas nama pengguna.

## Sumber publik

- [Linux v7.3 machine driver](https://github.com/torvalds/linux/blob/v7.3/sound/soc/intel/boards/sof_es8336.c)
- [Linux v7.3 ES8326 codec](https://github.com/torvalds/linux/blob/v7.3/sound/soc/codecs/es8326.c)
- [SOF #5967: amp tidak pulih setelah restart](https://github.com/thesofproject/linux/issues/5967)
- [SOF #5856: board Infinix dan GPIO](https://github.com/thesofproject/linux/issues/5856)
- [Infinix audio fix issue #2](https://github.com/Abhinav5383/infinix-x2-audio-fix/issues/2)
- [Perubahan upstream inversi headphone GPIO](https://github.com/torvalds/linux/commit/213c4e51267fd825cd21a08a055450cac7e0b7fb)
- [Panduan pengajuan patch kernel](https://docs.kernel.org/process/submitting-patches.html)

Penelusuran publik memakai skill you-search, source Linux diambil lewat opensrc.
Hasil pencarian mentah disimpan di workspace privat; repo publik menyertakan
tautan sumber di atas.
