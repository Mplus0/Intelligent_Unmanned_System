"""Board-side end-to-end smoke test; run after sourcing install/setup.bash."""
import json
import signal
import subprocess
import time
import urllib.request
from pathlib import Path
import cv2
import numpy as np
import rclpy
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_srvs.srv import Trigger

Path('test_results').mkdir(exist_ok=True)
log = open('test_results/launch.log', 'w')
p = subprocess.Popen(['ros2', 'launch', 'camera', 'camera.launch.py'], stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
rclpy.init()
n = rclpy.create_node('camera_acceptance')
stamps = []
meta = {}
def callback(m):
    stamps.append(time.monotonic())
    meta.update(width=m.width, height=m.height, encoding=m.encoding, size=len(m.data), step=m.step)
s = n.create_subscription(Image, '/camera/image_raw', callback, qos_profile_sensor_data)
try:
    deadline = time.monotonic() + 30
    while len(stamps) < 150 and time.monotonic() < deadline:
        rclpy.spin_once(n, timeout_sec=.2)
    assert len(stamps) >= 30, len(stamps)
    assert meta == dict(width=1920, height=1080, encoding='bgr8', size=6220800, step=5760), meta
    result = dict(frames=len(stamps), fps=(len(stamps)-1)/(stamps[-1]-stamps[0]), image=meta)
    client = n.create_client(Trigger, '/camera/save_image')
    assert client.wait_for_service(timeout_sec=5)
    future = client.call_async(Trigger.Request())
    rclpy.spin_until_future_complete(n, future, timeout_sec=10)
    assert future.done() and future.result().success
    result['saved_image'] = future.result().message
    assert cv2.imread(future.result().message).shape == (1080, 1920, 3)
    with urllib.request.urlopen('http://127.0.0.1:8080/', timeout=5) as r:
        assert r.status == 200
    with urllib.request.urlopen('http://127.0.0.1:8080/stream.mjpg', timeout=5) as r:
        assert r.readline().strip() == b'--frame'
        r.readline()
        size = int(r.readline().split(b':')[1])
        r.readline()
        data = r.read(size)
        assert cv2.imdecode(np.frombuffer(data, np.uint8), 1).shape == (1080, 1920, 3)
    result['preview'] = 'JPEG decoded 1920x1080'
    print(json.dumps(result, indent=2))
    Path('test_results/acceptance.json').write_text(json.dumps(result, indent=2))
finally:
    n.destroy_node()
    rclpy.shutdown()
    p.send_signal(signal.SIGINT)
    p.wait(timeout=20)
    log.close()
    print('Launch exit:', p.returncode)
