# Informasi Rilis

**Produk:** Sistem Rekap Gaji & Upah PT. Mega Artha Makmur  
**Versi:** Art Pro Portable v1.0.0  
**Arsitektur:** Vue 3 + Element Plus + Pinia + Vue Router; backend Python standard library non-Flask; SQLite lokal.

## Referensi desain

Frontend mengikuti arsitektur dan bahasa visual Art Design Pro dari `https://github.com/Daymychen/art-design-pro`, commit referensi `f3aaf58eec1a0e988f162352c33862327a484f95` (MIT). Source upstream tidak diperlukan saat runtime.

## Keamanan

- Server hanya bind ke `127.0.0.1`.
- Password disimpan sebagai PBKDF2-HMAC-SHA256.
- Session menggunakan token acak dan cookie HttpOnly/SameSite=Strict.
- Request perubahan data wajib membawa CSRF token.
- Database, akun, session, backup, export, dan data pengguna tidak disertakan dalam ZIP.

## Catatan kompatibilitas

- Runtime Windows: Python 3.8.10 embeddable 64-bit.
- Frontend ditargetkan ke Chrome/Edge 109.
- Windows 7 memerlukan SP1 serta browser kompatibel. Pengujian executable Windows langsung tidak tersedia pada build host Linux ARM64; backend, build Vue, HTTP smoke, dan WebKit E2E telah diuji pada build host.
