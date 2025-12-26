from setuptools import setup, find_packages
import os

# Read long description from README.md
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Automatically include package data
package_data = {
    "appimagemanager": [
        "resources/*.json",
        "resources/*.png",
    ],
}

setup(
    name="appimagemanager",
    version="1.0.1",
    description="Easily install, manage, and remove AppImage applications on Linux systems",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/tunjayoff/appimagemanager",
    author="Tuncay EŞSİZ",
    author_email="tuncayessiz9@gmail.com",
    license="MIT",
    packages=find_packages(include=["appimagemanager", "appimagemanager.*"]),
    include_package_data=True,
    package_data=package_data,
    python_requires=">=3.8",
    install_requires=[
        "PyQt6>=6.5",
        "packaging>=23.0",
    ],
    extras_require={
        "dev": [
            "build>=0.10.0",
            "twine>=4.0.2",
            "flake8>=6.0.0",
            "pyinstaller>=5.13.0",
            "pytest>=7.3.1",
        ],
    },
    entry_points={
        "console_scripts": [
            "appimagemanager=appimagemanager.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Utilities",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Environment :: X11 Applications :: Qt",
    ],
    keywords="appimage, linux, package-manager, desktop-integration, utility",
    project_urls={
        "Bug Reports": "https://github.com/tunjayoff/appimagemanager/issues",
        "Source": "https://github.com/tunjayoff/appimagemanager",
        "Documentation": "https://github.com/tunjayoff/appimagemanager/tree/main/documentation",
    },
) 