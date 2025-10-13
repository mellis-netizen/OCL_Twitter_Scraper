# Comprehensive Test Strategy - Scraping Cycle & Dashboard Metrics

## Executive Summary

This document outlines the complete testing strategy for validating the scraping cycle completion workflow and dashboard metric updates in the TGE Monitor application.

**Critical User Flow:**
```
User triggers scraping → Backend processes feeds → Metrics tracked → Database updated →
Frontend invalidates queries → Dashboard refreshes → User sees updated data
```

---

## Testing Pyramid

```
                    /\
                   /  \
                  / E2E \ ← 10% (End-to-end flow tests)
                 /------\
                /  API   \ ← 30% (Integration tests)
               /----------\
              /   Backend  \ ← 40% (Unit tests)
             /   Frontend   \ ← 20% (Component tests)
            /----------------\
```

---

## Test Coverage Areas

### 1. Backend Metrics Tracking (40%)
**Location:** `/tests/test_scraping_metrics.py`

#### Objectives
- Verify accurate tracking of scraping cycle metrics
- Validate database persistence of metrics
- Ensure feed statistics are correctly updated
- Test monitoring session lifecycle

#### Key Test Cases
- **Metrics Initialization:** Verify metrics object is properly initialized
- **Cycle Time Tracking:** Measure and validate cycle duration accuracy
- **Alert Counting:** Ensure alerts are counted correctly by source and confidence
- **Articles/Tweets Processing:** Track processing counts accurately
- **Feed Statistics Update:** Validate success_count, failure_count, tge_alerts_found
- **Database Persistence:** Confirm all metrics save to database
- **Monitoring Sessions:** Test session creation, updates, and completion
- **Error Tracking:** Verify error cycles are logged
- **Deduplication:** Test content deduplication logic

#### Technologies
- pytest
- unittest.mock
- SQLAlchemy (database mocking)

#### Success Criteria
- 100% code coverage for metrics tracking functions
- All tests pass in <5 seconds
- No database connection leaks

---

### 2. API Integration Tests (30%)
**Location:** `/tests/test_api_metrics.py`

#### Objectives
- Validate REST API endpoints return correct data
- Test endpoint response structure and data types
- Verify query parameters work correctly
- Ensure proper HTTP status codes

#### Key Test Cases
- **Health Endpoint:** Validate health check includes feed and system metrics
- **System Statistics:** Test /statistics/system endpoint structure and accuracy
- **Alert Statistics:** Verify /statistics/alerts with date range filtering
- **Monitoring Trigger:** Test POST /monitoring/trigger creates session
- **Session Status:** Validate GET /monitoring/session/{id} returns correct data
- **Session Progress:** Test real-time progress endpoint
- **Feed Endpoints:** Verify feed list includes updated statistics
- **Alert Endpoints:** Test alert listing with confidence filters
- **Query Performance:** Ensure API responses are fast (<200ms)

#### Technologies
- FastAPI TestClient
- pytest
- unittest.mock

#### Success Criteria
- All endpoints return 200 for valid requests
- Response schemas match specifications
- Average response time <200ms
- Proper error handling (404, 500, etc.)

---

### 3. Frontend Component Tests (20%)
**Location:** `/tests/test_dashboard_updates.py`

#### Objectives
- Test React component rendering and behavior
- Validate React Query integration
- Verify query invalidation triggers refetch
- Test loading and error states

#### Key Test Cases
- **Scraping Button State:** Disabled during active scraping
- **Progress Bar Updates:** Smooth progression from 0% to 100%
- **Step Indicators:** Sequential step completion visualization
- **Elapsed Timer:** Accurate time counter
- **Completion Statistics:** Display real data from API
- **Query Invalidation:** Verify invalidateQueries called with correct parameters
- **Delayed Refetch:** Test 3-second delayed refetch
- **Error Display:** Show error messages appropriately
- **Polling Mechanism:** Test 5-second polling for completion
- **Auto-Completion:** Verify 105-second timeout

#### Technologies
- Jest
- React Testing Library
- @testing-library/user-event
- @tanstack/react-query

#### Success Criteria
- All component tests pass
- No console warnings or errors
- Query invalidation coverage 100%
- Components properly cleanup on unmount

---

### 4. End-to-End Tests (10%)
**Location:** `/tests/docs/E2E_TEST_PLAN.md`

#### Objectives
- Validate complete user workflows
- Test real-world scenarios with actual backend
- Verify data flows through entire system
- Catch integration issues missed by unit tests

#### Key Scenarios

**Scenario 1: Complete Scraping Cycle with New Alerts**
- User triggers scraping
- Monitor progress through all steps
- Verify completion with statistics
- Confirm dashboard updates with new data

