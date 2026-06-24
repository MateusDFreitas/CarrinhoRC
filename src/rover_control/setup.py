from setuptools import find_packages, setup

package_name = "rover_control"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="CarrinhoRC",
    maintainer_email="dev@example.com",
    description="Control, telemetry and camera nodes for the CarrinhoRC rover.",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "manual_control_node = rover_control.manual_control_node:main",
            "telemetry_node = rover_control.telemetry_node:main",
            "webcam_node = rover_control.webcam_node:main",
        ],
    },
)
