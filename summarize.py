"""Print a per-image table and per-source bootstrap summary from a results file.

Usage: python summarize.py [results/gate-results.json]
Bootstrap: 5,000 paired image resamples, seed 20261002, percentile indices 124 and 4874.
"""
import json
import random
import statistics
import sys
from pathlib import Path

SEED = 20261002


def bootstrap(values):
    rng = random.Random(SEED)
    reps = sorted(statistics.mean(rng.choices(values, k=len(values))) for _ in range(5000))
    return statistics.mean(values), reps[124], reps[4874]


def main(path):
    results = json.loads(Path(path).read_text())
    print('| Source | ID | Clean ECC-valid | After A | After A then B | c2patool active manifest (image alone) |')
    print('|---|---:|---|---|---|---|')
    for r in results:
        s = r['stages']
        print(f"| {r['source']} | {r['id']} | {s['clean']['ecc_valid']} | {s['A']['classification']} | "
              f"{s['A_then_B']['classification']} | {s['A_then_B']['c2patool_active_manifest'] or 'none'} |")
    print()
    for source in sorted({r['source'] for r in results}):
        rows = [r for r in results if r['source'] == source]
        b = [int(r['stages']['A_then_B']['classification'] == 'B') for r in rows]
        m, lo, hi = bootstrap(b)
        print(f'{source}: exact B after A then B {m:.0%} [{lo:.0%}, {hi:.0%}] (n={len(rows)}); '
              f'zero failures in n images has one-sided exact 95% upper bound {1 - 0.05 ** (1 / len(rows)):.2%}')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'results/gate-results.json')
