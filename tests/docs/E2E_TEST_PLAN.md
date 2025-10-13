# End-to-End Test Plan - Scraping Cycle & Dashboard Updates

## Overview
This document outlines comprehensive end-to-end testing scenarios for the complete scraping cycle flow and dashboard metric updates.

## Critical User Flow
```
User Action → API Trigger → Background Scraping → Database Updates → Query Invalidation → Dashboard Refresh
```

---

## Test Scenario 1: Complete Scraping Cycle with New Alerts

### Objective
Verify that the entire scraping cycle completes successfully and dashboard displays updated metrics.

### Prerequisites
- Backend API running on localhost:8000
- Frontend running on localhost:3000
- Database seeded with initial companies and feeds
- At least 5 active RSS feeds configured

### Test Steps

#### 1. Initial State Verification
```
1. Navigate to Dashboard
2. Record current statistics:
   - Total Alerts: [X]
   - Total Feeds: [Y]
   - Alerts (24h): [Z]
   - Active Feeds: [A]
3. Navigate to Manual Controls page
```

**Expected Result:**
- Dashboard displays current statistics
- All stat cards show non-zero values
- Recent alerts list is populated

#### 2. Trigger Scraping Cycle
```
1. Click "Start Scraping Cycle" button
2. Observe UI changes
```

**Expected Result:**
- Button becomes disabled
- Button text changes to "Scraping in Progress... X%"
- Progress bar appears showing 5%
- Timer starts at 0:00
- Step indicators display with step 0 active

#### 3. Monitor Progress Updates
```
1. Watch progress bar increment
2. Observe step transitions
3. Monitor elapsed time counter
```

**Expected Result:**
- Progress bar smoothly increases from 5% to 95%
- Step indicators progress through all 6 steps:
  - Initialize (0-10%)
  - Fetch feeds (10-30%)
  - Monitor Twitter (30-50%)
  - Analyze content (50-70%)
  - Generate alerts (70-90%)
  - Finalize (90-100%)
- Elapsed time increments every second
- Active step shows spinning icon
- Completed steps show green checkmark

#### 4. Completion Verification
```
1. Wait for scraping to complete (max 105 seconds)
2. Observe completion message
```

**Expected Result:**
- Progress reaches 100%
- Green success card appears
- Card shows:
  - "Scraping Complete!" message
  - Alerts Generated: [count]
  - Feeds Checked: [count]
  - Duration: [MM:SS]
  - "Dashboard data refreshed" confirmation
- Button becomes enabled again

#### 5. Dashboard Update Verification
```
1. Navigate to Dashboard
2. Compare statistics to initial state
3. Check Recent Alerts list
```

**Expected Result:**
- Statistics have updated:
  - Total Alerts increased by [generated count]
  - Alerts (24h) reflects new alerts
  - Feed statistics show updated last_fetch times
- New alerts appear at top of Recent Alerts list
- New alerts display correct:
  - Confidence scores
  - Company names
  - Timestamps
  - Source (news/twitter)

#### 6. Feed Statistics Verification
```
1. Navigate to Feed Manager
2. Check individual feed statistics
```

**Expected Result:**
- Each feed shows updated metrics:
  - Last Fetch timestamp is recent (within last 2 minutes)
  - Success Count incremented
  - TGE Alerts Found updated if alerts generated
  - Health indicator shows green

---

## Test Scenario 2: Scraping Cycle with No New Alerts

### Objective
Verify system behavior when scraping completes but no new TGE alerts are found.

### Test Steps

#### 1. Trigger Scraping
```
1. Start scraping cycle from Manual Controls
```

#### 2. Monitor Completion
```
1. Wait for completion
2. Observe completion message
```

**Expected Result:**
- Progress completes normally
- Message displays: "Scraping completed - no new TGE alerts found in this cycle"
- Statistics card still shows:
  - Feeds Checked: [count]
  - Duration: [time]

