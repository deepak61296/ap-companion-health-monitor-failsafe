#!/bin/bash
#
# Companion Health Monitor - Automated Setup Script
#
# This script sets up everything needed to run the companion health monitor
# on any Linux system (Jetson, Raspberry Pi, or generic x86).
#
# Usage:
#   ./scripts/setup.sh
#
# What it does:
#   1. Checks system requirements
#   2. Creates Python virtual environment
#   3. Installs dependencies
#   4. Builds pymavlink with COMPANION_HEALTH message
#   5. Verifies installation
#   6. Creates default config file
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPANION_DIR="$(dirname "$SCRIPT_DIR")"
ARDUPILOT_DIR="$(dirname "$COMPANION_DIR")"
MAVLINK_DIR="$ARDUPILOT_DIR/modules/mavlink"
VENV_DIR="$COMPANION_DIR/venv"

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Error counter
ERRORS=0

# Check function
check() {
    if [ $? -eq 0 ]; then
        log_success "$1"
    else
        log_error "$1"
        ERRORS=$((ERRORS + 1))
    fi
}

echo ""
echo "=============================================="
echo " Companion Health Monitor - Setup Script"
echo "=============================================="
echo ""

# Detect platform
log_info "Detecting platform..."
PLATFORM="generic"
if [ -f /etc/nv_tegra_release ] || [ -d /sys/devices/gpu.0 ]; then
    PLATFORM="jetson"
    log_success "Detected: NVIDIA Jetson"
elif [ -f /usr/bin/vcgencmd ] || [ -f /opt/vc/bin/vcgencmd ]; then
    PLATFORM="raspberry_pi"
    log_success "Detected: Raspberry Pi"
else
    log_success "Detected: Generic Linux"
fi

# Check Python
log_info "Checking Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
    log_success "Python $PYTHON_VERSION found"
else
    log_error "Python 3 not found. Please install Python 3.8+"
    exit 1
fi

# Check pip
log_info "Checking pip..."
if python3 -m pip --version &> /dev/null; then
    log_success "pip found"
else
    log_error "pip not found. Installing..."
    sudo apt-get update && sudo apt-get install -y python3-pip
    check "pip installed"
fi

# Check mavlink directory
log_info "Checking MAVLink directory..."
if [ -d "$MAVLINK_DIR/pymavlink" ]; then
    log_success "MAVLink found at $MAVLINK_DIR"
else
    log_error "MAVLink not found at $MAVLINK_DIR"
    log_error "Make sure you're running from ArduPilot repository"
    exit 1
fi

# Check COMPANION_HEALTH message
log_info "Checking COMPANION_HEALTH message definition..."
if grep -q "COMPANION_HEALTH" "$MAVLINK_DIR/message_definitions/v1.0/ardupilotmega.xml" 2>/dev/null; then
    log_success "COMPANION_HEALTH message found in ardupilotmega.xml"
else
    log_error "COMPANION_HEALTH message not found!"
    log_error "Please add the message to ardupilotmega.xml first"
    exit 1
fi

# Create virtual environment
log_info "Creating virtual environment..."
if [ -d "$VENV_DIR" ]; then
    log_warning "Virtual environment already exists, recreating..."
    rm -rf "$VENV_DIR"
fi
python3 -m venv "$VENV_DIR"
check "Virtual environment created at $VENV_DIR"

# Activate virtual environment
log_info "Activating virtual environment..."
source "$VENV_DIR/bin/activate"
check "Virtual environment activated"

# Upgrade pip
log_info "Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1
check "pip upgraded"

# Install build dependencies
log_info "Installing build dependencies..."
pip install lxml cython > /dev/null 2>&1
check "Build dependencies installed (lxml, cython)"

# Build and install pymavlink
log_info "Building pymavlink with COMPANION_HEALTH message..."
log_info "This may take a few minutes..."
cd "$MAVLINK_DIR/pymavlink"
MDEF="$MAVLINK_DIR/message_definitions" pip install . > /dev/null 2>&1
check "pymavlink built and installed"

# Install runtime dependencies
log_info "Installing runtime dependencies..."
cd "$COMPANION_DIR"
pip install psutil pyserial PyYAML > /dev/null 2>&1
check "Runtime dependencies installed (psutil, pyserial, PyYAML)"

# Verify COMPANION_HEALTH message
log_info "Verifying COMPANION_HEALTH message..."
VERIFY_RESULT=$(python3 -c "
import os
os.environ['MAVLINK20'] = '1'
from pymavlink.dialects.v20 import ardupilotmega
print(ardupilotmega.MAVLINK_MSG_ID_COMPANION_HEALTH)
" 2>&1)

if [ "$VERIFY_RESULT" = "11061" ]; then
    log_success "COMPANION_HEALTH message verified (ID: 11061)"
else
    log_error "COMPANION_HEALTH message verification failed"
    log_error "Output: $VERIFY_RESULT"
    ERRORS=$((ERRORS + 1))
fi

# Create config file if it doesn't exist
log_info "Setting up configuration..."
if [ ! -f "$COMPANION_DIR/config.yaml" ]; then
    cp "$COMPANION_DIR/config.yaml.example" "$COMPANION_DIR/config.yaml"
    log_success "Created config.yaml from example"
else
    log_warning "config.yaml already exists, not overwriting"
fi

# Detect USB devices
log_info "Checking for USB serial devices..."
USB_DEVICES=$(ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null || true)
if [ -n "$USB_DEVICES" ]; then
    log_success "Found USB serial devices:"
    for dev in $USB_DEVICES; do
        echo "         $dev"
    done
else
    log_warning "No USB serial devices found (connect Cube Orange via USB)"
fi

# Print summary
echo ""
echo "=============================================="
echo " Setup Summary"
echo "=============================================="
echo ""
echo "  Platform:     $PLATFORM"
echo "  Python:       $PYTHON_VERSION"
echo "  Virtual env:  $VENV_DIR"
echo "  Config file:  $COMPANION_DIR/config.yaml"
echo ""

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}=============================================="
    echo " Setup completed successfully!"
    echo "==============================================${NC}"
    echo ""
    echo "Next steps:"
    echo ""
    echo "  1. Activate the virtual environment:"
    echo "     source $VENV_DIR/bin/activate"
    echo ""
    echo "  2. Edit config.yaml with your connection settings:"
    echo "     nano $COMPANION_DIR/config.yaml"
    echo ""
    echo "  3. Run the health monitor:"
    echo "     cd $COMPANION_DIR"
    echo "     python health_monitor.py --config config.yaml --verbose"
    echo ""
    echo "  For USB connection to Cube Orange:"
    echo "     python health_monitor.py --device /dev/ttyACM0 --verbose"
    echo ""
else
    echo -e "${RED}=============================================="
    echo " Setup completed with $ERRORS error(s)"
    echo "==============================================${NC}"
    echo ""
    echo "Please fix the errors above and run setup again."
    exit 1
fi
