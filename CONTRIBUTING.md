# Contributing Guide

Thank you for your interest in contributing to Requirements Bot! This guide covers our development standards, processes, and best practices.

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help maintain a positive development environment

## Getting Started

1. **Fork and clone** the repository
2. **Follow setup** instructions in `DEVELOPMENT.md`
3. **Create a feature branch** from `master`
4. **Make your changes** following our standards
5. **Submit a pull request** with clear description

## Development Standards

### Code Quality Principles

#### General Rules
- **Functions must be 10-20 lines maximum** - Break down longer functions
- **Single responsibility** - Each function does one thing well
- **Clear naming** - Names should explain purpose without comments
- **Early returns** - Use guard clauses to reduce nesting
- **Maximum 2 levels of indentation** - Keep code flat and readable

#### Documentation
- **Document the why, not the what** - Explain reasoning and context
- **Self-documenting code** - Use meaningful names over comments
- **Update docs** when changing public APIs

### Backend Standards (Python/FastAPI)

#### Code Style
```python
# Good: Clear, single responsibility
def create_user_session(user_id: str, expires_in: int = 3600) -> Session:
    if not user_id:
        raise ValueError("User ID is required")

    session_id = generate_session_id()
    expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

    return Session(
        id=session_id,
        user_id=user_id,
        expires_at=expires_at
    )

# Avoid: Multiple responsibilities, unclear naming
def handle_user(data, config, mode=None):
    # 50 lines of mixed logic...
```

#### Required Practices
- **Type hints** on all function signatures
- **Pydantic models** for all API schemas
- **Proper error handling** with meaningful messages
- **Database transactions** for data consistency
- **Comprehensive tests** for all endpoints

#### Testing Requirements
```python
# Test structure
def test_create_user_session():
    # Arrange
    user_id = "test-user"

    # Act
    session = create_user_session(user_id)

    # Assert
    assert session.user_id == user_id
    assert session.expires_at > datetime.utcnow()
```

### Frontend Standards (TypeScript/React)

#### Code Style
```typescript
// Good: Clear, typed, single responsibility
interface UserSessionProps {
  userId: string;
  onSessionEnd: () => void;
}

function UserSession({ userId, onSessionEnd }: UserSessionProps) {
  if (!userId) {
    return <div>Please log in</div>;
  }

  return (
    <div className="user-session">
      <SessionTimer onExpire={onSessionEnd} />
    </div>
  );
}

// Avoid: Unclear types, multiple responsibilities
function UserThing({ data, callbacks }: any) {
  // 30 lines handling sessions, UI, API calls...
}
```

#### Required Practices
- **Strict TypeScript** - No `any` types
- **Import API types** from `@req-bot/shared-types`
- **Component composition** over large components
- **Custom hooks** for reusable logic
- **Error boundaries** for error handling

### Type Safety

#### Backend-Frontend Integration
```typescript
// Correct: Use generated types
import type { paths, components } from '@req-bot/shared-types';

type SessionResponse = components['schemas']['SessionResponse'];
type CreateSessionRequest = components['schemas']['CreateSessionRequest'];

// API call with proper typing
const createSession = async (data: CreateSessionRequest): Promise<SessionResponse> => {
  // Implementation
};
```

## Pull Request Process

### Before Submitting
- [ ] **Run all tests** - `npm run test`
- [ ] **Type check passes** - `npm run type-check`
- [ ] **Linting clean** - `npm run lint`
- [ ] **Generate types** - `npm run generate:types` (if backend changes)
- [ ] **Manual testing** - Test your changes work end-to-end

### PR Requirements

#### Title Format
- `feat: add user session management`
- `fix: resolve authentication token expiry`
- `docs: update API documentation`
- `refactor: simplify session service`
- `test: add integration tests for auth`

#### Description Template
```markdown
## Summary
Brief description of changes and motivation.

## Changes
- Specific change 1
- Specific change 2

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Manual testing completed

## Type Safety
- [ ] Generated types updated (if backend changes)
- [ ] Frontend uses proper types
- [ ] No TypeScript errors

## Breaking Changes
List any breaking changes and migration steps.
```

