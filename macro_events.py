# macro_events.py
# Pull Macro Events (FOMC / CPI / PPI / PCE) into one clean table
#
# Sources:
# - CPI & PPI: BLS iCal (.ics)
# - PCE: proxied by BEA "Personal Income and Outlays" release dates (contains PCE / core PCE)
# - FOMC: Federal Reserve FOMC calendars page (scheduled meetings)
#
# Install:
#   pip install pandas requests beautifulsoup4
#
# Examples:
#   python macro_events.py --start 2023-01-01 --end 2026-01-12 --save-csv macro_events.csv
#   python macro_events.py --start 2024-01-01 --end 2024-12-31 --save-json macro_events.json

import argparse
import io
import re
from datetime import datetime, date
from typing import List, Dict, Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup

BLS_ICS_URL = "https://www.bls.gov/schedule/news_release/bls.ics"
BEA_ICS_URL = "https://www.bea.gov/news/schedule/ics/online-calendar-subscription.ics"
FOMC_CAL_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"

MONTHS = {
    "January": 1, "February": 2, "March": 3, "April": 4,
    "May": 5, "June": 6, "July": 7, "August": 8,
    "September": 9, "October": 10, "November": 11, "December": 12
}


def _unfold_ics_lines(text: str) -> List[str]:
    """RFC5545 line folding: lines starting with space/tab continue previous line."""
    lines = text.splitlines()
    out: List[str] = []
    for ln in lines:
        if (ln.startswith(" ") or ln.startswith("\t")) and out:
            out[-1] += ln[1:]
        else:
            out.append(ln)
    return out


def _parse_ics_dt(dt_raw: str) -> datetime:
    """
    Parse DTSTART-like values:
      - 20250107T133000Z
      - 20250107T133000
      - 20250107 (DATE)
    """
    dt_raw = dt_raw.strip()
    if re.fullmatch(r"\d{8}", dt_raw):
        return datetime.strptime(dt_raw, "%Y%m%d")
    if dt_raw.endswith("Z"):
        return datetime.strptime(dt_raw, "%Y%m%dT%H%M%SZ")
    return datetime.strptime(dt_raw, "%Y%m%dT%H%M%S")


def parse_ics_events(ics_text: str) -> pd.DataFrame:
    """
    Minimal iCal parser for VEVENT blocks; returns columns: DATE, SUMMARY.
    """
    lines = _unfold_ics_lines(ics_text)

    events: List[Dict[str, object]] = []
    in_event = False
    cur: Dict[str, object] = {}

    for ln in lines:
        if ln == "BEGIN:VEVENT":
            in_event = True
            cur = {}
            continue
        if ln == "END:VEVENT":
            if "SUMMARY" in cur and "DTSTART" in cur:
                events.append(cur)
            in_event = False
            cur = {}
            continue
        if not in_event:
            continue

        if ln.startswith("SUMMARY:"):
            cur["SUMMARY"] = ln.split("SUMMARY:", 1)[1].strip()
        elif ln.startswith("DTSTART"):
            # Handles "DTSTART:..." and "DTSTART;...:..."
            _, val = ln.split(":", 1)
            cur["DTSTART"] = _parse_ics_dt(val)

    if not events:
        return pd.DataFrame(columns=["DATE", "SUMMARY"])

    df = pd.DataFrame(events)
    df["DTSTART"] = pd.to_datetime(df["DTSTART"], utc=False)
    df["DATE"] = df["DTSTART"].dt.date
    return df[["DATE", "SUMMARY"]]


def fetch_ics(url: str) -> pd.DataFrame:
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return parse_ics_events(r.text)


def _within_range(df: pd.DataFrame, start_d: date, end_d: date) -> pd.DataFrame:
    if df.empty:
        return df
    return df[(df["DATE"] >= start_d) & (df["DATE"] <= end_d)].copy()


def pull_cpi_ppi(start_d: date, end_d: date) -> pd.DataFrame:
    bls = fetch_ics(BLS_ICS_URL)
    bls = _within_range(bls, start_d, end_d)

    # BLS summaries typically contain these phrases
    cpi_mask = bls["SUMMARY"].str.contains("Consumer Price Index", case=False, na=False)
    ppi_mask = bls["SUMMARY"].str.contains("Producer Price Index", case=False, na=False)

    out = []
    if cpi_mask.any():
        tmp = bls.loc[cpi_mask, ["DATE", "SUMMARY"]].copy()
        tmp["event"] = "CPI"
        tmp["source"] = "BLS iCal"
        out.append(tmp)
    if ppi_mask.any():
        tmp = bls.loc[ppi_mask, ["DATE", "SUMMARY"]].copy()
        tmp["event"] = "PPI"
        tmp["source"] = "BLS iCal"
        out.append(tmp)

    if not out:
        return pd.DataFrame(columns=["date", "event", "summary", "source"])

    df = pd.concat(out, ignore_index=True)
    df = df.rename(columns={"DATE": "date", "SUMMARY": "summary"})
    return df[["date", "event", "summary", "source"]].sort_values("date")


