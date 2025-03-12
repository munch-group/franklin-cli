#!/usr/bin/env bash
echo -n -e "\033]0;MBGexercises\007"
echo -e "\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n"

launch-exercise

osascript -e 'tell application "Terminal" to close (every window whose name contains "MBGexercises")' &