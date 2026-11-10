"""加载已训练模型，识别 MNIST 样本或自定义单个数字图片。"""
import argparse
from pathlib import Path
import torch
from PIL import Image, ImageOps
from torchvision import datasets, transforms
from mnist_experiment import Net, ConvNet


def main():
    root = Path(__file__).resolve().parent
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", type=Path, default=root / "results/cnn/model.pt")
    p.add_argument("--image", type=Path, help="单个数字，自动将浅色背景转为深色背景")
    p.add_argument("--index", type=int, default=0, help="未提供图片时识别测试集索引")
    args = p.parse_args()
    torch.set_num_threads(4)
    checkpoint = torch.load(args.model, map_location="cpu", weights_only=True)
    model = Net() if checkpoint["config"]["architecture"] == "MLP" else ConvNet()
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()
    transform = transforms.Compose([transforms.ToTensor(), transforms.Normalize((0.5,), (0.5,))])
    if args.image:
        img = Image.open(args.image).convert("L")
        corners = [img.getpixel(pos) for pos in [(0, 0), (img.width-1, 0),
                                                 (0, img.height-1), (img.width-1, img.height-1)]]
        if sum(corners) / 4 > 127:
            img = ImageOps.invert(img)
        bbox = img.point(lambda v: 255 if v > 40 else 0).getbbox()
        if bbox is None:
            raise ValueError("图片中未发现数字笔画")
        img = img.crop(bbox)
        img.thumbnail((20, 20), Image.Resampling.LANCZOS)
        canvas = Image.new("L", (28, 28))
        canvas.paste(img, ((28-img.width)//2, (28-img.height)//2))
        x, label = transform(canvas), None
    else:
        dataset = datasets.MNIST(root / "data", train=False, download=False, transform=transform)
        x, label = dataset[args.index]
    with torch.inference_mode():
        probabilities = model(x.unsqueeze(0)).softmax(1)[0]
    prediction = probabilities.argmax().item()
    print(f"Prediction: {prediction}; probability: {probabilities[prediction]:.6f}; true label: {label}")


if __name__ == "__main__":
    main()
