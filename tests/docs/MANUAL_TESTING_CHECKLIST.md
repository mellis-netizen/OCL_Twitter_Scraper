# Manual Testing Checklist - Scraping Cycle & Dashboard Updates

## Pre-Testing Setup

### Environment Preparation
- [ ] Backend API running on `http://localhost:8000`
- [ ] Frontend running on `http://localhost:3000`
- [ ] Database is accessible and seeded
- [ ] At least 5 active RSS feeds configured
- [ ] Redis cache is running (if applicable)
- [ ] Browser DevTools open for network monitoring

### Initial System Verification
- [ ] Navigate to `/health` endpoint
- [ ] Verify all systems healthy (database, redis, feeds)
- [ ] Check that feeds are marked as active in database
- [ ] Verify at least one company exists in database

---

## Test 1: Basic Scraping Cycle

### Step 1: Pre-Scraping State
- [ ] Navigate to Dashboard
- [ ] Record current statistics:
  - Total Alerts: \_\_\_\_\_
  - Total Feeds: \_\_\_\_\_
  - Alerts (24h): \_\_\_\_\_
  - Active Feeds: \_\_\_\_\_
- [ ] Take screenshot of Dashboard state

### Step 2: Trigger Scraping
- [ ] Navigate to Manual Controls page
- [ ] Click "Start Scraping Cycle" button
- [ ] Verify button becomes disabled
- [ ] Verify button text changes to "Scraping in Progress..."
- [ ] Take screenshot of progress bar

### Step 3: Monitor Progress
- [ ] Observe progress bar starts at ~5%
- [ ] Verify progress bar smoothly increments
- [ ] Check elapsed timer starts at 0:00 and increments
- [ ] Verify step indicators appear and update:
  - [ ] Step 0: Initializing scraping cycle
  - [ ] Step 1: Fetching RSS feeds and articles
  - [ ] Step 2: Monitoring Twitter accounts
  - [ ] Step 3: Analyzing content for TGE mentions
  - [ ] Step 4: Generating alerts
  - [ ] Step 5: Finalizing results
- [ ] Note any steps that show errors or take unusually long

### Step 4: Completion Verification
- [ ] Wait for progress to reach 100%
- [ ] Verify green completion card appears
- [ ] Check displayed statistics:
  - Alerts Generated: \_\_\_\_\_
  - Feeds Checked: \_\_\_\_\_
  - Duration: \_\_\_:\_\_\_
- [ ] Verify "Dashboard data refreshed" message appears
- [ ] Take screenshot of completion card

### Step 5: Dashboard Update Check
- [ ] Navigate back to Dashboard
- [ ] Compare new statistics to initial:
  - Total Alerts increased by: \_\_\_\_\_
  - Alerts (24h) shows: \_\_\_\_\_
  - Feed Last Fetch updated: ✅ / ❌
- [ ] Check Recent Alerts list for new alerts
- [ ] Verify new alerts have:
  - [ ] Correct timestamp (recent)
  - [ ] Confidence score displayed
  - [ ] Company name shown
  - [ ] Source indicator (news/twitter)
- [ ] Take screenshot of updated Dashboard

### Step 6: Feed Statistics
- [ ] Navigate to Feed Manager
- [ ] Check at least 3 feeds:
  - Feed 1: Success Count: \_\_\_\_, Last Fetch: \_\_\_\_\_
  - Feed 2: Success Count: \_\_\_\_, Last Fetch: \_\_\_\_\_
  - Feed 3: Success Count: \_\_\_\_, Last Fetch: \_\_\_\_\_
- [ ] Verify Last Fetch timestamps are recent (<2 minutes)
- [ ] Check TGE Alerts Found incremented if alerts generated

---

## Test 2: No New Alerts Scenario

### Purpose
Verify system behavior when scraping finds no new TGE alerts.

- [ ] Trigger another scraping cycle immediately after Test 1
- [ ] Wait for completion
- [ ] Verify message: "Scraping completed - no new TGE alerts found in this cycle"
- [ ] Check Dashboard:
  - [ ] Alert counts remain unchanged
  - [ ] Feed statistics still update
  - [ ] No errors displayed
