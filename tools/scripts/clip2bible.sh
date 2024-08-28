#!/bin/bash

if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS (Darwin)
    clipcommand="pbpaste"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    if command -v xsel &> /dev/null; then
        clipcommand="xsel --primary --output"
    elif command -v xclip &> /dev/null; then
        clipcommand="xclip -selection primary -out"
    else
        echo "Error: Neither xsel nor xclip is installed." >&2
        exit 1
    fi
else
    echo "Error: Unsupported OS: $OSTYPE" >&2
    exit 1
fi

mybible-cli -r "$($clipcommand)" --gui
