#!/usr/bin/env bash
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
GITHUB_USER="ukemedev"
REPO_NAME="everydayai-backend"
REMOTE="https://${GITHUB_USER}:${GITHUB_TOKEN}@github.com/${GITHUB_USER}/${REPO_NAME}.git"

cd "$REPO_DIR"

git init
git config user.email "agent@replit.com"
git config user.name "Replit Agent"
git add .
git commit -m "Update widget.js: set production Railway backend URL"
git branch -M main
git remote add origin "$REMOTE"
git push -u origin main --force

echo "Done! Pushed to https://github.com/${GITHUB_USER}/${REPO_NAME}"
