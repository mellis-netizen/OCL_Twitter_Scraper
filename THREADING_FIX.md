# Threading Issue Analysis & Fix

## Problem
The `execute_cycle()` function (nested inside `run_cycle()`) is NOT executing in Railway, causing `performance_metrics` to remain empty and progress bar to stay at 0%.

## Root Cause
Complex nested function structure with daemon threads may not work reliably in FastAPI async context on Railway:
- `run_cycle()` is a daemon thread
- `execute_cycle()` is defined INSIDE `run_cycle()` and started as another daemon thread
- The closure captures `session_id` from outer async function scope
- Railway environment may terminate daemon threads immediately or handle closures differently

## Evidence
- Session created successfully (status="running")
- But `performance_metrics` is empty (`{}`)
- Logs with `[session_id]` prefix are never written
- This means line 888-906 in `execute_cycle()` NEVER runs

## Solution
Simplify threading model by:
1. Remove nested `execute_cycle()` function
2. Move all logic directly into `run_cycle()`
3. Make closure variables explicit
4. Add immediate database write as first action (before any slow operations)

## Implementation
See api_threading_fix.py for the complete fixed version.
