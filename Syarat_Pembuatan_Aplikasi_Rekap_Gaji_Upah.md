# Syarat dan Spesifikasi Pembuatan Aplikasi Rekap Gaji & Upah

**Perusahaan:** PT. Mega Artha Makmur  
**Nama aplikasi:** Sistem Rekap Gaji & Upah  
**Basis acuan:** perilaku aplikasi Flask terakhir dan versi frontend Vue Art Design Pro  
**Status dokumen:** PRD / acuan pengembangan dan revisi

---

## 1. Tujuan Aplikasi

Aplikasi digunakan untuk mengelola proses payroll secara lokal/offline, mulai dari master karyawan, periode payroll, input kehadiran, perhitungan gaji/upah, potongan, kasbon, THR, transfer, laporan, slip gaji, backup, dan audit log.

Aplikasi harus mempertahankan perilaku perhitungan dan workflow dari aplikasi Flask terakhir, tetapi boleh menggunakan frontend Vue dengan tampilan Art Design Pro.

---

## 2. Prinsip Utama

1. **Data payroll disimpan lokal** di komputer pengguna menggunakan SQLite.
2. **Tidak membutuhkan internet** untuk menjalankan aplikasi setelah paket selesai dibuat.
3. **Tidak menggunakan Flask/Jinja pada runtime final.** Backend menggunakan Python Standard Library/non-Flask.
4. **Fungsi bisnis harus sama dengan aplikasi Flask terakhir.**
5. **Data tidak boleh hilang ketika ada perubahan roster atau tarif.**
6. **Periode yang sudah ditutup tidak boleh diubah secara sembarangan.**
7. **THR tidak digabungkan ke payroll reguler.**
8. **Total transfer harus dibandingkan dengan total gaji bersih/netto.**
9. **Data sensitif tidak boleh masuk ke source code, ZIP distribusi, log, atau repository.**

---

## 3. Target Pengguna dan Platform

### 3.1 Pengguna

- Administrator/operator akuntansi.
- Pengguna internal PT. Mega Artha Makmur.
- Penggunaan utama pada laptop Windows.

### 3.2 Target perangkat

- Windows 7 SP1 atau lebih baru.
- Windows 10/11.
- Laptop lama dengan RAM sekitar 4 GB tetap harus dapat menjalankan aplikasi dengan ringan.
- Browser Chrome/Edge yang kompatibel dengan target runtime.

### 3.3 Mode distribusi

Aplikasi harus tersedia sebagai portable package:

- tidak perlu instalasi Python;
- tidak perlu instalasi Node.js;
- tidak perlu `npm install` untuk pengguna akhir;
- dapat dijalankan melalui `jalankan.bat`;
- server hanya berjalan di `127.0.0.1`;
- browser dapat dibuka otomatis atau alamat aplikasi ditampilkan dengan jelas.

---

## 4. Requirement Desain dan UI

### 4.1 Arah visual

- Gaya **Art Design Pro**.
- Tampilan modern, rapi, premium, dan tidak generik.
- Tema utama **Navy Dark Premium / Biru Tenang Modern**.
- Font utama **Manrope** atau font lokal yang setara.
- Tidak menggunakan font eksternal yang wajib diambil dari internet.
- Kontras teks dan background harus jelas.
- Tabel harus memiliki header, row, badge/status, dan hierarchy visual yang jelas.

### 4.2 Layout

- Sidebar navigasi desktop.
- Sidebar dapat collapse.
- Mobile navigation menggunakan drawer/menu.
- Topbar dengan breadcrumb, theme switcher, identitas user, dan logout.
- Dashboard dengan metric cards, quick access, dan periode terakhir.
- Form menggunakan grid yang rapi.
- Dialog harus responsif dan tidak menyebabkan input bertumpuk secara keliru.
- Tidak boleh ada horizontal overflow pada lebar sekitar 390 px.

### 4.3 Menu minimal

1. Dashboard
2. Karyawan
3. Bagian
4. Aturan Payroll
5. Periode Payroll
6. Kehadiran
7. Rekap Gaji
8. Slip Gaji
9. Transfer
10. Potongan
11. Kasbon
12. THR
13. Laporan
14. Backup & Restore
15. Audit Log

---

## 5. Authentication dan Keamanan

### 5.1 Setup dan login

- Pada penggunaan pertama, administrator harus dibuat.
- Username wajib diisi.
- Password minimal 10 karakter pada alur setup.
- Password disimpan menggunakan PBKDF2-HMAC-SHA256 dengan salt.
- Password plaintext tidak boleh disimpan.
- Login gagal menampilkan pesan umum tanpa membocorkan detail akun.
- Logout harus menghapus session.

