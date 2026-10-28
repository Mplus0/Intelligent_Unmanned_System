from glob import glob
from setuptools import setup

package_name = 'camera'
setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name, package_name + '.camera_driver', package_name + '.image_processing', package_name + '.ros_node'],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/config', glob('config/*.yaml')),
        ('share/' + package_name + '/launch', glob('launch/*.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='RDK X5 User',
    maintainer_email='user@example.com',
    description='RDK camera capture and ROS 2 image publishing.',
    license='Apache-2.0',
    entry_points={'console_scripts': ['camera_node = camera.ros_node.camera_node:main']},
)
