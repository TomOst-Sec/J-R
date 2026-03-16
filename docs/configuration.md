# Configuration Reference

## Config File Locations

Argus loads configuration from (in priority order):

1. CLI flags (highest priority)
2. Environment variables (`ARGUS_*`)
3. `./argus.toml` (current directory)
4. `~/.argus/argus.toml` (home directory)
5. Built-in defaults (lowest priority)

Create a config file: `argus config init`

## Full Reference

```toml
[general]
default_threshold = 0.45          # Minimum confidence to include results
max_concurrent_requests = 10      # Concurrent HTTP requests
output_format = "table"           # Default output: "table" or "json"
language = "en"                   # Language for text analysis

[stealth]
user_agent_rotation = true        # Rotate User-Agent headers
min_delay = 2.0                   # Minimum delay between requests (seconds)
max_delay = 5.0                   # Maximum delay between requests (seconds)
respect_robots_txt = false        # Whether to check robots.txt

[proxy]
url = ""                          # Proxy URL (e.g., "socks5://127.0.0.1:9050")
rotation_strategy = "round-robin" # "round-robin" or "random"
# auth.username = ""
# auth.password = ""

[verification]
minimum_threshold = 0.30          # Discard accounts below this score
photo_matching_enabled = true     # Enable photo hash comparison
face_recognition_enabled = false  # Enable face recognition (requires [face] extra)

[verification.signal_weights]
photo = 0.35
bio = 0.20
timezone = 0.15
username = 0.10
connections = 0.10
writing_style = 0.10

[llm]
provider = "none"                 # "none", "openai", "anthropic"
model = ""                        # Model name
api_key = ""                      # API key (use ${OPENAI_API_KEY} for env var)
base_url = ""                     # Custom API endpoint

[output]
default_format = "table"          # "table", "json", "markdown", "csv"
report_template = ""              # Custom report template path
include_raw_data = false          # Include raw API responses in output

# Per-platform configuration
[platforms.github]
enabled = true
rate_limit_per_minute = 30
# credentials.token = "${GITHUB_TOKEN}"

[platforms.reddit]
enabled = true
rate_limit_per_minute = 20

[platforms.hackernews]
enabled = true
rate_limit_per_minute = 30

[platforms.twitter]
enabled = true
rate_limit_per_minute = 15

[platforms.linkedin]
enabled = true
rate_limit_per_minute = 10
```

## Environment Variable Overrides

Any config value can be overridden via environment variable using the `ARGUS_` prefix:

```bash
ARGUS_GENERAL_THRESHOLD=0.6         # general.default_threshold
ARGUS_STEALTH_MIN_DELAY=1.0         # stealth.min_delay
ARGUS_VERIFICATION_MINIMUM_THRESHOLD=0.5
```

## Environment Variable Interpolation

Use `${VAR_NAME}` syntax in config values to reference environment variables:

```toml
[llm]
api_key = "${OPENAI_API_KEY}"

[platforms.github]
credentials.token = "${GITHUB_TOKEN}"
```

## Per-Platform Configuration

Disable specific platforms:

```toml
[platforms.linkedin]
enabled = false

[platforms.instagram]
enabled = false
```

Adjust rate limits:

```toml
[platforms.github]
rate_limit_per_minute = 60  # Higher if using authenticated token
```

## Proxy Setup

### HTTP Proxy

```toml
[proxy]
url = "http://proxy.example.com:8080"
```

### SOCKS5 Proxy (Tor)

```toml
[proxy]
url = "socks5://127.0.0.1:9050"
```

### Proxy Rotation

```toml
[proxy]
rotation_strategy = "round-robin"  # or "random"
```
