import csv, datetime, sys

csv_file = sys.argv[1] if len(sys.argv) > 1 else 'hasil_screener.csv'
rows = []
with open(csv_file) as f:
    for r in csv.DictReader(f):
        rows.append(r)
perfect = [r for r in rows if int(r['score']) == 65]
now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M WIB')
md = '# Mangkuk Nasi Screener Report\n\n'
md += f'**Tanggal:** {now}\n\n'
md += f'**Total saham discan:** {len(rows)}\n\n'
md += '## Sinyal 65/65\n\n'
if perfect:
    md += '| Symbol | Close | Volume | Fase |\n|--------|-------|--------|------|\n'
    for r in perfect:
        md += f"| {r['symbol']} | {r['close']} | {r['volume']} | {r['fase']} |\n"
else:
    md += 'Tidak ada sinyal 65/65.\n\n'
md += '## Semua Score\n\n'
md += '| Symbol | Score | Fase | Bowl | Trend | Vol Contract | Spring |\n'
md += '|--------|-------|------|------|-------|-------------|--------|\n'
for r in rows:
    md += f"| {r['symbol']} | {r['score']} | {r['fase']} | {r['bowl']} | {r['trend_ok']} | {r['vol_contract']} | {r['spring']} |\n"
with open('report.md', 'w') as f:
    f.write(md)
print(f'Report generated: {len(perfect)}/{len(rows)} perfect scores')
