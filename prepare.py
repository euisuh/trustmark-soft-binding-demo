"""Download the five DiffusionDB (CC0) gate images into images/. DIV2K is not downloaded here.

DIV2K is licensed for academic research use; download DIV2K_valid_HR.zip yourself from
https://data.vision.ee.ethz.ch/cvl/DIV2K/ and use --div2k-zip to extract the five gate images.
Each image is converted to RGB and shrunk to fit 512x512 (LANCZOS), as in the original run.
Needs the shard(s) from Hugging Face (about 290 MB each).
"""
import argparse
import hashlib
import json
import shutil
import urllib.request
import zipfile
from pathlib import Path

REV = 'b8d0f99b3a58f59185e5d8a827c753d5ca5de340'
DDB_IDS = [226, 756, 466, 216, 250]
DIV2K_IDS = [881, 865, 877, 805, 830]
ROOT = Path(__file__).resolve().parent
EXPECTED = {i['source'] + '-' + str(i['id']): i['pixel_sha256']
            for i in json.loads((ROOT / 'results/gate-inputs.json').read_text())}


def fetch(url, path):
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        print('download', url, flush=True)
        with urllib.request.urlopen(url, timeout=180) as r, open(path, 'wb') as f:
            shutil.copyfileobj(r, f, 1 << 20)
    return path


def save(raw, key, out):
    import io
    from PIL import Image
    im = Image.open(io.BytesIO(raw)).convert('RGB')
    im.thumbnail((512, 512), Image.Resampling.LANCZOS)
    got = hashlib.sha256(im.tobytes()).hexdigest()
    print(key, 'pixels match recorded run' if got == EXPECTED[key] else 'PIXELS DIFFER from recorded run')
    im.save(out / f'{key}.png', format='PNG', compress_level=6)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, default=Path('images'))
    ap.add_argument('--cache', type=Path, default=Path('cache'))
    ap.add_argument('--div2k-zip', type=Path, default=None)
    args = ap.parse_args()
    import pyarrow.parquet as pq
    args.out.mkdir(parents=True, exist_ok=True)
    start = 0
    for shard in range(2):
        url = f'https://huggingface.co/datasets/poloclub/diffusiondb/resolve/{REV}/2m_first_1k/train-{shard:05d}-of-00002.parquet'
        table = pq.read_table(fetch(url, args.cache / f'diffusiondb-{shard}.parquet'), columns=['image'])
        for i in DDB_IDS:
            if start <= i < start + len(table):
                save(table['image'][i - start].as_py()['bytes'], f'diffusiondb-{i}', args.out)
        start += len(table)
    if args.div2k_zip:
        with zipfile.ZipFile(args.div2k_zip) as z:
            for i in DIV2K_IDS:
                save(z.read(f'DIV2K_valid_HR/{i:04d}.png'), f'div2k-{i}', args.out)


if __name__ == '__main__':
    main()