### 5.2 Session dan request security

- Session menggunakan token acak.
- Cookie session menggunakan `HttpOnly`.
- Cookie menggunakan `SameSite=Strict`.
- Request perubahan data wajib membawa CSRF token.
- Server hanya bind ke `127.0.0.1`.
- Body request memiliki batas ukuran.
- Path file backup/export harus divalidasi untuk mencegah path traversal.
- Response menggunakan header keamanan minimal, termasuk CSP.

### 5.3 Privasi

- Jangan menyimpan NIK, alamat lengkap, nomor rekening, atau data sensitif lain jika tidak dibutuhkan.
- Data payroll lokal tidak boleh dikirim ke provider eksternal.
- ZIP distribusi tidak boleh membawa database, akun administrator, backup, export, log pengguna, cache, atau credential.
- Karyawan dinonaktifkan menggunakan status aktif/nonaktif, bukan hard-delete yang berisiko menghilangkan histori payroll.

---

## 6. Master Data

### 6.1 Master Karyawan

Field minimal:

- ID karyawan.
- Nama.
- PTKP bila dibutuhkan oleh versi Flask.
- Kode bagian.
- Jabatan.
- Tanggal awal kerja.
- Tanggal akhir kerja.
- Tipe gaji: `harian` atau `bulanan`.
- Gaji bulanan.
- Upah harian.
- Uang makan per hari.
- Status aktif.
- Catatan.
- `policy_code` untuk pengecualian payroll, misalnya `NO_LEMBUR`.

Fungsi:

- Tambah karyawan.
- Edit karyawan.
- Nonaktifkan karyawan.
- Menampilkan karyawan aktif/nonaktif.
- Mencegah ID karyawan duplikat.
- Menyediakan roster snapshot saat periode dibuat.

### 6.2 Master Bagian

Bagian default:

| Kode | Nama | Kategori |
|---|---|---|
| PRO | Produksi | produksi |
| FIN | Finishing | finishing |
| LAS | Besi/Las | las |
| KTR | Kantor | kantor |
| KUS | Produksi Kusen | produksi |
| OPR | Operator | produksi |

### 6.3 Master Aturan Payroll

Aturan default yang harus tersedia:

| Nama aturan | Nilai default | Keterangan |
|---|---:|---|
| `jam_kerja_normal` | 8,5 | Jam kerja normal per hari |
| `uang_makan_lembur` | 10.000 | Uang makan lembur |
| `tarif_lembur_jam` | 20.000 | Tarif lembur per jam |
| `lembur_malam_harian` | 1 | Pengali lembur malam harian |
| `lembur_malam_bulanan` | 1 | Pengali lembur malam bulanan |
| `tgl_merah_harian` | 0,5 | Tambahan tanggal merah untuk harian |
| `tgl_merah_bulanan` | 0,5 | Tambahan tanggal merah untuk bulanan |
| `thr_harian_pembagi` | 312 | Pembagi THR harian |
| `thr_harian_pengali` | 26 | Pengali THR harian |
| `batas_jam_makan_lembur` | 18,0 | Batas uang makan lembur |
| `batas_jam_lembur_malam` | 22,0 | Batas lembur malam |

Nilai aturan harus disimpan di database dan digunakan oleh formula, bukan ditulis permanen di UI.

---

## 7. Periode Payroll

Fungsi:

- Membuat periode dengan nama dan tanggal mulai.
- Menghitung tanggal selesai periode.
- Membuat minggu payroll otomatis.
- Menampilkan minggu dan rentang tanggal.
- Menampilkan hari yang berada di dalam atau di luar rentang periode.
- Membuat snapshot roster karyawan dan tarif ketika periode dibuat.
- Status periode minimal:
  - `draft`;
  - `tutup`.
- Periode yang ditutup mengunci input kehadiran, transfer, potongan, dan perubahan data payroll.
- Periode dapat dibuka kembali secara eksplisit oleh administrator.

---

## 8. Kehadiran dan Lembur

Input kehadiran dilakukan per minggu dan per tanggal.

Field kehadiran minimal:

- ID minggu.
- ID karyawan.
- Tanggal.
- Upah hari.
- Tambahan tanggal merah.
- Uang makan lembur.
- Lembur malam.
- Jam lembur.
- Keterangan.

Aturan:

- Tanggal input harus berada di dalam rentang periode payroll.
- Jam lembur mendukung pecahan, minimal interval 0,5 jam.
- Contoh yang wajib didukung: `1,5 jam`.
- Data karyawan yang ditampilkan mengikuti snapshot periode.
- Input harus ditolak ketika periode sudah ditutup.
- Kehadiran dapat dimuat, diedit, dan disimpan secara batch.

