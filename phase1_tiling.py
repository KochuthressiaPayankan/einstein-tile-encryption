from email.mime import image
import matplotlib.pyplot as plt
from hat_amp.tiling import generate_tiling
from matplotlib.patches import Polygon
import hashlib
from PIL import Image
import numpy as np
import time


def generate_hat_tiling(level: int) -> list:
    """
    Returns a list of tiles.
    Each tile is a NumPy array of shape (13, 2) — 13 corner points, each an (x, y) pair.
    """
    hats = generate_tiling(level)
    print("Script finished running successfully!")
    return hats
def summarize_tiling(hats: list) -> dict:
    """
    Returns a dict with keys: 'num_tiles', 'total_points'
    """
    num_tiles = len(hats)
    total_points = num_tiles * 13
    return {'num_tiles': num_tiles, 'total_points': total_points}

def draw_tiling(hats: list, filename: str) -> None:
    fig, ax = plt.subplots(figsize=(8, 8))

    # TODO: loop over every tile in `hats`
    for tile in hats:
        #   for each tile, create: Polygon(tile, closed=True)
        polygon = Polygon(tile, closed=True)
        #   add it to the plot with: ax.add_patch(...)
        ax.add_patch(polygon)
        ax.autoscale_view()
    ax.set_aspect("equal")
    ax.axis("off")
    plt.savefig(filename)
    plt.close(fig)
def compute_centroids(hats: list) -> list:
    """
    Returns a list of centroids, one per tile.
    Each centroid is a NumPy array of shape (2,) — an (x, y) pair.
    """
    centroids = []
    for tile in hats:
        centroid = tile.mean(axis=0)
        centroids.append(centroid)
    return centroids 


def centroids_to_bytes(centroids: list) -> list:
    byte_stream = []
    for centroid in centroids:
        x, y = centroid
        text = f"{x},{y}"                    # turn the numbers into a string
        digest = hashlib.sha256(text.encode()).digest()  # hash it -> 32 random-looking bytes
        # TODO: pick 2 bytes from `digest` and append them to byte_stream
        byte_stream.append(digest[0])
        byte_stream.append(digest[1])
    return byte_stream
def generate_keystream(hats: list, length: int) -> list:
    """
    Generates a pseudorandom keystream of at least `length` bytes,
    derived from the tiling in `hats`, by re-hashing each centroid
    with an increasing counter until enough bytes are produced.
    """
    centroids = compute_centroids(hats)
    byte_stream = []

    counter = 0
    while len(byte_stream) < length:
        for centroid in centroids:
            x, y = centroid
            text = f"{x},{y},{counter}"   # <-- counter makes each round's hash different
            digest = hashlib.sha256(text.encode()).digest()
            byte_stream.append(digest[0])
            byte_stream.append(digest[1])
            if len(byte_stream) >= length:
                break
        counter += 1

    return byte_stream[:length]   # trim to exact length
def load_image(filepath: str) -> np.ndarray:
    """
    Loads an image and returns it as a NumPy array of shape
    (height, width, 3) — 3 for Red, Green, Blue color channels.
    """
    img = Image.open(filepath).convert("RGB")
    return np.array(img)
    pass
def permute_image(img: np.ndarray, seed: int) -> np.ndarray:
    """
    Scrambles the pixel positions of `img` using a shuffle order
    determined by `seed`. Returns the scrambled image, same shape as input.
    """
    original_shape = img.shape
    flat_img = img.flatten()

    np.random.seed(seed)
    order = np.random.permutation(len(flat_img))

    shuffled_flat = flat_img[order]
    return shuffled_flat.reshape(original_shape)
    pass
def unpermute_image(scrambled_img: np.ndarray, seed: int) -> np.ndarray:
    """
    Reverses permute_image — restores original pixel order given the same seed.
    """
    original_shape = scrambled_img.shape
    flat_scrambled = scrambled_img.flatten()

    np.random.seed(seed)
    order = np.random.permutation(len(flat_scrambled))
    inverse_order = np.argsort(order)

    restored_flat = flat_scrambled[inverse_order]
    return restored_flat.reshape(original_shape)
def _diffuse_pass(flat_img, keystream_array, forward=True):
    """One chained diffusion pass, in either forward or backward index order."""
    n = len(flat_img)
    idx_order = range(n) if forward else range(n - 1, -1, -1)
    out = np.zeros_like(flat_img)
    state = b'\x00' * 32
    for i in idx_order:
        state = hashlib.sha256(state + i.to_bytes(4, 'big')).digest()
        mask = state[0]
        val = flat_img[i] ^ keystream_array[i] ^ mask
        out[i] = val
        state = hashlib.sha256(state + bytes([int(val)])).digest()
    return out


def diffuse_image(img: np.ndarray, keystream: list) -> np.ndarray:
    """
    Two-pass chained diffusion: forward pass, then backward pass.
    Ensures a change anywhere in the image affects EVERY pixel,
    not just the ones that come after it.
    """
    original_shape = img.shape
    flat_img = img.flatten()
    keystream_array = np.array(keystream[:len(flat_img)], dtype=np.uint8)
    pass1 = _diffuse_pass(flat_img, keystream_array, forward=True)
    pass2 = _diffuse_pass(pass1, keystream_array, forward=False)
    return pass2.reshape(original_shape)


