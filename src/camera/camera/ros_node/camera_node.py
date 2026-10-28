from datetime import datetime
from array import array
import signal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading

import cv2
import rclpy
from rclpy.node import Node
from rclpy.executors import ExternalShutdownException
from rclpy.qos import qos_profile_sensor_data
from rcl_interfaces.msg import ParameterDescriptor
from sensor_msgs.msg import Image
from std_srvs.srv import Trigger

from camera.camera_driver import LibsrcampyCamera
from camera.image_processing import nv12_to_bgr


class PreviewState:
    def __init__(self):
        self.jpeg = None
        self.lock = threading.Lock()
        self.stopped = threading.Event()


def make_preview_handler(state):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/stream.mjpg':
                self.send_response(200)
                self.send_header('Cache-Control', 'no-cache')
                self.send_header('Connection', 'close')
                self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
                self.end_headers()
                try:
                    self.connection.settimeout(5.0)
                    while not state.stopped.is_set():
                        with state.lock:
                            jpeg = state.jpeg
                        if jpeg:
                            self.wfile.write(b'--frame\r\nContent-Type: image/jpeg\r\nContent-Length: ' + str(len(jpeg)).encode() + b'\r\n\r\n' + jpeg + b'\r\n')
                        state.stopped.wait(0.03)
                except (BrokenPipeError, ConnectionResetError, TimeoutError):
                    pass
                return
            if self.path not in ('/', '/index.html'):
                self.send_error(404)
                return
            page = b'<!doctype html><meta charset="utf-8"><title>Camera Preview</title><style>body{margin:0;background:#111;color:#eee;font:16px sans-serif;text-align:center}img{max-width:100vw;max-height:92vh}</style><h3>Camera Preview</h3><img src="/stream.mjpg">'
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(page)))
            self.end_headers()
            self.wfile.write(page)

        def log_message(self, *_args):
            pass
    return Handler


class CameraNode(Node):
    def __init__(self):
        super().__init__('camera')
        defaults = {
            'width': 1920, 'height': 1080, 'fps': 30,
            'pipe_id': 0, 'video_index': -1, 'channel': 2,
            'frame_id': 'camera_optical_frame', 'preview_enabled': True,
            'preview_host': '0.0.0.0', 'preview_port': 8080,
            'jpeg_quality': 80, 'save_dir': str(Path.home() / 'camera_images'),
            'preview_fps': 10,
        }
        for name, value in defaults.items():
            self.declare_parameter(name, value, ParameterDescriptor(read_only=True))
        p = {name: self.get_parameter(name).value for name in defaults}
        self.width, self.height = int(p['width']), int(p['height'])
        if self.width <= 0 or self.height <= 0 or self.width % 2 or self.height % 2 or int(p['fps']) <= 0:
            raise ValueError('宽高必须是正偶数，fps必须大于零')
        if not 1 <= int(p['jpeg_quality']) <= 100:
            raise ValueError('jpeg_quality必须在1至100之间')
        self.frame_id = str(p['frame_id'])
        self.jpeg_quality = int(p['jpeg_quality'])
        self.preview_fps = max(1, int(p['preview_fps']))
        self.preview_thread = None
        self.save_dir = Path(str(p['save_dir'])).expanduser()
        cv2.setNumThreads(2)
        self.publisher = self.create_publisher(Image, '/camera/image_raw', qos_profile_sensor_data)
        self.state = PreviewState()
        self.preview_server = None
        self.camera = LibsrcampyCamera(p['pipe_id'], p['video_index'], p['fps'], self.width, self.height, p['channel'])
        self.latest_bgr = None
        self.save_service = self.create_service(Trigger, '/camera/save_image', self.save_image)
        self.camera.start()
        if p['preview_enabled']:
            try:
                self.preview_server = ThreadingHTTPServer((str(p['preview_host']), int(p['preview_port'])), make_preview_handler(self.state))
            except Exception:
                self.camera.close()
                raise
            threading.Thread(target=self.preview_server.serve_forever, daemon=True).start()
            self.preview_thread = threading.Thread(target=self.encode_preview, daemon=True)
            self.preview_thread.start()
            self.get_logger().info(f"浏览器预览: http://<开发板IP>:{p['preview_port']}/")
        self.timer = self.create_timer(1.0 / max(1, int(p['fps'])), self.capture_once)
        self.get_logger().info(f'发布 /camera/image_raw ({self.width}x{self.height})')

    def capture_once(self):
        try:
            raw = self.camera.read()
            bgr = nv12_to_bgr(raw, self.width, self.height)
            if bgr is None:
                return
            msg = Image()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = self.frame_id
            msg.height, msg.width = self.height, self.width
            msg.encoding, msg.is_bigendian, msg.step = 'bgr8', 0, self.width * 3
            msg.data = array('B', bgr.tobytes())
            self.publisher.publish(msg)
            self.latest_bgr = bgr
        except Exception as exc:
            self.get_logger().error(f'图像采集或转换失败: {exc}', throttle_duration_sec=5.0)

    def encode_preview(self):
        while not self.state.stopped.wait(1.0 / self.preview_fps):
            bgr = self.latest_bgr
            if bgr is not None:
                ok, encoded = cv2.imencode('.jpg', bgr, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality])
                if ok:
                    with self.state.lock:
                        self.state.jpeg = encoded.tobytes()

    def save_image(self, _request, response):
        if self.latest_bgr is None:
            response.success, response.message = False, '尚未取得有效图像'
            return response
        try:
            self.save_dir.mkdir(parents=True, exist_ok=True)
            path = self.save_dir / (datetime.now().strftime('camera_%Y%m%d_%H%M%S_%f') + '.jpg')
            if not cv2.imwrite(str(path), self.latest_bgr):
                raise OSError('OpenCV写入失败')
            response.success, response.message = True, str(path)
        except Exception as exc:
            response.success, response.message = False, str(exc)
        return response

    def close(self):
        self.timer.cancel()
        self.state.stopped.set()
        if self.preview_thread:
            self.preview_thread.join(timeout=5)
        if self.preview_server:
            self.preview_server.shutdown()
            self.preview_server.server_close()
        self.camera.close()


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = CameraNode()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    except Exception as exc:
        if node is not None:
            node.get_logger().fatal(str(exc))
        else:
            print(f'相机节点启动失败: {exc}')
        raise
    finally:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        if node is not None:
            node.close()
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
