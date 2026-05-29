#!/usr/bin/env bash
# notify.sh - Notification hook for AI coding agents (Claude Code, Pi, Codex, Gemini)
#
# Input JSON fields (common): title, message, notification_type, session_id, cwd
# Input JSON fields (CC only): transcript_path, permission_mode
#
# Env vars used:
#   CLAUDE_CODE_VERSION                            - Claude Code detection (title fallback)
#   KITTY_LISTEN_ON, KITTY_PID, KITTY_WINDOW_ID  - kitty detection + navigation
#   TMUX, TMUX_PANE                                - tmux server + pane targeting
#   TERM_PROGRAM                                   - fallback terminal detection
#   CLAUDE_TERMINAL_BUNDLE_ID                      - manual override (all agents)

set -uo pipefail

shell_quote() {
	printf "'%s'" "$(printf '%s' "$1" | sed "s/'/'\\''/g")"
}

# --- Parse input ---
json_input="${1:-$(cat)}"

title=$(echo "$json_input" | jq -r '.title // ""')
message=$(echo "$json_input" | jq -r '.message // "Done"')
cwd=$(echo "$json_input" | jq -r '.cwd // ""')
notification_type=$(echo "$json_input" | jq -r '.notification_type // ""')
session_id=$(echo "$json_input" | jq -r '.session_id // ""')
permission_mode=$(echo "$json_input" | jq -r '.permission_mode // ""')

# --- Agent name: JSON title → env detection → generic fallback ---
if [[ -z "$title" ]]; then
	if [[ -n "${CLAUDE_CODE_VERSION:-}" ]]; then
		title="Claude Code"
	else
		title="Agent"
	fi
fi

# Slug for -group: lowercase, spaces → hyphens (e.g. "Claude Code" → "claude-code")
agent_slug=$(echo "$title" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')

# --- Title: prepend project name ---
if [[ -n "$cwd" ]]; then
	title="[$(basename "$cwd")] $title"
fi

# --- Git context: branch for subtitle ---
git_branch=""
if [[ -n "$cwd" && -d "$cwd/.git" ]]; then
	git_branch=$(git -C "$cwd" branch --show-current 2>/dev/null || true)
fi

# --- Emoji prefix + subtitle by type ---
subtitle=""
case "$notification_type" in
permission_prompt)
	title="🔐 $title"
	if [[ -n "$permission_mode" && "$permission_mode" != "default" ]]; then
		subtitle="Permission required · $permission_mode mode"
	else
		subtitle="Action required"
	fi
	;;
idle_prompt)
	title="💤 $title"
	subtitle="Waiting for input"
	[[ -n "$git_branch" ]] && subtitle="$subtitle · $git_branch"
	;;
esac

# --- Sound by type ---
sound_flag=()
case "$notification_type" in
permission_prompt) sound_flag=(-sound Funk) ;;
idle_prompt) sound_flag=(-sound default) ;;
esac

# --- Fallback if no terminal-notifier ---
if ! command -v terminal-notifier &>/dev/null; then
	echo "📢 $title: $message" >&2
	exit 0
fi

# --- Resolve tool paths (needed for -execute which runs in minimal-PATH /bin/sh) ---
kitty_bin=$(command -v kitty 2>/dev/null || echo "/opt/homebrew/bin/kitty")
tmux_bin=$(command -v tmux 2>/dev/null || echo "/opt/homebrew/bin/tmux")

# --- Discover tmux client metadata (works even when TERM_PROGRAM=tmux) ---
tmux_client_term=""
tmux_client_tty=""
tmux_session_name=""
tmux_window_index=""
if command -v tmux &>/dev/null && [[ -n "${TMUX_PANE:-}" ]]; then
	tmux_client_term=$(tmux display-message -p -t "$TMUX_PANE" '#{client_termname}' 2>/dev/null || true)
	tmux_client_tty=$(tmux display-message -p -t "$TMUX_PANE" '#{client_tty}' 2>/dev/null || true)
	tmux_session_name=$(tmux display-message -p -t "$TMUX_PANE" '#{session_name}' 2>/dev/null || true)
	tmux_window_index=$(tmux display-message -p -t "$TMUX_PANE" '#{window_index}' 2>/dev/null || true)
fi

# --- Skip idle notifications when the user is already viewing this pane ---
# Cheap tmux focus check: attached session + active window + active pane.
# Permission prompts are never suppressed — an action-required ping must fire.
if [[ "$notification_type" == "idle_prompt" && -n "${TMUX_PANE:-}" ]] && command -v tmux &>/dev/null; then
	pane_state=$(tmux display-message -p -t "$TMUX_PANE" '#{session_attached}:#{window_active}:#{pane_active}' 2>/dev/null || true)
	if [[ "$pane_state" =~ ^[1-9][0-9]*:1:1$ ]]; then
		exit 0
	fi
