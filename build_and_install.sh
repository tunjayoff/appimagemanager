#!/usr/bin/env bash
set -euo pipefail

# ANSI color codes for output styling
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Banner
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   AppImage Manager Build & Install   ${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Configuration
VERSION="1.0.0"
PKG_NAME="appimagemanager"
DEB_NAME="${PKG_NAME}_${VERSION}_amd64.deb"
MAINTAINER="tunjayoff <tuncayessiz9@gmail.com>"

# Clean previous builds and artifacts
rm -rf dist build .venv deb_pkg *.deb || true

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install build dependencies
pip install --upgrade pip
pip install pyinstaller

## Install project dependencies
echo -e "${YELLOW}Installing project dependencies...${NC}"
pip install -r requirements.txt

## Spinner for long-running commands
spinner() {
  local pid=$1
  local delay=0.1
  local spinstr='|/-\\'
  echo -n " "
  while kill -0 $pid 2>/dev/null; do
    for i in {0..3}; do
      echo -ne "\b${spinstr:$i:1}"
      sleep $delay
    done
  done
  echo -ne "\b"
}

# Build standalone executable
echo -e "${YELLOW}Building standalone executable...${NC}"
# Prepare log file
LOG_FILE="build.log"
# Determine PyQt6 plugins directory
PLUGINS_DIR=$(python3 - <<'PY'
import os, PyQt6; print(os.path.join(os.path.dirname(PyQt6.__file__), 'Qt6/plugins'))
PY
)
# Run PyInstaller in background, redirecting logs
(pyinstaller --log-level=WARN --clean --noconfirm --onefile --windowed --name ${PKG_NAME} \
  --add-data "appimagemanager/resources:appimagemanager/resources" \
  --add-data "${PLUGINS_DIR}/platforms:platforms" \
  --collect-all PyQt6 \
  main.py >"${LOG_FILE}" 2>&1) &
build_pid=$!
spinner $build_pid
wait $build_pid
build_status=$?
if [ $build_status -ne 0 ]; then
  echo -e "${RED}Build failed! Check ${LOG_FILE} for details.${NC}"
  exit $build_status
else
  echo -e " ${GREEN}Build succeeded!${NC}"
fi

# Prepare Debian package structure
echo -e "\n${YELLOW}Creating Debian package layout...${NC}"
mkdir -p deb_pkg/usr/bin deb_pkg/DEBIAN
cp dist/${PKG_NAME} deb_pkg/usr/bin/${PKG_NAME}

# Create control file
echo -e "${YELLOW}Creating Debian control file...${NC}"
cat > deb_pkg/DEBIAN/control <<EOF
Package: ${PKG_NAME}
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: amd64
Maintainer: ${MAINTAINER}
Depends: libxcb-cursor0
Description: Easily install, manage, and remove AppImage applications on Ubuntu with multi-language support.
EOF

# Build the .deb package
echo -e "${YELLOW}Building .deb package: ${DEB_NAME}${NC}"
dpkg-deb --build deb_pkg ${DEB_NAME}

# Uninstall any existing version
echo -e "\n${YELLOW}Removing existing installation (if any)...${NC}"
sudo dpkg -r ${PKG_NAME} || true

# Install newly built package
echo -e "${YELLOW}Installing new package ${DEB_NAME}...${NC}"
sudo dpkg -i ${DEB_NAME}

echo -e "\n${GREEN}Build and installation complete!${NC}"
echo -e "${GREEN}Run with: ${PKG_NAME}${NC}" 