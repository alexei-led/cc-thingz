#!/usr/bin/env bash
# Java/Kotlin linting: file-scoped formatters first, Gradle/Maven fallbacks only when configured.

jvm_nearest_gradle_root() {
	local file="$1" dir build_candidate=""
	dir=$(dirname "$file")
	while [[ -n "$dir" && "$dir" != "/" ]]; do
		if [[ -f "$dir/settings.gradle" || -f "$dir/settings.gradle.kts" || -x "$dir/gradlew" ]]; then
			printf '%s\n' "$dir"
			return 0
		fi
		if [[ -z "$build_candidate" ]] && { [[ -f "$dir/build.gradle" ]] || [[ -f "$dir/build.gradle.kts" ]]; }; then
			build_candidate="$dir"
		fi
		[[ "$dir" == "." ]] && break
		dir=$(dirname "$dir")
	done
	if [[ -f settings.gradle || -f settings.gradle.kts || -x gradlew ]]; then
		printf '%s\n' "."
		return 0
	fi
	[[ -n "$build_candidate" ]] && printf '%s\n' "$build_candidate"
}

jvm_nearest_pom() {
	local file="$1" dir
	if [[ "$file" == pom.xml && -f "$file" ]]; then
		printf '%s\n' "$file"
		return 0
	fi
	dir=$(dirname "$file")
	while [[ -n "$dir" && "$dir" != "/" ]]; do
		if [[ -f "$dir/pom.xml" ]]; then
			printf '%s\n' "$dir/pom.xml"
			return 0
		fi
		[[ "$dir" == "." ]] && break
		dir=$(dirname "$dir")
	done
	[[ -f pom.xml ]] && printf '%s\n' "pom.xml"
}

jvm_gradle_mentions() {
	local root="$1" pattern="$2"
	grep -RqiE "$pattern" "$root"/build.gradle "$root"/build.gradle.kts "$root"/settings.gradle "$root"/settings.gradle.kts "$root"/gradle.properties 2>/dev/null
}

jvm_pom_mentions() {
	local pom="$1" pattern="$2"
	grep -qiE "$pattern" "$pom" 2>/dev/null
}

jvm_run_gradle_task() {
	local root="$1" task="$2" output
	mark_lint_ran
	if [[ -x "$root/gradlew" ]]; then
		if output=$(cd "$root" && ./gradlew "$task" --quiet 2>&1); then
			log_debug "Gradle $task passed in $root"
			return 0
		fi
	elif command_exists gradle; then
		if output=$(gradle -p "$root" "$task" --quiet 2>&1); then
			log_debug "Gradle $task passed in $root"
			return 0
		fi
	else
		return 1
	fi
	add_error "JVM Gradle ($task)" "$(compact_output "$output")"
	return 2
}

jvm_run_maven_task() {
	local pom="$1" goal="$2" output
	mark_lint_ran
	if [[ -x "$(dirname "$pom")/mvnw" ]]; then
		if output=$(cd "$(dirname "$pom")" && ./mvnw -q "$goal" 2>&1); then
			log_debug "Maven $goal passed for $pom"
			return 0
		fi
	elif command_exists mvn; then
		if output=$(mvn -q -f "$pom" "$goal" 2>&1); then
			log_debug "Maven $goal passed for $pom"
			return 0
		fi
	else
		return 1
	fi
	add_error "JVM Maven ($goal)" "$(compact_output "$output")"
	return 2
}

jvm_run_ktlint_format() {
	local files=("$@") output
	[[ "${#files[@]}" -gt 0 ]] || return 0
	command_exists ktlint || return 1
	mark_format_ran
	mark_lint_ran
	if output=$(ktlint --format "${files[@]}" 2>&1); then
		log_debug "ktlint passed"
		return 0
	fi
	add_error "Kotlin Linter/Formatter (ktlint)" "$(compact_output "$output")"
	return 2
}

jvm_run_detekt() {
	local files=("$@") input output
	[[ "${#files[@]}" -gt 0 ]] || return 0
	command_exists detekt || return 1
	input=$(
		IFS=,
		printf '%s' "${files[*]}"
	)
	mark_lint_ran
	if output=$(detekt --input "$input" 2>&1); then
		log_debug "detekt passed"
		return 0
	fi
	add_error "Kotlin Static Analysis (detekt)" "$(compact_output "$output")"
	return 2
}

