# React TypeScript Patterns

Use this reference for `.tsx`, hooks, component state, forms, and React-specific tests.

## Components and Props

- Use plain function components. Do not default to `React.FC`.
- Use interfaces for props when project style allows extension.
- Type `children` explicitly with `React.ReactNode`.
- Keep components focused on rendering and user interaction. Move parsing, I/O, and domain logic out.

```tsx
interface ButtonProps {
  label: string;
  onClick: () => void;
  disabled?: boolean;
}

function Button({ label, onClick, disabled = false }: ButtonProps) {
  return (
    <button type="button" onClick={onClick} disabled={disabled}>
      {label}
    </button>
  );
}
```

## State

Model exclusive UI states with discriminated unions, not parallel booleans and nullable fields.

```typescript
type AsyncState<T> =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; data: T }
  | { status: "error"; error: string };
```

Use reducers when transitions matter.

```typescript
type State = { count: number };
type Action = { type: "increment" } | { type: "reset"; value: number };

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "increment":
      return { count: state.count + 1 };
    case "reset":
      return { count: action.value };
    default: {
      const exhaustive: never = action;
      return exhaustive;
    }
  }
}
```

## Effects and Data Loading

- Prefer framework or project data-loading patterns when present.
- In effects, handle cleanup and cancellation.
- Validate loaded data in the fetcher, not inside rendering code.
- Avoid stale updates after unmount or dependency changes.

```tsx
function useUser(userId: string): AsyncState<User> {
  const [state, setState] = useState<AsyncState<User>>({ status: "idle" });

  useEffect(() => {
    const controller = new AbortController();

    setState({ status: "loading" });
    void fetchUser(userId, { signal: controller.signal })
      .then((result) => {
        if (controller.signal.aborted) return;
        setState(
          result.ok
            ? { status: "success", data: result.value }
            : { status: "error", error: result.error },
        );
      })
      .catch(() => {
        if (controller.signal.aborted) return;
        setState({ status: "error", error: "network" });
      });

    return () => controller.abort();
  }, [userId]);

  return state;
}
```

## Context

- Use context for cross-cutting dependencies or state, not as a default global store.
- Keep context values small and stable.
- Throw from custom hooks when a required provider is missing.

```tsx
interface AuthContextValue {
  user: User | null;
  login: (credentials: Credentials) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}
```

## Forms

- Use controlled inputs or native form APIs for simple forms.
- Use the project's existing form/schema library when form state, validation, or reuse is complex.
- Validate submitted values at the boundary before producing domain types.
- Keep server/API validation errors distinct from client validation errors.

## Performance

- Do not add `memo`, `useMemo`, or `useCallback` by default.
- Memoize only for measured expensive work, stable identity required by memoized children, or dependency churn that causes real re-renders.
- Keep dependency arrays complete; fix stale closures instead of suppressing lint rules.
- Use lazy loading at route or heavy-feature boundaries, not for tiny components.

## Tests

- Test user-visible behavior, not props or hook internals.
- Prefer Testing Library queries by role/name.
- Use `userEvent` for interactions.
- Cover affected loading, success, error, empty, and validation states.
