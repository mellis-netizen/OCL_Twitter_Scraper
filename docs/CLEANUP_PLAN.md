# Repository Cleanup Plan

## 🗑️ Files Identified for Removal

### **Category 1: Legacy Files (Superseded by Optimized Versions)**

These files have been replaced by optimized versions and are no longer used:

1. **`src/main.py`** (1095 lines)
   - **Replaced by**: `src/main_optimized.py`
   - **Reason**: Legacy main script using old news_scraper.py and twitter_monitor.py
   - **Used by**: `tests/test_full_system.py` (also marked for removal), `docs/production/production_demo.py`
   - **Status**: ❌ REMOVE

2. **`src/news_scraper.py`** (19KB)
   - **Replaced by**: `src/news_scraper_optimized.py`
   - **Reason**: Legacy scraper without optimization features
   - **Used by**: `src/main.py` (marked for removal), `tests/test_full_system.py` (marked for removal)
   - **Status**: ❌ REMOVE

3. **`src/twitter_monitor.py`** (16KB)
   - **Replaced by**: `src/twitter_monitor_optimized.py`
   - **Reason**: Legacy Twitter monitor without optimizations
   - **Used by**: `src/main.py` (marked for removal), `tests/test_full_system.py` (marked for removal)
   - **Status**: ❌ REMOVE

---

### **Category 2: Outdated Test Files**

These test files reference legacy components:

4. **`tests/test_full_system.py`** (142 lines)
   - **Imports**: Legacy `src/main.py`, `src/news_scraper.py`, `src/twitter_monitor.py`
   - **Replaced by**: New comprehensive test suite in `tests/unit/`, `tests/integration/`, `tests/performance/`
   - **Status**: ❌ REMOVE

5. **`docs/production/production_demo.py`**
   - **Imports**: Legacy `main.py`
   - **Reason**: Demo file using outdated components
   - **Status**: ❌ REMOVE

---

### **Category 3: Duplicate/Specialized Files**

6. **`src/main_optimized_db.py`** (32KB)
   - **Purpose**: Database-specific version of main_optimized.py
   - **Reason**: Functionality merged into `main_optimized.py` with database support
   - **Note**: Review before removal - may have unique database features
   - **Status**: ⚠️ REVIEW FIRST, then remove if redundant

---

### **Category 4: Old Demo/Run Scripts**

7. **`tests/demo_enhanced_system.py`**
   - **Purpose**: Demo script for enhanced system
   - **Replaced by**: Comprehensive test suite and `main_optimized.py --mode test`
   - **Status**: ⚠️ KEEP if actively used for demos, otherwise remove

8. **`tests/run_enhanced_system.py`**
   - **Purpose**: Runner script
   - **Replaced by**: `main_optimized.py` with modes, `orchestrator.py`
   - **Status**: ⚠️ REVIEW - may have unique functionality

9. **`tests/run_tests.py`**
   - **Purpose**: Test runner
   - **Replaced by**: pytest configuration in `pytest.ini` and CI/CD workflow
   - **Status**: ⚠️ REVIEW - may be used by CI/CD

---

## 📊 Cleanup Summary

### Files to Remove Immediately (Safe)

| File | Size | Reason |
|------|------|--------|
| `src/main.py` | 47KB | Superseded by main_optimized.py |
| `src/news_scraper.py` | 19KB | Superseded by news_scraper_optimized.py |
| `src/twitter_monitor.py` | 16KB | Superseded by twitter_monitor_optimized.py |
| `tests/test_full_system.py` | 142 lines | Tests legacy components |
| `docs/production/production_demo.py` | Unknown | Uses legacy main.py |

**Total savings**: ~82KB+ of outdated code

### Files to Review Before Removal

| File | Reason for Review |
|------|-------------------|
| `src/main_optimized_db.py` | May have unique database features |
| `tests/demo_enhanced_system.py` | May be used for demos |
| `tests/run_enhanced_system.py` | May have unique functionality |
| `tests/run_tests.py` | May be used by CI/CD |

---

## 🎯 Recommended Action Plan

### Phase 1: Safe Removal (Low Risk)
Remove files that are clearly superseded and not used:
```bash
rm src/main.py
rm src/news_scraper.py
rm src/twitter_monitor.py
rm tests/test_full_system.py
rm docs/production/production_demo.py
```

### Phase 2: Review and Decision (Medium Risk)
Review these files for unique functionality:
1. Compare `src/main_optimized_db.py` with `src/main_optimized.py`
2. Check if demo scripts are referenced in documentation
3. Verify test runners aren't used by CI/CD

### Phase 3: Update References
After removal, verify no broken imports:
```bash
grep -r "from main import\|import main" . --include="*.py" --exclude-dir=__pycache__
grep -r "from news_scraper import\|import news_scraper" . --include="*.py" --exclude-dir=__pycache__
grep -r "from twitter_monitor import\|import twitter_monitor" . --include="*.py" --exclude-dir=__pycache__
```

---

## ✅ Benefits of Cleanup

1. **Reduced Confusion**: Developers won't accidentally use legacy code
2. **Clearer Architecture**: Only optimized, integrated versions remain
3. **Easier Maintenance**: Fewer files to maintain and update
4. **Smaller Repository**: ~100KB+ reduction in code size
5. **Better CI/CD**: Faster test runs without legacy code

---

## 🚨 Important Notes

**Before removing any file:**
1. ✅ Verify no active imports in current codebase
2. ✅ Check if referenced in documentation
3. ✅ Backup or commit to git (for easy recovery)
4. ✅ Run full test suite after removal
5. ✅ Update any CI/CD pipelines

**Git Safety:**
All removed files are preserved in git history. You can always recover them if needed:
```bash
git log --all --full-history -- path/to/file.py
git checkout <commit-hash> -- path/to/file.py
```

---

**Cleanup Status**: ⏳ PENDING USER APPROVAL
**Created**: 2025-10-11
**Last Updated**: 2025-10-11
