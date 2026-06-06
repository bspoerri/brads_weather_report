#!/bin/bash
# Manage the coastal report email distribution list.
#
#   ./recipients.sh add <email>      add an address to the distro list
#   ./recipients.sh remove <email>   remove an address
#   ./recipients.sh list             show the current list
#   ./recipients.sh <email>          shorthand for "add"
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FILE="$DIR/recipients.txt"
touch "$FILE"

is_email() { [[ "$1" =~ ^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$ ]]; }

list_recipients() {
    grep -vE '^\s*(#|$)' "$FILE" || true
}

add_recipient() {
    local email="$1"
    is_email "$email" || { echo "Not a valid email: $email" >&2; exit 1; }
    if list_recipients | grep -qixF "$email"; then
        echo "Already on the list: $email"
    else
        echo "$email" >> "$FILE"
        echo "Added: $email"
    fi
}

remove_recipient() {
    local email="$1"
    # Drop the line (case-insensitive exact match), keep comments/blanks.
    local tmp; tmp="$(mktemp)"
    grep -ivxF "$email" "$FILE" > "$tmp" || true
    mv "$tmp" "$FILE"
    echo "Removed (if present): $email"
}

cmd="${1:-list}"
case "$cmd" in
    list)   list_recipients ;;
    add)    add_recipient "${2:?usage: recipients.sh add <email>}" ;;
    remove) remove_recipient "${2:?usage: recipients.sh remove <email>}" ;;
    *)
        if is_email "$cmd"; then
            add_recipient "$cmd"
        else
            echo "Usage: recipients.sh add|remove|list [<email>]" >&2
            exit 1
        fi
        ;;
esac
