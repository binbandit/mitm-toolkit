# Example Workflow: Capturing and Mocking a REST API

This guide walks through capturing traffic from a real API and creating a local mock server.

## Scenario: Creating a Local Copy of GitHub API

### Step 1: Start the Capture

```bash
# Start capturing GitHub API traffic
mitm-toolkit capture --filter-hosts api.github.com
```

### Step 2: Configure Your System

Configure your terminal to use the proxy:

```bash
# For this session only
export http_proxy=http://127.0.0.1:8080
export https_proxy=http://127.0.0.1:8080
```

### Step 3: Make API Calls

Use curl or your application to make requests:

```bash
# Get user information
curl https://api.github.com/users/octocat

# Get repositories
curl https://api.github.com/users/octocat/repos

# Get a specific repo
curl https://api.github.com/repos/octocat/Hello-World

# Search repositories
curl "https://api.github.com/search/repositories?q=language:python&sort=stars"
```

### Step 4: Stop Capture and Analyze

Press `Ctrl+C` to stop the capture, then analyze:

```bash
# View captured hosts
mitm-toolkit list-hosts

# Analyze GitHub API
mitm-toolkit analyze api.github.com
```

Output:
```
Analysis complete for api.github.com
Base URL: https://api.github.com
Total Requests: 4
Unique Endpoints: 4
Authentication: None

Endpoints
┏━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Method ┃ Path                        ┃ Parameters  ┃
┡━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ GET    │ /users/{id}                 │ id          │
│ GET    │ /users/{id}/repos           │ id          │
│ GET    │ /repos/{id}/{id}            │ id, id      │
│ GET    │ /search/repositories        │ -           │
└────────┴─────────────────────────────┴─────────────┘
```

### Step 5: Generate Mock Server

```bash
# Generate a FastAPI mock
mitm-toolkit generate-mock api.github.com --output ./github-mock
```

### Step 6: Run the Mock Server

```bash
cd github-mock

# Install dependencies
pip install -r requirements.txt

# Run the server
python mock_server.py
```

The mock server is now running on `http://localhost:8000`

### Step 7: Test the Mock

```bash
# Test against the mock server
curl http://localhost:8000/users/octocat
```

## Advanced Example: Mobile App Backend

### Capturing Mobile Traffic

1. Start the proxy with filters:
```bash
mitm-toolkit capture \
  --filter-hosts "api.mobile-app.com" \
  --ignore-patterns "*.png,*.jpg,*.mp4"
```

2. Configure your phone:
   - Connect to same WiFi as computer
   - Set HTTP/HTTPS proxy to computer's IP:8080
   - Install mitmproxy certificate from mitm.it

3. Use the app normally to capture traffic

4. Generate comprehensive mock:
```bash
# Analyze the traffic
mitm-toolkit analyze api.mobile-app.com

# Export as OpenAPI for documentation
mitm-toolkit export api.mobile-app.com --format openapi --output mobile-api.yaml

# Generate mock server
mitm-toolkit generate-mock api.mobile-app.com --output ./mobile-mock

# Export Postman collection for testing
mitm-toolkit export api.mobile-app.com --format postman --output mobile-api.json
```

## Example: Creating Test Data

### Export cURL Scripts

```bash
# Export all captured requests as curl commands
mitm-toolkit export api.example.com --format curl --output ./test-scripts

# Run the scripts against your mock
cd test-scripts
./api.example.com_curl_commands.sh
```

### Export HAR for Browser Testing

```bash
# Export as HAR
mitm-toolkit export api.example.com --format har --output captures.har

# Import into browser dev tools or testing frameworks
```

## Filtering Examples

### Capture Specific Endpoints

```bash
# Only capture user-related endpoints
mitm-toolkit capture --filter-patterns "/users/*,/profile/*"
```

### Capture Multiple Services

```bash
# Capture both API and auth service
mitm-toolkit capture --filter-hosts "api.app.com,auth.app.com"
```

### Ignore Noise

```bash
# Ignore analytics and tracking
mitm-toolkit capture \
  --ignore-hosts "google-analytics.com,segment.io,mixpanel.com" \
  --ignore-patterns "*/tracking,*/analytics"
```