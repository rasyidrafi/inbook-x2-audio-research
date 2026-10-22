# Perbaikan speaker Infinix INBOOK X2 — 22 Oktober 2026

## Status

Driver yang diperbaiki sudah aktif tanpa reboot. Pemilik mengonfirmasi lagu
terdengar normal sesudah pemasangan. Ini memperbaiki bug stop/start yang berhasil
direproduksi pada laptop ini; pengujian jangka panjang dan sleep seluruh laptop
belum dilakukan.

## Penyebab yang dibuktikan

Driver machine snd_soc_sof_es8336 mematikan penguat speaker saat stream STOP,
tetapi tidak memulihkannya pada START jika DAPM (pengelola daya jalur audio)
tetap menganggap speaker menyala. Akibatnya data audio bisa tetap berjalan
sementara speaker diam.

Tes langsung ALSA dengan data hening mereproduksi bug pada versi lama:
- Start pertama: headphone-enable hi, speakers-enable hi.
- Tiga stop/prepare/start tanpa menutup PCM: headphone-enable hi,
  speakers-enable lo. Penghitung PCM tetap maju.

Sebelum tindakan, PipeWire juga ditemukan macet di hw_ptr=96 seperti pemeriksaan
pagi. Suspend/resume sink memulihkan progres, dan layanan audio direstart untuk
memuat ulang kartu setelah penggantian modul. Tes ALSA membuktikan bug GPIO,
bukan bahwa bug GPIO sendirian menyebabkan setiap bentuk kemacetan PipeWire.

## Perubahan permanen

- DKMS infinix-es8326 dinaikkan dari 1.0.0 ke 1.0.1.
- Pada START, PAUSE_RELEASE, dan RESUME, jadwalkan kembali pekerjaan pemulihan
  GPIO dengan delay 70 ms yang sudah digunakan driver.
- Perubahan hanya berlaku pada playback board Infinix EM_IC325 yang sudah
  ditangani patch GPIO lama, ketika DAPM menganggap speaker aktif.
- Patch lama, quirk=128, dan UCM khusus ES8326 dipertahankan.
- Modul dibangun dan dipasang untuk 7.2.9-2-cachyos serta 6.18.55-2-cachyos-lts.
- Modul aktif melaporkan 1.0.1-infinix; kernel mengonfirmasi versi ini dimuat.
- Tidak memasang polling/watchdog, tidak menonaktifkan penghematan daya global,
  dan tidak mengganti firmware.

Sumber baru: /usr/src/infinix-es8326-1.0.1/
Sumber lama tetap tersedia: /usr/src/infinix-es8326-1.0.0/
DKMS versi lama berstatus built, versi baru installed. Implementasi DKMS pada
mesin ini memilih versi terbaru saat autoinstall, sehingga versi lama dapat
tersimpan untuk rollback tanpa menimpa versi baru pada update berikutnya.

## Verifikasi

- Tes ALSA yang sama sesudah patch: start pertama dan ketiga restart menjaga
  kedua GPIO hi/hi, dengan penghitung PCM maju. Lihat restart-before.txt dan
  restart-after.txt.
- Enam playback PipeWire dengan file hening 2 detik semuanya exit 0 dalam
  sekitar 2,04–2,11 detik. Ada jeda 6 detik antarsebagian tes, tetapi pengguna
  juga memutar lagu: ini bukan bukti bahwa sink mengalami suspend pada setiap jeda.
- Pemilik menjawab: "Lagu terdengar normal".
- Saat lagu diputar, hw_ptr bergerak 2299248 -> 2323344 dalam sekitar 0,5 detik,
  sesuai 48 kHz. Speaker menjadi output aktif; ketiga layanan audio aktif.
- Percobaan playback pertama tepat setelah start layanan sempat gagal karena
  WirePlumber belum selesai menemukan output. Setelah output muncul, enam tes lulus.
- Kedua initramfs berhasil diperiksa dan tidak berisi modul codec/machine audio ini.
  Tidak perlu rebuild: boot akan mengambil modul baru dari /usr/lib/modules.
  Hasil tercatat di boot-verification.txt.

Tidak melakukan tes white noise/pink noise. Tes perbaikan ini memakai data hening.
Belum diverifikasi: reboot, sleep/resume seluruh laptop, headphone/mikrofon,
serta kestabilan penggunaan berjam-jam. Tidak ada klaim bahwa semua masalah audio
Linux yang mungkin terjadi pada board ini sudah terselesaikan.

## Rollback ke driver sebelumnya

Lakukan hanya jika perlu membatalkan patch. Perintah ini menghentikan audio sebentar.
Jalankan sebagai pengguna desktop; sudo hanya untuk operasi modul.

```bash
systemctl --user stop wireplumber pipewire-pulse.service pipewire-pulse.socket pipewire.service pipewire.socket
sudo dkms remove -m infinix-es8326 -v 1.0.1 --all
sudo dkms install -m infinix-es8326 -v 1.0.0 -k 7.2.9-2-cachyos
sudo dkms install -m infinix-es8326 -v 1.0.0 -k 6.18.55-2-cachyos-lts
sudo modprobe -r snd_soc_sof_es8336
sudo modprobe snd_soc_sof_es8336
systemctl --user start pipewire.socket pipewire-pulse.socket wireplumber pipewire-pulse.service
```

Rollback mengembalikan perilaku driver lama, termasuk kemungkinan bug yang diperbaiki di sini.

## Referensi

Laporan fungsi driver yang sama pada platform lain, dengan trace stop/start dan
workaround yang mendasari patch ini:
https://github.com/thesofproject/linux/issues/5967

Laporan exact board untuk kebutuhan patch GPIO sebelumnya:
https://github.com/thesofproject/linux/issues/5856

Log pemeriksaan pagi: ../audio-check-20261022/README.md
