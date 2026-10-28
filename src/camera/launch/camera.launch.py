from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    config = os.path.join(get_package_share_directory('camera'), 'config', 'camera.yaml')
    return LaunchDescription([
        DeclareLaunchArgument('params_file', default_value=config, description='Camera YAML configuration'),
        Node(package='camera', executable='camera_node', name='camera', output='screen', parameters=[LaunchConfiguration('params_file')]),
    ])
