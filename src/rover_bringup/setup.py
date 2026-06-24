from glob import glob

from setuptools import setup

package_name = "rover_bringup"

setup(
    name=package_name,
    version="0.1.0",
    packages=[],
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/launch", glob("launch/*.launch.py")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="CarrinhoRC",
    maintainer_email="dev@example.com",
    description="Launch files for the CarrinhoRC rover.",
    license="MIT",
)
