# MCP Server Setup Guide

## What Are MCP Servers?

MCP (Model Context Protocol) servers are **self-hosted processes** that provide structured tool access to external services. Unlike REST APIs where your code directly calls vendor endpoints, MCP servers:

1. Run on your local machine or infrastructure
2. Connect to vendor APIs internally
3. Expose standardized MCP tools to your RAVL loops

## Architecture Overview

```
┌─────────────────────────────────────┐
│  Your RAVL Loop                     │
│  (Generated Python code)            │
└─────────────────────────────────────┘
              ↓
   Uses MCPClientManager
              ↓
┌─────────────────────────────────────┐
│  MCP Server (YOUR MACHINE)          │
│  - Process you start locally        │
│  - Listening on localhost:3000      │
│  - Or runs as subprocess (stdio)    │
└─────────────────────────────────────┘
              ↓
   Calls vendor REST API
              ↓
┌─────────────────────────────────────┐
│  Vendor API (THEIR SERVERS)         │
│  - ClickUp: https://api.clickup.com │
│  - GitHub: https://api.github.com   │
│  - Slack: https://slack.com/api     │
└─────────────────────────────────────┘
```

## Key Concepts

### MCP vs REST APIs

| Aspect | REST API | MCP Server |
|--------|----------|------------|
| **Who hosts it?** | Vendor (ClickUp, GitHub) | You (on your machine) |
| **How to use?** | Direct HTTP calls | Connect to local server first |
| **Setup** | Just get API token | Download code, install deps, start server |
| **Standardization** | Varies by vendor | Standardized protocol |

### Transport Types

RAVL supports two ways to run MCP servers:

1. **SSE (Server-Sent Events)**
   - Server runs as a separate process
   - You start it manually: `npm start` or `python server.py`
   - Connects via HTTP URL: `http://localhost:3000`
   - Use for: Long-running services

2. **stdio (Standard Input/Output)**
   - Server runs as subprocess of your loop
   - Auto-started when loop runs
   - Uses command + args: `["npx", "-y", "@modelcontextprotocol/server-filesystem"]`
   - Use for: Self-contained tools

## Setup Steps

### Step 1: Find an MCP Server

**Option A: Official Servers**

The official MCP servers repository contains reference implementations:

```bash
git clone https://github.com/modelcontextprotocol/servers
cd servers
ls src/  # See available servers: filesystem, github, slack, etc.
```

**Option B: Community Servers**

Search GitHub for:
- `clickup-mcp-server` (example: taazkareem/clickup-mcp-server)
- `notion-mcp-server`
- `[service]-mcp-server`

**Option C: Write Your Own**

See: https://modelcontextprotocol.io/docs/building-servers

### Step 2: Install Dependencies

Navigate to the server directory and install:

```bash
cd servers/src/[server-name]

# For Node.js servers:
npm install

# For Python servers:
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables

Set up authentication for the vendor API the server will call:

```bash
# ClickUp example:
export CLICKUP_API_TOKEN="your_clickup_api_token"

# GitHub example:
export GITHUB_TOKEN="your_github_personal_access_token"

# Slack example:
export SLACK_BOT_TOKEN="your_slack_bot_token"
```

**Tip:** Add these to your `~/.bashrc` or `~/.zshrc` to persist across sessions.

### Step 4: Start the Server

**For SSE servers:**

```bash
npm start
# Server typically starts on http://localhost:3000
# Leave this terminal running!
```

**For stdio servers:**

No separate start needed - the server runs as a subprocess when your loop executes.

### Step 5: Register with RAVL

Add the server to RAVL's registry:

```bash
ravl --config
# Select: 4) MCP Servers
# Choose: Add new MCP server
# Enter server details (name, transport, URL/command, env var)
```

Or manually edit `.ravl/config/mcp_servers_registry.yml`:

```yaml
my_server:
  name: "My MCP Server"
  transport: "sse"
  url: "http://localhost:3000"
  env_var: "MY_API_TOKEN"
  documentation: "https://github.com/org/my-mcp-server"
  description: "What this server does"
```

### Step 6: Test the Connection

From the wizard:

```bash
ravl --config
# Select: 4) MCP Servers
# Choose: Test connections
```

Or write a test loop:

```markdown
# Act
Test connection to my_server MCP server and list available tools.
```

### Step 7: Use in Your Loops

Once registered and tested, your loops can use the MCP server:

```markdown
# Act
Use the ClickUp MCP server to fetch all tasks in "Strategic Initiatives" space.
```

The framework will generate code like:

```python
from ravl.common.integrations.mcp_client_manager import MCPClientManager
from ravl.common.integrations.mcp_registry import get_mcp_server_config