- [ ] Take screenshot

---

## Test 3: Progress Bar Accuracy

### Purpose
Verify progress bar accurately represents cycle progress.

- [ ] Start scraping cycle
- [ ] Record progress at 10-second intervals:
  - 0:10 - Progress: \_\_\_\_\_%
  - 0:20 - Progress: \_\_\_\_\_%
  - 0:30 - Progress: \_\_\_\_\_%
  - 0:40 - Progress: \_\_\_\_\_%
  - 0:50 - Progress: \_\_\_\_\_%
  - 1:00 - Progress: \_\_\_\_\_%
  - 1:30 - Progress: \_\_\_\_\_%
  - Complete - Progress: 100%
- [ ] Verify progress never decreases
- [ ] Verify progress caps at ~95% until completion
- [ ] Verify progress jumps to 100% on completion

---

## Test 4: Real-Time Dashboard Updates

### Purpose
Verify dashboard updates even when not actively viewing it.

- [ ] Open Dashboard in Browser Tab 1
- [ ] Open Manual Controls in Browser Tab 2
- [ ] Record initial statistics in Tab 1
- [ ] Switch to Tab 2, start scraping
- [ ] Immediately switch back to Tab 1
- [ ] Observe Dashboard (do NOT refresh manually)
- [ ] Verify statistics update automatically after scraping completes
- [ ] Check Network tab for refetch requests
- [ ] Verify refetch happens even though tab was inactive

---

## Test 5: Error Handling

### Scenario A: API Unavailable
- [ ] Stop backend API server
- [ ] Try to trigger scraping from frontend
- [ ] Verify error message appears:
  - [ ] Red background
  - [ ] Clear error description
  - [ ] "Failed to start scraping" or similar
- [ ] Verify button becomes enabled again
- [ ] Take screenshot of error
- [ ] Restart API and verify recovery

### Scenario B: Database Connection Issue
- [ ] (Optional) Temporarily block database connection
- [ ] Trigger scraping
- [ ] Monitor for errors in backend logs
- [ ] Verify frontend shows appropriate error
- [ ] Restore database connection
- [ ] Verify system recovers

### Scenario C: Malformed Feed URL
- [ ] Add a feed with invalid URL to database
- [ ] Trigger scraping
- [ ] Verify scraping continues despite failed feed
- [ ] Check that feed's failure_count incremented
- [ ] Verify other feeds still process successfully

---

## Test 6: Multiple Rapid Triggers

### Purpose
Verify system prevents concurrent scraping cycles.

- [ ] Start scraping cycle
- [ ] Wait 5 seconds
- [ ] Attempt to click "Start Scraping Cycle" button again
- [ ] Verify button remains disabled
- [ ] Verify no second cycle starts (check backend logs)
- [ ] Wait for first cycle to complete
- [ ] Verify button becomes enabled
- [ ] Start second cycle successfully

---

## Test 7: Polling Mechanism

### Purpose
Verify frontend polls API for completion.

- [ ] Open Browser DevTools → Network tab
- [ ] Start scraping cycle
- [ ] Filter network requests by "/statistics/system"
- [ ] Observe polling:
  - [ ] Request sent every ~5 seconds
  - [ ] Polling continues while scraping active
  - [ ] Polling stops after completion detected
- [ ] Note request count: \_\_\_\_\_
- [ ] Verify no excessive polling

---

## Test 8: Session Tracking

### Purpose
Verify monitoring session is tracked in database.

- [ ] Trigger scraping
- [ ] Note session_id from API response (check Network tab): \_\_\_\_\_\_\_\_\_
- [ ] During scraping, call: `GET /monitoring/session/{session_id}`
- [ ] Verify response shows:
  - [ ] status: "running"
  - [ ] articles_processed incrementing
  - [ ] performance_metrics updating
