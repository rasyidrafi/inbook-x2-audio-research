# Reproduksi dan pengujian

**Status update:** live hardware qualification failed. See
[hardware test report](hardware-test-20261022.md). Do not install or hot-reload
the candidates on a working machine. Instructions below describe the earlier
research workflow, not an approved deployment procedure.

## Build dan pengujian tanpa mengubah audio laptop

Semua kompilasi berikut dijalankan **di build-host**, di direktori proyek.
Tidak ada perintah install atau modprobe dalam skrip build.

```bash
cd ~/work/inbook-x2-audio-research
python3 scripts/prepare-candidate.py
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 tests/test_driver.py
bash scripts/build-remote.sh
```

Source upstream yang dipakai adalah v7.3 commit
`c03c1a14507dfaf8b856c2608f9ac216021fc222`, disimpan di
`inputs/linux-upstream/`. Generator menolak transformasi jika teks target tidak
cocok persis. Backport memakai source lokal 1.0.1 di `inputs/linux-current/`.
Untuk modul out-of-tree, include relatif `../../codecs/hdac_hda.h` disesuaikan
menjadi `hdac_hda.h`; ini perubahan packaging, bukan perubahan ABI.

Pada workspace riset privat, server memiliki header **persis kernel laptop**, di
`build/headers/<kernel>/build`. Repo publik tidak menyertakan header/toolchain itu.
Di workspace privat, toolchain tersalin dalam `build/toolchain23/`:
Clang/LLD 23.1.1 untuk kernel utama, GCC 16.2.1 untuk LTS, pahole 1.32.
ELF loader dan library dipakai melalui wrapper privat, bukan mengganti library
sistem server. Utilitas host objtool/modpost pada salinan header dibungkus dengan
runtime yang sama; executable asli disimpan sebagai `.elf`.

Untuk mengulang penyiapan dari laptop, `scripts/export-toolchain.py` dan
`scripts/export-gcc.py` hanya menyalin toolchain/library dan membuat arsip; tidak
melakukan build. Salin hasilnya dan header ke server, lalu jalankan
`scripts/prepare-header-runtime.py` di server sebelum build. Jangan menyalin
folder toolchain ini ke `/usr` server.

Build menghasilkan `build/modules/<kernel>/snd-soc-sof_es8336.ko`. Ini module
untuk kernel target laptop, **bukan kernel yang berjalan di server**. Jangan
memuatnya di `build-host`. Artefak belum ditandatangani untuk Secure Boot; kebutuhan
signing tergantung kebijakan kernel target. DKMS `AUTOINSTALL=no` untuk kandidat.

## Mengulang analisis Windows

Workspace lengkap mempunyai input vendor. Arsip kode yang dibagikan tidak
menyertakan binary Windows; cocokkan binary milik sendiri dengan hash pada
`analysis/input-sha256.txt` sebelum menganggap alamat fungsi sama.

Di server, pasang Ghidra 12.2 pada `.tools/ghidra_12.2_PUBLIC` dan Java 25 pada
`.tools/jdk25`. Ghidra 12.2 yang digunakan membutuhkan Java 25. Jalankan:

```bash
bash scripts/run-ghidra.sh
python3 scripts/analyze-driver.py
```

Analisis mengacu pada nilai INF default. Ini tidak merekam nilai registry Windows
saat runtime, bentuk gelombang I2C/GPIO, atau hasil dekompilasi yang sepenuhnya
terverifikasi. `register-call-inventory.csv` mengandung ekspresi/callsite;
jangan mengubahnya menjadi skrip register replay.

## Jika suara kembali bermasalah

Sebelum restart service menghapus kondisi gagal, jalankan snapshot read-only di
laptop dengan path file baru:

```bash
python3 scripts/capture-audio-state.py /tmp/inbook-audio-failed.json
```

Skrip membaca status PCM tiga kali dengan selang 0,5 detik dan meminta informasi
sink. Akses GPIO mungkin ditolak tanpa root, dan penolakan itu dicatat. Menjalankan
seluruh skrip sebagai root dapat membuat akses sesi WirePlumber tidak tersedia;
tambahkan pembacaan `sudo cat /sys/kernel/debug/gpio` secara terpisah bila diperlukan.
Tidak merekam suara, tidak memutar noise, tidak mengubah GPIO, driver, atau service.

- `hw_ptr` bergerak tetapi GPIO berubah ke level gagal: cocok dengan masalah
  jalur amplifier yang telah direproduksi.
- `hw_ptr` tidak bergerak selama playback yang seharusnya aktif: perlu investigasi
  stream/clock/SOF lebih lanjut. Status `RUNNING` saja bukan bukti transfer berjalan.
- PCM `closed` ketika tidak ada playback adalah normal.

## Status mesin dan rencana uji kandidat

Driver aktif tetap **1.0.1-infinix**, dengan parameter `quirk=128` dan UCM khusus
yang sudah terpasang sebelum tahap reverse engineering ini. Workaround
`~/.config/wireplumber/wireplumber.conf.d/51-inbook-x2-speaker.conf` juga masih ada:
timeout suspend sink 0, pause-on-idle false. Itu dapat mengurangi transisi idle
dan menambah konsumsi daya. Tidak dihapus selama tahap riset; jangan memakai
hasil playback dengan workaround itu sebagai bukti idle/suspend native sudah baik.

Kandidat 1.1.0 belum diaktifkan. Pengujian perangkat yang masih diperlukan:

1. Boot dengan kandidat dan cocokkan versi module, kernel, serta kedua GPIO.
2. Uji speaker dengan `quirk=128`, lalu uji autodetection tanpa override pada boot
   terpisah. Override lain tetap mengalahkan DMI seperti perilaku upstream.
3. Ulangi STOP/prepare/START tanpa menutup PCM, pause/release, dan XRUN recovery.
   Helper ALSA lama disimpan sebagai `validation/previous-restart-check.c`.
4. Uji speaker/headphone/mic, cold boot, suspend/resume seluruh laptop, serta
   penggunaan lama. Bedakan tes tanpa workaround WirePlumber dari tes dengannya.
5. Jika ada kegagalan, simpan snapshot sebelum recovery. Pemeriksaan race
   workqueue memerlukan trace kernel atau instrumentasi tambahan.

Langkah penggantian driver harus dijadwalkan sebagai uji perangkat tersendiri
karena menghentikan audio dan dapat memerlukan reboot. Tidak ada kebutuhan untuk
melakukan langkah tersebut demi membaca source, riset, atau hasil build ini.

## Rollback jika kandidat kelak dipasang

Simpan source DKMS 1.0.1 dan boot entry kernel yang sudah bekerja. Jika kandidat
telah didaftarkan sebagai `infinix-es8326/1.1.0`, rollback ke baseline yang saat
ini bekerja menggunakan:

```bash
sudo dkms remove -m infinix-es8326 -v 1.1.0 --all
sudo dkms install -m infinix-es8326 -v 1.0.1 -k 7.2.9-2-cachyos --force
sudo dkms install -m infinix-es8326 -v 1.0.1 -k 6.18.55-2-cachyos-lts --force
sudo depmod -a 7.2.9-2-cachyos
sudo depmod -a 6.18.55-2-cachyos-lts
```

Perintah DKMS di atas dapat membangun ulang bila cache binary tidak tersedia;
ikuti batas pengguna dengan membangun di server bila itu diperlukan. Reboot
terencana memuat kembali module baseline. Pulihkan `quirk=128` jika sebelumnya
dihapus untuk uji autodetection. Tidak ada rollback yang perlu dijalankan sekarang
karena kandidat belum dipasang.
