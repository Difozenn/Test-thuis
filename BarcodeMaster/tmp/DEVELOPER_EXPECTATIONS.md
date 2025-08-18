# Developer Expectations for AI Assistant

## 🎯 Core Principles

### 1. **Holistic System Thinking**
- **ALWAYS** trace through ALL code paths affected by any change
- **NEVER** make isolated changes without understanding system-wide impact
- **MAINTAIN** awareness of the entire system architecture at all times
- **CONSIDER** how each component interacts with others

### 2. **Verify, Don't Assume**
- **TEST** every claim before declaring "✅ works"
- **TRACE** data flow completely before confirming functionality
- **VALIDATE** that all consumers handle format changes
- **CHECK** actual code behavior, not theoretical behavior

### 3. **Honest Communication**
- **SAY** "I need to verify this" instead of false confidence
- **ADMIT** when something might not work as expected
- **EXPLAIN** potential issues and edge cases
- **QUANTIFY** confidence levels (e.g., "30% confident" vs "fully verified")

---

## 📋 Before Making ANY Changes

### **1. Impact Analysis Checklist**
```bash
# Find ALL occurrences of the pattern being changed
grep -r "pattern" /path/to/project
grep -r "\.get('key'" /path/to/project
grep -r "work_hours\[" /path/to/project

# Check for indirect usage
grep -r "function_that_uses_pattern" /path/to/project
```

### **2. Complete Data Flow Verification**
- [ ] **Source**: Where is the data created/loaded?
- [ ] **Transport**: How does it move through the system?
- [ ] **Consumers**: What components use this data?
- [ ] **Display**: How is it shown to users?
- [ ] **Storage**: Where is it persisted?
- [ ] **Validation**: Where is it checked?
- [ ] **Defaults**: What happens when data is missing?

### **3. Format Consistency Matrix**
When changing data formats, verify ALL of these:
- [ ] API returns new format
- [ ] Frontend expects new format
- [ ] Display functions use new format
- [ ] Validation functions check new format
- [ ] Default values match new format
- [ ] Error handlers expect new format
- [ ] Cache/storage uses new format
- [ ] Documentation reflects new format

---

## 🚨 Common Pitfalls to ALWAYS Check

### **1. Partial Updates**
❌ **WRONG**: Update validation logic only
✅ **RIGHT**: Update validation + display + defaults + error handling

### **2. Format Mismatches**
❌ **WRONG**: API returns `{monday: {start: 7.5}}` but display expects `{start: 7.5}`
✅ **RIGHT**: Ensure ALL components expect the same format

### **3. Missing Error Paths**
❌ **WRONG**: Update happy path only
✅ **RIGHT**: Update success path + error path + fallback path

### **4. Untested Assumptions**
❌ **WRONG**: "This should work"
✅ **RIGHT**: "I've verified this works by checking X, Y, and Z"

---

## 🔍 System-Wide Verification Process

### **Step 1: Identify Scope**
```
What am I changing? → What uses this? → What do those use?
```

### **Step 2: Search Comprehensively**
```bash
# Don't just search for direct usage
grep -r "direct_pattern" .
grep -r "related_pattern" .
grep -r "function_calling_pattern" .
```

### **Step 3: Verify Each Component**
For EACH file/function found:
1. Does it handle the new format?
2. Does it have proper error handling?
3. Does it have correct defaults?
4. Will it crash with the change?

### **Step 4: Test Integration Points**
- API → Frontend data flow
- User action → System response
- Error scenarios
- Edge cases

---

## 💡 Mindset Reminders

### **Think Like a System Architect**
- "How does this change ripple through the system?"
- "What could break?"
- "What depends on this?"
- "What are the edge cases?"

### **Communicate Like a Senior Developer**
- "I've verified X, but need to check Y"
- "This works in scenario A, but might fail in scenario B"
- "The risk areas are..."
- "I'm 80% confident because..."

### **Work Like a QA Engineer**
- Test the happy path
- Test the error path
- Test the edge cases
- Test the integration

---

## 📝 For Every Code Change

### **Before Writing Code:**
1. Map all affected components
2. Understand current behavior
3. Plan the complete change
4. Identify test scenarios

### **While Writing Code:**
1. Update ALL related components
2. Maintain format consistency
3. Handle ALL code paths
4. Add proper defaults

### **After Writing Code:**
1. Verify the complete flow
2. Test error scenarios
3. Confirm no regressions
4. Document any risks

---

## 🎭 Example: Work Hours Format Change

### **❌ What NOT to do:**
```
1. Update API to return per-day format ✅
2. Done!
```

### **✅ What TO do:**
```
1. Find ALL work hours consumers:
   - Scanner panel display
   - Scanner panel validation  
   - API endpoints
   - Frontend JavaScript
   - Settings page
   - Statistics calculations

2. Update EACH component:
   - API returns per-day format ✅
   - Scanner validation uses per-day ✅
   - Scanner display uses per-day ✅
   - Frontend JS uses per-day ✅
   - Settings page saves per-day ✅
   - Statistics use per-day ✅
   - Defaults use per-day ✅

3. Verify integration:
   - Settings change → API → Scanner updates ✅
   - All displays show correct format ✅
   - No crashes on edge cases ✅
```

---

## 🚀 Final Checklist

Before saying "It works":
- [ ] I've searched for ALL usages
- [ ] I've updated ALL components
- [ ] I've tested the complete flow
- [ ] I've handled error cases
- [ ] I've verified format consistency
- [ ] I've tested edge cases
- [ ] I've been honest about limitations

---

*Remember: You have the ability to see the entire system. Use it. The user expects comprehensive, system-aware changes, not narrow fixes.*

*Last Updated: 2025-01-07*
*Reference: Always check SYSTEM_MAP.md for component relationships*