# Frontend Issues Checklist - Quick Reference

## P0 - Critical (Must Fix Before Production)

- [ ] **useAuth.tsx:17-28** - Authentication completely mocked with hardcoded user
- [ ] **useAuth.tsx:44-57** - Auth functions (login/logout/register) are no-ops
- [ ] **useAuth.tsx:32-42** - WebSocket connects with empty token string
- [ ] **api.ts:65-80** - Auth methods implemented but never used (dead code)
- [ ] **Global** - No security controls, no access restrictions
- [ ] **Global** - No error boundaries to catch crashes

## P1 - High Priority (Fix This Sprint)

- [ ] **App.tsx:68-93** - System Status indicators are hardcoded, not real
- [ ] **ManualControls.tsx:46-104** - Aggressive 2s polling (use 5s or WebSocket)
- [ ] **AlertDashboard.tsx:28-62** - Real-time alerts not working (WebSocket issues)
- [ ] **api.ts:24** - Token in localStorage (XSS vulnerability)
- [ ] **api.ts:40-50** - 401 errors only logged, no user notification
- [ ] **websocket.ts:23** - WebSocket requires token but auth is disabled
- [ ] **useAlerts.ts:22-36** - WebSocket connection without proper auth
- [ ] **Global** - No React Error Boundary component
- [ ] **Global** - No toast/notification system for errors
- [ ] **Global** - 15+ console.log statements in production code
- [ ] **Global** - No unit tests (testing infrastructure needed)
- [ ] **Global** - Missing accessibility features (ARIA, focus management)

## P2 - Medium Priority (Fix Next Sprint)

### Type Safety
- [ ] **Dashboard.tsx:7** - seedResult typed as 'any'
- [ ] **ManualControls.tsx:20** - scrapingStats typed as 'any'
- [ ] **ManualControls.tsx:22** - realTimeMetrics typed as 'any'

### Error Handling
- [ ] **ManualControls.tsx:91** - Polling errors only logged to console
- [ ] **ManualControls.tsx:139** - Stats fetch errors only logged
- [ ] **websocket.ts:31,41,46** - Multiple console.log/error statements
- [ ] **api.ts:46** - console.warn for production errors

### UX Issues
- [ ] **Dashboard.tsx:39-44** - Simple loading text (add skeleton loader)
- [ ] **AlertDashboard.tsx:124-129** - Basic loading/empty states
- [ ] **FeedManager.tsx:208-213** - Simple loading states
- [ ] **CompanyManager.tsx:270-275** - Simple loading states
- [ ] **FeedManager.tsx:81** - Native window.confirm (use custom modal)
- [ ] **CompanyManager.tsx:101** - Native window.confirm (use custom modal)

### Accessibility
- [ ] **FeedManager.tsx:112-204** - Modal missing ARIA attributes
- [ ] **CompanyManager.tsx:127-266** - Modal missing ARIA attributes
- [ ] **Global** - No focus trap in modals
- [ ] **Global** - No Escape key handlers
- [ ] **Global** - Missing alt text on logo

### Configuration & Maintenance
- [ ] **ManualControls.tsx:24-31** - Progress steps hardcoded (move to constants)
- [ ] **ManualControls.tsx:61-74** - Phase-to-step mapping hardcoded
- [ ] **api.ts:20** - Hardcoded localhost fallback
- [ ] **websocket.ts:77-89** - Reconnection not visible to user

### Performance
- [ ] **AlertDashboard.tsx:34** - Array index used as React key
- [ ] **useAlerts.ts:29** - refetch() on every alert (debounce needed)
- [ ] **CompanyManager.tsx:68-82** - Manual string-to-array parsing

### Dead Code
- [ ] **App.tsx:42** - Empty comment for removed badge
- [ ] **Dashboard.tsx:24-37** - Unused seedMutation

## P3 - Low Priority (Nice to Have)

- [ ] **App.tsx:111-114** - Empty footer content
- [ ] **Dashboard.tsx:119** - Last check time shows "now" instead of real time
- [ ] **AlertDashboard.tsx:38** - Custom CSS class 'animate-pulse-slow' undefined
- [ ] **FeedManager.tsx:92-96** - Success rate edge case handling
- [ ] **useAlerts.ts:28** - Hardcoded 50 alert limit (use constant)
- [ ] **websocket.ts:20** - Fixed reconnection parameters (use exponential backoff)

## Cross-Cutting Improvements Needed

### Testing
- [ ] Set up Vitest + React Testing Library
- [ ] Add MSW for API mocking
- [ ] Create unit tests for all components
- [ ] Add integration tests
- [ ] Set up Playwright for E2E tests
- [ ] Configure test coverage reporting (80%+ target)

### Accessibility Audit
- [ ] Run axe DevTools audit
- [ ] Test with NVDA/JAWS screen readers
- [ ] Add aria-live regions for dynamic content
- [ ] Verify color contrast ratios
- [ ] Test keyboard navigation
- [ ] Add focus indicators

### Performance Optimization
- [ ] Implement React.lazy for code splitting
- [ ] Add React.memo to expensive components
- [ ] Use useCallback/useMemo strategically
- [ ] Implement virtual scrolling for long lists
- [ ] Profile with React DevTools Profiler
- [ ] Optimize bundle size

### Developer Experience
- [ ] Add Storybook for component development
- [ ] Create component documentation
- [ ] Set up error boundaries per route
- [ ] Add design system tokens
- [ ] Configure Prettier/ESLint rules
- [ ] Add pre-commit hooks

### Security Hardening
- [ ] Implement proper authentication
- [ ] Use httpOnly cookies instead of localStorage
- [ ] Add CSRF protection
- [ ] Implement rate limiting
- [ ] Add input sanitization
- [ ] Security audit before production

## Enhancement Opportunities

### UI/UX
- [ ] Add toast notification system (react-hot-toast)
- [ ] Implement skeleton loaders
- [ ] Add dark/light theme toggle
- [ ] Create data visualization charts
- [ ] Advanced filtering UI
- [ ] Export functionality for data

### Features
- [ ] Real-time browser notifications
- [ ] Alert management (mark read, archive, delete)
- [ ] Custom alert rules/filters
- [ ] Dashboard customization
- [ ] Bulk operations
- [ ] Search functionality

### State Management
- [ ] Evaluate Zustand/Jotai for global state
- [ ] Centralize WebSocket connection
- [ ] Choose polling OR WebSocket (not both)
- [ ] Add connection status to UI

---

## Quick Stats
- Total Issues: 47
- Critical: 6
- High: 12
- Medium: 18
- Low: 11

## Files by Quality Score
- F: hooks/useAuth.tsx (security critical)
- C: services/api.ts
- C+: ManualControls.tsx, services/websocket.ts
- B-: AlertDashboard.tsx, FeedManager.tsx, CompanyManager.tsx, useAlerts.ts
- B: App.tsx
- B+: Dashboard.tsx

## Priority Order
1. Fix authentication or remove it entirely
2. Fix WebSocket or switch to polling only
3. Add error boundaries
4. Remove all console.log statements
5. Add toast notification system
6. Implement accessibility features
7. Set up testing infrastructure
