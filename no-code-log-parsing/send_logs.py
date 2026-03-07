#!/usr/bin/env python3
"""
Send log messages from JSONC template files to the New Relic Log API.

This script:
- Loads environment variables from .env file or accepts them as arguments
- Loads a JSONC template file containing log entries
- Adds the logtype field to all log entries
- Streams logs to the appropriate New Relic Logs API endpoint (1 log every 5 seconds)

Usage:
    python send_logs.py
    python send_logs.py --log_file custom_logs.jsonc
    python send_logs.py --license_key YOUR_KEY --environment us_prod
    python send_logs.py --duration 60
"""

import argparse
import requests  # type: ignore
import json
import sys
import os
import math
import time
from pathlib import Path
from dotenv import load_dotenv  # type: ignore


# New Relic Log API endpoints
LOG_API_ENDPOINTS = {
    "staging": "https://staging-log-api.newrelic.com/log/v1",
    "us_prod": "https://log-api.newrelic.com/log/v1",
    "eu_prod": "https://log-api.eu.newrelic.com/log/v1"
}


def send_single_log(license_key, log_entry, endpoint_url):
    """
    Sends a single log entry to the New Relic Log API.

    Args:
        license_key (str): Your New Relic License Key.
        log_entry (dict): A single log entry dictionary.
        endpoint_url (str): The Log API endpoint URL.

    Returns:
        bool: True if the request was successful (status code 202), False otherwise.
    """
    headers = {
        "Api-Key": license_key,
        "Content-Type": "application/json"
    }

    payload_json = json.dumps([log_entry])

    try:
        response = requests.post(endpoint_url, headers=headers, data=payload_json, timeout=10)

        if response.status_code == 202:
            return True
        else:
            print(f"[ERROR] Failed to send log.", file=sys.stderr)
            print(f"Status Code: {response.status_code}", file=sys.stderr)
            print(f"Response: {response.text}", file=sys.stderr)
            return False
    except requests.exceptions.Timeout:
        print(f"[ERROR] Request timed out while sending log.", file=sys.stderr)
        return False
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] An error occurred while sending the request.", file=sys.stderr)
        print(f"Error: {e}", file=sys.stderr)
        return False


def add_logtype_to_entries(log_entries, logtype):
    """
    Adds the logtype field to all log entries.

    Args:
        log_entries (list): List of log entry dictionaries.
        logtype (str): The logtype value to add.

    Returns:
        list: Updated log entries with logtype field.
    """
    updated_entries = []
    for entry in log_entries:
        updated_entry = entry.copy()
        updated_entry["logtype"] = logtype
        updated_entries.append(updated_entry)
    return updated_entries


