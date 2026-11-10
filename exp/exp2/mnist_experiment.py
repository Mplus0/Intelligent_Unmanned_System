"""实验四：MNIST 基准、固定结构调参、卷积网络对比。仅使用 CPU。"""
import argparse
import csv
import json
import logging
import platform
import random
import sys
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader
from torchvision import datasets, transforms


class Net(nn.Module):
    """与实验文档一致的 784→512→256→10 全连接网络。"""
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(784, 512)
        self.fc2 = nn.Linear(512, 256)
        self.fc3 = nn.Linear(256, 10)

    def forward(self, x):
        x = x.flatten(1)
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        return self.fc3(x)  # 输出 logits，交叉熵内部完成 log-softmax


class ConvNet(nn.Module):
    """局部感受野、参数共享及池化保留图像空间信息。"""
    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(1, 16, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(16, 32, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2))
        self.classifier = nn.Sequential(
            nn.Flatten(), nn.Linear(32 * 7 * 7, 128), nn.ReLU(),
            nn.Dropout(0.25), nn.Linear(128, 10))

    def forward(self, x):
        return self.classifier(self.features(x))


def seed_all(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


@torch.inference_mode()
def evaluate(model, loader):
    model.eval()
    total_loss, predictions, targets = 0.0, [], []
    for x, y in loader:
        logits = model(x)
        total_loss += nn.functional.cross_entropy(logits, y, reduction="sum").item()
        predictions.append(logits.argmax(1))
        targets.append(y)
    predictions, targets = torch.cat(predictions), torch.cat(targets)
    return total_loss / len(targets), (predictions == targets).float().mean().item(), predictions, targets


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def plots(model, loader, dataset, folder):
    _, _, pred, target = evaluate(model, loader)
    cm = torch.bincount(target * 10 + pred, minlength=100).reshape(10, 10).numpy()
    np.savetxt(folder / "confusion_matrix.csv", cm, delimiter=",", fmt="%d")
    fig, ax = plt.subplots(figsize=(8, 7))
    im = ax.imshow(cm, cmap="Blues")
    for i in range(10):
        for j in range(10):
            ax.text(j, i, str(cm[i, j]), ha="center", va="center",
                    fontsize=8, color="white" if cm[i, j] > cm.max() / 2 else "black")
    ax.set(xticks=range(10), yticks=range(10), xlabel="Predicted digit",
           ylabel="True digit", title="MNIST test confusion matrix")
    fig.colorbar(im, ax=ax)
    fig.tight_layout()
    fig.savefig(folder / "confusion_matrix.png", dpi=160)
    plt.close(fig)
    for name, indices in [("predictions", list(range(25))),
                          ("errors", (pred != target).nonzero().flatten()[:25].tolist())]:
        fig, axes = plt.subplots(5, 5, figsize=(8, 8))
        for ax in axes.flat:
            ax.axis("off")
        for ax, idx in zip(axes.flat, indices):
            ax.imshow(dataset[idx][0].squeeze(), cmap="gray")
            correct = pred[idx] == target[idx]
            ax.set_title(f"True {target[idx]} / Pred {pred[idx]}",
                         fontsize=9, color="green" if correct else "red")
        fig.tight_layout()
        fig.savefig(folder / f"{name}.png", dpi=150)
        plt.close(fig)
    write_csv(folder / "test_predictions.csv",
              [{"index": i, "target": int(y), "prediction": int(p)}
               for i, (y, p) in enumerate(zip(target, pred))])


def run(args):
    root = Path(__file__).resolve().parent
    output = root / "results"
    output.mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s",
                        handlers=[logging.StreamHandler(sys.stdout),
                                  logging.FileHandler(output / "run.log", mode="w", encoding="utf-8")])
    torch.set_num_threads(args.threads)
    torch.use_deterministic_algorithms(True)
    transform = transforms.Compose([transforms.ToTensor(), transforms.Normalize((0.5,), (0.5,))])
    train = datasets.MNIST(root / "data", train=True, download=True, transform=transform)
    test = datasets.MNIST(root / "data", train=False, download=True, transform=transform)
    assert len(train) == 60000 and len(test) == 10000
    test_loader = DataLoader(test, batch_size=512, shuffle=False, num_workers=0)
    configs = [
        dict(name="baseline", architecture="MLP", epochs=10, batch_size=64,
             optimizer="SGD", lr=0.01, momentum=0.9, weight_decay=0.0, scheduler=False),
        dict(name="tuned_mlp", architecture="MLP", epochs=15, batch_size=64,
             optimizer="SGD", lr=0.03, momentum=0.9, weight_decay=0.0001, scheduler=True),
        dict(name="cnn", architecture="CNN", epochs=10, batch_size=128,
             optimizer="Adam", lr=0.001, momentum=0.0, weight_decay=0.0001, scheduler=True),
    ]
    env = dict(python=sys.version, executable=sys.executable, torch=torch.__version__,
               platform=platform.platform(), device="cpu", threads=args.threads,
               seed=args.seed, train_samples=len(train), test_samples=len(test))
    (output / "environment.json").write_text(json.dumps(env, indent=2), encoding="utf-8")
    summary, histories = [], {}
    for cfg in configs:
        if args.only != "all" and cfg["name"] != args.only:
            continue
        seed_all(args.seed)
        folder = output / cfg["name"]
        folder.mkdir(exist_ok=True)
        (folder / "config.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        model = Net() if cfg["architecture"] == "MLP" else ConvNet()
        loader = DataLoader(train, batch_size=cfg["batch_size"], shuffle=True, num_workers=0,
                            generator=torch.Generator().manual_seed(args.seed))
        if cfg["optimizer"] == "SGD":
            optimizer = torch.optim.SGD(model.parameters(), lr=cfg["lr"],
                                        momentum=cfg["momentum"], weight_decay=cfg["weight_decay"])
        else:
            optimizer = torch.optim.Adam(model.parameters(), lr=cfg["lr"],
                                         weight_decay=cfg["weight_decay"])
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=cfg["epochs"]) if cfg["scheduler"] else None
        criterion = nn.CrossEntropyLoss()
        history, started = [], time.perf_counter()
        logging.info("Starting %s: %s", cfg["name"], cfg)
        for epoch in range(1, cfg["epochs"] + 1):
            model.train()
            loss_sum, correct = 0.0, 0
            lr = optimizer.param_groups[0]["lr"]
            for x, y in loader:
                optimizer.zero_grad(set_to_none=True)
                logits = model(x)
                loss = criterion(logits, y)
                loss.backward()
                optimizer.step()
                loss_sum += loss.item() * len(y)
                correct += (logits.argmax(1) == y).sum().item()
            test_loss, accuracy, _, _ = evaluate(model, test_loader)
            row = dict(epoch=epoch, lr=lr, train_loss=loss_sum / len(train),
                       train_accuracy=correct / len(train), test_loss=test_loss,
                       test_accuracy=accuracy)
            history.append(row)
            write_csv(folder / "history.csv", history)
            logging.info("%s epoch %d/%d train_loss=%.5f test_accuracy=%.2f%%",
                         cfg["name"], epoch, cfg["epochs"], row["train_loss"], 100 * accuracy)
            if scheduler:
                scheduler.step()
        seconds = time.perf_counter() - started
        torch.save(dict(state_dict=model.state_dict(), config=cfg, seed=args.seed,
                        normalization_mean=0.5, normalization_std=0.5), folder / "model.pt")
        plots(model, test_loader, test, folder)
        summary.append(dict(name=cfg["name"], parameters=sum(p.numel() for p in model.parameters()),
                            epochs=cfg["epochs"], accuracy_percent=round(100 * accuracy, 4),
                            test_loss=test_loss, seconds=round(seconds, 2)))
        histories[cfg["name"]] = history
        write_csv(output / "summary.csv", summary)
        (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    for name, history in histories.items():
        axes[0].plot([r["epoch"] for r in history], [r["train_loss"] for r in history], label=name)
        axes[1].plot([r["epoch"] for r in history], [100 * r["test_accuracy"] for r in history], label=name)
    axes[0].set(xlabel="Epoch", ylabel="Training cross entropy")
    axes[1].set(xlabel="Epoch", ylabel="Test accuracy (%)")
    for ax in axes:
        ax.legend()
        ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(output / "training_curves.png", dpi=180)
    plt.close(fig)
    logging.info("Completed: %s", summary)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--only", choices=["all", "baseline", "tuned_mlp", "cnn"], default="all")
    run(parser.parse_args())
