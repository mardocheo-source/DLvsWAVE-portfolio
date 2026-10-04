#!/usr/bin/env python3
import os
import sys
import glob
import csv
import argparse
from datetime import datetime, timedelta
from collections import Counter

def main():
    parser = argparse.ArgumentParser(description="Find strongest forecast peak of previous cadence and compute next cadence window.")
    parser.add_argument("--prev-phase-dir", required=True, help="Path to previous phase directory (e.g. /path/to/30d)")
    args = parser.parse_args()

    prev_phase_dir = os.path.abspath(args.prev-phase-dir if hasattr(args, "prev-phase-dir") else args.prev_phase_dir)
    
    # 1. Search for best_trials_index.csv inside prev_phase_dir (recursively or in main_*)
    pattern = os.path.join(prev_phase_dir, "**", "best_trials_index.csv")
    files = glob.glob(pattern, recursive=True)
    
    if not files:
        print(f"# Error: No best_trials_index.csv files found under {prev_phase_dir}", file=sys.stderr)
        sys.exit(1)
        
    winner_row = None
    winner_score = -999999.0
    winner_file_path = None
    
    # 2. Iterate and find the absolute best trial across all runs in that phase (comparing history vs no-history)
    for f in files:
        try:
            with open(f, 'r', encoding='utf-8') as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    if not row.get('forecast_csv'):
                        continue
                    score = None
                    for col in ['overall', 'overall_mean']:
                        if col in row and row[col]:
                            try:
                                score = float(row[col])
                                break
                            except ValueError:
                                pass
                    if score is not None and score > winner_score:
                        winner_score = score
                        winner_row = row
                        winner_file_path = f
        except Exception as e:
            print(f"# Warning: failed to read {f}: {e}", file=sys.stderr)
            
    if winner_row is None:
        print(f"# Error: No valid trials found in best_trials_index.csv files under {prev_phase_dir}", file=sys.stderr)
        sys.exit(1)
        
    # 3. Locate forecast CSV path
    forecast_path = winner_row.get('forecast_csv')
    if not forecast_path or not os.path.exists(forecast_path):
        if forecast_path:
            rel_name = os.path.basename(forecast_path)
            sibling_path = os.path.join(os.path.dirname(winner_file_path), "master_with_usgs_core_astrofmt", rel_name)
            if os.path.exists(sibling_path):
                forecast_path = sibling_path
            else:
                sibling_path2 = os.path.join(os.path.dirname(winner_file_path), rel_name)
                if os.path.exists(sibling_path2):
                    forecast_path = sibling_path2
                else:
                    # Look recursively for the file name in the same pulsar_train directory
                    search_pattern = os.path.join(os.path.dirname(winner_file_path), "**", rel_name)
                    found = glob.glob(search_pattern, recursive=True)
                    if found:
                        forecast_path = found[0]
                    else:
                        forecast_path = None
                        
    if not forecast_path or not os.path.exists(forecast_path):
        print(f"# Error: Forecast CSV file not found: {winner_row.get('forecast_csv')}", file=sys.stderr)
        sys.exit(1)
        
    # 4. Read forecast CSV and find peak row
    with open(forecast_path, 'r', encoding='utf-8') as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
        
    if not rows:
        print(f"# Error: Forecast CSV is empty: {forecast_path}", file=sys.stderr)
        sys.exit(1)
        
    pred_col = None
    for col in ['pred_recalibrated', 'predicted']:
        if col in rows[0]:
            pred_col = col
            break
            
    if not pred_col:
        print(f"# Error: Could not find prediction column (predicted/pred_recalibrated) in {forecast_path}", file=sys.stderr)
        sys.exit(1)
        
    best_row = max(rows, key=lambda r: float(r[pred_col]))
    peak_date_str = best_row['date']
    peak_val = float(best_row[pred_col])
    
    # 5. Detect Cadence
    dates = [datetime.strptime(r['date'], "%Y-%m-%d") for r in rows]
    dates.sort()
    diffs = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
    if diffs:
        cadence_days = Counter(diffs).most_common(1)[0][0]
    else:
        cadence_days = 30
        for part in ["30d", "7d", "3d"]:
            if f"/{part}/" in forecast_path or f"/{part}/" in prev_phase_dir:
                cadence_days = int(part[:-1])
                break
                
    if 25 <= cadence_days <= 35:
        cadence_days = 30
    elif 5 <= cadence_days <= 10:
        cadence_days = 7
    elif 2 <= cadence_days <= 4:
        cadence_days = 3
        
    # 6. Calculate slot start/end and new window with 7d buffer
    peak_date = datetime.strptime(peak_date_str, "%Y-%m-%d")
    slot_start = peak_date
    slot_end = slot_start + timedelta(days=cadence_days)
    
    new_start = slot_start - timedelta(days=7)
    new_end = slot_end + timedelta(days=7)
    events_end = new_start - timedelta(days=1)
    
    # 7. Print debug details to stderr
    print(f"# Found best overall score {winner_score:.4f} in {os.path.basename(winner_file_path)}", file=sys.stderr)
    print(f"# Forecast path: {forecast_path}", file=sys.stderr)
    print(f"# Peak date in forecast: {peak_date_str} (value: {peak_val:.6f})", file=sys.stderr)
    print(f"# Detected previous cadence: {cadence_days} days", file=sys.stderr)
    print(f"# New focus window (slot + 7d buffer): {new_start.strftime('%Y-%m-%d')} to {new_end.strftime('%Y-%m-%d')}", file=sys.stderr)
    print(f"# Events end date: {events_end.strftime('%Y-%m-%d')}", file=sys.stderr)
    
    # 8. Print shell variables to stdout for eval $(...)
    print(f'FORECAST_START="{new_start.strftime("%Y-%m-%d")}"')
    print(f'FORECAST_END="{new_end.strftime("%Y-%m-%d")}"')
    print(f'EVENTS_END="{events_end.strftime("%Y-%m-%d")}"')
    print(f'PREV_PEAK_DATE="{peak_date.strftime("%Y-%m-%d")}"')
    print(f'PREV_PEAK_VAL="{peak_val:.6f}"')
    print(f'PREV_CADENCE_DAYS="{cadence_days}"')

if __name__ == "__main__":
    main()
