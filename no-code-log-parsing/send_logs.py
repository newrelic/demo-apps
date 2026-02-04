#!/usr/bin/env python3
"""
Send log messages from JSONC template files to the New Relic Log API.

This script:
- Loads environment variables from .env file or accepts them as arguments
- Loads a JSONC template file containing log entries
- Adds the logtype field to all log entries
- Sends the logs to the appropriate New Relic Logs API endpoint

Usage:
    python send_logs.py
    python send_logs.py --log_file custom_logs.jsonc
    python send_logs.py --license_key YOUR_KEY --environment us_prod
"""

import argparse
import requests  # type: ignore
import json
import sys
import os
from pathlib import Path
from dotenv import load_dotenv  # type: ignore


# New Relic Log API endpoints
LOG_API_ENDPOINTS = {
    "staging": "https://staging-log-api.newrelic.com/log/v1",
    "us_prod": "https://log-api.newrelic.com/log/v1",
    "eu_prod": "https://log-api.eu.newrelic.com/log/v1"
}


def send_log_batch(license_key, log_payload_list, endpoint_url):
    """
    Sends a batch of log entries to the New Relic Log API.

    Args:
        license_key (str): Your New Relic License Key.
        log_payload_list (list): A list of log entry dictionaries.
        endpoint_url (str): The Log API endpoint URL.

    Returns:
        bool: True if the request was successful (status code 202), False otherwise.
    """
    headers = {
        "Api-Key": license_key,
        "Content-Type": "application/json"
    }

    payload_json = json.dumps(log_payload_list)

    print(f"[INFO] Sending batch of {len(log_payload_list)} logs to {endpoint_url}", file=sys.stderr)
    print(f"[DEBUG] Payload size: {len(payload_json)} bytes", file=sys.stderr)

    try:
        response = requests.post(endpoint_url, headers=headers, data=payload_json, timeout=10)

        if response.status_code == 202:
            print(f"[SUCCESS] Successfully sent batch of {len(log_payload_list)} logs.", file=sys.stderr)
            return True
        else:
            print(f"[ERROR] Failed to send log batch.", file=sys.stderr)
            print(f"Status Code: {response.status_code}", file=sys.stderr)
            print(f"Response: {response.text}", file=sys.stderr)
            return False
    except requests.exceptions.Timeout:
        print(f"[ERROR] Request timed out while sending logs.", file=sys.stderr)
        return False
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] An error occurred while sending the request for log batch.", file=sys.stderr)
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
        epilog="Example: python send_logs.py --log_file logs.jsonc"
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

    args = parser.parse_args()

    # Get configuration from args or environment variables
    license_key = args.license_key or os.getenv('NR_LICENSE_KEY')
    environment = args.environment or os.getenv('NR_ENVIRONMENT', 'us_prod')
    logtype = args.logtype or os.getenv('NR_LOGTYPE')

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

    # Send logs
    print(f"[INFO] Sending logs to New Relic...", file=sys.stderr)
    if send_log_batch(license_key, updated_payload, endpoint_url):
        print("\n[SUCCESS] Log sending complete", file=sys.stderr)
        print(f"[SUCCESS] Sent {len(updated_payload)} log entries from '{log_file}'", file=sys.stderr)
        sys.exit(0)
    else:
        print("\n[ERROR] Log sending failed", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
