import time

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage

try:
    import cv2
except ImportError:
    cv2 = None


class WebcamNode(Node):
    """Publishes a USB/webcam stream as sensor_msgs/CompressedImage."""

    def __init__(self):
        super().__init__("webcam_node")
        self.declare_parameter("camera_index", 0)
        self.declare_parameter("camera_source", "")
        self.declare_parameter("camera_fps", 60.0)
        self.declare_parameter("frame_id", "front_camera")
        self.declare_parameter("jpeg_quality", 80)

        self.camera_index = int(self.get_parameter("camera_index").value)
        self.camera_source = str(self.get_parameter("camera_source").value).strip()
        self.camera_fps = float(self.get_parameter("camera_fps").value)
        self.frame_id = str(self.get_parameter("frame_id").value)
        self.jpeg_quality = int(self.get_parameter("jpeg_quality").value)

        self.publisher = self.create_publisher(
            CompressedImage, "/camera/image/compressed", 10
        )
        self.capture = None
        self.timer = None

        if cv2 is None:
            self.get_logger().error("python3-opencv is not installed; webcam disabled")
            return

        source = self.camera_source if self.camera_source else self.camera_index
        self.capture = cv2.VideoCapture(source)
        if not self.capture.isOpened():
            self.get_logger().error(f"could not open camera source {source}")
            return

        period = 1.0 / max(1.0, self.camera_fps)
        self.timer = self.create_timer(period, self.publish_frame)
        self.get_logger().info(f"publishing camera {source} at {self.camera_fps} FPS")

    def publish_frame(self):
        ok, frame = self.capture.read()
        if not ok:
            self.get_logger().warning("failed to read camera frame")
            time.sleep(0.1)
            return

        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality]
        ok, encoded = cv2.imencode(".jpg", frame, encode_params)
        if not ok:
            self.get_logger().warning("failed to encode camera frame")
            return

        msg = CompressedImage()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.frame_id
        msg.format = "jpeg"
        msg.data = encoded.tobytes()
        self.publisher.publish(msg)

    def destroy_node(self):
        if self.capture is not None:
            self.capture.release()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = WebcamNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
