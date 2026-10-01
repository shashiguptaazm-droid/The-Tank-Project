#!/usr/bin/env bash
set -euo pipefail

# Build and package MediGyaan.ipa for iOS devices (arm64)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${ROOT_DIR}"

echo "=== Step 1: Generating Xcode project with XcodeGen ==="
if ! command -v xcodegen &>/dev/null; then
    echo "XcodeGen not found. Installing via brew..."
    brew install xcodegen
fi
xcodegen generate

echo "=== Step 2: Archiving MediGyaan for iOS Device (Release arm64) ==="
rm -rf build/MediGyaan.xcarchive build/Payload build/MediGyaan.ipa
mkdir -p build

xcodebuild archive \
    -project MediGyaan.xcodeproj \
    -scheme MediGyaan \
    -destination "generic/platform=iOS" \
    -archivePath build/MediGyaan.xcarchive \
    -configuration Release \
    CODE_SIGNING_ALLOWED=NO \
    CODE_SIGNING_REQUIRED=NO \
    CODE_SIGN_IDENTITY="" \
    AD_HOC_CODE_SIGNING_ALLOWED=YES

echo "=== Step 3: Packaging Payload and creating MediGyaan.ipa ==="
mkdir -p build/Payload
cp -r build/MediGyaan.xcarchive/Products/Applications/MediGyaan.app build/Payload/

if command -v codesign &>/dev/null; then
    echo "Applying ad-hoc signature to app bundle..."
    codesign --force --deep --sign - build/Payload/MediGyaan.app 2>/dev/null || true
fi

cd build
zip -r -y MediGyaan.ipa Payload
ls -lh MediGyaan.ipa

echo "=== IPA Build Successful: $(pwd)/MediGyaan.ipa ==="
