"""MNIST 循环队列：生产者 4 Hz，消费者在 2 Hz 和 8 Hz 间切换。"""

import argparse
import gzip
import struct
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass(frozen=True)
class ImageItem:
    number: int
    image: np.ndarray


class CircularQueue:
    """使用计数区分空与满，20 个槽位均可用；调用方持锁访问。"""

    def __init__(self, capacity=20):
        self.capacity = capacity
        self.items = [None] * capacity
        self.head = self.tail = self.size = 0

    def is_empty(self):
        return self.size == 0

    def is_full(self):
        return self.size == self.capacity

    def enqueue(self, item):
        if self.is_full():
            return False
        self.items[self.tail] = item
        self.tail = (self.tail + 1) % self.capacity
        self.size += 1
        return True

    def dequeue(self):
        if self.is_empty():
            return None
        item = self.items[self.head]
        self.items[self.head] = None
        self.head = (self.head + 1) % self.capacity
        self.size -= 1
        return item


def load_mnist(path, count):
    if count < 1000:
        raise ValueError("至少需要读取 1000 张图片")
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rb") as stream:
        header = stream.read(16)
        if len(header) != 16:
            raise ValueError("MNIST 文件头不完整")
        magic, total, rows, cols = struct.unpack(">IIII", header)
        if magic != 2051 or (rows, cols) != (28, 28):
            raise ValueError("需要 MNIST IDX 图像文件（28×28），不是标签文件")
        if total < count:
            raise ValueError(f"数据集只有 {total} 张图片，需要 {count} 张")
        data = stream.read(count * rows * cols)
    if len(data) != count * rows * cols:
        raise ValueError("MNIST 图像数据不完整")
    images = np.frombuffer(data, dtype=np.uint8).reshape(count, rows, cols)
    return [ImageItem(i + 1, image) for i, image in enumerate(images)]


class Experiment:
    def __init__(self, images):
        self.images = images
        self.queue = CircularQueue(20)
        # 队列、频率和显示快照共用一把锁，状态更新保持一致。
        self.condition = threading.Condition()
        self.stop = threading.Event()
        self.consumer_hz = 2
        self.latest = None
        self.transition = "START: consumer 2 Hz"

    def report(self, action, number):
        print(f"{action:<9} id={number!s:<5} length={self.queue.size:2}/20 "
              f"producer=4Hz consumer={self.consumer_hz}Hz", flush=True)

    def produce(self):
        index = 0
        while not self.stop.is_set():
            with self.condition:
                item = self.images[index]
                if self.queue.enqueue(item):
                    self.report("ENQUEUE", item.number)
                    index = (index + 1) % len(self.images)
                else:
                    self.consumer_hz = 8
                    self.transition = "OVERFLOW: consumer -> 8 Hz"
                    self.report("OVERFLOW", item.number)
                    self.condition.notify_all()
                    # 本次入队失败，下一次生产仍尝试同一张图片。
            self.stop.wait(1 / 4)

    def consume(self):
        last_tick = time.monotonic()
        with self.condition:
            while not self.stop.is_set():
                remaining = last_tick + 1 / self.consumer_hz - time.monotonic()
                if remaining > 0:
                    # 上溢通知会提前唤醒，按新频率重新计算等待时间。
                    self.condition.wait(remaining)
                    continue
                last_tick = time.monotonic()
                item = self.queue.dequeue()
                if item is None:
                    self.consumer_hz = 2
                    self.transition = "UNDERFLOW: consumer -> 2 Hz"
                    self.report("UNDERFLOW", "-")
                else:
                    self.latest = item
                    self.report("DEQUEUE", item.number)

    def run(self):
        workers = [threading.Thread(target=self.produce, name="producer"),
                   threading.Thread(target=self.consume, name="consumer")]
        window = "MNIST circular queue"
        started = []
        try:
            cv2.namedWindow(window, cv2.WINDOW_AUTOSIZE)
            for worker in workers:
                worker.start()
                started.append(worker)
            # OpenCV 窗口操作放在主线程；消费者只发布最新出队图片。
            while not self.stop.is_set():
                with self.condition:
                    item = self.latest
                    size = self.queue.size
                    hz = self.consumer_hz
                    transition = self.transition
                canvas = np.zeros((430, 560, 3), dtype=np.uint8)
                if item is not None:
                    enlarged = cv2.resize(item.image, (280, 280),
                                          interpolation=cv2.INTER_NEAREST)
                    canvas[10:290, 140:420] = cv2.cvtColor(enlarged, cv2.COLOR_GRAY2BGR)
                state = "EMPTY" if size == 0 else "FULL" if size == 20 else "NORMAL"
                lines = [f"Image ID: {item.number if item else '-'}   Queue: {size}/20",
                         f"Producer: 4 Hz   Consumer: {hz} Hz   {state}",
                         transition, "Q / ESC / close window: exit"]
                for i, line in enumerate(lines):
                    cv2.putText(canvas, line, (12, 315 + i * 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
                cv2.imshow(window, canvas)
                key = cv2.waitKey(10) & 0xFF
                if key in (27, ord("q"), ord("Q")):
                    break
                if cv2.getWindowProperty(window, cv2.WND_PROP_VISIBLE) < 1:
                    break
        except KeyboardInterrupt:
            pass
        finally:
            self.stop.set()
            with self.condition:
                self.condition.notify_all()
            for worker in started:
                worker.join()
            cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path,
                        default=Path(__file__).parent / "data" / "train-images-idx3-ubyte.gz")
    parser.add_argument("--count", type=int, default=1000,
                        help="读取图片数量，至少 1000（默认 1000）")
    args = parser.parse_args()
    try:
        images = load_mnist(args.data, args.count)
    except (OSError, EOFError, ValueError) as error:
        parser.error(str(error))
    print(f"已读取 {len(images)} 张 MNIST 图片，将按编号循环生产。", flush=True)
    Experiment(images).run()


if __name__ == "__main__":
    main()
