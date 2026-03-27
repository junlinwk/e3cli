#!/usr/bin/env bash
#
# 建立 Homebrew tap 的快速設定腳本。
#
# 用法:
#   GITHUB_USER=your-username ./scripts/setup-homebrew-tap.sh
#
# 這個腳本會在本機產生一個 homebrew-e3cli 目錄，
# 你需要手動將它 push 到 GitHub 上的 homebrew-e3cli repo。
#
set -euo pipefail

GITHUB_USER="${GITHUB_USER:?請設定 GITHUB_USER 環境變數}"
TAP_DIR="homebrew-e3cli"

echo "==> 建立 Homebrew tap: ${GITHUB_USER}/e3cli"

mkdir -p "${TAP_DIR}/Formula"

# 複製 formula
if [ -f "Formula/e3cli.rb" ]; then
    cp Formula/e3cli.rb "${TAP_DIR}/Formula/e3cli.rb"
    # 替換 GitHub repo URL
    sed -i.bak "s|user/e3cli|${GITHUB_USER}/e3cli|g" "${TAP_DIR}/Formula/e3cli.rb"
    rm -f "${TAP_DIR}/Formula/e3cli.rb.bak"
fi

cat > "${TAP_DIR}/README.md" << 'TAPEOF'
# Homebrew Tap for e3cli

NYCU E3 Moodle automation CLI tool.

## Install

```bash
brew tap GITHUB_USER/e3cli
brew install e3cli
```

## Upgrade

```bash
brew update
brew upgrade e3cli
```
TAPEOF

sed -i.bak "s|GITHUB_USER|${GITHUB_USER}|g" "${TAP_DIR}/README.md"
rm -f "${TAP_DIR}/README.md.bak"

echo "==> 完成！tap 目錄已建立在: ${TAP_DIR}/"
echo ""
echo "下一步:"
echo "  1. 在 GitHub 建立 repo: ${GITHUB_USER}/homebrew-e3cli"
echo "  2. cd ${TAP_DIR} && git init && git add . && git commit -m 'Initial formula'"
echo "  3. git remote add origin git@github.com:${GITHUB_USER}/homebrew-e3cli.git"
echo "  4. git push -u origin main"
echo ""
echo "使用者安裝方式:"
echo "  brew tap ${GITHUB_USER}/e3cli && brew install e3cli"
