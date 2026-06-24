import json
import random

import rclpy
from rclpy.node import Node
from std_msgs.msg import Int16, String


class TelemetryNode(Node):
    """Publishes dashboard-friendly JSON telemetry."""

    def __init__(self):
        super().__init__("telemetry_node")
        self.declare_parameter("battery_percent", 87.0)

        self.esc_pwm = 1500
        self.servo_pwm = 1500
        self.control_status = "standby"
        self.battery_percent = float(self.get_parameter("battery_percent").value)

        self.telemetry_pub = self.create_publisher(String, "/rover/telemetry", 10)
        self.create_subscription(Int16, "/rover/esc_pwm", self.on_esc_pwm, 10)
        self.create_subscription(Int16, "/rover/servo_pwm", self.on_servo_pwm, 10)
        self.create_subscription(String, "/rover/control_status", self.on_control_status, 10)
        self.create_timer(0.2, self.publish_telemetry)

    def on_esc_pwm(self, msg):
        self.esc_pwm = msg.data

    def on_servo_pwm(self, msg):
        self.servo_pwm = msg.data

    def on_control_status(self, msg):
        self.control_status = msg.data

    def publish_telemetry(self):
        esc_span = 400.0
        speed_percent = min(100.0, abs(self.esc_pwm - 1500) / esc_span * 100.0)
        payload = {
            "battery": round(self.battery_percent, 1),
            "speed": round(speed_percent, 1),
            "esc_pwm": self.esc_pwm,
            "servo_pwm": self.servo_pwm,
            "control_status": self.control_status,
            "latency_ms": random.randint(12, 35),
        }
        self.telemetry_pub.publish(String(data=json.dumps(payload)))


def main(args=None):
    rclpy.init(args=args)
    node = TelemetryNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
