#!/bin/bash
set -e

echo "=== ETF Monitor Setup ==="

# 1. Create venv
if [ ! -d "venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv venv
fi

# 2. Activate venv
source venv/bin/activate

# 3. Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# 4. Create outputs directory
mkdir -p outputs
mkdir -p logs

# 5. Create .env if missing
if [ ! -f ".env" ]; then
  echo "Creating .env from template..."
  cp .env.example .env
  echo "⚠️  Please edit .env and add your SLACK_WEBHOOK_URL if desired"
fi

# 6. Activate repo-tracked git hooks (pre-commit secret guard)
if [ -d ".git" ] && [ -d ".githooks" ]; then
  git config core.hooksPath .githooks
  echo "Git hooks activated (.githooks/pre-commit)"
fi

# 7. Sanity checks
echo "Running sanity checks..."

if [ ! -d "inputs" ]; then
  echo "❌ ERROR: inputs/ folder not found!"
  exit 1
fi

if [ ! -f "inputs/FS_LU3098954871_de.pdf" ]; then
  echo "⚠️  WARNING: inputs/FS_LU3098954871_de.pdf not found"
fi

if [ ! -f "inputs/fwwdok_dxjMduzPQS.pdf" ]; then
  echo "⚠️  WARNING: inputs/fwwdok_dxjMduzPQS.pdf not found"
fi

if ! grep -q "SLACK_WEBHOOK_URL=https://" .env 2>/dev/null; then
  echo "⚠️  INFO: SLACK_WEBHOOK_URL not set in .env (Slack notifications disabled)"
fi

echo "✅ Setup complete! Run ./run.sh to start monitoring."
