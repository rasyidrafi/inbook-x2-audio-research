# Infinix INBOOK X2 — ES8326 research and Linux patch candidate

**Hardware qualification FAILED. Do not install the candidates permanently.**
Live testing found a GPIO teardown leak and a subsequent topology reload kernel
Oops. See [the hardware test report](docs/hardware-test-20261022.md). The source
is now the unqualified 1.1.1 research revision; earlier build results below
refer to 1.1.0 and are not proof of hardware safety.

Hasil pekerjaan: reverse engineering statis driver Windows, dua patch kernel
Linux, source modul DKMS kandidat **1.1.0**, alat analisis yang bisa dijalankan
ulang, dan pengujian transisi driver. Build/dekompilasi dilakukan di `build-host`.
Kandidat **belum dipasang ke laptop**.

Ini salinan publik berisi source, patch, laporan, dan log pengujian yang sudah
disaring. Nama host dan path pengguna diganti placeholder; PID pada log GPIO/PCM
disamarkan. Binary vendor, dekompilasi Windows, dump firmware, snapshot runtime,
toolchain, dan modul hasil build tidak disertakan. `build-host` adalah placeholder,
bukan alamat server yang dapat diakses pembaca.

Temuan terkuat: Linux dapat mematikan amplifier pada STOP lalu gagal menghidupkannya
kembali pada START, meskipun data audio berjalan. Windows memiliki konfigurasi
board dan pengaturan GPIO yang lebih spesifik. Perbaikan ini menargetkan bug yang
terbukti tersebut; belum merupakan jaminan bahwa semua penyebab kresek atau PCM
macet sudah terselesaikan.

## Baca hasilnya

- [Laporan riset dan perbandingan Windows–Linux](docs/research.md)
- [Hasil build, pengujian, dan batas verifikasi](docs/validation.md)
- [Cara mereproduksi, menguji perangkat, dan rollback](docs/reproduction.md)
- [Patch 1: deteksi board dan pengaturan GPIO](patches/0001-inbook-x2-board-gpio.patch)
- [Patch 2: pemulihan amplifier saat playback restart](patches/0002-inbook-x2-playback-restart.patch)
- [Source modul modern](module/sof_es8336_modern.c) dan [backport LTS](module/sof_es8336_legacy.c)
- [Konfigurasi board hasil ekstraksi](analysis/board-config.json)
- [Ringkasan inventaris reverse engineering](analysis/inventory-summary.json)

## Apa yang baru dikembangkan

1. Exporter Ghidra serta parser INF/callsite untuk menelusuri binary Windows:
   179 fungsi dan 223 lokasi penulisan register terindeks.
2. Pemetaan `_DSM 0x5B` ke flag polaritas GPIO, konfigurasi board yang benar,
   dan analisis resource/enable/mute Windows beserta batas kepastiannya.
3. Deteksi otomatis exact board Infinix, sehingga konfigurasi dua GPIO tidak
   hanya bergantung pada parameter manual `quirk=128`.
4. Port dan pemisahan fix GPIO/restart menjadi dua patch terhadap Linux v7.3,
   serta paket DKMS yang mendukung dua kernel terpasang.
5. Harness yang mengompilasi fungsi C driver asli dengan GPIO/workqueue tiruan;
   negative control mereproduksi amplifier tetap mute, kandidat memulihkannya.
6. Toolchain/build remote yang mengikuti compiler target dan alat snapshot
   read-only untuk membedakan GPIO mute dari PCM yang berhenti bergerak.

Fix restart itu sendiri **sudah ada dalam DKMS lokal 1.0.1 dari tahap troubleshooting
sebelumnya**. Pekerjaan baru memverifikasi dasar teknisnya melalui binary Windows,
menambah autodetection, membuat patch yang dapat direview, dan menyiapkan
reproduksi/test/build. Ini bukan driver Windows yang berhasil diterjemahkan
seluruhnya ke Linux atau driver codec baru dari nol.

## Susunan hasil

`module/` berisi source yang bisa dibangun; `patches/` untuk review upstream;
`scripts/` dan `tests/` untuk reproduksi; `validation/` berisi log tersaring;
`analysis/` berisi fakta konfigurasi dan hash input. `artifacts/` akan dibuat
secara lokal bila skrip packaging dijalankan dan tidak dilacak Git.

Workspace lengkap juga menyimpan binary vendor dan dekompilasi di `inputs/windows/`
dan `analysis/decompiled/`. Arsip kode untuk dibagikan tidak menyertakan keduanya,
toolchain, atau dump firmware privat. Source Linux referensi berlisensi GPL
disertakan agar patch dan pengujian C bisa direproduksi tanpa binary vendor.

Original code proyek ini berlisensi GPL-2.0-only. Source Linux yang disertakan
tetap mengikuti SPDX/copyright aslinya; lihat [LICENSE](LICENSE).

Untuk pengujian source tanpa input vendor, jalankan pada mesin build:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 tests/test_driver.py
```

Build modul memerlukan header dan compiler yang sesuai dengan kernel target;
lihat [panduan reproduksi](docs/reproduction.md). Analisis binary Windows
memerlukan input privat yang harus disediakan sendiri.