**Scenario 2: Scraping with No New Alerts**
- Trigger scraping
- Verify "no alerts found" message
- Confirm feed statistics still update

**Scenario 3: Real-Time Dashboard Updates**
- Start scraping in one tab
- Monitor dashboard in another tab
- Verify automatic updates without manual refresh

**Scenario 4: Error Handling**
- Test API unavailable scenario
- Test database connection failures
- Verify graceful degradation

**Scenario 5: Session Tracking**
- Verify session created on trigger
- Monitor real-time session updates
- Confirm final session state

#### Technologies
- Playwright or Cypress
- Full-stack integration (frontend + backend + database)

#### Success Criteria
- All E2E scenarios complete successfully
- Cycle completes in <120 seconds
- No data corruption
- Error recovery works

---

## Manual Testing (Critical Path)
**Location:** `/tests/docs/MANUAL_TESTING_CHECKLIST.md`

### When to Perform
- Before each release
- After significant refactoring
- When automated tests are insufficient

### Key Manual Tests
1. **Visual Inspection:** UI rendering on different browsers
2. **User Experience:** Flow feels smooth and responsive
3. **Edge Cases:** Unusual user behaviors
4. **Performance:** Subjective speed assessment
5. **Accessibility:** Keyboard navigation, screen readers
6. **Mobile Responsiveness:** Touch interactions

---

## Test Data Management

### Test Database Setup
```python
# fixtures/test_data.py

def create_test_companies(db_session):
    """Create test companies"""
    companies = [
        Company(name="Caldera", priority="HIGH", tokens=["CAL"]),
        Company(name="Fhenix", priority="HIGH", tokens=["FHE"]),
        Company(name="Polyhedra", priority="MEDIUM", tokens=["ZKP"])
    ]
    db_session.add_all(companies)
    db_session.commit()
    return companies

def create_test_feeds(db_session):
    """Create test RSS feeds"""
    feeds = [
        Feed(
            url="https://example.com/feed1",
            is_active=True,
            success_count=0,
            failure_count=0
        ),
        Feed(
            url="https://example.com/feed2",
            is_active=True,
            success_count=0,
            failure_count=0
        )
    ]
    db_session.add_all(feeds)
    db_session.commit()
    return feeds
```

### Mock Data Generators
```python
def generate_mock_article():
    """Generate mock news article"""
    return {
        'title': 'Caldera Announces TGE Launch Date',
        'content': 'Caldera has announced their Token Generation Event (TGE) will take place next week...',
        'url': 'https://example.com/article',
        'published': datetime.now(timezone.utc).isoformat()
    }

def generate_mock_tweet():
    """Generate mock tweet"""
    return {
        'text': 'Exciting news! Caldera $CAL TGE launching soon!',
        'url': 'https://twitter.com/user/status/123',
        'created_at': datetime.now(timezone.utc).isoformat()
    }
```

---

## Continuous Integration

### CI/CD Pipeline

```yaml
# .github/workflows/test.yml

name: Test Suite

on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run backend unit tests
        run: pytest tests/test_scraping_metrics.py -v --cov
      - name: Run API integration tests
        run: pytest tests/test_api_metrics.py -v --cov

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Install dependencies
        run: npm install
      - name: Run frontend tests
        run: npm test -- --coverage

  e2e-tests:
    runs-on: ubuntu-latest
    needs: [backend-tests, frontend-tests]
    steps:
      - uses: actions/checkout@v3
      - name: Start services
        run: docker-compose up -d
      - name: Run E2E tests
        run: npx playwright test
      - name: Upload test results
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: playwright-report/
```

---

## Performance Benchmarks

### Expected Performance Metrics

| Metric | Target | Acceptable | Critical |
|--------|--------|------------|----------|
| Cycle Duration | <90s | <120s | <180s |
| Articles Processed/s | >2 | >1 | >0.5 |
| Alert Generation Time | <5s | <10s | <20s |
| Database Query Time | <50ms | <100ms | <200ms |
| API Response Time | <100ms | <200ms | <500ms |
| Frontend Render Time | <1s | <2s | <5s |
| Query Refetch Time | <500ms | <1s | <2s |

### Performance Test Example

```python
def test_cycle_performance():
    """Test scraping cycle completes within time limit"""
    monitor = OptimizedCryptoTGEMonitor(swarm_enabled=False)

    start_time = time.time()
    monitor.run_monitoring_cycle()
    duration = time.time() - start_time

    assert duration < 120, f"Cycle took {duration}s, exceeds 120s limit"
```

---

## Error Scenarios

### High-Priority Error Cases

1. **Database Connection Lost**
   - Simulate: Stop database mid-cycle
   - Expected: Graceful error, no data corruption
   - Recovery: Auto-reconnect on next cycle

