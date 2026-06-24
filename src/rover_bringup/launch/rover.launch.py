from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, LogInfo, OpaqueFunction
from launch.launch_description_sources import AnyLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch.substitutions import PathJoinSubstitution
from ament_index_python.packages import PackageNotFoundError, get_package_share_directory


def is_enabled(value):
    return str(value).lower() in ("1", "true", "yes", "on")


def launch_setup(context, *args, **kwargs):
    camera_index = LaunchConfiguration("camera_index")
    camera_fps = LaunchConfiguration("camera_fps")
    max_linear_speed = LaunchConfiguration("max_linear_speed")
    max_angular_speed = LaunchConfiguration("max_angular_speed")
    enable_camera = LaunchConfiguration("enable_camera").perform(context)
    enable_rosbridge = LaunchConfiguration("enable_rosbridge").perform(context)
    rosbridge_port = LaunchConfiguration("rosbridge_port")

    actions = []
    if is_enabled(enable_rosbridge):
        try:
            rosbridge_share = get_package_share_directory("rosbridge_server")
            rosbridge_path = PathJoinSubstitution(
                [rosbridge_share, "launch", "rosbridge_websocket_launch.xml"]
            )
            actions.append(
                IncludeLaunchDescription(
                    AnyLaunchDescriptionSource(rosbridge_path),
                    launch_arguments={"port": rosbridge_port}.items(),
                )
            )
        except PackageNotFoundError:
            actions.append(
                LogInfo(
                    msg=(
                        "rosbridge_server not found; dashboard WebSocket disabled. "
                        "Install ros-$ROS_DISTRO-rosbridge-server."
                    )
                )
            )
    else:
        actions.append(LogInfo(msg="rosbridge disabled by enable_rosbridge:=false"))

    actions.extend(
        [
            Node(
                package="rover_control",
                executable="manual_control_node",
                name="manual_control_node",
                output="screen",
                parameters=[
                    {
                        "max_linear_speed": max_linear_speed,
                        "max_angular_speed": max_angular_speed,
                    }
                ],
            ),
            Node(
                package="rover_control",
                executable="telemetry_node",
                name="telemetry_node",
                output="screen",
            ),
        ]
    )
    if is_enabled(enable_camera):
        actions.append(
            Node(
                package="rover_control",
                executable="webcam_node",
                name="webcam_node",
                output="screen",
                parameters=[
                    {
                        "camera_index": camera_index,
                        "camera_fps": camera_fps,
                    }
                ],
            )
        )
    else:
        actions.append(LogInfo(msg="webcam disabled by enable_camera:=false"))

    return actions


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument("camera_index", default_value="0"),
            DeclareLaunchArgument("camera_fps", default_value="20.0"),
            DeclareLaunchArgument("max_linear_speed", default_value="1.0"),
            DeclareLaunchArgument("max_angular_speed", default_value="1.0"),
            DeclareLaunchArgument("enable_camera", default_value="true"),
            DeclareLaunchArgument("enable_rosbridge", default_value="true"),
            DeclareLaunchArgument("rosbridge_port", default_value="9090"),
            OpaqueFunction(function=launch_setup),
        ]
    )
