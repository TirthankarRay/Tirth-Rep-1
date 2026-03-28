#!/usr/bin/env bash
set -euo pipefail

echo "=== Minutes Deployment Setup ==="

# Detect platform
OS="$(uname -s)"
ARCH="$(uname -m)"

install_minutes_cli() {
    if command -v minutes &>/dev/null; then
        echo "minutes CLI already installed: $(minutes --version)"
        return 0
    fi

    case "$OS" in
        Darwin)
            echo "Installing via Homebrew..."
            brew tap silverstein/tap
            brew install minutes
            ;;
        Linux)
            if command -v cargo &>/dev/null; then
                echo "Installing via Cargo..."
                cargo install minutes-cli
            else
                echo "Rust not found. Installing rustup first..."
                curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
                source "$HOME/.cargo/env"
                cargo install minutes-cli
            fi
            ;;
        *)
            echo "Unsupported OS: $OS" >&2
            exit 1
            ;;
    esac
}

install_mcp_server() {
    if command -v npx &>/dev/null; then
        echo "MCP server available via: npx minutes-mcp"
    else
        echo "Node.js not found. Install Node.js 20+ for MCP server support." >&2
    fi
}

setup_whisper_model() {
    local model="${1:-tiny}"
    echo "Downloading Whisper model: $model"
    minutes setup --model "$model"
}

create_directories() {
    mkdir -p "$HOME/.minutes/inbox"
    mkdir -p "$HOME/meetings"
    echo "Created inbox at ~/.minutes/inbox"
    echo "Created meetings dir at ~/meetings"
}

configure_minutes() {
    local config_dir="$HOME/.config/minutes"
    mkdir -p "$config_dir"

    if [ ! -f "$config_dir/config.toml" ]; then
        cp "$(dirname "$0")/config.toml" "$config_dir/config.toml"
        # Adjust paths for local install
        sed -i.bak 's|/data/inbox|~/.minutes/inbox|g' "$config_dir/config.toml"
        sed -i.bak 's|/data/meetings|~/meetings|g' "$config_dir/config.toml"
        rm -f "$config_dir/config.toml.bak"
        echo "Configuration written to $config_dir/config.toml"
    else
        echo "Configuration already exists at $config_dir/config.toml"
    fi
}

main() {
    install_minutes_cli
    install_mcp_server
    create_directories
    configure_minutes
    setup_whisper_model "${1:-tiny}"

    echo ""
    echo "=== Setup Complete ==="
    echo "Run 'minutes health' to verify installation"
    echo "Run 'minutes demo' to test with a sample recording"
    echo "Run 'minutes watch' to start the file watcher"
}

main "$@"