# Initialize MCP client
mcp_manager = MCPClientManager()
config = get_mcp_server_config('clickup')

# Connect and call tool
if mcp_manager.connect('clickup', config):
    result = mcp_manager.call_tool('clickup', 'list_tasks', {
        'space_name': 'Strategic Initiatives',
        'include_subtasks': True
    })
    mcp_manager.disconnect('clickup')
```

## Troubleshooting

### "Connection failed" Error

**Problem:** Loop can't connect to MCP server.

**Solutions:**
1. **Check if server is running:**
   ```bash
   curl http://localhost:3000
   # Should return a response, not "connection refused"
   ```

2. **Check port number:**
   - Server might be on different port (3001, 8080, etc.)
   - Update `url` in registry to match

3. **Check logs:**
   - Look at server terminal output for errors
   - Common: missing environment variables

### "Bearer token required" Error

**Problem:** Server needs authentication but token not provided.

**Solutions:**
1. **Set environment variable:**
   ```bash
   export CLICKUP_API_TOKEN="your_token"
   ```

2. **Add to .env file** (preferred):
   ```bash
   # In project root .env
   CLICKUP_API_TOKEN=your_token
   ```

3. **Restart server** after setting variables

### "Tool not found" Error

**Problem:** Trying to call a tool that doesn't exist on the server.

**Solutions:**
1. **List available tools:**
   ```bash
   ravl --config
   # Select: 4) MCP Servers
   # Choose: Test connections
   # Shows available tools for each server
   ```

2. **Check server documentation** for correct tool names

3. **Update server** - newer versions may have more tools

## Available Official Servers

As of 2024, the official MCP servers repository includes:

| Server | Transport | Description | Setup |
|--------|-----------|-------------|-------|
| **filesystem** | stdio | Local file operations | Easy (npx auto-downloads) |
| **github** | sse | GitHub API operations | Manual setup required |
| **slack** | sse | Slack workspace operations | Manual setup required |
| **google-drive** | sse | Google Drive file access | Manual setup required |

Check the latest: https://github.com/modelcontextprotocol/servers

## Common Misconceptions

### ❌ "I thought MCP servers were hosted by vendors"

**No.** MCP servers are self-hosted. Vendors provide REST APIs, not MCP servers. You run the MCP server yourself.

### ❌ "Isn't https://mcp.clickup.com an MCP endpoint?"

**No.** That URL is ClickUp's OAuth infrastructure (authentication), not an MCP server. The subdomain name is misleading.

### ❌ "Do I need to write my own MCP server?"

**Not necessarily.** Use official or community servers if they exist. Only write your own if no server exists for your target API.

### ❌ "Can't RAVL auto-download and start MCP servers?"

**Not for SSE servers.** For `stdio` transport with `npx` commands, yes (auto-downloading works). For `sse` servers that run separately, you must start them manually.

## Advanced Topics

### Running Multiple MCP Servers

You can run multiple servers simultaneously:

```bash
# Terminal 1: ClickUp server
cd servers/src/clickup && npm start  # Port 3000

# Terminal 2: GitHub server
cd servers/src/github && npm start   # Port 3001

# Terminal 3: Slack server
cd servers/src/slack && npm start    # Port 3002
```

Register each with unique URLs in the registry.

### Using Docker for MCP Servers

Package MCP servers in Docker for easier deployment:

```dockerfile
FROM node:20
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
ENV PORT=3000
EXPOSE 3000
CMD ["npm", "start"]
```

```bash
docker build -t my-mcp-server .
docker run -p 3000:3000 -e CLICKUP_API_TOKEN=token my-mcp-server
```

### Remote MCP Servers

For team collaboration, run MCP servers on a shared machine:

```yaml
clickup:
  transport: "sse"
  url: "http://team-server.local:3000"  # Not localhost!
  env_var: "CLICKUP_API_TOKEN"
```

**Security:** Use HTTPS with authentication for production deployments.

## Resources

- **MCP Documentation**: https://modelcontextprotocol.io/
- **Official Servers**: https://github.com/modelcontextprotocol/servers
- **Building Servers**: https://modelcontextprotocol.io/docs/building-servers
- **RAVL Framework**: `.ravl/CLAUDE.md` for architecture details
