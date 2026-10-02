"""Check recorded results, and optionally a fresh run, for the claims in the README.

Usage: python verify.py [fresh_results.json]
Recorded checks need no models. With a fresh run, every image must also match the
recorded classification (and, if the run is deterministic on your machine, the payload bits).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load(p):
    return json.loads(Path(p).read_text())


def main():
    rec = load(ROOT / 'results/gate-results.json')
    assert len(rec) == 10 and len({r['key'] for r in rec}) == 10
    for r in rec:
        s = r['stages']
        assert s['A']['classification'] == 'A' and s['A_then_B']['classification'] == 'B', r['key']
        assert all(s[x]['c2patool_returncode'] == 1 and not s[x]['c2patool_active_manifest'] for x in ('A', 'A_then_B'))
    summ = load(ROOT / 'results/gate-summary.json')
    assert summ['verdict'] == 'REVISE' and not summ['gate_passed']
    print('recorded results OK: B after A->B 10/10, c2patool 0/10')
    if len(sys.argv) > 1:
        by_key = {r['key']: r for r in rec}
        fresh = load(sys.argv[1])
        for r in fresh:
            assert r['stages']['A']['classification'] == 'A', r['key']
            assert r['stages']['A_then_B']['classification'] == 'B', r['key']
            old = by_key.get(r['key'])
            if old:
                same = all(r['stages'][k]['payload'] == old['stages'][k]['payload'] for k in r['stages'])
                print(r['key'], 'payloads identical to recorded run' if same else 'payload bits differ from recorded run (classification matches)')
        print(f'fresh run OK: {len(fresh)} images, exact A after A, exact B after A then B')


if __name__ == '__main__':
    main()
