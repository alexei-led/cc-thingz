import type { HookDescriptor, ToolCategory } from "./schema.js";

const TOOL_CATEGORIES: Readonly<Record<string, ToolCategory>> = {
  bash: "command",
  shell: "command",
  read: "read",
  write: "write",
  edit: "edit",
  grep: "search",
  find: "search",
  ls: "search",
  glob: "search",
  search: "search",
  web: "web",
  fetch: "web",
  browse: "web",
  task: "task",
  subagent: "task",
};

export function categoryForTool(toolName: string): ToolCategory {
  const normalized = toolName.toLowerCase();
  if (normalized.startsWith("mcp") || normalized.includes("__mcp__")) return "mcp";
  return TOOL_CATEGORIES[normalized] ?? "other";
}

export function matchesTool(hook: HookDescriptor, toolName: string): boolean {
  return hook.matcher === undefined || hook.matcher.tools.includes(categoryForTool(toolName));
}
