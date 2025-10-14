# Progress Bar Fix

## Problem
The progress bar stays at 0% even though the API is being called and responding.

## Root Cause
SQLAlchemy doesn't automatically detect changes to nested JSON fields. When updating `performance_metrics['phase']`, SQLAlchemy doesn't know the JSON object changed and doesn't persist it to the database.

## Solution
Use `flag_modified()` to explicitly tell SQLAlchemy that the JSON field changed:

```python
from sqlalchemy.orm.attributes import flag_modified

# Update the JSON field
session.performance_metrics = updated_dict

# CRITICAL: Mark as modified
flag_modified(session, 'performance_metrics')

# Now commit will persist the change
db_session.commit()
```

## Files Fixed
1. `src/main_optimized.py:559-567` - Added flag_modified to _update_progress
2. `src/api.py:896-903` - Added flag_modified to initial progress
3. `src/api.py:943-954` - Added flag_modified to completion metrics

## Testing
```bash
# Start backend
cd src && python -m uvicorn api:app --reload

# Click "Start Scraping Cycle" in frontend
# Progress bar should now update in real-time!
```

## Expected Behavior
- Progress starts at 5% (initializing)
- Moves to 15% (scraping news)
- Updates through 11 phases
- Reaches 100% (completed)
