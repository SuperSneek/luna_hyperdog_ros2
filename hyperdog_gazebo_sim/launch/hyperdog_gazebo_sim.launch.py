# __________________________________________________________________________________
# MIT License                                                                       |
#                                                                                   |
# Copyright (c) 2024 W.M. Nipun Dhananjaya Weerakkodi                               |
#                                                                                   | 
# Permission is hereby granted, free of charge, to any person obtaining a copy      |
# of this software and associated documentation files (the "Software"), to deal     |
# in the Software without restriction, including without limitation the rights      |
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell         |
# copies of the Software, and to permit persons to whom the Software is             |
# furnished to do so, subject to the following conditions:                          |
#                                                                                   |
# The above copyright notice and this permission notice shall be included in all    |
# copies or substantial portions of the Software.                                   |
#                                                                                   |
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR        |
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,          |
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE       |
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER            |
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,     |
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE     |
# SOFTWARE.                                                                         |
# __________________________________________________________________________________|
 
import os

from black import out
from launch import LaunchDescription
from ament_index_python.packages import get_package_share_directory
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, ExecuteProcess, RegisterEventHandler, OpaqueFunction
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration, PythonExpression
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.event_handlers import OnProcessExit

from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution

import xacro

# configure robot's urdf file
pkg_hyperdog_gazebo = 'hyperdog_gazebo_sim'
robot_description_subpath = 'description/hyperdog.urdf.xacro'
xacro_file = os.path.join(get_package_share_directory(pkg_hyperdog_gazebo),robot_description_subpath)
robot_description_raw = xacro.process_file(xacro_file).toxml()

#configure gazebo
pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')
pkg_hyperdog_gazebo = get_package_share_directory('hyperdog_gazebo_sim')

# Set the path to the world file
world_file_name = 'flat.sdf'
world_path = os.path.join(pkg_hyperdog_gazebo, 'worlds', world_file_name)
# world_path = os.path.join(pkg_hyperdog_gazebo, 'worlds', 'contact.world')

# world_path = "/usr/share/gazebo-11/worlds/friction_demo.world"


# configure hyperdog teleop
teleop_pkg_name = 'hyperdog_teleop'
teleop_launch_file = "/hyperdog_teleop.launch.py"

# set the controller
gazebo_controller = 'hyperdog_joint_controller'
 


 
def generate_launch_description():
  use_sim_time = LaunchConfiguration('use_sim_time', default=True)
  headless = LaunchConfiguration('headless')

  def robot_state_publisher(context):
    performed_description_format = LaunchConfiguration('description_format').perform(context)
    # Get URDF or SDF via xacro
    robot_description_content = robot_description_raw
    robot_description = {'robot_description': robot_description_content}
    node_robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[robot_description]
    )
    return [node_robot_state_publisher]
  
  robot_controllers = PathJoinSubstitution(
    [
        FindPackageShare("hyperdog_gazebo_sim"),
        "config",
        "hyperdog_joint_controller.yaml",
    ]
  )

  spawn_entity = Node(
          package='ros_gz_sim',
          executable='create',
          arguments=[
              '-topic', 'robot_description',
              '-x', '0',
              '-y', '0',
              '-z', '1'
          ],
      )
  
  joint_state_broadcaster_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster'],
    )
  
  forward_command_controller = ExecuteProcess(
        cmd=['ros2', 'control', 'load_controller', '--set-state', 'active', 
            'gazebo_joint_controller'],
        output='screen'
    )
  
  effort_controller = ExecuteProcess(
        cmd=['ros2', 'control', 'load_controller', '--set-state', 'inactive', 
            'effort_controller'],
        output='screen'
    )
  
  # Bridge
  bridge = Node(
      package='ros_gz_bridge',
      executable='parameter_bridge',
      arguments=['/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'],
      output='screen'
  )

  ld = LaunchDescription([
      # Launch gazebo environment
      IncludeLaunchDescription(
          PythonLaunchDescriptionSource(
              [PathJoinSubstitution([FindPackageShare('ros_gz_sim'),
                                     'launch',
                                     'gz_sim.launch.py'])]),
          launch_arguments=[('gz_args', [' -r -v 1 empty.sdf'])]),
      RegisterEventHandler(
          event_handler=OnProcessExit(
              target_action=spawn_entity,
              on_exit=[joint_state_broadcaster_spawner],
          )
      ),
      RegisterEventHandler(
          event_handler=OnProcessExit(
              target_action=joint_state_broadcaster_spawner,
              on_exit=[forward_command_controller, effort_controller],
          )
      ),
      bridge,
      spawn_entity,
      # Launch Arguments
      DeclareLaunchArgument(
          'use_sim_time',
          default_value=use_sim_time,
          description='If true, use simulated clock'),
      DeclareLaunchArgument(
          'description_format',
          default_value='urdf',
          description='Robot description format to use, urdf or sdf'),
  ])
  ld.add_action(OpaqueFunction(function=robot_state_publisher))
  return ld

  