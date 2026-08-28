"""Command-line interface for Pulse."""

import argparse
import sys
import time
from typing import NoReturn

from pulse import __version__
from pulse.config import add_endpoint, remove_endpoint, get_endpoints, load_config
from pulse.storage import init_db, record_check, get_history, get_status, get_last_status
from pulse.monitor import check_endpoint
from pulse.alerts import log_alert, format_status_message


def cmd_check(args: argparse.Namespace) -> int:
    """Execute the 'check' command.
    
    Args:
        args: Parsed command-line arguments.
    
    Returns:
        int: Exit code (0 for success, 1 for down/error).
    """
    init_db()
    config = load_config()
    timeout = args.timeout or config["default_timeout"]
    expected_status = getattr(args, "expected_status", 200)
    
    result = check_endpoint(args.url, timeout=timeout, expected_status=expected_status)
    record_check(
        url=args.url,
        status_code=result["status_code"],
        response_time=result["response_time"],
        is_up=result["is_up"],
        error_message=result["error"],
    )
    
    # Check for state change and log alert
    last_status = get_last_status(args.url)
    log_alert(args.url, last_status, result["is_up"])
    
    if getattr(args, "json", False):
        import json
        print(json.dumps(result, indent=2))
    else:
        print(format_status_message(
            args.url,
            result["is_up"],
            result["response_time"],
            result["status_code"],
        ))
    
    return 0 if result["is_up"] else 1


def cmd_monitor(args: argparse.Namespace) -> None:
    """Execute the 'monitor' command (daemon mode).
    
    Args:
        args: Parsed command-line arguments.
    """
    init_db()
    endpoints = get_endpoints()
    config = load_config()
    
    if not endpoints:
        print("No endpoints configured. Use 'pulse add <url>' to add one.")
        sys.exit(1)
    
    print(f"Starting Pulse monitor with {len(endpoints)} endpoint(s)...")
    print("Press Ctrl+C to stop.")
    
    try:
        while True:
            for endpoint in endpoints:
                url = endpoint["url"]
                timeout = endpoint.get("timeout", config["default_timeout"])
                expected_status = endpoint.get("expected_status", 200)
                
                result = check_endpoint(url, timeout=timeout, expected_status=expected_status)
                record_check(
                    url=url,
                    status_code=result["status_code"],
                    response_time=result["response_time"],
                    is_up=result["is_up"],
                    error_message=result["error"],
                )
                
                # Check for state change and log alert
                last_status = get_last_status(url)
                log_alert(url, last_status, result["is_up"])
                
                print(format_status_message(
                    url,
                    result["is_up"],
                    result["response_time"],
                    result["status_code"],
                ))
            
            # Wait for next check cycle
            time.sleep(config["check_interval"])
    except KeyboardInterrupt:
        print("\nMonitor stopped.")


def cmd_history(args: argparse.Namespace) -> None:
    """Execute the 'history' command.
    
    Args:
        args: Parsed command-line arguments.
    """
    init_db()
    
    if args.url:
        history = get_history(args.url, limit=args.limit)
    else:
        history = get_history(limit=args.limit)
    
    if getattr(args, "json", False):
        import json
        print(json.dumps(history, indent=2))
        return
    
    if not history:
        print("No check history found.")
        return
    
    print(f"{'Timestamp':<25} {'URL':<40} {'Status':<10} {'Time':<10} {'Result'}")
    print("-" * 100)
    
    for record in history:
        timestamp = record["timestamp"][:19]  # Trim microseconds
        url = record["url"][:38]
        status_code = str(record["status_code"]) if record["status_code"] else "N/A"
        response_time = f"{record['response_time']*1000:.0f}ms"
        result = "UP" if record["is_up"] else "DOWN"
        print(f"{timestamp:<25} {url:<40} {status_code:<10} {response_time:<10} {result}")