#### 3. Dashboard Behavior
```
1. Navigate to Dashboard
2. Verify statistics
```

**Expected Result:**
- Alert counts remain unchanged
- Feed statistics still update (last_fetch, success_count)
- No new alerts in Recent Alerts list
- System remains healthy

---

## Test Scenario 3: Real-Time Dashboard Updates

### Objective
Verify that dashboard updates in real-time even if not actively viewing Manual Controls.

### Test Steps

#### 1. Setup
```
1. Open Dashboard in tab 1
2. Open Manual Controls in tab 2
3. Record initial statistics in tab 1
```

#### 2. Trigger Scraping from Tab 2
```
1. In tab 2, start scraping cycle
2. Immediately switch to tab 1 (Dashboard)
```

#### 3. Monitor Dashboard
```
1. Observe if Dashboard shows updates
2. Check for refetch indicators
```

**Expected Result:**
- Dashboard queries automatically refetch due to invalidation
- Loading indicators briefly appear
- Statistics update with new data
- React Query `refetchType: 'all'` ensures inactive tabs also refetch

---

## Test Scenario 4: Multiple Rapid Triggers

### Objective
Verify system handles multiple scraping triggers appropriately.

### Test Steps

#### 1. First Trigger
```
1. Start scraping cycle
2. Wait 5 seconds
```

#### 2. Second Trigger Attempt
```
1. Try to click "Start Scraping Cycle" button again
```

**Expected Result:**
- Button remains disabled
- No second scraping cycle starts
- Original cycle continues uninterrupted

#### 3. Wait for Completion
```
1. Let first cycle complete
2. Try clicking button again
```

**Expected Result:**
- After completion, button becomes enabled
- Second trigger works normally

---

## Test Scenario 5: Progress Polling Mechanism

### Objective
Verify that frontend correctly polls for completion based on alert count changes.

### Test Steps

#### 1. Monitor Network Traffic
```
1. Open browser DevTools → Network tab
2. Start scraping cycle
3. Filter requests to /statistics/system
```

**Expected Result:**
- GET /statistics/system called every 5 seconds
- Continues polling while isScrapingActive = true
- Stops polling when completion detected

#### 2. Alert Detection
```
1. When new alerts appear in database
2. Next poll should detect increased total_alerts
```

**Expected Result:**
- Frontend detects: stats.total_alerts > initialAlertCount
- completeScrapingProcess() is called
- Alert count difference displayed: "Found X new alerts"

---

## Test Scenario 6: Error Handling

### Objective
Verify error scenarios are handled gracefully.

### Test Steps

#### 1. API Unavailable
```
1. Stop backend API
2. Try to trigger scraping
```

**Expected Result:**
- Error message displays in red
- Message: "Error: Failed to start scraping"
- Button becomes enabled again
- No progress tracking starts

#### 2. Scraping Failure During Cycle
```
1. Start scraping with misconfigured feeds
2. Wait for completion
```

**Expected Result:**
- Cycle completes (or times out after 105s)
- Error handling in backend marks session as "failed"
- Frontend shows appropriate error message
- Dashboard still attempts to refresh data

---

## Test Scenario 7: Session Tracking

### Objective
Verify monitoring session is properly tracked in database.

### Test Steps

#### 1. Trigger Scraping
```
1. Start scraping cycle
2. Note session_id from API response
```

#### 2. Query Session Status
```
1. Call GET /monitoring/session/{session_id}
2. Check response while cycle is running
```

**Expected Result:**
- Session exists with status: "running"
- Real-time metrics update:
  - articles_processed increments
  - tweets_processed increments
  - feeds_processed increments
  - performance_metrics.phase updates

#### 3. After Completion
```
1. Query session again after completion
2. Verify final state
```

**Expected Result:**
- Session status: "completed"
- Final metrics populated:
  - articles_processed: [total]
  - tweets_processed: [total]
  - alerts_generated: [total]
  - feeds_processed: [total]
