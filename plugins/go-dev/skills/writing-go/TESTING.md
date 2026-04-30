# Go Testing Reference

## Test Design

- Test behavior through public interfaces, not private helpers.
- Prefer integration-style tests when they give a stable signal.
- Mock only system boundaries: external APIs, time, randomness, filesystem, subprocesses.
- Do not mock internal collaborators just to assert call counts.
- Use red-green-refactor for risky changes: one failing test, minimal code, refactor only when green.
- Delete shallow tests once deeper interface tests cover the behavior.

## Frameworks

- **testify**: Assertions (`require`, `assert`)
- **mockery**: Interface mock generation with EXPECT pattern

```bash
go install github.com/vektra/mockery/v2@latest

mockery --all --keeptree
mockery --name=UserStore --dir=internal/service
```

## require vs assert

**require** stops test immediately on failure (`t.FailNow()`) — use for **prerequisites**.
**assert** logs failure but continues (`t.Fail()`) — use for **independent checks**.

```go
func TestUser(t *testing.T) {
    user, err := GetUser("123")

    // Prerequisites: must pass or test is meaningless
    require.NoError(t, err)
    require.NotNil(t, user)

    // Independent assertions: collect all failures
    assert.Equal(t, "123", user.ID)
    assert.Equal(t, "test@example.com", user.Email)
    assert.True(t, user.IsActive)
}
```

**When to use require:**

- Nil checks before accessing fields/methods
- Error checks when success is required to proceed
- Setup validation (db connection, file exists)
- Any precondition where failure makes remaining assertions meaningless

**When to use assert:**

- Multiple property checks on same object
- Validating several independent conditions
- When you want to see all failures in one run

**Never call require/assert from goroutines** — must be called from test goroutine.

## Table-Driven Tests

```go
func TestValidateEmail(t *testing.T) {
    tests := []struct {
        name    string
        email   string
        wantErr string
    }{
        {"valid", "user@example.com", ""},
        {"empty", "", "email required"},
        {"no_at", "invalid", "invalid format"},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            err := ValidateEmail(tt.email)
            if tt.wantErr == "" {
                require.NoError(t, err)
            } else {
                require.ErrorContains(t, err, tt.wantErr)
            }
        })
    }
}
```

## Mocking with Mockery

**Generate typesafe mocks with EXPECT pattern (mandatory):**

```bash
# For private interfaces (avoid import cycles) - generate in-package
mockery --name=userStore --inpackage --with-expecter

# For public interfaces - generate in mocks package
mockery --name=UserStore --with-expecter --dir=internal/service --output=internal/service/mocks

# Project-wide generation (use go:generate comments)
mockery --all --with-expecter --keeptree
```

**Interface annotation pattern:**

```go
// Private interface at consumer - use --inpackage to avoid import cycles
//go:generate mockery --name=userStore --inpackage --with-expecter
type userStore interface {
    Get(ctx context.Context, id string) (*User, error)
    Save(ctx context.Context, user *User) error
}
```

### mock.Anything vs Exact Values vs mock.MatchedBy

**CRITICAL: Choose argument matchers deliberately—overusing `mock.Anything` weakens tests.**

| Matcher              | Use When                                                       | Example                                             |
| -------------------- | -------------------------------------------------------------- | --------------------------------------------------- |
| **Exact value**      | Business-critical values from test fixtures                    | `"project.dataset.table"`, `"wu-123"`, `customerId` |
| **`mock.Anything`**  | Don't-care values: `context.Context`, loggers, tracing spans   | `mock.Anything` for ctx                             |
| **`mock.MatchedBy`** | Partial matching: SQL patterns, complex structs, generated IDs | `mock.MatchedBy(func(q string) bool { ... })`       |

**Examples:**

```go
func TestService_GetUser(t *testing.T) {
    store := NewMockuserStore(t)
    svc := NewService(store)

    expected := &User{ID: "123", Name: "Test"}

    // context.Context → mock.Anything (correct)
    // user ID "123" → exact value (business-critical!)
    store.EXPECT().
        Get(mock.Anything, "123").
        Return(expected, nil)

    user, err := svc.GetUser(context.Background(), "123")
    require.NoError(t, err)
    assert.Equal(t, expected, user)
}

func TestService_SetRunning(t *testing.T) {
    state := NewMockstateTracker(t)

    // Use EXACT values for business-critical parameters
    state.EXPECT().
        SetRunning(mock.Anything, "project.dataset.table", "20241201", "wu-123").
        Return(nil)

    // ...
}

func TestService_CreateUser(t *testing.T) {
    store := NewMockuserStore(t)
    svc := NewService(store)

    // mock.MatchedBy for partial struct validation
    store.EXPECT().
        Save(mock.Anything, mock.MatchedBy(func(u *User) bool {
            return u.Email == "test@example.com" && u.ID != ""
        })).
        Return(nil)

    err := svc.CreateUser(context.Background(), "test@example.com")
    require.NoError(t, err)
}

func TestService_ExecuteQuery(t *testing.T) {
    db := NewMockdatabase(t)

    // mock.MatchedBy for SQL pattern matching (normalize whitespace)
    db.EXPECT().
        Exec(mock.MatchedBy(func(q string) bool {
            normalized := strings.Join(strings.Fields(q), " ")
            return strings.HasPrefix(normalized, "INSERT INTO users")
        }), mock.Anything).
        Return(sqlResult, nil)

    // ...
}

func TestService_GetUser_NotFound(t *testing.T) {
    store := NewMockuserStore(t)
    svc := NewService(store)

    store.EXPECT().
        Get(mock.Anything, "unknown").
        Return(nil, ErrNotFound)

    _, err := svc.GetUser(context.Background(), "unknown")
    require.ErrorIs(t, err, ErrNotFound)
}
```