def cmd_status(args: argparse.Namespace) -> None:
    """Execute the 'status' command.
    
    Args:
        args: Parsed command-line arguments.
    """
    init_db()
    
    status = get_status(args.url)
    
    if getattr(args, "json", False):
        import json
        print(json.dumps(status, indent=2))
        return
    
    if not status:
        print("No status data available.")
        return
    
    if args.url:
        # Single URL status
        data = status[args.url]
        uptime = data["uptime_percentage"]
        icon = "✓" if data["is_up"] else "✗"
        print(f"{icon} {args.url}")
        print(f"  Status: {'UP' if data['is_up'] else 'DOWN'}")
        print(f"  Last check: {data['last_check'][:19] if data['last_check'] else 'N/A'}")
        print(f"  Uptime: {uptime:.1f}% ({data['up_checks']}/{data['total_checks']} checks)")
    else:
        # All endpoints status
        print(f"{'URL':<50} {'Status':<10} {'Uptime':<10} {'Last Check'}")
        print("-" * 90)
        for url, data in status.items():
            url_display = url[:48]
            status_icon = "✓" if data["is_up"] else "✗"
            status_text = "UP" if data["is_up"] else "DOWN"
            uptime = f"{data['uptime_percentage']:.1f}%"
            last_check = data["last_check"][:19] if data["last_check"] else "N/A"
            print(f"{url_display:<50} {status_text:<10} {uptime:<10} {last_check}")


def cmd_add(args: argparse.Namespace) -> None:
    """Execute the 'add' command.
    
    Args:
        args: Parsed command-line arguments.
    """
    add_endpoint(
        args.url,
        interval=args.interval,
        timeout=args.timeout,
        expected_status=getattr(args, "expected_status", None),
    )
    print(f"Added endpoint: {args.url}")


def cmd_remove(args: argparse.Namespace) -> None:
    """Execute the 'remove' command.
    
    Args:
        args: Parsed command-line arguments.
    """
    if remove_endpoint(args.url):
        print(f"Removed endpoint: {args.url}")
    else:
        print(f"Endpoint not found: {args.url}")
        sys.exit(1)


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser.
    
    Returns:
        argparse.ArgumentParser: Configured parser.
    """
    parser = argparse.ArgumentParser(
        prog="pulse",
        description="Pulse - A minimal service uptime monitor",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # check command
    check_parser = subparsers.add_parser(
        "check",
        help="Check a single URL immediately",
    )
    check_parser.add_argument("url", help="URL to check")
    check_parser.add_argument(
        "-t", "--timeout",
        type=int,
        help="Request timeout in seconds",
    )
    check_parser.add_argument(
        "--expected-status",
        type=int,
        default=200,
        help="Expected HTTP status code (default: 200)",
    )
    check_parser.add_argument(
        "--json",
        action="store_true",
        help="Output result as JSON",
    )
    check_parser.set_defaults(func=cmd_check)
    
    # monitor command
    monitor_parser = subparsers.add_parser(
        "monitor",
        help="Start monitoring all configured endpoints",
    )
    monitor_parser.set_defaults(func=cmd_monitor)
    
    # history command
    history_parser = subparsers.add_parser(
        "history",
        help="Show check history",
    )
    history_parser.add_argument(
        "-u", "--url",
        help="Filter by URL",
    )
    history_parser.add_argument(
        "-n", "--limit",
        type=int,
        default=20,
        help="Number of records to show (default: 20)",
    )
    history_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    history_parser.set_defaults(func=cmd_history)
    
    # status command
    status_parser = subparsers.add_parser(
        "status",
        help="Show current status of endpoints",
    )
    status_parser.add_argument(
        "-u", "--url",
        help="Filter by URL",
    )
    status_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    status_parser.set_defaults(func=cmd_status)
    
    # add command
    add_parser = subparsers.add_parser(
        "add",
        help="Add an endpoint to monitor",
    )
    add_parser.add_argument("url", help="URL to add")
    add_parser.add_argument(
        "-i", "--interval",
        type=int,
        help="Check interval in seconds",
    )
    add_parser.add_argument(
        "-t", "--timeout",
        type=int,
        help="Request timeout in seconds",
    )
    add_parser.add_argument(
        "--expected-status",
        type=int,
        default=200,
        help="Expected HTTP status code (default: 200)",
    )
    add_parser.set_defaults(func=cmd_add)
    
    # remove command
    remove_parser = subparsers.add_parser(
        "remove",
        help="Remove an endpoint from monitoring",
    )
    remove_parser.add_argument("url", help="URL to remove")
    remove_parser.set_defaults(func=cmd_remove)
    
    return parser


def main() -> NoReturn:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(0)
    
    args.func(args)
