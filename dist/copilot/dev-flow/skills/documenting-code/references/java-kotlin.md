# Java and Kotlin documentation

Use this only for JVM files. The host skill owns scope, editing, and verification.

## Public API docs

- Use Javadoc/KDoc for public APIs, extension points, framework hooks, CLI commands, and non-obvious contracts.
- Document nullability, ownership, threading/coroutine expectations, cancellation, blocking behavior, exceptions, and side effects.
- Keep examples compilable or clearly marked as pseudo-code.
- Do not restate obvious getters, records, data classes, or implementation steps.

## Comments

- Explain why a transaction boundary, dispatcher, virtual thread, lock, retry, timeout, or framework annotation is required.
- Explain Java/Kotlin interop constraints when annotations or `@Jvm*` declarations exist for callers.
- Delete comments that paraphrase syntax or stale framework behavior.

## Build docs

- Update README/operator docs when JDK, Gradle/Maven, Kotlin, wrapper, toolchain, formatter, or test commands change.
- Prefer wrapper commands in docs: `./gradlew` or `./mvnw`.
- Include focused test commands when they are the intended fast feedback loop.