fi

# --- Recover the launching terminal when tmux masks TERM_PROGRAM as "tmux" ---
effective_term="${TERM_PROGRAM:-}"
if [[ -n "${TMUX_PANE:-}" && (-z "$effective_term" || "$effective_term" == "tmux") ]] && command -v tmux &>/dev/null; then
	recovered_term=$(tmux show-environment -g TERM_PROGRAM 2>/dev/null | sed -n 's/^TERM_PROGRAM=//p' || true)
	[[ -n "$recovered_term" ]] && effective_term="$recovered_term"
fi

# --- Detect parent terminal via kitty socket, tmux client term, or recovered TERM_PROGRAM ---
kitty_socket=""
if [[ -n "${KITTY_LISTEN_ON:-}" ]]; then
	kitty_socket="$KITTY_LISTEN_ON"
elif [[ -n "${KITTY_PID:-}" ]]; then
	kitty_socket="unix:/tmp/kitty-${KITTY_PID}"
fi
kitty_socket_path="${kitty_socket#unix:}"

if [[ -n "$kitty_socket" && -S "$kitty_socket_path" ]]; then
	BUNDLE_ID="net.kovidgoyal.kitty"
elif [[ "$tmux_client_term" == *kitty* ]]; then
	BUNDLE_ID="net.kovidgoyal.kitty"
elif [[ "$tmux_client_term" == *alacritty* ]]; then
	BUNDLE_ID="org.alacritty"
else
	case "$effective_term" in
	iTerm.app) BUNDLE_ID="com.googlecode.iterm2" ;;
	WezTerm) BUNDLE_ID="com.github.wez.wezterm" ;;
	Alacritty) BUNDLE_ID="org.alacritty" ;;
	kitty) BUNDLE_ID="net.kovidgoyal.kitty" ;;
	*) BUNDLE_ID="com.apple.Terminal" ;;
	esac
fi
BUNDLE_ID="${CLAUDE_TERMINAL_BUNDLE_ID:-$BUNDLE_ID}"

# --- Build click-to-navigate command (kitty + tmux) ---
execute_cmd=""
nav_parts=()
if [[ "$BUNDLE_ID" == "net.kovidgoyal.kitty" ]]; then
	nav_parts+=("/usr/bin/open -b net.kovidgoyal.kitty")
fi

if [[ -n "$kitty_socket" && -S "$kitty_socket_path" && -n "${KITTY_WINDOW_ID:-}" ]]; then
	nav_parts+=("$(shell_quote "$kitty_bin") @ --to $(shell_quote "$kitty_socket") focus-tab -m window_id:$(shell_quote "$KITTY_WINDOW_ID") 2>/dev/null")
fi

if command -v tmux &>/dev/null && [[ -n "${TMUX_PANE:-}" ]]; then
	tmux_prefix="$(shell_quote "$tmux_bin")"
	if [[ -n "${TMUX:-}" ]]; then
		tmux_prefix="TMUX=$(shell_quote "$TMUX") $tmux_prefix"
	fi
	if [[ -n "$tmux_client_tty" && -n "$tmux_session_name" ]]; then
		nav_parts+=("$tmux_prefix switch-client -c $(shell_quote "$tmux_client_tty") -t $(shell_quote "$tmux_session_name") 2>/dev/null")
	fi
	if [[ -n "$tmux_session_name" && -n "$tmux_window_index" ]]; then
		nav_parts+=("$tmux_prefix select-window -t $(shell_quote "${tmux_session_name}:${tmux_window_index}") 2>/dev/null")
	fi
	nav_parts+=("$tmux_prefix select-pane -t $(shell_quote "$TMUX_PANE") 2>/dev/null")
fi

if [[ ${#nav_parts[@]} -gt 0 ]]; then
	execute_cmd=$(printf '%s; ' "${nav_parts[@]}")
	execute_cmd="${execute_cmd%; }"
fi

# --- Send notification ---
tn_args=(
	-title "$title"
	-message "$message"
	-activate "$BUNDLE_ID"
)
[[ -n "$subtitle" ]] && tn_args+=(-subtitle "$subtitle")
[[ -n "$session_id" ]] && tn_args+=(-group "${agent_slug}-${session_id}")
[[ ${#sound_flag[@]} -gt 0 ]] && tn_args+=("${sound_flag[@]}")
[[ -n "$execute_cmd" ]] && tn_args+=(-execute "$execute_cmd")

terminal-notifier "${tn_args[@]}" 2>/dev/null ||
	echo "📢 $title: $message" >&2