---

## 9. Formula Payroll

### 9.1 Karyawan harian

```text
Upah = Upah Harian × Hari Masuk
Uang Makan = Uang Makan/Hari × Hari Masuk
```

### 9.2 Karyawan bulanan

```text
Gaji = Gaji Bulanan
Upah Harian = 0
Uang Makan = Uang Makan/Hari × Hari Masuk
```

### 9.3 Tambahan tanggal merah

Untuk karyawan harian:

```text
Tambahan Tanggal Merah = Tarif Tanggal Merah Harian × Upah Harian × Jumlah Tanggal Merah
```

Untuk karyawan bulanan:

```text
Tambahan Tanggal Merah = Tarif Tanggal Merah Bulanan × Uang Makan/Hari × Jumlah Tanggal Merah
```

Bagian `FIN` dan `LAS` tidak mendapatkan tambahan tanggal merah.

### 9.4 Lembur

```text
Uang Makan Lembur = Tarif Uang Makan Lembur × Jumlah Uang Makan Lembur
Lembur Malam Harian = Upah Harian × Jumlah Lembur Malam
Lembur Malam Bulanan = Uang Makan/Hari × Jumlah Lembur Malam
Lembur Jam = Tarif Lembur/Jam × Total Jam Lembur
```

Karyawan dengan `policy_code=NO_LEMBUR` tidak mendapatkan komponen lembur. Kompatibilitas data lama yang menggunakan nama khusus harus tetap dipertahankan jika masih diperlukan.

### 9.5 Total penghasilan

```text
Total Penghasilan =
  Gaji Bulanan
+ Upah Harian
+ Uang Makan
+ Tambahan Tanggal Merah
+ Uang Makan Lembur
+ Lembur Malam
+ Lembur Jam
```

THR tidak masuk ke total payroll reguler.

### 9.6 Total bersih/netto

```text
Total Bersih = Total Penghasilan - Total Potongan
```

Potongan mencakup:

- potongan manual/izin;
- kasbon yang belum lunas sesuai periode;
- alokasi kasbon ke periode.

---

## 10. Rekap Gaji

Rekap harus menampilkan per karyawan:

- ID karyawan.
- Nama.
- Bagian.
- Jabatan.
- Tipe gaji.
- Gaji bulanan.
- Upah harian.
- Uang makan.
- Tambahan tanggal merah.
- Uang makan lembur.
- Lembur malam.
- Lembur jam.
- Hari masuk.
- THR terpisah.
- Potongan.
- Total penghasilan.
- Total bersih/netto.

Rekap harus memiliki baris total periode untuk komponen utama.

---

## 11. Potongan

Fungsi:

- Tambah potongan.
- Pilih karyawan.
- Jenis potongan.
- Nominal potongan.
- Keterangan.
- Hapus potongan ketika periode masih draft.
- Potongan masuk ke total netto.

---

## 12. Kasbon

Field minimal:

- ID kasbon.
- ID karyawan.
- Tanggal.
- Jenis kasbon.
- Jumlah.
- Status: `belum_lunas` atau `lunas`.
- Keterangan.

Fungsi:

- Tambah kasbon.
- Lihat daftar kasbon.
- Alokasikan cicilan ke periode tertentu.
- Validasi nominal alokasi tidak boleh melebihi saldo.
- Menandai kasbon lunas secara manual.
- Otomatis menandai lunas jika seluruh saldo sudah dialokasikan.
- Menolak alokasi ganda untuk kasbon dan periode yang sama.

---

## 13. THR

- THR tersedia sebagai menu terpisah.
- THR tidak digabung ke payroll reguler.
- THR dapat dihitung otomatis sesuai aturan.
- THR disimpan per karyawan dan periode.
- THR dapat ditampilkan dalam rekap/laporan sebagai komponen terpisah.

---

## 14. Transfer dan Selisih

Field transfer minimal:

- ID periode.
- Bank.
- Tanggal.
- Nomor referensi.
- Nominal transfer.
- Keterangan.

Dashboard transfer harus menampilkan:

```text
Target Netto
Total Sudah Transfer
Selisih = Target Netto - Total Sudah Transfer
```

Fungsi:

- Tambah transaksi transfer.
- Hapus transaksi transfer saat periode masih draft.
- Menampilkan riwayat transfer.
- Menampilkan bank dan nomor referensi.
- Membandingkan transfer dengan total bersih/netto, bukan total penghasilan bruto.

---

