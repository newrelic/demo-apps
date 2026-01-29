# No-Code Log Parsing Demo

This demo showcases New Relic's log parsing capabilities using a Python script to send structured logs to the New Relic Logs API. The script demonstrates how to send custom log data to New Relic for analysis, pattern detection, and observability.

## Overview

This application allows you to send pre-configured log messages to New Relic. The sample logs include structured log entries from multiple services (checkout service, shipping service, and auth service) with different formats that demonstrate New Relic's log parsing capabilities.

You can run the script multiple times to simulate different scenarios or send the same logs repeatedly for testing and demonstration purposes.

## Prerequisites

- Python 3.7 or higher
- A New Relic account
- A New Relic License Key (Ingest - License)

## Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd demo-apps/no-code-log-parsing
```

### 2. Create a Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the sample environment file and update it with your New Relic credentials:

```bash
cp .env.sample .env
```

Edit `.env` and set the following values:

```bash
NR_LICENSE_KEY=your_license_key_here
NR_ENVIRONMENT=us_prod  # Options: us_prod, eu_prod, staging
NR_LOGTYPE=demo_app_logs  # Custom identifier for your logs
```

To get your License Key:
1. Log in to New Relic
2. Navigate to: https://one.newrelic.com/launcher/api-keys-ui.api-keys-launcher
3. Create or copy an existing "Ingest - License" key

## Usage

The script sends logs from a JSONC file to New Relic. By default, it uses `logs.jsonc`, but you can specify a different file.

### Basic Usage

Send logs using default settings:
```bash
python send_logs.py
```

Send logs from a specific file:
```bash
python send_logs.py --log_file logs.jsonc
```

### Advanced Usage

You can override environment variables using command-line arguments:

```bash
python send_logs.py --log_file logs.jsonc \
  --license_key YOUR_LICENSE_KEY \
  --environment us_prod \
  --logtype custom_log_type
```

### Command-Line Options

- `--log_file` (optional): Path to the JSONC log file to send (default: `logs.jsonc`)
  - Can be a relative path (relative to script directory) or absolute path
  - Example: `--log_file logs.jsonc` or `--log_file /path/to/custom_logs.jsonc`

- `--license_key` (optional): Override the license key from `.env`

- `--environment` (optional): Override the New Relic environment
  - `us_prod`: US Production (default)
  - `eu_prod`: EU Production
  - `staging`: Staging environment

- `--logtype` (optional): Override the log type identifier from `.env`

## Workflow

### Typical Demo Flow

1. **Setup**: Configure your `.env` file with your New Relic credentials

2. **Send Initial Logs**:
   ```bash
   python send_logs.py
   ```

3. **Explore in New Relic**:
   - Navigate to the Logs UI in New Relic
   - Filter by your `logtype` value
   - Analyze the logs from different services
   - Set up parsing rules or patterns
   - Create dashboards or alerts

4. **Send Logs Again** (optional):
   ```bash
   python send_logs.py
   ```
   - You can run the script multiple times to generate more log data
   - Useful for testing parsing rules, alerts, or demonstrating features

5. **Analyze Patterns**:
   - Review parsed log fields in the New Relic UI
   - Demonstrate how structured data can be extracted from log messages
   - Show how different log formats are handled
   - Create queries using the parsed fields

## Log File Format

The script uses JSONC (JSON with Comments) format for log templates. Each log entry should be a JSON object with your desired fields.

Example log entry:
```jsonc
{
  "message": "Application started successfully",
  "level": "INFO",
  "service.name": "my-service",
  "timestamp": 1640000000000,
  "custom_field": "custom_value"
}
```

Comments are supported:
```jsonc
[
  // This is a comment
  {
    "message": "Log entry here"
  }
]
```

### Customizing Log Content

To customize the logs sent to New Relic:

1. Edit `logs.jsonc` with your desired log entries
2. You can create multiple JSONC files for different scenarios and use `--log_file` to specify which one to send

The `logtype` field will be automatically added to all log entries based on your configuration.

### Sample Logs

The included `logs.jsonc` file contains 30 sample log entries from three different services:
- **Checkout Service** (10 entries): User checkout events with purchase details, amounts, and status
- **Shipping Service** (10 entries): Shipping tracking updates with carrier information and delivery status
- **Auth Service** (10 entries): Authentication events with login attempts, methods, and results

Each service uses a different log format with pipe-delimited key-value pairs to demonstrate various parsing patterns.

## Troubleshooting

### License Key Issues
- Ensure your license key is an "Ingest - License" key, not a User API key
- Verify the key is correctly set in `.env` or passed via `--license_key`

### Connection Issues
- Verify your `NR_ENVIRONMENT` matches your account region (US or EU)
- Check your network connection and firewall settings

### Log File Issues
- Ensure your log file contains a valid JSON array
- Check that comments use `//` syntax (JSONC format)
- Verify the file path is correct (relative to script directory or absolute path)
- Default file `logs.jsonc` should be in the same directory as `send_logs.py`

### Viewing Logs in New Relic
- Logs may take a few seconds to appear in the UI
- Use the query: `logtype:'your_logtype_value'` to filter your logs
- Check the time range in the UI matches when you sent the logs

## API Endpoints

The script uses the following New Relic Log API endpoints:

- **US Production**: https://log-api.newrelic.com/log/v1
- **EU Production**: https://log-api.eu.newrelic.com/log/v1
- **Staging**: https://staging-log-api.newrelic.com/log/v1

## License

This demo application is provided as-is for demonstration purposes.