def pull_pce_proxy(start_d: date, end_d: date) -> pd.DataFrame:
    """
    PCE release dates are typically the BEA 'Personal Income and Outlays' release.
    That release includes PCE price index / core PCE, so we use it as PCE event dates.
    """
    bea = fetch_ics(BEA_ICS_URL)
    bea = _within_range(bea, start_d, end_d)

    mask = bea["SUMMARY"].str.contains("Personal Income and Outlays", case=False, na=False)
    if not mask.any():
        return pd.DataFrame(columns=["date", "event", "summary", "source"])

    df = bea.loc[mask, ["DATE", "SUMMARY"]].copy()
    df["event"] = "PCE"
    df["source"] = "BEA iCal (Personal Income & Outlays)"
    df = df.rename(columns={"DATE": "date", "SUMMARY": "summary"})
    return df[["date", "event", "summary", "source"]].sort_values("date")


def pull_fomc_meetings(start_d: date, end_d: date) -> pd.DataFrame:
    """
    Scrape scheduled FOMC meeting dates from the Fed page.
    We mark the *decision day* as the end date of a meeting range (e.g., Jan 30-31 -> Jan 31).
    """
    r = requests.get(FOMC_CAL_URL, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    text = soup.get_text("\n")

    meetings = []
    for y in range(start_d.year, end_d.year + 1):
        # Extract a chunk for the year. This is heuristic but works well in practice.
        # Try to find "YYYY FOMC Meetings" section.
        m = re.search(rf"{y}\s+FOMC Meetings(.*?)(\n\s*\n)", text, flags=re.S)
        if not m:
            # fallback: take a larger slice until next year heading if present
            m = re.search(rf"{y}\s+FOMC Meetings(.*?){y-1}\s+FOMC Meetings", text, flags=re.S)
        if not m:
            continue

        sec = m.group(1)
        lines = [ln.strip() for ln in sec.splitlines() if ln.strip()]

        i = 0
        while i < len(lines) - 1:
            month = lines[i]
            if month in MONTHS:
                day_line = lines[i + 1]

                # Skip notation votes or other non-meeting items
                if "notation" in day_line.lower():
                    i += 2
                    continue

                # Match date ranges like "30-31" or "30-1" (month rollover)
                rng = re.match(r"^(\d{1,2})\s*-\s*(\d{1,2})\*?$", day_line)
                single = re.match(r"^(\d{1,2})\*?$", day_line)

                if rng:
                    d1 = int(rng.group(1))
                    d2 = int(rng.group(2))
                    mm = MONTHS[month]
                    yy = y

                    end_mm, end_yy = mm, yy
                    if d2 < d1:
                        end_mm += 1
                        if end_mm == 13:
                            end_mm = 1
                            end_yy += 1

                    try:
                        decision_day = date(end_yy, end_mm, d2)
                        meetings.append((decision_day, "FOMC decision day (scheduled)", "Federal Reserve (FOMC calendars)"))
                    except ValueError:
                        pass

                elif single:
                    d = int(single.group(1))
                    mm = MONTHS[month]
                    try:
                        decision_day = date(y, mm, d)
                        meetings.append((decision_day, "FOMC meeting (scheduled)", "Federal Reserve (FOMC calendars)"))
                    except ValueError:
                        pass

                i += 2
            else:
                i += 1

    if not meetings:
        return pd.DataFrame(columns=["date", "event", "summary", "source"])

    df = pd.DataFrame(meetings, columns=["date", "summary", "source"]).drop_duplicates(subset=["date", "summary"])
    df = df[(df["date"] >= start_d) & (df["date"] <= end_d)].sort_values("date")
    df["event"] = "FOMC"
    return df[["date", "event", "summary", "source"]]


def pull_all_macro_events(start: str, end: str) -> pd.DataFrame:
    start_d = datetime.strptime(start, "%Y-%m-%d").date()
    end_d = datetime.strptime(end, "%Y-%m-%d").date()

    parts = [
        pull_fomc_meetings(start_d, end_d),
        pull_cpi_ppi(start_d, end_d),
        pull_pce_proxy(start_d, end_d),
    ]
    df = pd.concat([p for p in parts if not p.empty], ignore_index=True)
    if df.empty:
        return df

    df = df.sort_values(["date", "event"]).reset_index(drop=True)
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=str, required=True, help="YYYY-MM-DD")
    ap.add_argument("--end", type=str, required=True, help="YYYY-MM-DD")
    ap.add_argument("--save-csv", type=str, default=None, help="Path to save CSV")
    ap.add_argument("--save-json", type=str, default=None, help="Path to save JSON")
    args = ap.parse_args()

    df = pull_all_macro_events(args.start, args.end)

    print(f"Pulled {len(df)} events from {args.start} to {args.end}")
    if not df.empty:
        print(df.tail(20).to_string(index=False))

    if args.save_csv:
        df.to_csv(args.save_csv, index=False)
        print(f"Saved CSV -> {args.save_csv}")

    if args.save_json:
        df.to_json(args.save_json, orient="records", date_format="iso")
        print(f"Saved JSON -> {args.save_json}")


if __name__ == "__main__":
    main()
