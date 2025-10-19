# Contributing Guide

**Last Updated**: 2025-10-05

## Quick Start

1. Fork and clone
2. Run `npm run setup` (see [DEVELOPMENT.md](DEVELOPMENT.md))
3. Create branch: `git checkout -b feature/your-feature`
4. Make changes following standards below
5. Run tests: `npm run test && npm run lint && npm run type-check`
6. Submit PR with clear description

## Code Quality Standards

### Core Rules

| Rule | Requirement |
|------|-------------|
| Function length | 10-20 lines max |
| Responsibility | Single responsibility only |
| Naming | Self-explanatory without comments |
| Nesting | Maximum 2 levels |
| Returns | Use early returns (guard clauses) |

### Documentation

- Document **why**, not **what**
- Use meaningful names over comments
- Update docs when changing public APIs

### Backend (Python/FastAPI)

**Required**:
- Type hints on all functions
- Pydantic models for API schemas
- Comprehensive tests for endpoints
- Proper error handling

```python
# Good
def create_user_session(user_id: str, expires_in: int = 3600) -> Session:
    if not user_id:
        raise ValueError("User ID is required")

    session_id = generate_session_id()
    expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

    return Session(id=session_id, user_id=user_id, expires_at=expires_at)

# Bad
def handle_user(data, config, mode=None):
    # 50 lines of mixed logic...
```

### Frontend (TypeScript/React)

**Required**:
- Strict TypeScript (no `any`)
- Import types from `@specscribe/shared-types`
- Component composition over large components
- Custom hooks for reusable logic

```typescript
// Good
interface UserSessionProps {
  userId: string;
  onSessionEnd: () => void;
}

function UserSession({ userId, onSessionEnd }: UserSessionProps) {
  if (!userId) return <div>Please log in</div>;
  return <div className="user-session"><SessionTimer onExpire={onSessionEnd} /></div>;
}

// Bad
function UserThing({ data, callbacks }: any) {
  // 30 lines handling sessions, UI, API calls...
}
```

### Type Safety

```typescript
import type { paths, components } from '@specscribe/shared-types';

type SessionResponse = components['schemas']['SessionResponse'];
type CreateSessionRequest = components['schemas']['CreateSessionRequest'];

const createSession = async (data: CreateSessionRequest): Promise<SessionResponse> => {
  // Implementation
};
```

## Pull Request Process

### Before Submitting

- [ ] Tests pass: `npm run test`
- [ ] Types check: `npm run type-check`
- [ ] Lint clean: `npm run lint`
- [ ] Types generated (if backend changed): `npm run generate:types`
- [ ] Manual testing completed

### PR Format

**Title**: `feat: add user session management` or `fix: resolve auth token expiry`

**Prefixes**: `feat`, `fix`, `docs`, `refactor`, `test`

**Description Template**:
```markdown
## Summary
Brief description and motivation.

## Changes
- Change 1
- Change 2

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Manual testing completed

## Type Safety
- [ ] Generated types updated (if backend changes)
- [ ] No TypeScript errors

## Breaking Changes
List any breaking changes and migration steps.
```

### Review Checklist

- Code quality (functions <20 lines, clear names, single responsibility)
- Test coverage
- Type safety
- Documentation updates
- No performance regressions

## Testing

<details>
<summary>Backend Testing</summary>

```python
# Unit test
def test_session_creation():
    session = create_session("user123")
    assert session.is_valid()

# API endpoint test
def test_create_session_endpoint(client):
    response = client.post("/sessions", json={"user_id": "test"})
    assert response.status_code == 201

# Run tests
cd apps/backend
poetry run pytest
poetry run pytest --cov=specscribe  # With coverage
```

</details>

<details>
<summary>Frontend Testing (Future)</summary>

```typescript
// Component test
test('UserSession renders correctly', () => {
  render(<UserSession userId="test" onSessionEnd={mockFn} />);
  expect(screen.getByText('Session active')).toBeInTheDocument();
});

// Run tests
cd apps/frontend
npm test
```

</details>

## Git Workflow

**Branch naming**: `feature/user-auth`, `fix/session-bug`, `docs/api-update`

**Commit format**:
```
feat: add OAuth integration with Google

- Implement OAuth callback handling
- Add JWT token generation
- Update user authentication flow

Closes #123
```

**Merge requirements**:
- All checks pass
- Code review approval
- Up-to-date with master
- Clean commit history

## Architecture Guidelines

<details>
<summary>API Design</summary>

- RESTful endpoints with clear resource names
- Consistent response formats (Pydantic models)
- Proper HTTP status codes
- Authentication on protected routes
- Request validation with meaningful errors

</details>

<details>
<summary>Database Design</summary>

- Normalized structure with proper relationships
- Database constraints for data integrity
- Migrations for schema changes
- Indexes for performance-critical queries

</details>

<details>
<summary>Frontend Architecture</summary>

- Component-based design
- React Query for server state
- React Hook Form + Zod for validation
- Responsive design (Tailwind CSS)
- WCAG accessibility guidelines

</details>

## Security

**Backend**: Input validation, SQL injection prevention (ORM), auth verification, rate limiting

**Frontend**: XSS prevention, CSRF protection, secure token storage, CSP headers

## Areas for Contribution

**High Priority**: AI provider integrations, error handling, export formats (PDF/DOCX), performance, test coverage

**Medium Priority**: UI/UX, documentation, refactoring, question templates, accessibility

**Good First Issues**: Check [issue tracker](https://github.com/wzwietering/specscribe/issues) for `good-first-issue` label

## Getting Help

- [DEVELOPMENT.md](DEVELOPMENT.md) - Setup and workflows
- [GitHub Issues](https://github.com/wzwietering/specscribe/issues) - Search existing issues
- PR comments - Ask questions

Thank you for contributing!
