import pandas as pd
from pandas.api.types import is_string_dtype, is_object_dtype

NULL_TOKENS = {"", "*", "INVALID", "REDACTED"}   # عدّلها لو عايز
INT_COLS    = ["count"]
FLOAT_COLS  = ["annualized_adjusted_basic_pay", "length_of_service_years"]
DATE_COLS   = ["appointment_not_to_exceed_date", "service_computation_date_leave"]

def clean(df: pd.DataFrame, meta: dict) -> pd.DataFrame:
    df = df.copy()

    # أسماء الأعمدة
    df.columns = (df.columns.str.strip().str.lower()
                  .str.replace(r"\W+", "_", regex=True))

    # النصوص: trim + تحويل الـ placeholders لـ NULL
    for c in df.columns:
        if is_string_dtype(df[c]) or is_object_dtype(df[c]):
            s = df[c].astype("string").str.strip()
            df[c] = s.mask(s.str.upper().isin(NULL_TOKENS))

    # الأنواع
    for c in INT_COLS:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")
    for c in FLOAT_COLS:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in DATE_COLS:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")

    # أعمدة التتبّع
    df["data_year"]   = int(meta["year"])
    df["data_month"]  = int(meta["month"])
    df["source_file"] = meta["filename"]
    return df