def _undiffuse_pass(flat_img, keystream_array, forward=True):
    n = len(flat_img)
    idx_order = range(n) if forward else range(n - 1, -1, -1)
    out = np.zeros_like(flat_img)
    state = b'\x00' * 32
    for i in idx_order:
        state = hashlib.sha256(state + i.to_bytes(4, 'big')).digest()
        mask = state[0]
        out[i] = flat_img[i] ^ keystream_array[i] ^ mask
        state = hashlib.sha256(state + bytes([int(flat_img[i])])).digest()
    return out


def undiffuse_image(diffused_img: np.ndarray, keystream: list) -> np.ndarray:
    """
    Reverses the two-pass diffusion — must undo backward pass first,
    then forward pass (reverse order, same principle as decrypt vs encrypt).
    """
    original_shape = diffused_img.shape
    flat_img = diffused_img.flatten()
    keystream_array = np.array(keystream[:len(flat_img)], dtype=np.uint8)
    undo2 = _undiffuse_pass(flat_img, keystream_array, forward=False)
    undo1 = _undiffuse_pass(undo2, keystream_array, forward=True)
    return undo1.reshape(original_shape)
def encrypt(img: np.ndarray, seed: int, keystream: list) -> np.ndarray:
    """
    Full encryption: permute pixel positions, then diffuse pixel values.
    """
    permuted = permute_image(img, seed)
    diffused = diffuse_image(permuted, keystream)
    return diffused


def decrypt(img: np.ndarray, seed: int, keystream: list) -> np.ndarray:
    """
    Full decryption: undiffuse pixel values, then unpermute pixel positions.
    Note the REVERSE order compared to encrypt.
    """
    undiffused = undiffuse_image(img, keystream)
    unpermuted = unpermute_image(undiffused, seed)
    return unpermuted
def compute_entropy(img: np.ndarray) -> float:
    """
    Computes the Shannon entropy of an image's pixel values.
    """
    flat_img = img.flatten()
    counts = np.bincount(flat_img, minlength=256)
    probabilities = counts / len(flat_img)

    entropy = 0
    for p in probabilities:
        if p > 0:
            entropy -= p * np.log2(p)

    return entropy
def compute_correlation(img: np.ndarray) -> float:
    """
    Computes the correlation coefficient between horizontally
    adjacent pixels in the image.
    """
    pixels_a = img[:, :-1, :].flatten()
    pixels_b = img[:, 1:, :].flatten()

    correlation_matrix = np.corrcoef(pixels_a, pixels_b)
    return correlation_matrix[0, 1]
def compute_npcr(encrypted_a: np.ndarray, encrypted_b: np.ndarray) -> float:
    """
    Percentage of pixels that differ between two encrypted images.
    """
    diff = encrypted_a != encrypted_b
    return (np.sum(diff) / diff.size) * 100


def compute_uaci(encrypted_a: np.ndarray, encrypted_b: np.ndarray) -> float:
    """
    Average intensity difference between two encrypted images, as a percentage.
    """
    diff = np.abs(encrypted_a.astype(int) - encrypted_b.astype(int))
    return (np.mean(diff) / 255) * 100
def key_sensitivity_test(img, keystream):
    """
    Encrypts with the correct seed, then tries decrypting with a
    slightly wrong seed. Should produce garbage, not a close-but-off image.
    """
    encrypted = encrypt(img, seed=42, keystream=keystream)
    wrong_decrypted = decrypt(encrypted, seed=43, keystream=keystream)
    Image.fromarray(wrong_decrypted).save("wrong_key_decrypt.png")
def derive_key_params(passphrase: str) -> tuple:
    """
    Derives a permutation seed and tiling level from a passphrase,
    instead of using small raw integers directly as the key.
    This expands the effective key space to match SHA-256 (2^256),
    instead of the ~2^35 space of a raw small seed+level.
    """
    digest = hashlib.sha256(passphrase.encode()).digest()
    seed = int.from_bytes(digest[0:4], 'big')
    level = 2 + (digest[4] % 4)  # maps to level 2-5
    return seed, level
