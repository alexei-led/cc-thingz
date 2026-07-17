/**
 * Instruction-file discovery for the InstructionsLoaded synthetic hook event.
 *
 * Walks parent directories from cwd up to the filesystem root looking for
 * AGENTS.md, CLAUDE.md, and `.claude/rules/*.md`. Also pulls the user-level
 * AGENTS.md from the Pi agent dir.
 */

import { existsSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";

import { agentDir } from "./config.js";

export interface InstructionFile {
	file_path: string;
	memory_type: string;
	load_reason: string;
}

export function discoverInstructionFiles(cwd: string): InstructionFile[] {
	const files: InstructionFile[] = [];
	const seen = new Set<string>();
	const add = (filePath: string, memoryType: string, loadReason = "session_start") => {
		if (!existsSync(filePath)) return;
		if (seen.has(filePath)) return;
		seen.add(filePath);
		files.push({ file_path: filePath, memory_type: memoryType, load_reason: loadReason });
	};

	add(join(agentDir(), "AGENTS.md"), "User");

	let current = cwd;
	while (true) {
		add(join(current, "AGENTS.md"), "Project");
		add(join(current, "CLAUDE.md"), "Project");
		const rulesDir = join(current, ".claude", "rules");
		if (existsSync(rulesDir)) {
			try {
				for (const file of readdirSync(rulesDir)) {
					if (file.endsWith(".md")) {
						add(join(rulesDir, file), "Project", "path_glob_match");
					}
				}
			} catch {
				// ignore unreadable rules dir
			}
		}
		const parent = dirname(current);
		if (parent === current) break;
		current = parent;
	}

	return files;
}