- [ ] After completion, call same endpoint
- [ ] Verify response shows:
  - [ ] status: "completed"
  - [ ] Final metrics populated
  - [ ] end_time set
- [ ] Take screenshot of session data

---

## Test 9: Query Invalidation

### Purpose
Verify React Query invalidation strategy.

- [ ] Open Browser Console
- [ ] Run: `window.queryClient = queryClient` (if not already available)
- [ ] Start scraping cycle
- [ ] When complete, check console logs for:
  - [ ] "invalidateQueries: ['statistics']"
  - [ ] "invalidateQueries: ['feeds']"
  - [ ] "invalidateQueries: ['alerts']"
  - [ ] "invalidateQueries: ['companies']"
  - [ ] "invalidateQueries: ['health']"
- [ ] Verify all include `refetchType: 'all'`
- [ ] Wait 3 seconds after completion
- [ ] Verify delayed refetch for feeds and statistics

---

## Test 10: Feed Statistics Persistence

### Purpose
Verify feed statistics are saved correctly to database.

### Using Database Tool
- [ ] Before scraping, query database:
  ```sql
  SELECT id, url, success_count, failure_count, tge_alerts_found, last_fetch
  FROM feeds
  WHERE is_active = true
  LIMIT 5;
  ```
- [ ] Record results:
  - Feed 1: success=\_\_\_, failure=\_\_\_, tge=\_\_\_, fetch=\_\_\_\_\_
  - Feed 2: success=\_\_\_, failure=\_\_\_, tge=\_\_\_, fetch=\_\_\_\_\_
  - Feed 3: success=\_\_\_, failure=\_\_\_, tge=\_\_\_, fetch=\_\_\_\_\_

- [ ] Run scraping cycle
- [ ] Wait for completion
- [ ] Query database again (same query)
- [ ] Verify for each feed:
  - [ ] success_count incremented by 1
  - [ ] last_fetch timestamp updated (within last 2 minutes)
  - [ ] tge_alerts_found incremented if alerts found
  - [ ] failure_count unchanged (if feed succeeded)

### Using API
- [ ] Before scraping: `GET /feeds`
- [ ] Record statistics for 3 feeds
- [ ] Run scraping cycle
- [ ] After scraping: `GET /feeds`
- [ ] Compare statistics (same checks as database method)

---

## Test 11: Alert Details Verification

### Purpose
Verify generated alerts contain correct information.

- [ ] After scraping completes with new alerts
- [ ] Navigate to Dashboard → Recent Alerts
- [ ] Click on a new alert to view details
- [ ] Verify alert contains:
  - [ ] Title (not empty)
  - [ ] Content/Summary
  - [ ] Confidence score (0.0 - 1.0)
  - [ ] Company name (if matched)
  - [ ] Source (news or twitter)
  - [ ] Source URL (clickable)
  - [ ] Timestamp (recent)
  - [ ] Urgency level (low/medium/high/critical)
  - [ ] Keywords matched
  - [ ] Token symbols (if detected)
- [ ] Take screenshot of alert details

---

## Test 12: Performance Validation

### Purpose
Verify scraping cycle completes within acceptable time.

- [ ] Start scraping cycle
- [ ] Record start time: \_\_:\_\_:\_\_
- [ ] Record completion time: \_\_:\_\_:\_\_
- [ ] Calculate duration: \_\_\_\_ seconds
- [ ] Verify duration < 120 seconds
- [ ] Check completion card shows accurate duration
- [ ] Review backend logs for performance warnings

---

## Test 13: Concurrent User Scenario

### Purpose
Verify system handles multiple users viewing dashboard during scraping.

- [ ] Open Dashboard in Browser Window 1
- [ ] Open Dashboard in Browser Window 2 (incognito/different user)
- [ ] From Window 1, navigate to Manual Controls and start scraping
- [ ] Observe Window 2 (do not touch it)
- [ ] Verify Window 2 dashboard also updates after scraping completes
- [ ] Check that both windows show consistent data

---

## Test 14: Browser Compatibility

