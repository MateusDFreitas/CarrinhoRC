import math

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from std_msgs.msg import Int16, String


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


class ManualControlNode(Node):
    """Converts /cmd_vel commands into ESC and steering servo PWM targets."""

    def __init__(self):
        super().__init__("manual_control_node")

        self.declare_parameter("max_linear_speed", 1.0)
        self.declare_parameter("max_angular_speed", 1.0)
        self.declare_parameter("esc_neutral_pwm", 1500)
        self.declare_parameter("esc_min_pwm", 1100)
        self.declare_parameter("esc_max_pwm", 1900)
        self.declare_parameter("servo_center_pwm", 1500)
        self.declare_parameter("servo_min_pwm", 1000)
        self.declare_parameter("servo_max_pwm", 2000)
        self.declare_parameter("command_timeout_s", 0.35)

        self.max_linear_speed = float(self.get_parameter("max_linear_speed").value)
        self.max_angular_speed = float(self.get_parameter("max_angular_speed").value)
        self.esc_neutral_pwm = int(self.get_parameter("esc_neutral_pwm").value)
        self.esc_min_pwm = int(self.get_parameter("esc_min_pwm").value)
        self.esc_max_pwm = int(self.get_parameter("esc_max_pwm").value)
        self.servo_center_pwm = int(self.get_parameter("servo_center_pwm").value)
        self.servo_min_pwm = int(self.get_parameter("servo_min_pwm").value)
        self.servo_max_pwm = int(self.get_parameter("servo_max_pwm").value)
        self.command_timeout_s = float(self.get_parameter("command_timeout_s").value)

        self.last_command_time = self.get_clock().now()
        self.esc_pwm = self.esc_neutral_pwm
        self.servo_pwm = self.servo_center_pwm

        self.esc_pub = self.create_publisher(Int16, "/rover/esc_pwm", 10)
        self.servo_pub = self.create_publisher(Int16, "/rover/servo_pwm", 10)
        self.status_pub = self.create_publisher(String, "/rover/control_status", 10)
        self.create_subscription(Twist, "/cmd_vel", self.on_cmd_vel, 10)
        self.create_timer(0.05, self.on_timer)

        self.get_logger().info("manual_control_node ready: listening on /cmd_vel")

    def on_cmd_vel(self, msg):
        linear = clamp(msg.linear.x, -self.max_linear_speed, self.max_linear_speed)
        angular = clamp(msg.angular.z, -self.max_angular_speed, self.max_angular_speed)

        linear_scale = linear / self.max_linear_speed if self.max_linear_speed else 0.0
        angular_scale = angular / self.max_angular_speed if self.max_angular_speed else 0.0

        if math.isclose(linear_scale, 0.0, abs_tol=0.001):
            self.esc_pwm = self.esc_neutral_pwm
        elif linear_scale > 0:
            span = self.esc_max_pwm - self.esc_neutral_pwm
            self.esc_pwm = round(self.esc_neutral_pwm + span * linear_scale)
        else:
            span = self.esc_neutral_pwm - self.esc_min_pwm
            self.esc_pwm = round(self.esc_neutral_pwm + span * linear_scale)

        left_span = self.servo_center_pwm - self.servo_min_pwm
        right_span = self.servo_max_pwm - self.servo_center_pwm
        if angular_scale >= 0:
            self.servo_pwm = round(self.servo_center_pwm + right_span * angular_scale)
        else:
            self.servo_pwm = round(self.servo_center_pwm + left_span * angular_scale)

        self.esc_pwm = int(clamp(self.esc_pwm, self.esc_min_pwm, self.esc_max_pwm))
        self.servo_pwm = int(clamp(self.servo_pwm, self.servo_min_pwm, self.servo_max_pwm))
        self.last_command_time = self.get_clock().now()

    def on_timer(self):
        age = (self.get_clock().now() - self.last_command_time).nanoseconds / 1e9
        if age > self.command_timeout_s:
            self.esc_pwm = self.esc_neutral_pwm
            self.servo_pwm = self.servo_center_pwm

        self.esc_pub.publish(Int16(data=self.esc_pwm))
        self.servo_pub.publish(Int16(data=self.servo_pwm))
        mode = "timeout_stop" if age > self.command_timeout_s else "active"
        self.status_pub.publish(String(data=mode))


def main(args=None):
    rclpy.init(args=args)
    node = ManualControlNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