#### Review Checklist
- **Code quality** - Functions under 20 lines, clear names, single responsibility
- **Test coverage** - New code is tested
- **Type safety** - Proper TypeScript usage
- **Documentation** - Updated if needed
- **Performance** - No obvious performance regressions

### Review Process
1. **Automated checks** must pass (CI/CD)
2. **Code review** by maintainer
3. **Address feedback** and update
4. **Final approval** and merge

## Architecture Guidelines

### API Design
- **RESTful endpoints** with clear resource names
- **Consistent response formats** using Pydantic models
- **Proper HTTP status codes**
- **Authentication/authorization** on protected routes
- **Request validation** with meaningful error messages

### Database Design
- **Normalized structure** with proper relationships
- **Database constraints** for data integrity
- **Migrations** for schema changes
- **Indexes** for performance-critical queries

### Frontend Architecture
- **Component-based** design with clear boundaries
- **State management** using React Query for server state
- **Form handling** with React Hook Form + Zod validation
- **Responsive design** with Tailwind CSS
- **Accessibility** following WCAG guidelines

## Testing Strategy

### Backend Testing
```python
# Unit tests for business logic
def test_session_creation():
    session = create_session("user123")
    assert session.is_valid()

# Integration tests for API endpoints
def test_create_session_endpoint(client):
    response = client.post("/sessions", json={"user_id": "test"})
    assert response.status_code == 201

# End-to-end tests for critical flows
def test_authentication_flow():
    # Test complete OAuth flow
```

### Frontend Testing (Future)
```typescript
// Component tests
test('UserSession renders correctly', () => {
  render(<UserSession userId="test" onSessionEnd={mockFn} />);
  expect(screen.getByText('Session active')).toBeInTheDocument();
});

// Integration tests
test('session creation flow', async () => {
  // Test complete user flow
});
```

## Git Workflow

### Branch Naming
- `feature/user-authentication`
- `fix/session-expiry-bug`
- `docs/api-documentation`
- `refactor/session-service`

### Commit Messages
```
feat: add OAuth integration with Google

- Implement OAuth callback handling
- Add JWT token generation
- Update user authentication flow

Closes #123
```

### Merge Requirements
- **All checks pass** (tests, linting, type checking)
- **Code review approval**
- **Up-to-date with master**
- **Clean commit history**

## Environment Management

### Development
- Use `.env` files (never commit them)
- Document required environment variables
- Provide example `.env.example` files

### Production
- Use environment-specific configurations
- Secure secret management
- Proper logging and monitoring

## Performance Considerations

### Backend
- **Database query optimization**
- **Proper caching strategies**
- **Connection pooling**
- **Background job processing**

### Frontend
- **Code splitting** for large bundles
- **Image optimization**
- **React Query caching**
- **Lazy loading** for non-critical components

## Security Guidelines

### Backend Security
- **Input validation** on all endpoints
- **SQL injection prevention** using ORM
- **Authentication verification** on protected routes
- **Rate limiting** for API endpoints
- **Secure session management**

### Frontend Security
- **XSS prevention** through proper escaping
- **CSRF protection** for sensitive operations
- **Secure token storage**
- **Content Security Policy** headers

## Release Process

### Versioning
- Follow semantic versioning (major.minor.patch)
- Update version in relevant package.json files
- Tag releases in git

### Deployment
- **Staging deployment** for testing
- **Production deployment** after approval
- **Rollback procedures** if issues arise

## Getting Help

- **Documentation** - Check `DEVELOPMENT.md` first
- **GitHub Issues** - Search existing issues
- **Pull Request Discussion** - Ask questions in PR comments
- **Code Examples** - Check test files for usage patterns

## Recognition

Contributors who follow these guidelines and make meaningful contributions will be recognized in our contributor list and release notes.

Thank you for helping make Requirements Bot better! 🚀