### Chrome
- [ ] Run Test 1 (Basic Scraping Cycle) in Chrome
- [ ] Verify all features work correctly
- [ ] Note any issues: \_\_\_\_\_\_\_\_\_

### Firefox
- [ ] Run Test 1 in Firefox
- [ ] Verify all features work correctly
- [ ] Note any issues: \_\_\_\_\_\_\_\_\_

### Safari
- [ ] Run Test 1 in Safari
- [ ] Verify all features work correctly
- [ ] Note any issues: \_\_\_\_\_\_\_\_\_

---

## Test 15: Mobile Responsiveness

### Purpose
Verify scraping controls and progress work on mobile devices.

- [ ] Open application on mobile device or use browser device emulator
- [ ] Navigate to Manual Controls
- [ ] Verify:
  - [ ] Button is appropriately sized
  - [ ] Progress bar is visible
  - [ ] Step indicators are readable
  - [ ] Completion card displays properly
- [ ] Start scraping cycle
- [ ] Monitor progress on mobile
- [ ] Verify updates work correctly
- [ ] Take screenshot

---

## Test 16: Data Integrity

### Purpose
Verify no data corruption or loss during scraping.

- [ ] Before scraping, count total records:
  ```sql
  SELECT
    (SELECT COUNT(*) FROM companies) as companies,
    (SELECT COUNT(*) FROM feeds) as feeds,
    (SELECT COUNT(*) FROM alerts) as alerts;
  ```
  - Companies: \_\_\_\_\_
  - Feeds: \_\_\_\_\_
  - Alerts: \_\_\_\_\_

- [ ] Run scraping cycle
- [ ] After scraping, count again
- [ ] Verify:
  - [ ] Company count unchanged (unless new detected)
  - [ ] Feed count unchanged
  - [ ] Alert count increased or unchanged (never decreased)
  - [ ] No duplicate alerts created

---

## Test 17: Long-Running Stability

### Purpose
Verify system stability over extended period.

- [ ] Run 5 scraping cycles back-to-back
- [ ] Record results for each:
  - Cycle 1: Duration=\_\_\_, Alerts=\_\_\_, Errors=\_\_\_
  - Cycle 2: Duration=\_\_\_, Alerts=\_\_\_, Errors=\_\_\_
  - Cycle 3: Duration=\_\_\_, Alerts=\_\_\_, Errors=\_\_\_
  - Cycle 4: Duration=\_\_\_, Alerts=\_\_\_, Errors=\_\_\_
  - Cycle 5: Duration=\_\_\_, Alerts=\_\_\_, Errors=\_\_\_
- [ ] Verify no memory leaks (check browser memory usage)
- [ ] Verify no performance degradation
- [ ] Check backend logs for connection pool exhaustion

---

## Bug Reporting Template

If any test fails, document using this template:

**Test ID:** [e.g., Test 5, Scenario A]
**Browser:** [Chrome/Firefox/Safari/etc.]
**Expected Result:** [What should happen]
**Actual Result:** [What actually happened]
**Steps to Reproduce:**
1. [Step 1]
2. [Step 2]
3. [Step 3]

**Screenshots:** [Attach screenshots]
**Console Errors:** [Copy any console errors]
**Network Logs:** [Note any failed requests]
**Backend Logs:** [Copy relevant backend logs]

---

## Sign-Off

**Tester Name:** \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

**Date:** \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

**Environment:**
- Backend Version: \_\_\_\_\_\_\_\_\_\_\_\_
- Frontend Version: \_\_\_\_\_\_\_\_\_\_\_\_
- Database Version: \_\_\_\_\_\_\_\_\_\_\_\_

**Test Results Summary:**
- Total Tests: 17
- Passed: \_\_\_\_\_
- Failed: \_\_\_\_\_
- Blocked: \_\_\_\_\_
- Skipped: \_\_\_\_\_

**Overall Status:** ✅ Pass / ❌ Fail / ⚠️ Pass with Issues

**Notes:**
\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_
\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_
\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_
