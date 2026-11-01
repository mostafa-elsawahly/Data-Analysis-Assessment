import sys, time, requests, pandas as pd
from pathlib import Path
from clean_lib import clean

BASE = "https://data.opm.gov/api/v1/files"
DATASETS = sys.argv[1:] or ["accessions", "separations"]
OUT = Path("datasets")
TMP = Path("tmp")
TMP.mkdir(exist_ok=True)

def get(url, **kw):
    for i in range(5):
        r = requests.get(url, timeout=180, **kw)
        if r.status_code == 429:
            time.sleep(15 * (i + 1)); continue
        return r
    r.raise_for_status()

for ds in DATASETS:
    for year in range(2022, 2027):
        r = get(f"{BASE}/{ds}", params={"current": "true", "year": year})
        if r.status_code == 204 or not r.content:
            print("No data:", ds, year); continue
        for f in sorted(r.json(), key=lambda x: x["month"]):
            local = OUT / str(year) / ds.capitalize() / f"{f['filename']}.parquet"
            if local.exists():
                print("Exists, skipping:", local); continue

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
            print("Done:", local, len(df), "rows")