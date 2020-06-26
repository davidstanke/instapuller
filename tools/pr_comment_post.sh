#!/usr/bin/env bash
set -eEou pipefail

# parameters:
# $1: the repo (as org/repo) containing the PR
# $2: the number of the PR to post to
# $3: the text to post to the PR
# $4: the GitHub access token for an account with PR comment permissions

REPO=$1
PR_NUMBER=$2
COMMENT=$3
GITHUB_TOKEN=$4

PAYLOAD="{\"body\":\"$COMMENT\"}"
PR_URL="https://api.github.com/repos/$REPO/issues/$PR_NUMBER/comments"

echo "posting $PAYLOAD to $PR_URL..."

curl -s -H "Authorization: token $GITHUB_TOKEN" -X POST -d "$PAYLOAD" $PR_URL