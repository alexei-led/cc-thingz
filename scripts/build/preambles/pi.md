<!-- Pi platform guidance -->
<!-- Use installed Pi tool names exactly. Installed extensions may add toolsets such as Task*, Monitor*, and Loop*; use the visible tool names exactly and do not translate them to Claude syntax. -->
<!-- Prefer Task* over `todo` when task-tracking tools are available; `todo` is the cc-thingz fallback. Prefer MonitorCreate for long-running background commands and LoopCreate for scheduled or event-driven follow-up instead of Bash sleep/poll loops. -->
<!-- Use subagent for delegated work. Use wait to block on async subagent runs only when no independent work remains. -->
<!-- Use ctx7 or npx ctx7@latest through bash when Context7 documentation lookup is required. -->
