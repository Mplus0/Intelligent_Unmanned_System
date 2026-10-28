# RDK X5 智能无人系统 ROS 2 工作空间

工作空间包含一个 `camera` 功能包，负责相机采集、图像转换、ROS 2 发布、图片保存和浏览器预览。

## 构建与启动

```bash
cd ~/workspace/Intelligent_Unmanned_Systems
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
ros2 launch camera camera.launch.py
```

工作空间统一使用 `~/workspace/Intelligent_Unmanned_Systems`，请保持路径大小写一致。

默认配置为 1920×1080、30 FPS。图像发布到 `/camera/image_raw`，编码 `bgr8`，节点名为 `camera`。订阅端使用 Sensor Data / Best Effort QoS。浏览器 MJPEG 预览独立编码，默认最高 10 FPS，避免影响 ROS 发布。

## 局域网浏览器预览

电脑与开发板连接同一局域网，启动上述摄像头节点后，在电脑浏览器直接打开：

**http://172.16.6.16:8080/**

MJPEG 视频流地址为 `http://172.16.6.16:8080/stream.mjpg`，可用于网页嵌入。默认服务监听 `0.0.0.0:8080`；保持配置中的 `preview_enabled: true` 和 `preview_host: 0.0.0.0`。若开发板 IP 或 `preview_port` 改变，请相应修改访问地址。

预览仅在摄像头节点运行时可用。浏览器通过 HTTP 获取画面，ROS 2 图像话题同时正常发布。

## 保存图片与参数配置

调用 `ros2 service call /camera/save_image std_srvs/srv/Trigger '{}'` 保存当前帧到配置的 `save_dir`（默认 `~/camera_images`），服务返回实际文件路径。

参数文件为 `src/camera/config/camera.yaml`。宽高必须为正偶数，实际支持的分辨率和帧率取决于硬件；`video_index: -1` 自动探测相机，`channel: 2` 已在本机测试。可配置 `width`、`height`、`fps`、`pipe_id`、`video_index`、`channel`、`frame_id`、`preview_enabled`、`preview_host`、`preview_port`、`preview_fps`、`jpeg_quality` 和 `save_dir`。参数在启动时读取，修改后重启节点。

```bash
ros2 launch camera camera.launch.py params_file:=/absolute/path/camera.yaml
```

按 Ctrl+C 关闭节点并释放摄像头。运行本包前须关闭其他占用 CSI 相机的官方示例。

同一摄像头只运行一个采集进程。若启动时出现 `No camera sensor found`，先确认已有摄像头节点或官方示例已退出；本次故障由后台旧节点占用引起，结束旧节点后恢复。若设备空闲时仍报错，再检查 `video_index` 和 CSI 连接。

## 目录

```text
src/
└── camera/
    ├── camera/
    │   ├── camera_driver/      # 硬件采集
    │   ├── image_processing/   # NV12转BGR
    │   └── ros_node/           # 发布、保存、预览
    ├── config/camera.yaml
    └── launch/camera.launch.py
```

驱动封装在 `camera_driver/libsrcampy_camera.py`，NV12 转换在 `image_processing/nv12.py`，ROS 发布、保存服务和预览在 `ros_node/camera_node.py`。更换硬件时替换驱动实现，维持 `start/read/close` 接口及 NV12 输出即可。

## 环境与验证

板端已具备 Humble、hobot_vio、OpenCV、NumPy。已将 colcon 安装到 `~/.local/bin`，并在 `.bashrc` 添加 PATH；已有终端可执行 `export PATH="$HOME/.local/bin:$PATH"`。不需要 sudo 启动摄像头。官方接口参考：https://developer.d-robotics.cc/rdk_x_doc/en/Basic_Application/multi_media_sp_dev_api/RDK_X5/pydev_multimedia_api_x5/object_camera

2026-10-28 板端验证：`camera` 包构建成功；清理后台占用后复测连续接收 150 帧，约 29.92 FPS，1920×1080、bgr8；保存服务成功，JPEG 可解码；HTTP 预览服务返回 200 和完整 JPEG；节点正常退出。帧率是本次短时测试结果，实际负载可能影响性能。

节点停止时可复验：

```bash
source install/setup.bash
python3 verify_camera.py
```

测试会启动相机、保存一张照片并自动关闭，结果保存在 `test_results/acceptance.json` 和 `test_results/launch.log`。该测试需要真实硬件，不应与正在运行的摄像头节点同时执行。
