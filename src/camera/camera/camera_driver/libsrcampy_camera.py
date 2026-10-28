class LibsrcampyCamera:
    """Thin lifecycle wrapper around the board-provided libsrcampy API."""
    def __init__(self, pipe_id=0, video_index=-1, fps=30, width=1920, height=1080, channel=2):
        self.pipe_id, self.video_index = int(pipe_id), int(video_index)
        self.fps, self.width, self.height = int(fps), int(width), int(height)
        self.channel = int(channel)
        self._camera = None

    def start(self):
        if self._camera is not None:
            return
        try:
            from hobot_vio import libsrcampy
        except ImportError as exc:
            raise RuntimeError('未找到 RDK X5 系统提供的 hobot_vio.libsrcampy') from exc
        cam = libsrcampy.Camera()
        result = cam.open_cam(self.pipe_id, self.video_index, self.fps, self.width, self.height)
        if result != 0:
            cam.close_cam()
            raise RuntimeError(f'libsrcampy.open_cam 失败，返回值: {result}')
        self._camera = cam

    def read(self):
        if self._camera is None:
            raise RuntimeError('相机尚未启动')
        try:
            return self._camera.get_img(self.channel, self.width, self.height)
        except TypeError:
            return self._camera.get_img(self.channel)

    def close(self):
        if self._camera is not None:
            try:
                self._camera.close_cam()
            finally:
                self._camera = None
