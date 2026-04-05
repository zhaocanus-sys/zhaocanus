#!/bin/bash
set -e

echo "╔══════════════════════════════════════════╗"
echo "║       AquaMark — Project Setup           ║"
echo "║       Professional Watermark Studio      ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# Check if we're on macOS
if [[ "$(uname)" != "Darwin" ]]; then
    echo "⚠️  This script requires macOS with Xcode installed."
    echo "   Please run this on your Mac."
    exit 1
fi

# Check Xcode
if ! command -v xcodebuild &> /dev/null; then
    echo "❌ Xcode not found. Please install Xcode from the App Store."
    exit 1
fi

XCODE_VERSION=$(xcodebuild -version | head -1)
echo "✅ $XCODE_VERSION detected"

# Check for XcodeGen (optional)
if command -v xcodegen &> /dev/null; then
    echo "✅ XcodeGen found — generating project..."
    cd "$(dirname "$0")"
    xcodegen generate
    echo "✅ AquaMark.xcodeproj generated"
else
    echo "ℹ️  XcodeGen not found."
    echo "   Option A: Install with 'brew install xcodegen' then re-run"
    echo "   Option B: Create project manually in Xcode (see README.md)"
    echo ""
    echo "   To install XcodeGen:"
    echo "   brew install xcodegen"
    echo ""

    read -p "Install XcodeGen now? (y/N): " install_xcodegen
    if [[ "$install_xcodegen" =~ ^[Yy]$ ]]; then
        if command -v brew &> /dev/null; then
            brew install xcodegen
            cd "$(dirname "$0")"
            xcodegen generate
            echo "✅ AquaMark.xcodeproj generated"
        else
            echo "❌ Homebrew not found. Install from https://brew.sh"
            exit 1
        fi
    fi
fi

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║            Next Steps                    ║"
echo "╠══════════════════════════════════════════╣"
echo "║ 1. Open AquaMark.xcodeproj in Xcode     ║"
echo "║ 2. Select AquaMark target                ║"
echo "║ 3. Signing & Capabilities → set Team     ║"
echo "║ 4. Change Bundle ID if needed            ║"
echo "║ 5. Add your App Icon (1024x1024)         ║"
echo "║ 6. Select iPhone simulator → Cmd+R       ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# Open in Xcode if project exists
if [[ -d "AquaMark.xcodeproj" ]]; then
    read -p "Open in Xcode now? (Y/n): " open_xcode
    if [[ ! "$open_xcode" =~ ^[Nn]$ ]]; then
        open AquaMark.xcodeproj
    fi
fi

echo "🎉 Setup complete!"
