from setuptools import setup, find_packages

setup(
    name="appimagemanager",
    version="1.0.0",
    description="Easily install, manage, and remove AppImage applications on Ubuntu with multi-language support",
    url="https://github.com/tunjayoff/appimagemanager",
    author="tunjayoff",
    author_email="tuncayessiz9@gmail.com",
    license="MIT",
    packages=find_packages(include=["appimagemanager", "appimagemanager.*"]),
    include_package_data=True,
    install_requires=[
        "PyQt6>=6.5",
    ],
    entry_points={
        "console_scripts": [
            "appimagemanager=appimagemanager.main:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
    ],
) 