- end_time timestamp set
- performance_metrics includes cycle_time

---

## Test Scenario 8: Feed Statistics Persistence

### Objective
Verify feed statistics are accurately persisted to database.

### Test Steps

#### 1. Record Initial Feed Stats
```sql
SELECT url, success_count, failure_count, tge_alerts_found, last_fetch
FROM feeds
WHERE is_active = true;
```

#### 2. Run Scraping Cycle
```
1. Trigger scraping
2. Wait for completion
```

#### 3. Query Feed Stats Again
```sql
SELECT url, success_count, failure_count, tge_alerts_found, last_fetch
FROM feeds
WHERE is_active = true;
```

**Expected Result:**
- For each successfully scraped feed:
  - success_count incremented by 1
  - last_fetch updated to recent timestamp
  - tge_alerts_found incremented if alerts were generated from that feed
- For any failed feeds:
  - failure_count incremented by 1

---

## Test Scenario 9: Query Invalidation Strategy

### Objective
Verify React Query invalidation strategy works correctly.

### Test Steps

#### 1. Monitor Query Cache
```javascript
// In browser console:
console.log(queryClient.getQueryCache().getAll());
```

#### 2. Trigger Scraping
```
1. Complete scraping cycle
2. Monitor console for invalidation calls
```

**Expected Result:**
- invalidateQueries called for:
  - ['statistics']
  - ['feeds']
  - ['alerts']
  - ['companies']
  - ['health']
- All calls include `refetchType: 'all'`
- Queries refetch even if components unmounted

#### 3. Delayed Refetch
```
1. After initial invalidation
2. Wait 3 seconds
```

**Expected Result:**
- Secondary refetchQueries called for:
  - ['feeds']
  - ['statistics']
- This catches any delayed database updates

---

## Test Scenario 10: Performance Validation

### Objective
Verify scraping cycle completes within acceptable time limits.

### Test Steps

#### 1. Measure Cycle Time
```
1. Start scraping cycle
2. Record start time
3. Record completion time
```

**Expected Result:**
- Cycle completes in < 120 seconds (2 minutes)
- Frontend progress bar estimates ~105 seconds (1:45)
- Actual time displayed in completion stats

#### 2. Database Performance
```
1. Check database query performance
2. Monitor alert insertion time
```

**Expected Result:**
- Alert insertion: < 100ms per alert
- Feed statistics update: < 500ms total
- No database connection timeouts

---

## Automated E2E Test Implementation

### Playwright Test Example

```typescript
// e2e/scraping-cycle.spec.ts

import { test, expect } from '@playwright/test';

test.describe('Scraping Cycle Flow', () => {
  test('complete scraping cycle updates dashboard', async ({ page }) => {
    // Navigate to dashboard
    await page.goto('http://localhost:3000/dashboard');

    // Record initial alert count
    const initialAlertCount = await page
      .locator('[data-testid="total-alerts"]')
      .textContent();

    // Navigate to manual controls
    await page.goto('http://localhost:3000/manual-controls');

    // Trigger scraping
    await page.click('[data-testid="start-scraping-button"]');

    // Verify button disabled
    await expect(
      page.locator('[data-testid="start-scraping-button"]')
    ).toBeDisabled();

    // Verify progress bar appears
    await expect(
      page.locator('[data-testid="progress-bar"]')
    ).toBeVisible();

    // Wait for completion (max 120s)
    await expect(
      page.locator('[data-testid="scraping-complete"]')
    ).toBeVisible({ timeout: 120000 });

    // Navigate back to dashboard
    await page.goto('http://localhost:3000/dashboard');

    // Verify alert count updated
    const finalAlertCount = await page
      .locator('[data-testid="total-alerts"]')
      .textContent();

    expect(parseInt(finalAlertCount)).toBeGreaterThanOrEqual(
      parseInt(initialAlertCount)
    );
  });

  test('progress bar updates sequentially', async ({ page }) => {
    await page.goto('http://localhost:3000/manual-controls');

    await page.click('[data-testid="start-scraping-button"]');

    // Check progress increments
    let previousProgress = 0;
    for (let i = 0; i < 5; i++) {
      await page.waitForTimeout(5000);
      const progressText = await page
        .locator('[data-testid="progress-percentage"]')
        .textContent();
      const currentProgress = parseInt(progressText);
      expect(currentProgress).toBeGreaterThan(previousProgress);
      previousProgress = currentProgress;
    }
  });

  test('feed statistics update after scraping', async ({ page }) => {
    await page.goto('http://localhost:3000/feed-manager');

    // Record feed stats
    const initialStats = await page
      .locator('[data-testid="feed-success-count"]')
      .first()
      .textContent();

    // Trigger scraping
    await page.goto('http://localhost:3000/manual-controls');
    await page.click('[data-testid="start-scraping-button"]');
    await expect(
      page.locator('[data-testid="scraping-complete"]')
    ).toBeVisible({ timeout: 120000 });

    // Check feed stats updated
    await page.goto('http://localhost:3000/feed-manager');
    const finalStats = await page
      .locator('[data-testid="feed-success-count"]')
      .first()
      .textContent();

    expect(parseInt(finalStats)).toBeGreaterThan(parseInt(initialStats));
  });
});
```

