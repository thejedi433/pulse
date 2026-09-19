# Pulse

**Pulse** is a minimal service uptime monitor designed for always-on devices like the Raspberry Pi. It periodically checks your configured endpoints, tracks their availability history, and alerts you when services go down or come back up.

## Features

- ✓ Monitor multiple URLs/endpoints
- ✓ Configurable check intervals and timeouts
- ✓ SQLite database for persistent history
- ✓ State-change alerting with clear up/down transitions
- ✓ CLI interface for manual checks and daemon mode
- ✓ **Telegram notifications** on status changes
- ✓ Minimal dependencies
- ✓ Type hints and comprehensive tests

## Installation

### From Source

```bash
cd /path/to/pulse
python3 -m venv venv
source venv/activate
pip install -e ".[dev]"
```

### System-wide (optional)

```bash
pip install .
```

## Quick Start

### Add endpoints to monitor

```bash
pulse add https://api.example.com/health
pulse add https://status.example.com -i 120 -t 10
```

Options:
- `-i, --interval`: Check interval in seconds (default: 60)
- `-t, --timeout`: Request timeout in seconds (default: 10)

### Check a single URL immediately

```bash
pulse check https://api.example.com/health
```

Output:
```
✓ https://api.example.com/health: UP (status=200, time=45ms)
```

### Start the monitoring daemon

```bash
pulse monitor
```

This checks all configured endpoints at their specified intervals. Press `Ctrl+C` to stop.

### View current status

```bash
pulse status
```

Output:
```
URL                                                Status     Uptime     Last Check
------------------------------------------------------------------------------------------
https://api.example.com/health                     UP         99.5%      2026-08-15T10:30:00
https://status.example.com                         DOWN       87.2%      2026-08-15T10:29:55
```

For a single endpoint:
```bash
pulse status -u https://api.example.com/health
```

### View check history

```bash
pulse history
pulse history -u https://api.example.com/health
pulse history -n 50  # Show last 50 records
```

### Remove an endpoint

```bash
pulse remove https://old-service.example.com
```

## Configuration

Configuration is stored at `~/.config/pulse/config.toml`:

```toml
check_interval = 60
default_timeout = 10

[[endpoints]]
url = "https://api.example.com/health"
interval = 60
timeout = 10
expected_status = 200

[[endpoints]]
url = "https://status.example.com"
interval = 120
timeout = 15
expected_status = 200
```

## Telegram Notifications

Pulse can send Telegram alerts when endpoints change state. To enable:

1. Create a Telegram bot via [@BotFather](https://t.me/BotFather)
2. Get your chat ID (message [@userinfobot](https://t.me/userinfobot))
3. Set environment variables:

```bash
export PULSE_TELEGRAM_TOKEN="your-bot-token"
export PULSE_TELEGRAM_CHAT_ID="your-chat-id"
```

Once configured, Pulse will send Telegram messages whenever an endpoint changes from UP to DOWN or vice versa. Alerts are also logged to `~/.local/share/pulse/alerts.log` regardless of Telegram configuration.

## Storage

- **Database**: `~/.local/share/pulse/pulse.db` (SQLite)
- **Alerts log**: `~/.local/share/pulse/alerts.log`

The database stores:
- Timestamp
- URL
- HTTP status code
- Response time
- Up/down status
- Error messages

## Alerts

Pulse logs alerts to `~/.local/share/pulse/alerts.log` when:
- An endpoint is first checked (INITIAL status)
- An endpoint changes from UP to DOWN or vice versa (STATE CHANGE)

Example alert output:
```
[2026-08-15T10:30:00] INITIAL: https://api.example.com/health is UP
[2026-08-15T10:35:00] STATE CHANGE: https://api.example.com/health went from UP to DOWN
[2026-08-15T10:40:00] STATE CHANGE: https://api.example.com/health went from DOWN to UP
```

If Telegram notifications are configured, state changes (not initial checks) are also sent via Telegram.

## HTTP Checks

Pulse considers an endpoint **UP** when:
- The request completes within the timeout
- The HTTP status code is in the 2xx range (200-299)

Error handling:
- Network timeouts → marked as DOWN
- DNS failures → marked as DOWN
- Connection refused → marked as DOWN
- Non-2xx status codes → marked as DOWN

## Running Tests

```bash
cd /path/to/pulse
python3 -m pytest
```

Run with coverage:
```bash
python3 -m pytest --cov=pulse --cov-report=term-missing
```

## Docker (Optional)

Pulse can run in a Docker container, which is useful for deployment consistency and works on ARM64 (Raspberry Pi).

### Build

```bash
docker build -t pulse-monitor .
```

### Run

```bash
# Create config directory and initial config
mkdir -p ~/pulse/config
cat > ~/pulse/config/config.toml << 'EOF'
check_interval = 60
default_timeout = 10

[[endpoints]]
url = "https://api.example.com/health"
interval = 60
timeout = 10
EOF

# Run container with optional Telegram config
docker run -d \
  --name pulse \
  -v ~/pulse/config:/config \
  -v ~/pulse/data:/data \
  -e HOME=/home/pulse \
  -e PULSE_TELEGRAM_TOKEN="your-token" \
  -e PULSE_TELEGRAM_CHAT_ID="your-chat-id" \
  --restart unless-stopped \
  pulse-monitor
```

Volume mounts:
- `/config` → Configuration directory (config.toml)
- `/data` → Data directory (pulse.db, alerts.log)

### Logs

```bash
docker logs -f pulse
```

### Manual commands inside container

```bash
# Check a URL
docker exec pulse pulse check https://api.example.com/health

# View status
docker exec pulse pulse status

# Add endpoint
docker exec pulse pulse add https://new-service.example.com
```

### Docker Compose (optional)

```yaml
# docker-compose.yml
version: "3.8"
services:
  pulse:
    build: .
    container_name: pulse
    volumes:
      - ./config:/config
      - ./data:/data
    environment:
      - HOME=/home/pulse
      - PULSE_TELEGRAM_TOKEN=${PULSE_TELEGRAM_TOKEN}
      - PULSE_TELEGRAM_CHAT_ID=${PULSE_TELEGRAM_CHAT_ID}
    restart: unless-stopped
```

Run with `docker compose up -d`.

## Systemd Service (Optional)

For automatic startup on Raspberry Pi:

```ini
# /etc/systemd/system/pulse.service
[Unit]
Description=Pulse Uptime Monitor
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
ExecStart=/home/pi/projects/pulse/venv/bin/pulse monitor
Environment=PULSE_TELEGRAM_TOKEN=your-token
Environment=PULSE_TELEGRAM_CHAT_ID=your-chat-id
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable pulse
sudo systemctl start pulse
sudo systemctl status pulse
```

## CLI Reference

```
pulse <command> [options]

Commands:
  check <url>        Check a single URL immediately
  monitor            Start monitoring all configured endpoints (daemon)
  status             Show current status of endpoints
  history            Show check history
  add <url>          Add an endpoint to monitor
  remove <url>       Remove an endpoint from monitoring

Options:
  --version          Show version and exit
  --help             Show help message
```

## License

MIT License - see LICENSE file for details.

## Author

@thejedi433
