#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
#  Configure OpenCode Providers from TankOS .env.keys
# ═══════════════════════════════════════════════════════════════════════════
#
#  This script reads API keys from .env.keys and configures OpenCode
#  to use all 10 AI providers.
#
#  Usage:
#    chmod +x setup_opencode_providers.sh
#    ./setup_opencode_providers.sh
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
echo "  ║       Configure OpenCode Providers                      ║"
echo "  ║       Using TankOS API Keys                             ║"
echo "  ╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if .env.keys exists
if [ ! -f ".env.keys" ]; then
    echo -e "${RED}ERROR: .env.keys not found${NC}"
    echo "Please run this script from The-Tank-Project directory"
    exit 1
fi

# Source the .env.keys file
source .env.keys

# OpenCode binary
OPENCODE="/home/shashi/.opencode/bin/opencode"

# Check if OpenCode is installed
if [ ! -f "$OPENCODE" ]; then
    echo -e "${RED}ERROR: OpenCode not installed${NC}"
    echo "Run: curl -fsSL https://opencode.ai/install | bash"
    exit 1
fi

echo -e "${BLUE}Configuring providers...${NC}"

# Function to configure a provider
configure_provider() {
    local provider=$1
    local env_key=$2
    local key_value=$3
    
    if [ -n "$key_value" ]; then
        echo -e "  ${GREEN}✓${NC} Configuring ${CYAN}${provider}${NC}..."
        # Set environment variable for OpenCode
        export "${env_key}=${key_value}"
    else
        echo -e "  ${YELLOW}⚠${NC} ${provider} - No API key found (${env_key})"
    fi
}

# Configure all 10 providers (using OpenCode's expected env var names)
configure_provider "Groq" "GROQ_API_KEY" "${GROQ_API_KEY}"
configure_provider "OpenRouter" "OPENROUTER_API_KEY" "${OPENROUTER_API_KEY}"
configure_provider "Google Gemini" "GEMINI_API_KEY" "${GEMINI_API_KEY}"
configure_provider "Mistral AI" "MISTRAL_API_KEY" "${MISTRAL_API_KEY}"
configure_provider "Cerebras" "CEREBRAS_API_KEY" "${CEREBRAS_API_KEY}"
configure_provider "Cohere" "COHERE_API_KEY" "${COHERE_API_KEY}"
configure_provider "Replicate" "REPLICATE_API_KEY" "${REPLICATE_API_KEY}"
configure_provider "Hugging Face" "HUGGINGFACE_HUB_TOKEN" "${HUGGINGFACE_API_KEY}"
configure_provider "Cloudflare Workers AI" "CLOUDFLARE_AI_GATEWAY_API_KEY" "${CLOUDFLARE_WORKER_API_KEY}"
configure_provider "OpenAI" "OPENAI_API_KEY" "${OPENAI_API_KEY}"
configure_provider "NVIDIA (Qwen3 Coder + Nemotron)" "NVIDIA_API_KEY" "${NVIDIA_API_KEY}"

echo ""
echo -e "${BLUE}Creating OpenCode environment file...${NC}"

# Create a wrapper script that loads the environment
cat > /home/shashi/.opencode/env.sh << 'ENVEOF'
#!/bin/bash
# Load TankOS API keys for OpenCode
if [ -f "/home/shashi/The-Tank-Project/.env.keys" ]; then
    set -a
    source /home/shashi/The-Tank-Project/.env.keys
    set +a
fi
ENVEOF

chmod +x /home/shashi/.opencode/env.sh

echo -e "${GREEN}✓ Environment file created${NC}"

echo ""
echo -e "${BLUE}Testing OpenCode with providers...${NC}"

# Test OpenCode with a simple prompt
cd /home/shashi/The-Tank-Project
source /home/shashi/.opencode/env.sh

echo -e "${YELLOW}Testing OpenCode...${NC}"
timeout 20 $OPENCODE run "Say hello" 2>&1 || true

echo ""
echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                    Setup Complete!                       ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}To use OpenCode with TankOS:${NC}"
echo ""
echo -e "  ${YELLOW}cd The-Tank-Project${NC}"
echo -e "  ${YELLOW}source /home/shashi/.opencode/env.sh${NC}"
echo -e "  ${YELLOW}opencode${NC}"
echo ""
echo -e "${GREEN}Or run TankOS Agent Chat:${NC}"
echo -e "  ${YELLOW}python3 -m tank_os.shell.terminal.agent_chat${NC}"
echo ""
