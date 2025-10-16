# Testing Checklist - User Configuration Bug Fix

## ✅ Pre-Testing Verification

Before testing, verify the database contains users:
```
Database path: C:\Users\Administrator\Desktop\Test-thuis-main\BarcodeMaster\dist\database\central_logging.sqlite
Expected users: NESTING, ACCURA, OPUS, KL GANNOMAT, GR GANNOMAT, HANDWERK, BOERE
```

## 🔧 Test 1: Admin Panel - View Existing Users

**Steps:**
1. Launch the application
2. Navigate to Admin Panel
3. Click on "Gebruiker Configuratie" tab

**Expected Result:**
- ✅ All 7 users should be visible in the list
- ✅ Each user should show their processing type
- ✅ Each user should show their active status
- ✅ Each user should show their import path (if configured)

**Status:** [ ] Pass [ ] Fail

---

## ➕ Test 2: Admin Panel - Add New User

**Steps:**
1. In the "Gebruiker Configuratie" tab
2. Scroll to "Nieuwe Gebruiker Toevoegen" section
3. Enter username: `TEST_USER`
4. Select processing type: `GEEN_PROCESSING`
5. Click "Toevoegen" button

**Expected Result:**
- ✅ User appears immediately in the list above
- ✅ No need to restart or refresh
- ✅ User shows with correct processing type
- ✅ User is marked as active by default

**Status:** [ ] Pass [ ] Fail

---

## 🗑️ Test 3: Admin Panel - Remove User

**Steps:**
1. Find the TEST_USER you just added
2. Click the "Verwijderen" button next to it
3. Confirm the deletion

**Expected Result:**
- ✅ User disappears from the list immediately
- ✅ No error messages

**Status:** [ ] Pass [ ] Fail

---

## 📝 Test 4: Scanner Panel - Manual Entry Dialog

**Steps:**
1. Navigate to Scanner Panel
2. Click the green "Handmatige Invoer" button

**Expected Result:**
- ✅ Dialog opens with title "Handmatige Project Invoer"
- ✅ "Items per Gebruiker" section shows all configured users
- ✅ Each user has input fields for items
- ✅ NESTING shows: Nesting + Opdeelzaag fields
- ✅ ACCURA shows: Items + Sides fields
- ✅ Other users show: single Items field

**Status:** [ ] Pass [ ] Fail

---

## 🔄 Test 5: Consistency Check

**Steps:**
1. Go to Admin Panel → Gebruiker Configuratie
2. Note the list of users and their order
3. Go to Scanner Panel → Click "Handmatige Invoer"
4. Compare the users shown in the dialog

**Expected Result:**
- ✅ Same users appear in both places
- ✅ Same order (if applicable)
- ✅ Same processing types

**Status:** [ ] Pass [ ] Fail

---

## 🔌 Test 6: API Fallback (Optional)

**Steps:**
1. Stop the database API server
2. Try to open Admin Panel → Gebruiker Configuratie
3. Try to open Scanner Panel → Handmatige Invoer

**Expected Result:**
- ✅ Application doesn't crash
- ✅ Falls back to config.json file
- ✅ May show outdated data, but remains functional

**Status:** [ ] Pass [ ] Fail [ ] Skipped

---

## 📊 Test Summary

| Test | Status | Notes |
|------|--------|-------|
| View Existing Users | [ ] | |
| Add New User | [ ] | |
| Remove User | [ ] | |
| Manual Entry Dialog | [ ] | |
| Consistency Check | [ ] | |
| API Fallback | [ ] | |

---

## 🐛 Issues Found

If any tests fail, document here:

1. **Test Name:**
   - **Issue:**
   - **Steps to Reproduce:**
   - **Expected:**
   - **Actual:**

---

## ✅ Sign-Off

- **Tested By:** _________________
- **Date:** _________________
- **All Tests Passed:** [ ] Yes [ ] No
- **Ready for Production:** [ ] Yes [ ] No
