# 实验四 PyTorch 手写数字识别

本实验使用 MNIST 完整训练集 60000 张和测试集 10000 张，在 CPU 上完成三组真实训练。运行结果见 `results/summary.csv`，原理和实验结论见 `实验结果与分析.md`。

## 环境和运行

实际使用现有 conda 环境 `Unmanned_systems`（Python/PyTorch 等版本详见 `results/environment.json` 和 `requirements-lock.txt`）。本次为 Windows 原生 CPU 运行，未使用文档示例的 WSL Ubuntu；网络、损失函数和基准训练参数保持一致。

在 Anaconda Prompt 中执行：

```bat
conda activate Unmanned_systems
cd /d D:\Desktop\无人系统\exp2
python mnist_experiment.py
python verify_results.py
python predict.py --index 0
python predict.py --image your_digit.png
```

若本机 `conda.exe` 启动时出现 DLL 错误，可以使用已验证的等价入口：

```bat
D:\Anaconda\python.exe -m conda run --no-capture-output -n Unmanned_systems python D:\Desktop\无人系统\exp2\mnist_experiment.py
```

也可运行 `run_experiment.bat`。完整训练会重新写入同名结果；先备份需保留的旧结果。

在另一台机器创建最小环境：

```bat
conda create -n mnist_exp2 python=3.10 -y
conda activate mnist_exp2
python -m pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cpu
python -m pip install matplotlib numpy pillow
python mnist_experiment.py
```

也可以在没有同名环境的机器上执行 `conda env create -f environment.yml`，重建实验所需的最小环境。`requirements-lock.txt` 是实际使用的既有环境全部 pip 包快照，可能包含本实验不需要的包。

首次运行需联网下载 MNIST，后续使用 `data/` 中的缓存。若默认下载源失败，可先执行 `python download_mnist.py`，从备用公开镜像直连下载并校验 MD5。`--only baseline`、`--only tuned_mlp`、`--only cnn` 可单独运行一组；此时汇总文件只包含本次运行组，`verify_results.py` 需要完整三组结果。`--seed 42` 固定随机种子，`--threads 4` 设置 CPU 线程数。

## 文件说明

- `mnist_experiment.py`：数据加载、网络定义、三组训练、测试和绘图。
- `predict.py`：加载保存的权重，识别测试集样本或自定义图片。
- `results/summary.csv` / `summary.json`：最终测试指标、参数量和训练耗时。
- `results/training_curves.png`：训练损失和测试准确率曲线。
- `results/run.log`：实际训练日志。
- `results/baseline`、`tuned_mlp`、`cnn`：各组参数、逐轮记录、模型权重、混淆矩阵、预测示例、错误示例和全部测试预测。
- `data/`：MNIST 原始数据。

## 评估约定

三组配置在运行前固定，均报告最后一轮权重的测试结果，不按测试准确率选择最佳轮次。逐轮测试曲线仅用于本次教学观察；没有利用测试集反向传播，也没有进行测试集上的自动参数搜索。固定结构调参组同时改变多个训练参数，因此结果评价的是参数组合的总体效果，不能单独归因于某个参数。CNN 同时使用不同优化器及批大小，属于整体方案比较，并非严格的单变量网络结构消融。

本次是单种子实验，准确率差异不能直接解释为统计显著性。若继续系统搜索超参数，应从训练集中划分独立验证集，最后只评估一次测试集，并采用多种子重复实验。

自定义图片预处理会将浅色背景反转、裁剪数字并居中缩放，但其分布可能与 MNIST 不同；输出 softmax 概率不是经过校准的置信度。
