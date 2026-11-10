"""默认下载失败时，直连公开 MNIST 镜像并核验 torchvision 的 MD5。"""
import gzip
import hashlib
from pathlib import Path
import urllib.request
from torchvision.datasets import MNIST

root = Path(__file__).resolve().parent / "data/MNIST/raw"
root.mkdir(parents=True, exist_ok=True)
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
for filename, expected_md5 in MNIST.resources:
    target = root / filename
    if not target.exists() or hashlib.md5(target.read_bytes()).hexdigest() != expected_md5:
        url = "https://storage.googleapis.com/cvdf-datasets/mnist/" + filename
        print("Downloading", url, flush=True)
        with opener.open(url, timeout=120) as response:
            content = response.read()
        if hashlib.md5(content).hexdigest() != expected_md5:
            raise ValueError(f"MD5 mismatch: {filename}")
        target.write_bytes(content)
    (root / filename.removesuffix(".gz")).write_bytes(gzip.decompress(target.read_bytes()))
    print("Verified", filename, flush=True)