2. **API Rate Limiting**
   - Simulate: Rapid scraping triggers
   - Expected: Rate limit error, retry with backoff
   - Recovery: Wait and retry

3. **Network Timeout**
   - Simulate: Slow/hanging feed requests
   - Expected: Timeout after 120s, partial results
   - Recovery: Mark feed as failed, continue

4. **Invalid Feed Data**
   - Simulate: Malformed RSS/XML
   - Expected: Skip feed, log error
   - Recovery: Continue with other feeds

5. **Memory Exhaustion**
   - Simulate: Process 1000+ articles
   - Expected: Graceful degradation
   - Recovery: Process in batches

---

## Test Execution Schedule

### Pre-Commit (Developer)
- [ ] Run unit tests for changed files
- [ ] Run linter and type checker
- [ ] Manual smoke test of changed functionality

### Pre-PR (Developer)
- [ ] Run full backend test suite
- [ ] Run full frontend test suite
- [ ] Run relevant E2E tests
- [ ] Update test documentation if needed

### CI Pipeline (Automated)
- [ ] Run all unit tests
- [ ] Run all integration tests
- [ ] Run code coverage analysis
- [ ] Run linting and security checks

### Pre-Release (QA Team)
- [ ] Run full E2E test suite
- [ ] Complete manual testing checklist
- [ ] Performance benchmarking
- [ ] Cross-browser testing
- [ ] Mobile responsiveness testing

### Post-Release (Monitoring)
- [ ] Monitor error rates
- [ ] Track performance metrics
- [ ] User feedback analysis
- [ ] Sentry/error tracking review

---

## Test Metrics & Reporting

### Coverage Targets
- **Backend Code Coverage:** >80%
- **Frontend Code Coverage:** >75%
- **API Endpoint Coverage:** 100%
- **Critical Path Coverage:** 100%

### Reporting Tools
- **Backend:** pytest-cov → Codecov
- **Frontend:** Jest coverage → Codecov
- **E2E:** Playwright HTML Report
- **Dashboard:** Codecov.io

### Success Criteria

#### For Release
- ✅ All automated tests pass
- ✅ Code coverage meets targets
- ✅ Manual testing checklist 100% complete
- ✅ No critical bugs remaining
- ✅ Performance benchmarks met
- ✅ Security scan passes

---

## Known Limitations

### Current Test Gaps
1. **Load Testing:** No tests for concurrent users (>10)
2. **Long-Running Stability:** No 24-hour endurance tests
3. **Network Resilience:** Limited intermittent connection tests
4. **Browser Compatibility:** Only Chrome/Firefox tested
5. **Mobile Testing:** Limited device coverage

### Future Improvements
- [ ] Add load testing with Locust or k6
- [ ] Implement chaos engineering tests
- [ ] Expand browser compatibility matrix
- [ ] Add visual regression testing (Percy)
- [ ] Implement contract testing (Pact)

---

## Test Maintenance

### Regular Reviews
- **Weekly:** Review flaky tests, fix or skip
- **Monthly:** Review test coverage, identify gaps
- **Quarterly:** Refactor tests, remove obsolete
- **Annually:** Full test strategy review

### Documentation Updates
- Update test documentation with code changes
- Keep manual checklist current
- Document new edge cases discovered
- Share test results in team meetings

---

## Contact & Support

**Test Owner:** QA Team
**Test Infrastructure:** DevOps Team
**Questions:** #testing-support Slack channel

---

## Appendix: Test File Structure

```
tests/
├── __init__.py
├── test_scraping_metrics.py      # Backend unit tests
├── test_api_metrics.py            # API integration tests
├── test_dashboard_updates.py      # Frontend component tests
├── fixtures/
│   ├── __init__.py
│   └── test_data.py               # Shared test data
├── integration/
│   └── test_full_flow.py          # Integration tests
├── e2e/
│   ├── scraping-cycle.spec.ts     # Playwright E2E tests
│   └── dashboard-updates.spec.ts
├── performance/
│   └── test_benchmarks.py         # Performance tests
└── docs/
    ├── TEST_STRATEGY.md           # This file
    ├── E2E_TEST_PLAN.md           # E2E scenarios
    └── MANUAL_TESTING_CHECKLIST.md # Manual test checklist
```

---

## Conclusion

This comprehensive test strategy ensures the scraping cycle and dashboard update workflow is thoroughly validated at all levels of the testing pyramid. By combining automated unit, integration, and E2E tests with structured manual testing, we can confidently release updates knowing the critical user flow is stable and reliable.

**Remember:** Tests are not just for catching bugs—they're documentation, safety nets, and design feedback. Invest in good tests, and they'll pay dividends in code quality and team velocity.
