# MITM Toolkit - Complete Guide

A powerful, AI-enhanced toolkit for capturing, analyzing, and mocking HTTP/HTTPS traffic. Build local replicas of any service with intelligent traffic analysis, automatic test generation, and real-time monitoring.

> ⚠️ **IMPORTANT**: This tool intercepts network traffic. Use it legally and ethically only on systems you own or have explicit permission to test. See [SECURITY.md](SECURITY.md) for security considerations and legal guidelines.

## 🌐 Live Dashboard

**Try the dashboard without installing Node.js!**  
Visit: **https://binbandit.github.io/mitm-toolkit/**

The hosted dashboard can connect to your locally running MITM Toolkit instance:
1. Start local capture: `mitm-toolkit capture`
2. Run dashboard server: `mitm-toolkit dashboard`
3. Visit the GitHub Pages dashboard
4. It automatically connects to `localhost:8000`

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Core Concepts](#core-concepts)
- [Detailed Usage Guide](#detailed-usage-guide)
  - [Traffic Capture](#traffic-capture)
  - [Analysis](#analysis)
  - [Mock Generation](#mock-generation)
  - [Test Generation](#test-generation)
  - [AI-Powered Features](#ai-powered-features)
  - [Advanced Features](#advanced-features)
- [Command Reference](#command-reference)
- [Configuration](#configuration)
- [Plugins](#plugins)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)

## Features

### Core Capabilities
- **Smart Traffic Capture**: Filter by hosts, URL patterns, ignore lists
- **Real-time Dashboard**: WebSocket-powered live request viewer
- **Mock Server Generation**: Auto-generate FastAPI/Express.js servers
- **Test Generation**: Create pytest, Playwright, and k6 tests automatically
- **Multi-format Export**: HAR, OpenAPI, Postman, cURL scripts

### Advanced Features
- **AI Analysis**: Local LLM integration with Ollama for intelligent insights
- **GraphQL Support**: Auto-introspection and schema generation
- **Session Management**: Track user flows and multi-step operations
- **WebSocket Analysis**: Protocol detection (Socket.IO, GraphQL-WS, JSON-RPC)
- **Plugin System**: Extensible architecture for custom processors
- **Request Replay**: Modify and replay captured requests
- **Security Scanning**: Automatic vulnerability detection

## Installation

### Prerequisites

- Python 3.10+
- mitmproxy certificate (installed automatically)
- Ollama (optional, for AI features)

### Install with uv (Recommended)

```bash
# Install uv if you haven't
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone repository
git clone https://github.com/binbandit/mitm-toolkit.git
cd mitm-toolkit

# Install with uv
uv pip install -e .
```

### Install with pip

```bash
# Clone repository
git clone https://github.com/binbandit/mitm-toolkit.git
cd mitm-toolkit

# Install with pip
pip install -e .
```

### Install Ollama for AI Features (Optional)

```bash
# macOS/Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama
ollama serve

# Pull recommended models
ollama pull llama2          # General purpose
ollama pull codellama       # Better for API analysis
ollama pull mistral         # Fast and efficient

# Thinking/Reasoning models (more advanced analysis)
ollama pull deepseek-r1:7b  # DeepSeek reasoning model
ollama pull qwq:32b         # Alibaba's QwQ reasoning model
ollama pull gptoss          # Community reasoning model
```

## Quick Start

### 1. Initial Setup

```bash
# View setup instructions
mitm-toolkit setup

# This will show you how to:
# - Install mitmproxy certificates
# - Configure system proxy
# - Set up browser/device
```

### 2. Start Capturing

```bash
# Basic capture (all traffic)
mitm-toolkit capture

# Capture specific host
mitm-toolkit capture --filter-hosts api.example.com

# Multiple hosts
mitm-toolkit capture --filter-hosts "api.example.com,auth.example.com"

# With ignore list
mitm-toolkit capture --filter-hosts api.example.com --ignore-hosts "analytics.google.com"
```

### 3. View Real-time Dashboard

```bash
# In a new terminal
mitm-toolkit dashboard

# Open http://localhost:8000 in browser
```

### 4. Analyze Captured Traffic

```bash
# List captured hosts
mitm-toolkit list-hosts

# Analyze a specific host
mitm-toolkit analyze api.example.com

# View captured requests
mitm-toolkit show-requests api.example.com
```

### 5. Generate Mock Server

```bash
# Generate FastAPI mock
mitm-toolkit generate-mock api.example.com --output ./mock-server

# Generate Express.js mock
mitm-toolkit generate-mock api.example.com --type express --output ./mock-server

# Run the mock
cd mock-server
python mock_server.py  # or: npm install && npm start
```

## Core Concepts

### How It Works

1. **Proxy Setup**: Routes your HTTP/HTTPS traffic through mitmproxy
2. **Smart Capture**: Filters and stores requests/responses in SQLite
3. **Pattern Analysis**: Identifies API endpoints, parameters, and schemas
4. **Mock Generation**: Creates working mock servers from patterns
5. **AI Enhancement**: Uses local LLMs for deeper insights

### Traffic Flow

```
Your App/Browser → MITM Proxy → Target API
                       ↓
                  SQLite Storage
                       ↓
                Analysis & Generation
```

## Detailed Usage Guide

### Traffic Capture

#### Basic Capture

```bash
# Start proxy on default port 8080
mitm-toolkit capture

# Custom port
mitm-toolkit capture --port 9090
```

#### Filtering

```bash
# Filter by host
mitm-toolkit capture --filter-hosts api.example.com

# Multiple hosts
mitm-toolkit capture --filter-hosts "api.example.com,api2.example.com"

# Filter by URL patterns (regex)
mitm-toolkit capture --filter-patterns "/api/v1/*,/graphql"

# Ignore hosts
mitm-toolkit capture --ignore-hosts "google-analytics.com,segment.io"

# Ignore patterns
mitm-toolkit capture --ignore-patterns "*.js,*.css,*.png"

# Combined filters
mitm-toolkit capture \
  --filter-hosts api.example.com \
  --filter-patterns "/api/*" \
  --ignore-patterns "*.js,*.css"
```

#### System Proxy Configuration

**macOS:**
```bash
# Set proxy
networksetup -setwebproxy Wi-Fi 127.0.0.1 8080
networksetup -setsecurewebproxy Wi-Fi 127.0.0.1 8080

# Unset proxy
networksetup -setwebproxystate Wi-Fi off
networksetup -setsecurewebproxystate Wi-Fi off
```

**Linux:**
```bash
# Set proxy
export http_proxy=http://127.0.0.1:8080
export https_proxy=http://127.0.0.1:8080

# Unset proxy
unset http_proxy https_proxy
```

**Application-specific:**
```bash
# curl
curl -x http://127.0.0.1:8080 https://api.example.com

# Python requests
HTTP_PROXY=http://127.0.0.1:8080 python script.py

# Node.js
HTTP_PROXY=http://127.0.0.1:8080 node app.js
```

### Analysis

#### Basic Analysis

```bash
# Analyze captured traffic
mitm-toolkit analyze api.example.com

# Output includes:
# - Endpoint patterns
# - Common headers
# - Authentication type
# - Request/response schemas
```

#### GraphQL Analysis

```bash
# Analyze GraphQL traffic
mitm-toolkit analyze-graphql graphql.api.com

# Detects:
# - Queries, mutations, subscriptions
# - Operation patterns
# - Schema structure
# - Common variables
```

#### Session Analysis

```bash
# Analyze user sessions and flows
mitm-toolkit analyze-sessions ecommerce.com

# Identifies:
# - User sessions
# - Multi-step flows (login, checkout, etc.)
# - Session durations
# - Common user paths
```

#### AI-Powered Analysis

```bash
# Analyze with AI (requires Ollama)
mitm-toolkit ai-analyze api.example.com

# Use specific model
mitm-toolkit ai-analyze api.example.com --model codellama

# Use thinking/reasoning models for deeper analysis
mitm-toolkit ai-analyze api.example.com --model deepseek-r1:7b
mitm-toolkit ai-analyze api.example.com --model qwq:32b
mitm-toolkit ai-analyze api.example.com --model gptoss

# Provides:
# - Security insights
# - Performance bottlenecks
# - API design recommendations
# - Anomaly detection
# - Step-by-step reasoning (with thinking models)
```

### Mock Generation

#### Generate Mock Server

```bash
# FastAPI (Python)
mitm-toolkit generate-mock api.example.com --output ./mock

# Express.js (Node.js)
mitm-toolkit generate-mock api.example.com --type express --output ./mock
```

#### Mock Server Structure

```
mock/
├── mock_server.py      # FastAPI server
├── requirements.txt    # Python dependencies
├── Dockerfile         # Docker configuration
└── README.md          # Instructions
```

#### Running the Mock

```bash
# Python/FastAPI
cd mock
pip install -r requirements.txt
python mock_server.py

# Docker
docker build -t api-mock .
docker run -p 8000:8000 api-mock

# Node.js/Express
cd mock
npm install
npm start
```

#### Customizing Mocks

Edit `mock_server.py` to customize responses:

```python
@app.get("/api/users/{user_id}")
async def get_user(user_id: str):
    # Add custom logic
    if user_id == "123":
        return {"id": "123", "name": "Test User"}
    return {"error": "User not found"}
```

### Test Generation

#### Generate Tests

```bash
# Pytest tests
mitm-toolkit generate-tests api.example.com --type pytest --output tests.py

# Playwright E2E tests
mitm-toolkit generate-tests api.example.com --type playwright --output e2e.spec.js

# k6 load tests
mitm-toolkit generate-tests api.example.com --type k6 --output loadtest.js
```

#### Running Tests

```bash
# Pytest
pytest tests.py -v

# Playwright
npx playwright test e2e.spec.js

# k6
k6 run loadtest.js
```

### AI-Powered Features

#### Setup Ollama

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Start server
ollama serve

# Pull models
ollama pull llama2
ollama pull codellama
```

#### AI Analysis Commands

```bash
# API pattern analysis
mitm-toolkit ai-analyze api.example.com

# Generate test scenarios
mitm-toolkit ai-analyze api.example.com --model codellama

# Security audit with standard model
mitm-toolkit ai-analyze api.example.com --model llama2

# Deep reasoning analysis with thinking models
mitm-toolkit ai-analyze api.example.com --model deepseek-r1:7b
mitm-toolkit ai-analyze api.example.com --model qwq:32b
mitm-toolkit ai-analyze api.example.com --model gptoss
```

#### AI Insights Include

- **Security**: Vulnerabilities, misconfigurations, exposed data
- **Performance**: Slow endpoints, N+1 queries, caching opportunities
- **Architecture**: RESTful compliance, API design patterns
- **Reliability**: Error handling, retry logic, timeouts
- **Testing**: Edge cases, test scenarios, fuzzing targets
- **Reasoning** (with thinking models): Step-by-step analysis showing thought process

#### Thinking Models

Thinking/reasoning models provide deeper analysis by showing their thought process:

- **deepseek-r1**: DeepSeek's reasoning model - excellent for complex API analysis
- **qwq**: Alibaba's QwQ model - strong at mathematical and logical reasoning
- **gptoss**: Community model - good general reasoning capabilities

These models take longer to respond but provide more thorough analysis with visible reasoning steps.

### Advanced Features

#### Request Replay

```bash
# Replay a specific request
mitm-toolkit replay <request-id>

# Replay to different host
mitm-toolkit replay <request-id> --target-host localhost:8000

# Modify request
mitm-toolkit replay <request-id> --modify '{"headers": {"Authorization": "Bearer NEW_TOKEN"}}'
```

#### Export Formats

```bash
# HAR (HTTP Archive)
mitm-toolkit export api.example.com --format har --output capture.har

# OpenAPI/Swagger
mitm-toolkit export api.example.com --format openapi --output api.yaml

# Postman Collection
mitm-toolkit export api.example.com --format postman --output collection.json

# cURL Scripts
mitm-toolkit export api.example.com --format curl --output ./curl-scripts
```

#### Real-time Dashboard

```bash
# Start dashboard
mitm-toolkit dashboard --port 8000

# Features:
# - Live request monitoring
# - Filter and search
# - Performance metrics
# - Request/response details
```

## Command Reference

### Capture Commands

| Command | Description | Example |
|---------|-------------|---------|
| `capture` | Start capturing traffic | `mitm-toolkit capture` |
| `--port` | Proxy port | `--port 9090` |
| `--filter-hosts` | Capture specific hosts | `--filter-hosts api.example.com` |
| `--filter-patterns` | URL patterns to capture | `--filter-patterns "/api/*"` |
| `--ignore-hosts` | Hosts to ignore | `--ignore-hosts analytics.google.com` |
| `--ignore-patterns` | Patterns to ignore | `--ignore-patterns "*.css"` |

### Analysis Commands

| Command | Description | Example |
|---------|-------------|---------|
| `list-hosts` | List captured hosts | `mitm-toolkit list-hosts` |
| `analyze` | Analyze host traffic | `mitm-toolkit analyze api.example.com` |
| `analyze-graphql` | GraphQL analysis | `mitm-toolkit analyze-graphql api.example.com` |
| `analyze-sessions` | Session analysis | `mitm-toolkit analyze-sessions api.example.com` |
| `ai-analyze` | AI-powered analysis | `mitm-toolkit ai-analyze api.example.com` |
| `show-requests` | View captured requests | `mitm-toolkit show-requests api.example.com` |

### Generation Commands

| Command | Description | Example |
|---------|-------------|---------|
| `generate-mock` | Generate mock server | `mitm-toolkit generate-mock api.example.com` |
| `generate-tests` | Generate tests | `mitm-toolkit generate-tests api.example.com` |
| `export` | Export captured data | `mitm-toolkit export api.example.com --format har` |

### Utility Commands

| Command | Description | Example |
|---------|-------------|---------|
| `dashboard` | Launch web dashboard | `mitm-toolkit dashboard` |
| `replay` | Replay requests | `mitm-toolkit replay <id>` |
| `list-plugins` | List available plugins | `mitm-toolkit list-plugins` |
| `setup` | Setup instructions | `mitm-toolkit setup` |

## Configuration

### Storage Location

```bash
# Default: ./captures.db
export MITM_TOOLKIT_DB=/path/to/custom.db
```

### Plugin Directory

```bash
# Default: ~/.mitm-toolkit/plugins/
export MITM_TOOLKIT_PLUGINS=/path/to/plugins
```

## Plugins

### Built-in Plugins

1. **SensitiveDataMasker**: Masks passwords, tokens, API keys
2. **RequestDeduplicator**: Filters duplicate requests
3. **PerformanceAnalyzer**: Analyzes response times
4. **SecurityScanner**: Detects security issues
5. **JSONBeautifier**: Formats JSON responses
6. **HeaderNormalizer**: Normalizes headers

### Creating Custom Plugins

1. Create plugin file:

```python
# ~/.mitm-toolkit/plugins/my_plugin.py
from mitm_toolkit.plugins import RequestProcessorPlugin

class MyPlugin(RequestProcessorPlugin):
    name = "MyPlugin"
    version = "1.0.0"
    description = "My custom plugin"

    def initialize(self):
        # Setup code
        pass

    def process_request(self, request):
        # Modify request
        print(f"Processing: {request.url}")
        return request

    def process_response(self, response):
        # Modify response
        return response
```

2. Configure plugin:

```yaml
# ~/.mitm-toolkit/plugins/plugins.yaml
plugins:
  - name: MyPlugin
    file: my_plugin.py
    enabled: true
    config:
      setting1: value1
      setting2: value2
```

### Plugin Types

- **RequestProcessorPlugin**: Process requests/responses
- **TransformerPlugin**: Transform data during export
- **AnalyzerPlugin**: Custom analysis logic

## Examples

### Example 1: Capturing Mobile App Traffic

```bash
# 1. Start capture for mobile API
mitm-toolkit capture --filter-hosts api.mobileapp.com

# 2. Configure phone WiFi proxy to computer_ip:8080

# 3. Install mitmproxy certificate on phone (visit mitm.it)

# 4. Use the app normally

# 5. Analyze captured traffic
mitm-toolkit analyze api.mobileapp.com

# 6. Generate mock for local development
mitm-toolkit generate-mock api.mobileapp.com --output ./mobile-mock

# 7. Generate tests
mitm-toolkit generate-tests api.mobileapp.com --type pytest --output test_mobile.py
```

### Example 2: GraphQL API Analysis

```bash
# 1. Capture GraphQL traffic
mitm-toolkit capture --filter-hosts graphql.example.com

# 2. Make various GraphQL queries

# 3. Analyze GraphQL operations
mitm-toolkit analyze-graphql graphql.example.com

# 4. Export schema
mitm-toolkit export graphql.example.com --format openapi --output schema.yaml

# 5. AI analysis for optimization
mitm-toolkit ai-analyze graphql.example.com --model codellama
```

### Example 3: E-commerce Site Analysis

```bash
# 1. Capture with session tracking
mitm-toolkit capture --filter-hosts shop.example.com

# 2. Browse site: login → browse → add to cart → checkout

# 3. Analyze user flows
mitm-toolkit analyze-sessions shop.example.com

# 4. Generate E2E tests for the flow
mitm-toolkit generate-tests shop.example.com --type playwright --output checkout.spec.js

# 5. Generate load test
mitm-toolkit generate-tests shop.example.com --type k6 --output load.js
```

### Example 4: API Security Audit

```bash
# 1. Capture API traffic
mitm-toolkit capture --filter-hosts api.production.com

# 2. Make various API calls

# 3. Run AI security analysis
mitm-toolkit ai-analyze api.production.com --model llama2

# 4. Export for security team
mitm-toolkit export api.production.com --format har --output audit.har
```

### Example 5: Creating Local Development Environment

```bash
# 1. Capture production API
mitm-toolkit capture --filter-hosts api.production.com

# 2. Use application normally to capture endpoints

# 3. Analyze and generate mock
mitm-toolkit analyze api.production.com
mitm-toolkit generate-mock api.production.com --output ./local-api

# 4. Start mock server
cd local-api
docker build -t local-api .
docker run -p 8000:8000 local-api

# 5. Point application to localhost:8000
```

## Troubleshooting

### Certificate Issues

**Problem**: HTTPS connections failing

**Solution**:
```bash
# Install certificate
mitm-toolkit capture
# Visit http://mitm.it and install certificate

# macOS: Add to System Keychain and trust
# Linux: Copy to /usr/local/share/ca-certificates/
# Windows: Install to Trusted Root Certificate Store
```

### No Requests Captured

**Problem**: Traffic not being captured

**Check**:
1. Proxy settings correct: `127.0.0.1:8080`
2. Certificate installed and trusted
3. Filter patterns not too restrictive
4. Application using system proxy

```bash
# Test proxy
curl -x http://127.0.0.1:8080 https://example.com

# Check capture logs
mitm-toolkit capture --verbose
```

### Ollama Not Working

**Problem**: AI features not available

**Solution**:
```bash
# Check Ollama status
curl http://localhost:11434/api/tags

# Start Ollama
ollama serve

# Pull model
ollama pull llama2

# Test
mitm-toolkit ai-analyze api.example.com --model llama2
```

### Database Issues

**Problem**: Storage errors

**Solution**:
```bash
# Check database
sqlite3 captures.db "SELECT COUNT(*) FROM requests;"

# Reset database
rm captures.db
mitm-toolkit capture  # Will create new database
```

### Performance Issues

**Problem**: Slow capture or analysis

**Solutions**:
```bash
# Limit capture scope
mitm-toolkit capture --filter-hosts "specific.api.com" --ignore-patterns "*.js,*.css,*.png"

# Use sampling for analysis
mitm-toolkit analyze api.example.com --sample 1000

# Clean old data
sqlite3 captures.db "DELETE FROM requests WHERE timestamp < date('now', '-7 days');"
```

## Best Practices

1. **Filter Aggressively**: Only capture what you need
2. **Use Ignore Patterns**: Skip static assets (JS, CSS, images)
3. **Regular Cleanup**: Clear old captures periodically
4. **Secure Storage**: Captured data may contain sensitive information
5. **Test Locally First**: Verify mocks before using in development
6. **Version Control**: Store generated mocks and tests in git
7. **Document Patterns**: Keep notes on detected flows and patterns

## Contributing

Contributions welcome! Please submit pull requests or open issues on GitHub.

## License

MIT License - see LICENSE file for details

## Support

- **Documentation**: This README
- **Issues**: [GitHub Issues](https://github.com/binbandit/mitm-toolkit/issues)
- **Examples**: See `/examples` directory

## Acknowledgments

Built on top of these excellent projects:
- [mitmproxy](https://mitmproxy.org/) - HTTP/HTTPS proxy
- [FastAPI](https://fastapi.tiangolo.com/) - Mock server framework
- [Ollama](https://ollama.ai/) - Local LLM runtime
- [Rich](https://rich.readthedocs.io/) - Terminal formatting
