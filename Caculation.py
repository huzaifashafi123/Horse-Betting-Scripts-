import pandas as pd
import numpy as np
from collections import defaultdict

# Load CSV
df = pd.read_csv('cleaned_file.csv')

# Clean numeric columns
pos_cols = ['pp', 'start', 'quarter', 'half', 'three_quarter', 'str', 'fin', 'odds']
for col in pos_cols:
    df[col] = pd.to_numeric(df[col], errors='coerce')

# Parse date column
df['date'] = pd.to_datetime(df['date'], dayfirst=True, errors='coerce')

def detect_speed_bias_closers(df):
    results = []
    for (track, date), group in df.groupby(['track_name', 'date']):
        races = group.groupby('race_number')
        lead_winners = 0
        total_races = 0
        closers_outperformed = []

        for race_id, race in races:
            if race.empty or race['fin'].isna().all():
                continue

            total_races += 1
            winner = race.loc[race['fin'].idxmin()]
            if winner['quarter'] == 1.0:
                lead_winners += 1

            for _, horse in race.iterrows():
                if pd.notna(horse['quarter']) and pd.notna(horse['fin']):
                    if horse['quarter'] >= horse['fin'] + 2:
                        closers_outperformed.append(horse)

        if total_races == 0:
            continue

        lead_win_pct = lead_winners / total_races
        if lead_win_pct >= 0.7:
            for horse in closers_outperformed:
                results.append({
                    'track_name': track,
                    'date': date,
                    'horse_name': horse['horse_name'],
                    'fin': horse['fin'],
                    'quarter': horse['quarter'],
                    'comment': horse['comments']
                })

    return pd.DataFrame(results)


def detect_post_bias_and_outperformers(df):
    results = []
    bias_days = []

    for (track, date), group in df.groupby(['track_name', 'date']):
        races = group.groupby('race_number')
        total_wins = 0
        inside_wins = 0
        win_by_pp = defaultdict(int)

        horses_by_race = {}

        for race_id, race in races:
            if race.empty or race['fin'].isna().all():
                continue

            total_wins += 1
            winner = race.loc[race['fin'].idxmin()]
            pp = winner['pp']
            if pd.notna(pp):
                win_by_pp[int(pp)] += 1
                if int(pp) in [1, 2, 3]:
                    inside_wins += 1

            # Rank horses by odds
            race = race.copy()
            race['odds_rank'] = race['odds'].rank(method='min')
            horses_by_race[race_id] = race

        if total_wins == 0:
            continue

        inside_win_pct = inside_wins / total_wins

        if inside_win_pct >= 0.6:
            bias_type = 'inside'
        elif inside_win_pct <= 0.1:
            bias_type = 'outside'
        else:
            continue  # no strong bias

        bias_days.append((track, date, bias_type))

        for race_id, race in horses_by_race.items():
            for _, horse in race.iterrows():
                if pd.notna(horse['fin']) and pd.notna(horse['odds_rank']):
                    if horse['odds_rank'] - horse['fin'] >= 2:
                        is_inside = horse['pp'] in [1, 2, 3]
                        if (bias_type == 'inside' and not is_inside) or \
                           (bias_type == 'outside' and is_inside):
                            results.append({
                                'track_name': track,
                                'date': date,
                                'bias_type': bias_type,
                                'horse_name': horse['horse_name'],
                                'pp': horse['pp'],
                                'fin': horse['fin'],
                                'odds': horse['odds'],
                                'odds_rank': horse['odds_rank'],
                                'comment': horse['comments']
                            })

    return pd.DataFrame(results), bias_days

speed_bias_closers = detect_speed_bias_closers(df)
speed_bias_closers.to_csv('speed_bias_closers.csv', index=False)

# Method 2:
post_bias_outperformers, bias_days = detect_post_bias_and_outperformers(df)
post_bias_outperformers.to_csv('post_bias_outperformers.csv', index=False)
df = pd.DataFrame(bias_days)
df.to_csv("bias_days.csv")
print("Bias Days Detected:", bias_days)