---

## Performance Benchmarks

### Expected Timing
- **Scraping Initialization**: < 2 seconds
- **RSS Feed Fetching**: 30-60 seconds (depends on feed count)
- **Twitter Monitoring**: 20-40 seconds
- **Content Analysis**: 10-20 seconds
- **Alert Generation**: < 5 seconds
- **Database Updates**: < 3 seconds
- **Total Cycle Time**: 60-120 seconds

### Expected Metrics
- **Articles Processed**: 50-200 per cycle
- **Tweets Processed**: 20-100 per cycle
- **Feeds Processed**: 10-30 feeds
- **Alerts Generated**: 0-20 per cycle
- **Success Rate**: > 95%

---

## Error Recovery Testing

### Scenario: Database Connection Lost
```
1. Stop database mid-cycle
2. Observe error handling
3. Restart database
4. Verify recovery
```

### Scenario: API Rate Limiting
```
1. Trigger multiple rapid scraping cycles
2. Verify rate limiting kicks in
3. Check error messages
```

### Scenario: Network Timeout
```
1. Simulate slow network
2. Verify timeout handling
3. Check partial data handling
```

---

## Monitoring & Observability

### Key Metrics to Track
- Cycle completion rate
- Average cycle duration
- Alert generation rate
- Feed success rate
- Error frequency
- Query refetch count

### Logging Verification
```
1. Check backend logs for cycle start/end
2. Verify feed statistics logging
3. Confirm alert creation logs
4. Check error logs for failures
```

---

## Test Execution Checklist

- [ ] Run all unit tests: `pytest tests/test_scraping_metrics.py -v`
- [ ] Run API integration tests: `pytest tests/test_api_metrics.py -v`
- [ ] Run frontend component tests: `npm test -- tests/ManualControls.test.tsx`
- [ ] Execute E2E tests: `playwright test e2e/scraping-cycle.spec.ts`
- [ ] Manual testing of complete flow
- [ ] Performance benchmarking
- [ ] Load testing (multiple concurrent users)
- [ ] Error injection testing
- [ ] Database integrity validation

---

## Success Criteria

All tests pass if:
1. ✅ Scraping cycle completes within 120 seconds
2. ✅ All metrics accurately track activity
3. ✅ Dashboard updates reflect database changes
4. ✅ Query invalidation triggers refetch
5. ✅ Feed statistics persist correctly
6. ✅ No memory leaks or connection leaks
7. ✅ Error handling gracefully recovers
8. ✅ Real-time progress tracking works
9. ✅ Multiple cycles can run sequentially
10. ✅ No data corruption or inconsistency
