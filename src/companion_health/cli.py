"""
Command-line interface for companion health monitor.

AP_FLAKE8_CLEAN
"""

import argparse
import logging
import signal
import sys
from typing import List, Optional

from .config import Config
from .monitor import HealthMonitor


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        args: Arguments to parse (defaults to sys.argv)

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description='Companion Computer Health Monitor for ArduPilot',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use config file
  %(prog)s --config config.yaml

  # Connect to SITL via UDP
  %(prog)s --device udpout:127.0.0.1:14560

  # Connect via USB serial
  %(prog)s --device /dev/ttyACM0 --baud 115200

  # Connect via UART with higher rate
  %(prog)s --device /dev/ttyS0 --baud 921600 --rate 2.0
"""
    )
    parser.add_argument(
        '--config', '-c',
        help='Path to YAML configuration file'
    )
    parser.add_argument(
        '--device', '-d',
        help='MAVLink connection string (overrides config)'
    )
    parser.add_argument(
        '--baud', '-b',
        type=int,
        help='Baud rate for serial connections (overrides config)'
    )
    parser.add_argument(
        '--rate', '-r',
        type=float,
        help='Message send rate in Hz (overrides config)'
    )
    parser.add_argument(
        '--source-system', '-s',
        type=int,
        help='MAVLink source system ID (overrides config)'
    )
    parser.add_argument(
        '--source-component',
        type=int,
        help='MAVLink source component ID (overrides config)'
    )
    parser.add_argument(
        '--platform', '-p',
        choices=['generic', 'raspberry_pi', 'jetson'],
        help='Force specific platform backend (overrides auto-detect)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable debug logging'
    )
    parser.add_argument(
        '--version',
        action='store_true',
        help='Show version and exit'
    )
    return parser.parse_args(args)


def build_config(args: argparse.Namespace) -> Config:
    """Build configuration from args and optional config file.

    Args:
        args: Parsed command-line arguments

    Returns:
        Config instance
    """
    # Start with config file if provided
    if args.config:
        config = Config.from_file(args.config)
    else:
        config = Config()

    # Override with command-line arguments
    if args.device:
        config.connection.device = args.device
    if args.baud:
        config.connection.baud = args.baud
    if args.rate:
        config.monitoring.rate_hz = args.rate
    if args.source_system:
        config.connection.source_system = args.source_system
    if args.source_component:
        config.connection.source_component = args.source_component
    if args.platform:
        config.platform = args.platform

    return config


def main(args: Optional[List[str]] = None) -> int:
    """Main entry point.

    Args:
        args: Command-line arguments (defaults to sys.argv)

    Returns:
        Exit code
    """
    parsed = parse_args(args)

    if parsed.version:
        from . import __version__
        print(f"companion-health-monitor {__version__}")
        return 0

    logging.basicConfig(
        level=logging.DEBUG if parsed.verbose else logging.INFO,
        format='%(asctime)s %(levelname)s: %(message)s',
        datefmt='%H:%M:%S'
    )

    config = build_config(parsed)
    monitor = HealthMonitor(config)

    def signal_handler(signum: int, frame) -> None:
        logging.info("Received signal %d, stopping...", signum)
        monitor.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    return monitor.run()


if __name__ == '__main__':
    sys.exit(main())
