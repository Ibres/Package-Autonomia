import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    config = os.path.join(
        get_package_share_directory('hydrone_supervisor'),
        'config',
        'supervisor_params.yaml'
    )

    return LaunchDescription([
        Node(
            package='hydrone_supervisor',
            executable='supervisor_node',
            name='hydrone_supervisor',
            output='screen',
            parameters=[config],
            remappings=[
                ('/gps/fix', '/mavros/global_position/global'),
                ('/imu/data', '/mavros/imu/data'),
                ('/battery', '/mavros/battery'),
            ]
        )
    ])
