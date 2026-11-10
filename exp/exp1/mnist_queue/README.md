# 实验三：基于 Python 实现循环队列

## 环境配置

在本目录打开终端，手动执行：

```powershell
conda env create -f environment.yml
conda activate Unmanned_systems
```

环境使用 Python 3.10、NumPy 和带窗口显示功能的 OpenCV。需要可显示桌面窗口的环境。
若本机 `conda.exe` 仍有 DLL 启动错误，可用以下命令创建环境：

```powershell
& 'D:\Anaconda\python.exe' -m conda env create -f environment.yml
```

## 数据集

将标准 MNIST 训练图像文件 `train-images-idx3-ubyte.gz` 放在 `main.py` 同级的 `data` 目录中。
需自行准备数据，不自动下载，不需要标签文件。也支持用 `--data` 指定未压缩的 IDX 图像文件。

```text
mnist_queue/
  main.py
  environment.yml
  README.md
  data/
    train-images-idx3-ubyte.gz
```

## 运行

激活环境后执行：

```powershell
python main.py
# 可选：指定文件和读取数量
python main.py --data data/train-images-idx3-ubyte --count 2000
```

默认读取并封装 1000 张图片，编号从 1 开始，读取数量不能小于 1000。
生产者与消费者分别使用独立线程，生产者约每 0.25 秒尝试入队，消费者初始约每 0.5 秒尝试出队。
采用固定数组、头尾指针和计数手动实现循环队列，有效容量为 20；所有队列及共享状态访问均受同一把锁保护。

满队列继续入队时判定上溢，本次入队失败，消费者切换至 8 Hz，生产者下次重试同一图片。
空队列继续出队时判定下溢，消费者恢复至 2 Hz。达到满/空状态本身不触发切换。
数据遍历完后从第一张继续，直到按 Q、Esc、Ctrl+C 或关闭窗口退出。

OpenCV 在主线程显示消费者最新取出的图片、编号、队列长度、频率、当前队列状态及最近一次频率变化；
终端逐次输出入队、出队、上溢及下溢事件。显示采用最新图片快照，窗口卡顿时不阻塞队列线程。
频率由系统线程调度实现，为近似值，不保证硬实时。

本次交付仅创建代码和配置文件，未创建 Conda 环境、安装依赖、运行程序或执行测试。
