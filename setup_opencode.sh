#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
#  TankOS + OpenCode Setup Script
# ═══════════════════════════════════════════════════════════════════════════
#
#  This script sets up OpenCode with the TankOS Agent Chat mechanism,
#  giving you access to 1,166+ robot tools via MCP protocol.
#
#  Usage:
#    chmod +x setup_opencode.sh
#    ./setup_opencode.sh
#
# ═══════════════════════════════════════════════════════════════════════════

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
echo "  ╔═══════════════════════════════════════════════════════════╗"
echo "  ║       TankOS + OpenCode Integration Setup                ║"
echo "  ║       1,166+ Robot Tools via MCP Protocol                ║"
echo "  ╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if we're in the right directory
if [ ! -f "tank_os/agent_framework/mcp_server.py" ]; then
    echo -e "${RED}ERROR: Please run this script from The-Tank-Project root directory${NC}"
    exit 1
fi

# ═══════════════════════════════════════════════════════════════════════════
#  Step 1: Install OpenCode
# ═══════════════════════════════════════════════════════════════════════════

echo -e "${BLUE}[1/4] Installing OpenCode...${NC}"

if command -v opencode &> /dev/null; then
    echo -e "${GREEN}  ✓ OpenCode already installed${NC}"
else
    echo "  Installing OpenCode..."
    curl -fsSL https://opencode.ai/install | bash
    echo -e "${GREEN}  ✓ OpenCode installed${NC}"
fi

# ═══════════════════════════════════════════════════════════════════════════
#  Step 2: Install Python Dependencies
# ═══════════════════════════════════════════════════════════════════════════

echo -e "${BLUE}[2/4] Installing Python dependencies...${NC}"

# Check for mcp package
if python3 -c "import mcp" 2>/dev/null; then
    echo -e "${GREEN}  ✓ mcp package already installed${NC}"
else
    echo "  Installing mcp package..."
    pip install mcp
    echo -e "${GREEN}  ✓ mcp package installed${NC}"
fi

# Check for fastmcp
if python3 -c "from mcp.server.fastmcp import FastMCP" 2>/dev/null; then
    echo -e "${GREEN}  ✓ FastMCP available${NC}"
else
    echo "  Installing FastMCP dependencies..."
    pip install "mcp[cli]"
    echo -e "${GREEN}  ✓ FastMCP installed${NC}"
fi

# ═══════════════════════════════════════════════════════════════════════════
#  Step 3: Configure OpenCode
# ═══════════════════════════════════════════════════════════════════════════

echo -e "${BLUE}[3/4] Configuring OpenCode...${NC}"

# Check if opencode.json exists
if [ -f "opencode.json" ]; then
    echo -e "${GREEN}  ✓ opencode.json already exists${NC}"
else
    echo "  Creating opencode.json..."
    cat > opencode.json << 'EOF'
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "tankos": {
      "type": "local",
      "command": ["python3", "tank_os/agent_framework/mcp_server.py"],
      "enabled": true,
      "cwd": ".",
      "environment": {
        "PYTHONPATH": "."
      },
      "timeout": 10000
    }
  },
  "tools": {
    "tankos_*": true
  }
}
EOF
    echo -e "${GREEN}  ✓ opencode.json created${NC}"
fi

# ═══════════════════════════════════════════════════════════════════════════
#  Step 4: Configure AI Providers
# ═══════════════════════════════════════════════════════════════════════════

echo -e "${BLUE}[4/5] Configuring AI providers...${NC}"

# Check .env.keys for API keys
if [ -f ".env.keys" ]; then
    echo -e "${GREEN}  ✓ Found .env.keys${NC}"
    
    # Count configured providers
    configured=0
    for key in GROQ_API_KEY OPENROUTER_API_KEY GEMINI_API_KEY MISTRAL_API_KEY CEREBRAS_API_KEY COHERE_API_KEY REPLICATE_API_KEY HUGGINGFACE_API_KEY CLOUDFLARE_WORKER_API_KEY OPENAI_API_KEY; do
        if grep -q "^${key}=.\+" .env.keys 2>/dev/null; then
            configured=$((configured + 1))
        fi
    done
    echo -e "  ${CYAN}${configured}/10 AI providers configured${NC}"
else
    echo -e "${YELLOW}  ⚠ No .env.keys found — providers will need manual configuration${NC}"
fi

# ═══════════════════════════════════════════════════════════════════════════
#  Step 5: Test the Integration
# ═══════════════════════════════════════════════════════════════════════════

echo -e "${BLUE}[5/5] Testing TankOS MCP Server...${NC}"

# Test if the MCP server can start
echo "  Testing MCP server initialization..."
if python3 -c "
import sys
sys.path.insert(0, '.')
from tank_os.agent_framework.mcp_server import _get_registry, AI_PROVIDERS
import os
registry = _get_registry()
tools = len(registry.list())
configured = sum(1 for p in AI_PROVIDERS.values() if os.environ.get(p['env_key']))
print(f'  Found {tools} tools, {configured}/10 AI providers')
" 2>/dev/null; then
    echo -e "${GREEN}  ✓ TankOS MCP server ready${NC}"
else
    echo -e "${YELLOW}  ⚠ MCP server test failed (may work when OpenCode starts it)${NC}"
fi

# ═══════════════════════════════════════════════════════════════════════════
#  Summary
# ═══════════════════════════════════════════════════════════════════════════

echo ""
echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                    Setup Complete!                       ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}To use OpenCode with TankOS:${NC}"
echo ""
echo -e "  ${YELLOW}cd The-Tank-Project${NC}"
echo -e "  ${YELLOW}opencode${NC}"
echo ""
echo -e "${GREEN}Available TankOS tools:${NC}"
echo -e "  • ${CYAN}tankos_list_tools${NC}     - List all 1,166+ tools"
echo -e "  • ${CYAN}tankos_invoke_tool${NC}    - Invoke any tool by name"
echo -e "  • ${CYAN}tankos_search_tools${NC}   - Search tools by keyword"
echo -e "  • ${CYAN}tankos_camera_vision${NC}  - Capture camera + YOLO detection"
echo -e "  • ${CYAN}tankos_system_status${NC}  - Get system status"
echo -e "  • ${CYAN}tankos_shell_command${NC}  - Execute shell commands"
echo ""
echo -e "${GREEN}Example prompts:${NC}"
echo -e "  • ${CYAN}\"What tools are available?\"${NC}"
echo -e "  • ${CYAN}\"Capture from the camera\"${NC}"
echo -e "  • ${CYAN}\"Navigate to the kitchen\"${NC}"
echo -e "  • ${CYAN}\"What's the system status?\"${NC}"
echo -e "  • ${CYAN}\"Send an SMS to Shashi\"${NC}"
echo ""
echo -e "${GREEN}Documentation:${NC}"
echo -e "  • OpenCode docs: https://opencode.ai/docs/"
echo -e "  • TankOS docs: ./docs/"
echo ""
