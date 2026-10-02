# TrustMark soft-binding demo

A small, reproducible demonstration of two behaviours relevant to C2PA soft-binding resolution:

1. With TrustMark 0.9.2 (Q model, BCH_5) on CPU, embedding payload A and then payload B into the same image still decodes B exactly. On the ten day-0 images this held 10/10 (`results/gate-results.json`).
2. c2patool 0.27.22, given only the watermarked image, does not resolve a manifest from the watermark. It returned "No claim found" on 0/10 images (`results/gate-results.json`, field `c2patool_active_manifest`).

## What this is not

This is a demonstration, not original research. It does not claim novelty and it is not an attack on any deployed system. Both behaviours are already described in prior work:

- Bulychev et al., section 4 and Table 2, measure attacker-message recovery and ownership forgery against watermarks: <https://arxiv.org/html/2605.16796v1> (arXiv 2605.16796).
- The TrustMark paper, section 4.4, compares overwriting with removal and re-embedding: <https://arxiv.org/html/2311.18297v1#S4.SS4> (arXiv 2311.18297).

What this repository adds is a pinned, CPU-only reproduction and a concrete note that the released c2patool CLI does not perform watermark-to-manifest discovery on its own. That second point covers one tool at one version. Other consumers were not tested and their behaviour is unverified. A fuller discussion of consumers was out of scope here.

It may be useful if you work on soft-binding resolution and want a small fixture: ten images, exact payloads, and a known-negative CLI result.

## Status

The original pilot was designed as a larger overwrite-versus-removal comparison. It stopped at its day-0 consumer gate: no real resolving consumer could be evaluated locally, so the full comparison was never run. Not measured: LPIPS or PSNR matching, removal arms, any false-attribution display rate, and any trusted-timestamp defense. Verdict recorded in `results/gate-summary.json`: `REVISE`, `gate_passed: false`.

## Results

Source: `results/gate-results.json`. Printed by `python summarize.py`. The "SIMULATED lookup" column comes from the original pilot's exact-ID dictionary lookup, which is not a real consumer and is not reproduced by these scripts; it only restates that the decoded payload was B.

| Source | ID | Clean ECC-valid | After A | After A then B | c2patool image-only active manifest | SIMULATED lookup after B |
|---|---:|---|---|---|---|---|
| diffusiondb | 226 | False | A | B | none | SIMULATED: B |
| diffusiondb | 756 | False | A | B | none | SIMULATED: B |
| diffusiondb | 466 | False | A | B | none | SIMULATED: B |
| diffusiondb | 216 | False | A | B | none | SIMULATED: B |
| diffusiondb | 250 | False | A | B | none | SIMULATED: B |
| div2k | 881 | True | A | B | none | SIMULATED: B |
| div2k | 865 | False | A | B | none | SIMULATED: B |
| div2k | 877 | False | A | B | none | SIMULATED: B |
| div2k | 805 | False | A | B | none | SIMULATED: B |
| div2k | 830 | False | A | B | none | SIMULATED: B |

Per stratum (5 images each): exact A after A, 100% [100%, 100%]; exact B after A then B, 100% [100%, 100%]. Intervals are image bootstrap, 5,000 resamples, seed 20261002.

Limitations:

- Ten images, five per source. Zero failures in five images only bounds the failure rate below 45.07% (one-sided exact 95%). The bootstrap intervals are degenerate for the same reason.
- These are calibration-image gate diagnostics, not held-out inference.
- The A-then-B versus A recovery difference (0 percentage points) is not an overwrite-versus-removal comparison.
- One clean DIV2K image (881) decoded an ECC-valid payload that matches neither A nor B ("other" in the original log). No clean image matched a registered payload.
- Images were resized to fit 512x512 before embedding, with WM_STRENGTH=1.0. Image quality was not measured.
- CPU, two threads. GPU behaviour was not tested.
- c2patool was run with no settings and no sidecar, on the image file only. Other versions and other consumers are untested.
- The original pilot's attempts to sign with locally generated certificates failed (CoseX5ChainMissing; root cause not established). That signing work is not part of this repository.

## Reproduce

Pinned: Python 3.11, `trustmark==0.9.2`, `torch==2.14.1` (full list in `requirements.txt`, recorded in `results/environment.json`), c2patool 0.27.22. Recorded on macOS arm64.

```
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

TrustMark downloads its Q checkpoints on first use (`results/model-hashes.json` lists the URLs, MD5 and SHA-256). Weights are not stored in this repository.

Images. DiffusionDB is CC0; `prepare.py` downloads the two pinned parquet shards (about 290 MB each) from Hugging Face and extracts the five gate images:

```
.venv/bin/python prepare.py
```

DIV2K is licensed for academic research use, so it is not downloaded automatically. Get `DIV2K_valid_HR.zip` from <https://data.vision.ee.ethz.ch/cvl/DIV2K/> and extract the five gate images with:

```
.venv/bin/python prepare.py --div2k-zip path/to/DIV2K_valid_HR.zip
```

`prepare.py` checks each converted image against the pixel hash recorded in `results/gate-inputs.json` and prints whether it matches. Any directory of PNGs also works with `demo.py`; use any images you have the right to process.

c2patool (optional). Download the 0.27.22 release for your platform from <https://github.com/contentauth/c2pa-rs/releases/tag/c2patool-v0.27.22>. For the macOS universal build the archive SHA-256 should be `d064ca72e599c74e5fdc2ed04b47d6cb62210a2b14db589d078c2ec27c98d3df` (`results/c2patool-hashes.json`). Without `--c2patool` the CLI check is skipped.

Run:

```
.venv/bin/python demo.py --images images --c2patool /path/to/c2patool
.venv/bin/python verify.py run/results.json
.venv/bin/python summarize.py run/results.json
```

Expected output (five DiffusionDB images, verified in a fresh environment):

```
diffusiondb-216 {'clean': 'missing', 'A': 'A', 'A_then_B': 'B'}
...
B recovered exactly after A then B: 5/5
c2patool resolved a manifest from image alone: 0/5
recorded results OK: B after A->B 10/10, c2patool 0/10
diffusiondb-216 payloads identical to recorded run
...
fresh run OK: 5 images, exact A after A, exact B after A then B
```

`python verify.py` with no argument checks only the recorded results and needs no models.

## Files

- `demo.py`: embed A then B, decode from saved PNGs, run c2patool on the image alone.
- `prepare.py`: fetch the gate images (DiffusionDB automatic, DIV2K from your own copy).
- `summarize.py`, `verify.py`: table, bootstrap and assertions over a results file.
- `results/`: recorded day-0 output (`gate-results.json`, `gate-summary.json`, `gate-inputs.json`, `gate-run.json`, `environment.json`, `model-hashes.json`, `c2patool-hashes.json`).

## Licence

MIT (`LICENSE`). TrustMark, DiffusionDB, DIV2K and c2patool keep their own licences.
