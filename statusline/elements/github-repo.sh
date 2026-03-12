#!/bin/bash
remote=$(git -C "${PWD}" remote get-url origin 2>/dev/null) || exit 0
[[ "$remote" == *github.com* ]] || exit 0
# Extract "user/repo" from SSH or HTTPS URL
repo=$(printf '%s' "$remote" | sed -E 's|.*github\.com[:/]||; s|\.git$||')
[ -n "$repo" ] && echo "$repo"
