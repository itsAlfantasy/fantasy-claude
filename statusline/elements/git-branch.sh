#!/bin/bash
branch=$(git -C "${PWD}" rev-parse --abbrev-ref HEAD 2>/dev/null)
[ -n "$branch" ] && echo " $branch"
