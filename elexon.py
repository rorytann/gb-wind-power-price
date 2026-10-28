import requests
import pandas as pd

BASE = "https://data.elexon.co.uk/bmrs/api/v1"

def _fetch_mid_chunk(start, end):
    params = {"from": start, "to": end}
    r = requests.get(f"{BASE}/balancing/pricing/market-index", params=params, timeout = 30)
    r.raise_for_status()
    payload = r.json()

    df = pd.DataFrame(payload["data"])
    df = df[df["volume"] > 0].copy()
    df["startTime"] = pd.to_datetime(df["startTime"], utc = True)
    df["pv"] = df["price"] * df["volume"]
    g = df.groupby("startTime")[["pv", "volume"]].sum()
    g["price"] = g["pv"] / g["volume"]

    return g[["price", "volume"]]


def fetch_mid(start,end):
    """

    Half-hourly APX market index price (£/Mwh), indexed
    by UTC start time.

    """  

    edges = list(pd.date_range(start, end, freq="7D"))
    if edges[-1] < pd.Timestamp(end):     
        edges.append(pd.Timestamp(end))

    chunks = []
    for a, b in zip(edges[:-1], edges[1:]):
        chunk = _fetch_mid_chunk(a.strftime("%Y-%m-%dT%H:%MZ"),
                                b.strftime("%Y-%m-%dT%H:%MZ"))
        chunks.append(chunk)

    df = pd.concat(chunks)
    df = df[~df.index.duplicated()]

    return df

def _fetch_wind_chunk(start, end):
    params = {"settlementDateFrom": start, "settlementDateTo": end, "fuelType": "WIND"}
    r = requests.get(f"{BASE}/datasets/FUELHH", params=params, timeout = 30)
    r.raise_for_status()
    payload = r.json()
    
    df = pd.DataFrame(payload["data"])
    df = df[df["fuelType"] == "WIND"].copy()
    df["startTime"] = pd.to_datetime(df["startTime"], utc = True)
    df = df.sort_values("startTime")
    df = df.set_index("startTime")

    return df[["generation"]].rename(columns={"generation": "wind_mw"})


def fetch_wind(start, end):
    
    edges = list(pd.date_range(start, end, freq="7D"))
    if edges[-1] < pd.Timestamp(end):      
        edges.append(pd.Timestamp(end))

    chunks = []
    for a, b in zip(edges[:-1], edges[1:]):
        chunk = _fetch_wind_chunk(a.strftime("%Y-%m-%d"),
                                b.strftime("%Y-%m-%d"))
        chunks.append(chunk)

    df = pd.concat(chunks)
    df = df[~df.index.duplicated()]

    return df