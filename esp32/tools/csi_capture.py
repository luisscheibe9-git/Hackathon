#!/usr/bin/env python3
"""Record Espressif CSI CSV, or guide the roommate's three-round motion test."""
import argparse
import csv
import json
import math
import statistics
import time
from datetime import datetime
from pathlib import Path

import serial
from serial.tools import list_ports


def parse_row(line):
    if not line.startswith('CSI_DATA,'):
        return None
    row = next(csv.reader([line]))
    if len(row) != 25:
        return None
    values = json.loads(row[24])
    if len(values) != int(row[22]) or len(values) < 128:
        return None
    if any(type(x) is not int or not -128 <= x <= 127 for x in values):
        return None
    # Original ESP32 LLTF: retain active tones, excluding DC, guards, and
    # the first two complex samples (which can be invalid per the CSI flag).
    tones = list(range(6, 32)) + list(range(33, 59))
    amps = [math.hypot(values[2*i], values[2*i+1]) for i in tones]
    rms = math.sqrt(statistics.mean(x*x for x in amps))
    if not rms:
        return None
    return {
        'rssi': int(row[3]), 'channel': int(row[16]),
        'key': tuple(row[i] for i in (2, 4, 5, 6, 7, 16, 17, 22)),
        'amplitudes': [x/rms for x in amps], 'raw': line.strip(),
    }


def record(port, writer, seconds, trial, label):
    port.reset_input_buffer()
    start = last_report = time.monotonic()
    previous = {}
    changes = []
    frames = 0
    malformed = 0
    while time.monotonic() - start < seconds:
        line = port.readline().decode('utf-8', errors='replace').strip()
        try:
            frame = parse_row(line)
        except (ValueError, IndexError, TypeError, csv.Error):
            malformed += 1
            continue
        if frame is None:
            continue
        now = time.monotonic()
        old = previous.get(frame['key'])
        delta = None
        if old and now-old[0] < 1:
            delta = statistics.mean(abs(a-b) for a, b in zip(frame['amplitudes'], old[1]))
            changes.append(delta)
        previous[frame['key']] = (now, frame['amplitudes'])
        frames += 1
        writer.writerow([time.time(), trial, label, frame['rssi'], frame['channel'],
                         '' if delta is None else delta, frame['raw']])
        if now-last_report >= 1:
            value = 'waiting' if delta is None else f'{delta:.4f}'
            print(f'\r{label}: {frames} frames | RSSI {frame["rssi"]} dBm | change {value}    ', end='', flush=True)
            last_report = now
    elapsed = time.monotonic()-start
    median = statistics.median(changes) if changes else None
    print(f'\n{label}: {frames} frames ({frames/elapsed:.1f}/s); median change: {median}; malformed: {malformed}')
    return {'trial': trial, 'label': label, 'frames': frames, 'fps': frames/elapsed,
            'median_change': median, 'malformed': malformed}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--port')
    ap.add_argument('--baud', type=int, default=921600)
    ap.add_argument('--seconds', type=float, default=20)
    ap.add_argument('--trials', type=int, default=3)
    ap.add_argument('--test', action='store_true', help='Guided empty/walking/standing trials')
    args = ap.parse_args()
    if args.seconds <= 0 or args.trials <= 0:
        ap.error('seconds and trials must be positive')
    if not args.port:
        ports = [p.device for p in list_ports.comports() if p.vid == 0x10C4 and p.pid == 0xEA60]
        if len(ports) != 1:
            ap.error('Connect one CP2102 ESP32, or specify --port. No firmware is changed by this tool.')
        args.port = ports[0]
    output = Path(__file__).resolve().parents[1] / 'data'
    output.mkdir(exist_ok=True)
    path = output / f'csi-motion-{datetime.now():%Y%m%d-%H%M%S}.csv'
    results = []
    # Keep DTR/RTS deasserted to avoid deliberately resetting the board.
    connection = serial.Serial(baudrate=args.baud, timeout=.25)
    connection.dtr = connection.rts = False
    connection.port = args.port
    connection.open()
    try:
        with connection, path.open('w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['host_timestamp', 'trial', 'label', 'rssi', 'channel', 'change', 'raw_csi'])
            if args.test:
                tasks = [('empty', 'leave the room'), ('walking', 'walk across the router-to-board path'),
                         ('standing', 'stand still near the middle of the path')]
                for trial in range(1, args.trials+1):
                    for label, instruction in tasks:
                        input(f'\nTrial {trial}/{args.trials}, {label}: {instruction}. Press Enter when ready: ')
                        print('Recording begins in 6 seconds…', flush=True)
                        time.sleep(6)
                        results.append(record(connection, writer, args.seconds, trial, label))
                        f.flush()
            else:
                results.append(record(connection, writer, args.seconds, 0, 'unlabelled'))
    finally:
        connection.close()
        path.with_suffix('.json').write_text(json.dumps(results, indent=2)+'\n')
        print(f'Saved: {path}')
    if not results or any(r['frames'] == 0 for r in results):
        raise SystemExit('No CSI in at least one recording. Check Wi-Fi, antenna, serial baud, and firmware.')


if __name__ == '__main__':
    try:
        main()
    except (serial.SerialException, KeyboardInterrupt) as error:
        raise SystemExit(str(error) or 'Stopped')
