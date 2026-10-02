"""Embed payload A then B with TrustMark (Q, BCH_5, CPU), decode, and run c2patool on the image alone.

Usage: python demo.py --images images/ [--c2patool PATH] [--out run/results.json]
Payload bits are derived from the image file stem, so the ten gate images
(images/diffusiondb-226.png, ...) reproduce the payloads recorded in results/.
"""
import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

SEED = 20261002


def classify(payload, valid, expected):
    if not valid:
        return 'missing'
    return next((k for k, v in expected.items() if payload == v), 'other')


def payload_bits(key, role, capacity):
    raw = hashlib.sha256(f'i7:{SEED}:{key.replace("-", ":", 1)}:{role}'.encode()).digest()
    return ''.join(f'{b:08b}' for b in raw)[:capacity]


def c2patool(binary, path):
    if not binary:
        return None, None
    run = subprocess.run([binary, str(path)], capture_output=True, text=True, timeout=90)
    manifest = None
    try:
        manifest = json.loads(run.stdout).get('active_manifest')
    except json.JSONDecodeError:
        pass
    return run.returncode, manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--images', type=Path, default=Path('images'))
    ap.add_argument('--c2patool', default=None, help='path to c2patool 0.27.22 (optional)')
    ap.add_argument('--out', type=Path, default=Path('run/results.json'))
    ap.add_argument('--limit', type=int, default=None)
    args = ap.parse_args()

    import torch
    from PIL import Image
    from trustmark import TrustMark
    torch.set_num_threads(2)
    tm = TrustMark(device='cpu', model_type='Q', encoding_type=TrustMark.Encoding.BCH_5, verbose=False)
    capacity = tm.schemaCapacity()
    assert capacity == 61, capacity

    paths = sorted(args.images.glob('*.png'))[:args.limit]
    assert paths, f'no PNG images in {args.images}'
    results = []
    with tempfile.TemporaryDirectory() as tmp:
        for p in paths:
            key = p.stem
            expected = {r: payload_bits(key, r, capacity) for r in ('A', 'B')}
            x = Image.open(p).convert('RGB')
            y = tm.encode(x, expected['A'], MODE='binary', WM_STRENGTH=1.0)
            z = tm.encode(y, expected['B'], MODE='binary', WM_STRENGTH=1.0)
            stages = {}
            for stage, im in (('clean', x), ('A', y), ('A_then_B', z)):
                f = Path(tmp) / f'{key}-{stage}.png'
                im.save(f, format='PNG', compress_level=6)
                # Decode from the saved PNG, not the in-memory image.
                payload, valid, schema = tm.decode(Image.open(f).convert('RGB'), MODE='binary')
                rc, manifest = c2patool(args.c2patool, f)
                stages[stage] = {'payload': payload, 'ecc_valid': bool(valid), 'schema': int(schema),
                                 'classification': classify(payload, valid, expected),
                                 'png_sha256': hashlib.sha256(f.read_bytes()).hexdigest(),
                                 'c2patool_returncode': rc, 'c2patool_active_manifest': manifest}
            results.append({'key': key, 'source': key.split('-')[0], 'id': key.split('-')[1], 'stages': stages})
            print(key, {s: v['classification'] for s, v in stages.items()}, flush=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(results, indent=2, sort_keys=True) + '\n')
    n = len(results)
    b = sum(r['stages']['A_then_B']['classification'] == 'B' for r in results)
    print(f'B recovered exactly after A then B: {b}/{n}')
    if args.c2patool:
        found = sum(bool(r['stages']['A_then_B']['c2patool_active_manifest']) for r in results)
        print(f'c2patool resolved a manifest from image alone: {found}/{n}')


if __name__ == '__main__':
    main()