def main():
    """
    Main function to parse arguments and process the log file.
    """
    # Load .env file if it exists
    env_path = Path(__file__).parent / '.env'
    load_dotenv(dotenv_path=env_path)

    parser = argparse.ArgumentParser(
        description="Send log messages from JSONC templates to the New Relic Log API.",
        epilog="Example: python send_logs.py --log_file logs.jsonc --duration 60"
    )
    parser.add_argument(
        "--log_file",
        default="logs.jsonc",
        help="Path to the JSONC log file to send (default: logs.jsonc)"
    )
    parser.add_argument(
        "--license_key",
        help="Your New Relic License Key (overrides .env)"
    )
    parser.add_argument(
        "--environment",
        choices=['staging', 'us_prod', 'eu_prod'],
        help="Target environment (overrides .env)"
    )
    parser.add_argument(
        "--logtype",
        help="Log type identifier to add to all logs (overrides .env)"
    )
    parser.add_argument(
        "--duration",
        type=int,
        help="Total duration to stream logs in seconds (overrides NR_DURATION_SECONDS in .env)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        choices=[1, 5],
        help="Seconds between each log send (1 or 5, overrides NR_INTERVAL_SECONDS in .env, default: 5)"
    )

    args = parser.parse_args()

    # Get configuration from args or environment variables
    license_key = args.license_key or os.getenv('NR_LICENSE_KEY')
    environment = args.environment or os.getenv('NR_ENVIRONMENT', 'us_prod')
    logtype = args.logtype or os.getenv('NR_LOGTYPE')

    # Resolve interval from arg or env
    if args.interval is not None:
        interval = args.interval
    else:
        interval_env = os.getenv('NR_INTERVAL_SECONDS', '5')
        try:
            interval = int(interval_env)
        except ValueError:
            print(f"[ERROR] NR_INTERVAL_SECONDS must be an integer, got: {interval_env}", file=sys.stderr)
            sys.exit(1)
        if interval not in (1, 5):
            print(f"[ERROR] NR_INTERVAL_SECONDS must be 1 or 5, got: {interval}", file=sys.stderr)
            sys.exit(1)

    # Resolve duration from arg or env
    if args.duration is not None:
        duration = args.duration
    else:
        duration_env = os.getenv('NR_DURATION_SECONDS')
        if not duration_env:
            print("[ERROR] Duration is required. Provide via --duration or set NR_DURATION_SECONDS in .env", file=sys.stderr)
            sys.exit(1)
        try:
            duration = int(duration_env)
        except ValueError:
            print(f"[ERROR] NR_DURATION_SECONDS must be an integer, got: {duration_env}", file=sys.stderr)
            sys.exit(1)

    if duration <= 0:
        print(f"[ERROR] Duration must be a positive integer, got: {duration}", file=sys.stderr)
        sys.exit(1)

    # Validate required parameters
    if not license_key:
        print("[ERROR] License key is required. Provide via --license_key or set NR_LICENSE_KEY in .env", file=sys.stderr)
        sys.exit(1)

    if not logtype:
        print("[ERROR] Log type is required. Provide via --logtype or set NR_LOGTYPE in .env", file=sys.stderr)
        sys.exit(1)

    if environment not in LOG_API_ENDPOINTS:
        print(f"[ERROR] Invalid environment '{environment}'", file=sys.stderr)
        sys.exit(1)

    endpoint_url = LOG_API_ENDPOINTS[environment]

    # Determine log file path
    log_file = args.log_file
    if os.path.isabs(log_file):
        log_path = Path(log_file)
    else:
        log_path = Path(__file__).parent / log_file

    print(f"[INFO] Loading log template from: {log_file}", file=sys.stderr)
    print(f"[INFO] Log type: {logtype}", file=sys.stderr)
    print(f"[INFO] Environment: {environment}", file=sys.stderr)

    # Read the log file
    try:
        with open(log_path, 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"[ERROR] The file '{log_file}' was not found.", file=sys.stderr)
        print(f"[ERROR] Expected location: {log_path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Error reading file '{log_file}': {e}", file=sys.stderr)
        sys.exit(1)

    # Filter out comment lines (starting with //) to support JSONC format
    filtered_lines = [line for line in lines if not line.strip().startswith('//')]
    json_content = "".join(filtered_lines)

    if not json_content.strip():
        print(f"[ERROR] The log file '{log_file}' is empty or contains only comments.", file=sys.stderr)
        sys.exit(1)

    # Parse JSON
    try:
        payload = json.loads(json_content)
    except json.JSONDecodeError as e:
        print(f"[ERROR] Failed to parse '{log_file}' as JSON.", file=sys.stderr)
        print(f"Details: {e}", file=sys.stderr)
        sys.exit(1)

    # Validate payload structure
    if not isinstance(payload, list) or not payload:
        print(f"[ERROR] The log file '{log_file}' does not contain a valid, non-empty JSON list.", file=sys.stderr)
        sys.exit(1)

    print(f"[INFO] Found {len(payload)} log entries in template", file=sys.stderr)

    # Add logtype to all entries
    print(f"[INFO] Adding logtype '{logtype}' to all log entries", file=sys.stderr)
    updated_payload = add_logtype_to_entries(payload, logtype)

    # Stream logs
    total_logs = math.ceil(duration / interval)
    loops = math.ceil(total_logs / len(updated_payload))

    print(f"[INFO] Duration: {duration}s | Interval: {interval}s | Total logs: {total_logs} | Loops: {loops}", file=sys.stderr)

    log_sequence = (updated_payload * loops)[:total_logs]

    success_count = 0
    for i, log_entry in enumerate(log_sequence, 1):
        print(f"[INFO] Sending log {i}/{total_logs}...", file=sys.stderr)
        if send_single_log(license_key, log_entry, endpoint_url):
            success_count += 1
        if i < total_logs:
            time.sleep(interval)

    print(f"\n[SUCCESS] Streaming complete: {success_count}/{total_logs} logs sent successfully", file=sys.stderr)
    if success_count < total_logs:
        sys.exit(1)


if __name__ == "__main__":
    main()
