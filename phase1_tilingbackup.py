import matplotlib.pyplot as plt
from hat_amp.tiling import generate_tiling
from matplotlib.patches import Polygon
import hashlib
from PIL import Image
import numpy as np

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
def diffuse_image(img: np.ndarray, keystream: list) -> np.ndarray:
    """
    XORs each pixel value with a corresponding keystream byte.
    Returns the diffused image, same shape as input.
    """
    original_shape = img.shape
    flat_img = img.flatten()

    keystream_array = np.array(keystream[:len(flat_img)], dtype=np.uint8)
    diffused_flat = flat_img ^ keystream_array

    return diffused_flat.reshape(original_shape)
def undiffuse_image(diffused_img: np.ndarray, keystream: list) -> np.ndarray:
    """
    Reverses diffuse_image — restores original pixel values given the same keystream.
    """
    original_shape = diffused_img.shape
    flat_img = diffused_img.flatten()

    keystream_array = np.array(keystream[:len(flat_img)], dtype=np.uint8)
    restored_flat = flat_img ^ keystream_array

    return restored_flat.reshape(original_shape)


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

plt.hist(byte_stream, bins=32)
plt.savefig("keystream_histogram.png")