## 15. Slip Gaji

- Memilih periode.
- Memilih karyawan.
- Menampilkan slip individual.
- Menampilkan identitas payroll yang diperlukan tanpa membocorkan data sensitif berlebihan.
- Menampilkan komponen penghasilan, potongan, total bersih, dan THR bila ada.
- Slip dapat dicetak melalui browser.
- Data slip mengikuti formula dan snapshot periode.

---

## 16. Laporan dan Export

Jenis laporan:

1. Laporan internal lengkap.
2. Laporan konsultan ringkas.

Laporan konsultan minimal memuat:

- Kode.
- Nama.
- Tipe gaji.
- Hari masuk.
- Gaji bulanan.
- Upah harian.
- Uang makan.
- Lembur.
- Total tunjangan.
- Potongan.
- Total gaji/upah netto.

Laporan internal memuat rincian komponen payroll.

Export:

- Format `.xlsx`.
- Judul perusahaan dan periode.
- Header rapi.
- Total periode.
- Nama file mencantumkan jenis laporan dan ID/periode.
- File export disimpan lokal.

---

## 17. Backup dan Restore

Fungsi:

- Membuat backup database.
- Menampilkan daftar backup.
- Restore backup yang dipilih.
- Sebelum restore, database aktif diamankan otomatis.
- Path backup harus divalidasi.
- Restore harus memerlukan konfirmasi.
- Backup tidak ikut dalam ZIP distribusi awal.

---

## 18. Audit Log

Audit log minimal mencatat:

- Waktu.
- Aksi.
- Tabel/modul.
- ID data.
- Detail.

Aksi yang perlu dicatat antara lain:

- tambah/edit karyawan;
- nonaktifkan karyawan;
- buat periode;
- simpan kehadiran;
- tambah/hapus transfer;
- tambah/hapus potongan;
- tambah/alokasi/lunasi kasbon;
- hitung THR;
- export laporan;
- backup;
- restore.

---

## 19. Struktur Teknis yang Diinginkan

### Runtime pengguna akhir

- Vue 3 hasil build statis.
- Backend Python Standard Library non-Flask.
- SQLite lokal.
- Runtime Python portable Windows.
- Launcher `jalankan.bat`.

### Source development

- Source Vue lengkap.
- TypeScript.
- Vite.
- Element Plus.
- Vue Router.
- Pinia bila digunakan untuk state bersama.
- Test suite Python dan E2E Playwright.
- Script build dan packaging.

---

## 20. Kriteria Penerimaan

Aplikasi dianggap memenuhi syarat apabila:

- [ ] Dapat dijalankan melalui `jalankan.bat` tanpa instalasi Python pada komputer pengguna.
- [ ] Setup administrator dan login berfungsi.
- [ ] Data tersimpan di SQLite lokal.
- [ ] Master karyawan, bagian, dan aturan tersedia.
- [ ] Periode membuat minggu otomatis dan snapshot roster.
- [ ] Input kehadiran mingguan dan tanggal berfungsi.
- [ ] Jam lembur pecahan seperti 1,5 jam dihitung benar.
- [ ] Formula harian dan bulanan sesuai aturan.
- [ ] Bagian FIN/LAS tidak mendapat tambahan tanggal merah.
- [ ] Policy `NO_LEMBUR` berfungsi.
- [ ] Potongan dan kasbon masuk ke perhitungan netto.
- [ ] Kasbon dapat dialokasikan dan dilunasi.
- [ ] THR terpisah dari payroll reguler.
- [ ] Transfer dibandingkan dengan target netto.
- [ ] Slip individual dapat dicetak.
- [ ] Laporan internal/konsultan dapat diexport ke Excel.
- [ ] Periode tertutup mengunci perubahan payroll.
- [ ] Backup dan restore berfungsi.
- [ ] Audit log tersedia.
- [ ] Tidak ada horizontal overflow pada mobile.
- [ ] Test otomatis dan E2E lulus.
- [ ] ZIP portable tidak membawa data pengguna atau credential.
- [ ] Source project dapat diedit dan dibuild ulang.

---

## 21. Batasan dan Catatan

- Pengujian executable Windows langsung harus dilakukan pada Windows aktual. Build host Linux hanya dapat memverifikasi source, build frontend, struktur runtime PE, HTTP smoke, dan E2E browser.
- Perubahan formula payroll harus melalui review karena dapat memengaruhi hasil gaji historis.
- Data payroll yang sudah diproses harus dibackup sebelum migrasi atau revisi besar.
- Perubahan UI tidak boleh mengubah formula dan perilaku bisnis tanpa persetujuan.
