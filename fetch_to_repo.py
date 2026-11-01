import os, sys, time, requests, pandas as pd
from pathlib import Path
from clean_lib import clean

BASE = "https://data.opm.gov/api/v1/files"
DATASETS = sys.argv[1:] or ["accessions", "separations"]
YEAR_FROM = int(os.getenv("YEAR_FROM", "2022"))
YEAR_TO = int(os.getenv("YEAR_TO", "2026"))
MONTH_FROM = int(os.getenv("MONTH_FROM", "1"))
MONTH_TO = int(os.getenv("MONTH_TO", "12"))
OUT = Path(os.getenv("OUT_DIR", "datasets"))
TMP = Path("tmp")
TMP.mkdir(exist_ok=True)

EXISTING = set()
ef = os.getenv("EXISTING_FILE")
if ef and Path(ef).exists():
    EXISTING = set(Path(ef).read_text().split())

def get(url, **kw):
    for i in range(5):
        r = requests.get(url, timeout=180, **kw)
        if r.status_code == 429:
            time.sleep(15 * (i + 1)); continue
        return r
    r.raise_for_status()

for ds in DATASETS:
    for year in range(YEAR_FROM, YEAR_TO + 1):
        r = get(f"{BASE}/{ds}", params={"current": "true", "year": year})
        if r.status_code == 204 or not r.content:
            print("No data:", ds, year); continue
        for f in sorted(r.json(), key=lambda x: x["month"]):
            if not (MONTH_FROM <= int(f["month"]) <= MONTH_TO):
                continue
            rel = f"{year}/{ds.capitalize()}/{f['filename']}.parquet"
            local = OUT / rel
            if local.exists() or rel in EXISTING:
                print("Exists, skipping:", rel); continue

            raw = TMP / local.name
            url = f"{BASE}/{ds}/{f['year']}/{f['month']}/{f['version']}/download"
            with get(url, stream=True) as resp:
                resp.raise_for_status()
                with open(raw, "wb") as fh:
                    for chunk in resp.iter_content(1 << 20):
                        fh.write(chunk)

            df = clean(pd.read_parquet(raw), f)
            raw.unlink()
            local.parent.mkdir(parents=True, exist_ok=True)
            df.to_parquet(local, index=False, compression="zstd")
            print("Done:", rel, len(df), "rows")
            del df
