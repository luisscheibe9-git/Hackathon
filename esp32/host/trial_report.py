"""Summarise a demo trial from the server's live log (esp32/data/live-log-<date>.csv).

Prints every change of alert state with its clock time, how many fall alerts fired, and the
lowest packet rate per sensing path, so a rehearsal can be scored as pass/fail.

    python host/trial_report.py                    # today's log, last 15 minutes
    python host/trial_report.py --since 10:05      # from 10:05 today
    python host/trial_report.py --log data/live-log-20261115.csv --since 10:05 --until 10:20
"""
import argparse
import csv
import glob
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")


def clock_to_t(clock, day):
    return time.mktime(time.strptime(f"{day} {clock}", "%Y%m%d %H:%M"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--log", help="live-log CSV (default: newest in esp32/data)")
    ap.add_argument("--since", help="HH:MM today (default: 15 minutes ago)")
    ap.add_argument("--until", help="HH:MM today (default: now)")
    a = ap.parse_args()

    log = a.log or max(glob.glob(os.path.join(DATA, "live-log-*.csv")), default=None, key=os.path.getmtime)
    if not log:
        raise SystemExit("No live log found. Start host/server.py and run a trial first.")
    day = os.path.basename(log)[9:17] if os.path.basename(log).startswith("live-log-") else time.strftime("%Y%m%d")
    t0 = clock_to_t(a.since, day) if a.since else time.time() - 15 * 60
    t1 = clock_to_t(a.until, day) + 59 if a.until else time.time()

    rows = [r for r in csv.DictReader(open(log, newline="")) if t0 <= float(r["t"]) <= t1]
    if not rows:
        raise SystemExit(f"No rows between those times in {log}.")

    print(f"{log}\n{rows[0]['clock']} to {rows[-1]['clock']} ({len(rows)} ticks of 0.5 s)\n")
    print("clock     state            model guess")
    prev, alerts, low_pps = None, 0, {}
    for r in rows:
        key = (r["state"], r["best"])
        if key != prev:
            print(f"{r['clock']}  {r['state']:<16} {r['best']} ({float(r['confidence']):.0%})")
            if r["state"] == "alert" and (prev is None or prev[0] != "alert"):
                alerts += 1
            prev = key
        for part in filter(None, r["pps"].split("|")):
            link, pps = part.split(":")
            low_pps[link] = min(low_pps.get(link, 1e9), float(pps))

    print(f"\nFall alerts fired: {alerts}")
    weak = {k: v for k, v in low_pps.items() if v < 10}
    print("Lowest packets/s per path: " + ", ".join(f"{k} {v:.0f}" for k, v in sorted(low_pps.items())))
    if weak:
        print("WARNING: path(s) dropped below 10 packets/s: " + ", ".join(sorted(weak))
              + ". Check power and antennas before the demo.")


if __name__ == "__main__":
    main()
