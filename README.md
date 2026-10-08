[README.md](https://github.com/user-attachments/files/33209910/README.md)
# Einstein Tile Image Encryption

A permutation-diffusion image encryption scheme that uses the aperiodic **hat monotile** ("Einstein tile") as a source of structured randomness. A passphrase is hashed with SHA-256 to derive a seed and a tiling level; the resulting tiling drives both the pixel scrambling (permutation) and the keystream used for diffusion.

> **Status:** research prototype, work in progress. Not audited. Do not use to protect real data.

## How it works

1. **Key derivation.** A passphrase is hashed with SHA-256 to produce a seed and a tiling level. Changing a single character of the passphrase yields a completely different seed.
2. **Tiling generation.** The hat monotile tiling is generated at the derived level (e.g. level 5 gives 54,289 tiles).
3. **Permutation.** Pixel positions are scrambled using an ordering derived from the tiling.
4. **Diffusion.** A keystream derived from the tiling and key is combined with the scrambled pixels so that small plaintext changes spread across the whole ciphertext.
5. **Decryption** reverses the steps using the same passphrase. A wrong key produces noise (see `wrong_key_decrypt.png`).

## Results

Benchmark on five test images (checkerboard, gradient, random noise, smooth RGB gradient, a real photo). All five decrypt back to the original exactly (`round_trip_ok: True`).

| Metric | Mean | Ideal |
|---|---|---|
| Encrypted entropy | 7.9970 | ~8.0 |
| Encrypted correlation | 0.0030 | ~0 |
| NPCR | 99.63% | ~99.6% |
| UACI | 33.51% | ~33.46% |
| Encryption time | 0.38 s | n/a |

Example on a 417x626 RGB image: entropy 7.6040 → 7.9998, adjacent-pixel correlation 0.9997 → 0.0026.

## Repository contents

| File | Description |
|---|---|
| `phase1_tiling.py` | Main script: tiling, key derivation, encryption, decryption, and metrics |
| `my_tiling.png` | Visualization of the generated tiling |
| `scrambled_test.png`, `diffused_test.png` | Output after the permutation and diffusion stages |
| `encrypted_final.png`, `decrypted_final.png` | Final ciphertext and recovered image |
| `wrong_key_decrypt.png` | Decryption attempt with an incorrect key |
| `keystream_histogram.png` | Keystream value distribution |

## Setup and usage

```bash
git clone https://github.com/KochuthressiaPayankan/einstein-tile-encryption.git
cd einstein-tile-encryption

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt   # or: pip install numpy pillow matplotlib

python phase1_tiling.py
```

## Roadmap

- Formal cryptanalysis (key sensitivity, differential and statistical attacks)
- Larger benchmark set of standard test images
- Multi-trial averaging for all metrics
- Write-up for publication

## Author

Kochuthressia Payankan, B.Tech CSE, Sahrdaya College of Engineering and Technology.
