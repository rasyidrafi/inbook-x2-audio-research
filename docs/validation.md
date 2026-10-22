# Hasil verifikasi — 22 Oktober 2026

## Kandidat yang dibangun

| Target kernel laptop | Compiler di build-host | Hasil |
| --- | --- | --- |
| `7.2.9-2-cachyos` | Clang/LLD 23.1.1 | Compile, link, MODPOST, BTF selesai; vermagic cocok |
| `6.18.55-2-cachyos-lts` | GCC 16.2.1 20260810 | Compile, link, MODPOST, BTF selesai; vermagic cocok |

Kedua module melaporkan `version: 1.1.0-research`. Log final terdapat di
`validation/build-*.log`, metadata di `validation/modinfo-*.txt`, versi compiler
di `validation/compiler.txt`. Binary hasil build berada di `artifacts/modules/`.

Build memakai salinan header kernel terpasang, termasuk konfigurasi dan
`Module.symvers`, serta pahole 1.32. Tidak ada compiler flags yang dihapus untuk
memaksa build berhasil. Percobaan awal Clang 22 gagal karena opsi baru kernel;
toolchain disamakan dengan kernel. LTS memakai GCC, sehingga build LTS juga
disesuaikan ke GCC asli. Include lokal untuk `hdac_hda.h` diperbaiki pada packaging
out-of-tree. Server dilengkapi dependensi build dan kmod untuk membaca metadata.

Tidak membangun seluruh kernel. Tidak melakukan kompilasi/dekompilasi berat
pada laptop. Laptop hanya dipakai untuk mengedit, membaca bukti, menyalin
toolchain/header, menjalankan parser ringan, dan menyimpan hasil.

## Pengujian kode

`validation/tests.log` mencatat hasil final berikut:

- **5 tes Python lulus**: pemilihan section INF yang benar, parsing nested call,
  penolakan tebakan nilai dinamis, penolakan call terpotong, serta penerapan
  kedua patch dengan fuzz=0 yang menghasilkan source kandidat persis.
- **72 kombinasi transisi** pada fungsi upstream sebagai negative control:
  kondisi speaker tetap mute sesudah restart direproduksi sesuai harapan.
- **72 kombinasi transisi** pada kandidat modern: lulus.
- **72 kombinasi transisi** pada kandidat LTS: lulus.

Harness mengambil `pcm_pop_work_events()` dan `sof_8336_trigger()` langsung dari
file source yang diperiksa, lalu mengompilasinya dengan stub GPIO/workqueue.
Variasi mencakup board cocok/tidak cocok, playback/capture, speaker powered/off,
ketiga jenis stop dan ketiga jenis start. Ada pengulangan restart, pembatalan
pekerjaan yang masih antre, pemeriksaan delay 70 ms, dan invalid command.
Ini pengujian fungsi C asli dalam lingkungan tiruan, **bukan kernel berjalan**.
Tidak menguji scheduling paralel, irq/locking, DMI runtime, atau sinyal listrik.

`checkpatch.pl --no-tree --no-signoff` menghasilkan **0 error dan 0 warning**
untuk kedua patch. `--no-signoff` disengaja karena belum ada sertifikasi DCO
manusia. Kalimat otomatis checkpatch “ready for submission” hanya berarti lolos
style dengan opsi tersebut; kandidat belum dianggap hardware-qualified atau
siap diterima maintainer.

## Bukti perangkat dari versi sebelumnya

Tes berikut adalah bukti **DKMS 1.0.1 yang sudah terpasang sebelum pekerjaan
reverse engineering**, bukan hasil uji pemasangan kandidat 1.1.0:

- `previous-restart-before.txt`: first start hi/hi, tiga restart hi/lo;
  penghitung PCM terus bergerak.
- `previous-restart-after.txt`: first start dan tiga restart semuanya hi/hi;
  penghitung PCM bergerak.
- `previous-pipewire-verification.txt`: enam playback hening berhasil.
- Pengguna mengonfirmasi “Lagu terdengar normal”.

Snapshot read-only pada tahap akhir riset menunjukkan module aktif masih
`1.0.1-infinix`, dengan hw_ptr `33953568 → 33977568 → 34001712` dalam dua
interval sekitar 0,5 detik. Ini cocok dengan progres 48 kHz pada saat snapshot;
bukan bukti audibilitas, tidak menjamin stabilitas jangka panjang, dan tidak
menguji kandidat. Snapshot lengkap disimpan lokal sebagai
`validation/current-readonly-snapshot.json` dan tidak masuk arsip source publik.

## Belum diverifikasi

- Memuat kandidat 1.1.0 pada laptop dan boot dengan autodetection tanpa quirk override.
- Reboot/cold boot, headphone/mic, suspend/resume seluruh laptop, dan pemakaian lama.
- Semua kemungkinan race pada pekerjaan GPIO yang berjalan bersamaan dengan STOP.
- Penyebab PCM pernah macet pada hw_ptr=96; tidak disamakan dengan bug amplifier.
- Perilaku runtime Windows melalui trace WDF/I2C/GPIO; hasil saat ini statis.

Modul kandidat belum dipasang, service audio tidak direstart pada tahap riset
ini, dan belum ada patch dikirim ke proyek eksternal. Workaround WirePlumber
yang terpasang pada tahap sebelumnya tetap ada; lihat `reproduction.md`.
