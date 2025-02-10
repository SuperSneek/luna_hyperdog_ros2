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
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, ExecuteProcess, RegisterEventHandler
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration, PythonExpression
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.event_handlers import OnProcessExit

from launch.substitutions import PathJoinSubstitution

import xacro

# configure robot's urdf file
pkg_hyperdog_gazebo = 'hyperdog_gazebo_sim'
robot_description_subpath = 'description/hyperdog.urdf.xacro'
xacro_file = os.path.join(get_package_share_directory(pkg_hyperdog_gazebo),robot_description_subpath)
robot_description_raw = xacro.process_file(xacro_file).toxml()

#configure gazebo
pkg_ros_gz_sim = FindPackageShare(package='ros_gz_sim').find('ros_gz_sim') 
pkg_hyperdog_gazebo = FindPackageShare(package='hyperdog_gazebo_sim').find('hyperdog_gazebo_sim')

# Set the path to the world file
world_file_name = 'contact.world'
world_path = os.path.join(pkg_hyperdog_gazebo, 'worlds', world_file_name)
# world_path = os.path.join(pkg_hyperdog_gazebo, 'worlds', 'contact.world')

# world_path = "/usr/share/gazebo-11/worlds/friction_demo.world"


# configure hyperdog teleop
teleop_pkg_name = 'hyperdog_teleop'
teleop_launch_file = "/hyperdog_teleop.launch.py"

# set the controller
gazebo_controller = 'hyperdog_joint_controller'
 
robot_controllers = PathJoinSubstitution(
  [
      FindPackageShare("hyperdog_gazebo_sim"),
      "config",
      "hyperdog_joint_controller.yaml",
  ]
)

 
def generate_launch_description():

  headless = LaunchConfiguration('headless')
  use_sim_time = LaunchConfiguration('use_sim_time')
  use_simulator = LaunchConfiguration('use_simulator')
  pkg_hyperdog_sim = get_package_share_directory('hyperdog_gazebo_sim')
  world = os.path.join(pkg_hyperdog_sim, 'worlds', 'flat.sdf')
 
  declare_simulator_cmd = DeclareLaunchArgument(
    name='headless',
    default_value='False',
    description='Whether to execute gzclient')
     
  declare_use_sim_time_cmd = DeclareLaunchArgument(
    name='use_sim_time',
    default_value='true',
    description='Use simulation (Gazebo) clock if true')
 
  declare_use_simulator_cmd = DeclareLaunchArgument(
    name='use_simulator',
    default_value='True',
    description='Whether to start the simulator')

  declare_robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description':robot_description_raw,
                    'use_sim_time':True}])
  
  hyperdog_gz_joint_ctrl_node = Node(
    package='hyperdog_gazebo_sim',
    executable='hyperdog_gazebo_joint_ctrl_node',
    output='screen'
  )
    
  robot_controllers_arg = DeclareLaunchArgument(
      "controller_config_path",
      default_value=robot_controllers,
      description="Path to the controller manager parameter file"
  )

  controller_config_path = LaunchConfiguration("controller_config_path")

  controller_node = Node(
      package="controller_manager",
      executable="ros2_control_node",
      parameters=[controller_config_path],
      output="both",
  )

  spawn_entity = Node(
            package='ros_gz_sim',
            executable='create',
            arguments=[
                '-name', 'luna',
                '-topic', 'robot_description',
                '-x', '0',
                '-y', '0',
                '-z', '1'
            ],
        )

  load_joint_state_controller = ExecuteProcess(
        cmd=['ros2', 'control', 'load_controller', '--set-state', 'active',
            'joint_state_broadcaster'],
        output='screen' )
  
  laod_forward_command_controller = ExecuteProcess(
        cmd=['ros2', 'control', 'load_controller', '--set-state', 'active', 
            'gazebo_joint_controller'],
        output='screen'
    )
  
  bridge = Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            parameters=[{
                'config_file': os.path.join(pkg_hyperdog_sim, 'config','gz_bridge.yaml'),
            }],
            output='screen'
        )

  pkg_gz_sim = get_package_share_directory('ros_gz_sim')


  # Specify the actions
  # Start Gazebo server
  gazebo = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_gz_sim, 'launch', 'gz_sim.launch.py')
            ),
            launch_arguments={'gz_args': f'-r {world}'}.items()
        )

 

  # Create the launch description and populate
  return  LaunchDescription([    
    declare_robot_state_publisher,
    RegisterEventHandler(
      event_handler=OnProcessExit(
        target_action=spawn_entity,
        on_exit=[load_joint_state_controller],
      )
    ),
    RegisterEventHandler(
      event_handler=OnProcessExit(
        target_action=load_joint_state_controller,
        on_exit=[laod_forward_command_controller],
      )
    ),
    bridge,
    robot_controllers_arg,
    declare_simulator_cmd,
    declare_use_sim_time_cmd,
    declare_use_simulator_cmd,
    gazebo,

    # load_joint_state_controller,
    # laod_forward_command_controller,

    controller_node,
    hyperdog_gz_joint_ctrl_node,
  
 ])