def make_test_images(size=(128, 128)) -> dict:
    """
    Generates a small set of synthetic test images with different
    statistical properties, so evaluation isn't based on just one image.
    """
    h, w = size
    images = {}

    # Checkerboard - high frequency, low original entropy
    check = np.zeros((h, w, 3), dtype=np.uint8)
    block = 8
    for i in range(h):
        for j in range(w):
            if (i // block + j // block) % 2 == 0:
                check[i, j] = [255, 255, 255]
    images['checkerboard'] = check

    # Gradient - highly correlated, smooth
    grad = np.zeros((h, w, 3), dtype=np.uint8)
    for i in range(h):
        grad[i, :, :] = int(255 * i / h)
    images['gradient'] = grad

    # Random noise - baseline/stress test
    np.random.seed(7)
    images['random_noise'] = np.random.randint(0, 256, size=(h, w, 3), dtype=np.uint8)

    # Smooth RGB gradient - photo-like smooth color transitions
    smooth = np.zeros((h, w, 3), dtype=np.uint8)
    xx, yy = np.meshgrid(np.linspace(0, 1, w), np.linspace(0, 1, h))
    smooth[:, :, 0] = (xx * 255).astype(np.uint8)
    smooth[:, :, 1] = (yy * 255).astype(np.uint8)
    smooth[:, :, 2] = ((xx * yy) * 255).astype(np.uint8)
    images['smooth_gradient_rgb'] = smooth

    return images
def run_full_evaluation(passphrase):
    """
    Runs encrypt/decrypt + all Phase 4 metrics across every synthetic
    test image, plus your real test.png, and prints a results table.
    """
    seed, level = derive_key_params(passphrase)
    print(f"Derived seed={seed}, level={level}\n")

    hats_for_key = generate_hat_tiling(level)
    print(f"Regenerated tiling at derived level {level}: {len(hats_for_key)} tiles\n")

    images = make_test_images()
    images['my_real_photo'] = load_image("test.png")
    results = []
    for name, test_img in images.items():
        needed = test_img.size
        keystream = generate_keystream(hats_for_key, needed)

        t0 = time.time()
        encrypted = encrypt(test_img, seed, keystream)
        enc_time = time.time() - t0

        t0 = time.time()
        decrypted = decrypt(encrypted, seed, keystream)
        dec_time = time.time() - t0

        correct = np.array_equal(test_img, decrypted)

        img_b = test_img.copy()
        img_b[0, 0, 0] ^= 1
        encrypted_b = encrypt(img_b, seed, keystream)

        row = {
            'image': name,
            'round_trip_ok': correct,
            'entropy_enc': compute_entropy(encrypted),
            'corr_enc': compute_correlation(encrypted),
            'npcr': compute_npcr(encrypted, encrypted_b),
            'uaci': compute_uaci(encrypted, encrypted_b),
            'enc_time_sec': round(enc_time, 3),
        }
        results.append(row)
        print(f"--- {name} ---")
        for k, v in row.items():
            print(f"  {k}: {v}")
        print()

    print("===== AVERAGES =====")
    for key in ['entropy_enc', 'corr_enc', 'npcr', 'uaci', 'enc_time_sec']:
        vals = [r[key] for r in results]
        print(f"{key}: mean={np.mean(vals):.4f}")

    return results

if __name__ == "__main__":
    
    hats = generate_hat_tiling(2)
    print(len(hats))
    print(hats[0].shape)
    result = summarize_tiling(hats)
    print(result)
    draw_tiling(hats, "my_tiling.png")
    centroids = compute_centroids(hats)
    print(len(centroids))
    print(centroids[0])
    byte_stream = centroids_to_bytes(centroids)
    print(len(byte_stream))
    print(byte_stream[:10])
    print("Total values:", len(byte_stream))
    print("Unique values:", len(set(byte_stream)))
    keystream = generate_keystream(hats, 500)
    print(len(keystream))
    print(len(set(keystream)))
    img = load_image("test.png")
    print(img.shape)
    print(img.dtype)
    scrambled = permute_image(img, seed=42)
    print(scrambled.shape)
    draw_scrambled = Image.fromarray(scrambled)
    draw_scrambled.save("scrambled_test.png")
    restored = unpermute_image(scrambled, seed=42)
    print(np.array_equal(img, restored))
    keystream = generate_keystream(hats, img.size)   # img.size = total pixel values needed
    diffused = diffuse_image(img, keystream)
    print(diffused.dtype)
    Image.fromarray(diffused).save("diffused_test.png")
    encrypted = encrypt(img, seed=42, keystream=keystream)
    decrypted = decrypt(encrypted, seed=42, keystream=keystream)
    print(np.array_equal(img, decrypted))
    Image.fromarray(encrypted).save("encrypted_final.png")
    Image.fromarray(decrypted).save("decrypted_final.png")
    print("Original entropy:", compute_entropy(img))
    print("Encrypted entropy:", compute_entropy(encrypted))
    print("Original correlation:", compute_correlation(img))
    print("Encrypted correlation:", compute_correlation(encrypted))
    img_b = img.copy()
    img_b[0, 0, 0] = img_b[0, 0, 0] ^ 1

    encrypted_a = encrypt(img, seed=42, keystream=keystream)
    encrypted_b = encrypt(img_b, seed=42, keystream=keystream)

    print("NPCR:", compute_npcr(encrypted_a, encrypted_b))
    print("UACI:", compute_uaci(encrypted_a, encrypted_b))

    key_sensitivity_test(img, keystream)
    seed, level = derive_key_params("my-secret-passphrase-2026")
    print("Derived seed:", seed)
    print("Derived level:", level)

    seed2, level2 = derive_key_params("my-secret-passphrase-2027")  # 1 char different
    print("Derived seed (1 char diff):", seed2)
    run_full_evaluation(passphrase="my-secret-passphrase-2026")
    
plt.hist(byte_stream, bins=32)
plt.savefig("keystream_histogram.png")