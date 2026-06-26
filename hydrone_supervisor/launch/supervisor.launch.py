from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='hydrone_supervisor',
            executable='supervisor_node',
            name='hydrone_supervisor',
            output='screen',
            parameters=[{'use_sim_time': True}],
            # Mapeamentos podem ser feitos aqui ou via namespaces no código
        )
    ])
