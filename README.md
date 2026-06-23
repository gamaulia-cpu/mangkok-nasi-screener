# Mangkuk Nasi Wyckoff Screener — IDX

Screener otomatis untuk mendeteksi **akumulasi Wyckoff fase A/B/C** (pola mangkuk nasi) pada saham IDX.

Berdasarkan 4 komponen:

| Komponen | Bobot | Keterangan |
|----------|-------|------------|
| **Bowl Formation** | 25 | Range 15-60%, sideways <15%, price pos 30-80% |
| **Trend Efficiency** | 10 | Return 20-bar antara -30% s/d +15% |
| **Vol Contraction** | 15 | Volume 10-bar terakhir <70% MA volume 20 |
| **Spring (Vol Climax)** | 15 | Volume spike >2.5x MA volume dalam 20 bar terakhir |
| **Total** | **65** | Sinyal hanya jika 65/65 |

## Cara Pakai

### Lokal

```bash
pip install -r requirements.txt
python screener.py stocks.txt           # hanya 65/65
python screener.py stocks.txt --all     # semua skor
python screener.py stocks.txt --csv hasil.csv
python screener.py --single AGII.JK     # screen 1 saham
```

### GitHub Actions (otomatis)

- Setiap hari Senin-Jumat **17:30 WIB** setelah bursa tutup
- Bisa di-trigger manual via **Workflow Dispatch** di tab Actions
- Hasil otomatis di-upload sebagai **artifact** (CSV + Markdown report)

## Output

Sinyal **65/65** berarti keempat komponen akumulasi Wyckoff terpenuhi:

- **Fase A** — Spring / Volume Climax (selling climax + smart money accumulation)
- **Fase B** — Otomatis Rally / Bowl (harga rebound + sideways, bowl terbentuk)
- **Fase C** — Kontraksi / Test (volume mengering, supply habis)

> ⚠️ Ini hanya screener — bukan sinyal beli instan. Konfirmasi tambahan (SOS breakout, LPS pullback) tetap diperlukan.