### Argument Matcher Decision Tree

1. **Is it context.Context, logger, or tracer?** → `mock.Anything`
2. **Is it a business value from test fixture?** → **Exact value** (table name, partition ID, customer ID, work unit ID)
3. **Is it a complex object with some important fields?** → `mock.MatchedBy` checking key fields
4. **Is it SQL or JSON with variable formatting?** → `mock.MatchedBy` with normalization
5. **Is it a generated ID/timestamp?** → `mock.Anything` or `mock.MatchedBy` with type check

### Helper Matchers for Common Patterns

```go
// Reusable matcher for SQL validation
func SQLContains(pattern string) interface{} {
    return mock.MatchedBy(func(q string) bool {
        normalized := strings.Join(strings.Fields(q), " ")
        return strings.Contains(normalized, pattern)
    })
}

// Reusable matcher for struct field validation
func UserWithEmail(email string) interface{} {
    return mock.MatchedBy(func(u *User) bool {
        return u.Email == email
    })
}

// Usage
db.EXPECT().Exec(SQLContains("INSERT INTO users"), mock.Anything).Return(result, nil)
store.EXPECT().Save(mock.Anything, UserWithEmail("test@example.com")).Return(nil)
```

## HTTP Handler Tests

```go
func TestHandler_CreateUser(t *testing.T) {
    svc := NewMockuserService(t)
    h := NewHandler(svc)

    svc.EXPECT().
        CreateUser(mock.Anything, mock.MatchedBy(func(req CreateUserRequest) bool {
            return req.Email == "test@example.com" && req.Name == "Test"
        })).
        Return(&User{ID: "123"}, nil)

    body := `{"name": "Test", "email": "test@example.com"}`
    req := httptest.NewRequest(http.MethodPost, "/users", strings.NewReader(body))
    req.Header.Set("Content-Type", "application/json")
    rec := httptest.NewRecorder()

    h.CreateUser(rec, req)

    assert.Equal(t, http.StatusCreated, rec.Code)
}
```

## Go 1.25: testing/synctest

Deterministic concurrent testing:

```go
func TestRetryWithBackoff(t *testing.T) {
    synctest.Run(func() {
        attempts := 0
        client := &RetryClient{
            Do: func() error {
                attempts++
                if attempts < 3 {
                    return errors.New("temporary")
                }
                return nil
            },
            MaxRetries: 3,
            Backoff:    time.Second,
        }

        err := client.Execute()
        require.NoError(t, err)
        assert.Equal(t, 3, attempts)
    })
}
```

## Integration Tests

```go
//go:build integration

func TestDatabase_Integration(t *testing.T) {
    if testing.Short() {
        t.Skip("skipping integration test")
    }

    db, cleanup := setupTestDB(t)
    defer cleanup()

    store := NewPostgresStore(db)
    user := &User{Name: "Test", Email: "test@example.com"}

    err := store.Save(context.Background(), user)
    require.NoError(t, err)

    got, err := store.Get(context.Background(), user.ID)
    require.NoError(t, err)
    assert.Equal(t, user.Name, got.Name)
}
```

## Benchmarks

```go
func BenchmarkProcess(b *testing.B) {
    data := generateTestData(1000)
    b.ResetTimer()
    for i := 0; i < b.N; i++ {
        Process(data)
    }
}

func BenchmarkProcess_Parallel(b *testing.B) {
    data := generateTestData(1000)
    b.RunParallel(func(pb *testing.PB) {
        for pb.Next() {
            Process(data)
        }
    })
}
```

## Test Fixtures

```go
func loadFixture(t *testing.T, name string) []byte {
    t.Helper()
    data, err := os.ReadFile(filepath.Join("testdata", name))
    require.NoError(t, err)
    return data
}
```

## Coverage

```bash
go test -coverprofile=coverage.out ./...
go tool cover -html=coverage.out
go tool cover -func=coverage.out | grep total
```

## Guidelines

**CRITICAL: Zero tolerance for test waste**

- **No pointless tests**: Don't test trivial behavior (getters, constructors setting fields)
- **No naive tests**: Don't just test obvious happy paths—include edge cases
- **No duplicate tests**: Same scenario tested multiple ways → keep one, delete others
- **Combine with table-driven**: 2+ tests for same function → single table-driven test (mandatory)
- **No comments in tests**: Tests should be self-explanatory unless logic is genuinely non-obvious

**Standard Guidelines**

- Test behavior, not implementation
- One logical assertion per test case
- Use `t.Parallel()` for independent tests
- Table-driven tests are **mandatory** for multiple cases (not optional)
- Descriptive `name` fields: `"valid_email"`, `"empty_returns_error"`, `"boundary_max_value"`
- Keep tables under 15-20 rows; split logically if larger