jvm_has_build_file() {
	local file="$1"
	case "$file" in
	pom.xml | build.gradle | build.gradle.kts | settings.gradle | settings.gradle.kts | gradle.properties) return 0 ;;
	*) return 1 ;;
	esac
}

lint_java_kotlin() {
	log_debug "java/kotlin checks"

	local files=()
	while IFS= read -r file; do
		files+=("$file")
	done < <(get_changed_files ".java" ".kt" ".kts" "pom.xml" "build.gradle" "build.gradle.kts" "settings.gradle" "settings.gradle.kts" "gradle.properties")
	if [[ "${#files[@]}" -eq 0 ]]; then
		log_debug "No uncommitted Java/Kotlin files, skipping JVM checks"
		return 0
	fi

	local java_files=() kotlin_files=() build_files=() file
	for file in "${files[@]}"; do
		case "$file" in
		*.java) java_files+=("$file") ;;
		*.kt | *.kts) kotlin_files+=("$file") ;;
		esac
		if jvm_has_build_file "$(basename "$file")"; then
			build_files+=("$file")
		fi
	done

	local java_formatted=0 kotlin_formatted=0 kotlin_linted=0
	if [[ "${#java_files[@]}" -gt 0 ]] && command_exists google-java-format; then
		run_formatter_on_files --format-only "Java Formatter (google-java-format)" "google-java-format -i" "" "${java_files[@]}"
		java_formatted=1
	fi
	if [[ "${#kotlin_files[@]}" -gt 0 ]]; then
		if jvm_run_ktlint_format "${kotlin_files[@]}"; then
			kotlin_formatted=1
			kotlin_linted=1
		fi
		if jvm_run_detekt "${kotlin_files[@]}"; then
			kotlin_linted=1
		fi
	fi

	local roots=() poms=() tmp root pom
	tmp=$(mktemp 2>/dev/null || printf '/tmp/cc-thingz-jvm-lint.%s' "$$")
	for file in "${files[@]}"; do
		root=$(jvm_nearest_gradle_root "$file" || true)
		[[ -n "$root" ]] && printf 'g|%s\n' "$root"
		pom=$(jvm_nearest_pom "$file" || true)
		[[ -n "$pom" ]] && printf 'm|%s\n' "$pom"
	done | sort -u >"$tmp"
	while IFS='|' read -r kind value; do
		[[ -n "$value" ]] || continue
		case "$kind" in
		g) roots+=("$value") ;;
		m) poms+=("$value") ;;
		esac
	done <"$tmp"
	rm -f "$tmp"

	for root in "${roots[@]}"; do
		if { [[ "${#java_files[@]}" -gt 0 && "$java_formatted" -eq 0 ]] || [[ "${#kotlin_files[@]}" -gt 0 && "$kotlin_formatted" -eq 0 ]]; } && jvm_gradle_mentions "$root" 'spotless'; then
			mark_format_ran
			jvm_run_gradle_task "$root" spotlessApply || true
		fi
		if [[ "${#kotlin_files[@]}" -gt 0 && "$kotlin_linted" -eq 0 ]] && jvm_gradle_mentions "$root" 'detekt'; then
			jvm_run_gradle_task "$root" detekt || true
			kotlin_linted=1
		elif [[ "${#kotlin_files[@]}" -gt 0 && "$kotlin_linted" -eq 0 ]] && jvm_gradle_mentions "$root" 'ktlint'; then
			jvm_run_gradle_task "$root" ktlintCheck || true
			kotlin_linted=1
		fi
		if [[ "${#build_files[@]}" -gt 0 ]]; then
			jvm_run_gradle_task "$root" help || true
		fi
	done
	for pom in "${poms[@]}"; do
		if { [[ "${#java_files[@]}" -gt 0 && "$java_formatted" -eq 0 ]] || [[ "${#kotlin_files[@]}" -gt 0 && "$kotlin_formatted" -eq 0 ]]; } && jvm_pom_mentions "$pom" 'spotless'; then
			mark_format_ran
			jvm_run_maven_task "$pom" spotless:apply || true
		fi
		if [[ "${#build_files[@]}" -gt 0 ]]; then
			jvm_run_maven_task "$pom" validate || true
		fi
	done
}
