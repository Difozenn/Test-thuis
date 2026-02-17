# Developer Expectations for AI Assistant - BarcodeMatch

*This file should be read at the start of every development session*

## 🎯 Core Principles (Same as BarcodeMaster)

### 1. **Holistic System Thinking**
- **ALWAYS** trace through ALL code paths affected by any change
- **NEVER** make isolated changes without understanding system-wide impact
- **MAINTAIN** awareness of the entire system architecture at all times
- **CONSIDER** integration with BarcodeMaster

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

## 🔗 BarcodeMatch-Specific Considerations

### **Integration Constraints**
1. **Session Types**: ONLY XLSX_UPDATED and MANUAL (never SCANNER)
2. **Work Hours**: ALWAYS inherit from BarcodeMaster (never override)
3. **API Dependency**: BarcodeMaster API must be running
4. **Data Format**: Must match BarcodeMaster's expected formats

### **Before ANY Change:**
Ask yourself:
- Does this change affect BarcodeMaster integration?
- Will this work with both session types (XLSX_UPDATED/MANUAL)?
- Does this respect BarcodeMaster's authority over work hours?
- Will this handle API connection failures gracefully?

---

## 📋 BarcodeMatch Change Checklist

### **1. Session Management Changes**
- [ ] Verify only XLSX_UPDATED/MANUAL types used
- [ ] Check BarcodeMaster API compatibility
- [ ] Test work hours validation still works
- [ ] Ensure proper error handling for API failures

### **2. UI Changes**
- [ ] Scanner panel reflects BarcodeMaster work hours
- [ ] Database panel right-click menu works
- [ ] Status displays match BarcodeMaster format
- [ ] Error states handled gracefully

### **3. Integration Changes**
- [ ] API endpoints match BarcodeMaster format
- [ ] Session data structure unchanged
- [ ] Work hours inheritance maintained
- [ ] User mapping still valid

---

## 🚨 BarcodeMatch-Specific Pitfalls

### **1. Session Type Violations**
❌ **WRONG**: Implementing SCANNER session support
✅ **RIGHT**: Reject any SCANNER session attempts

### **2. Work Hours Override**
❌ **WRONG**: Creating local work hours configuration
✅ **RIGHT**: Always fetch from BarcodeMaster API

### **3. Direct Database Access**
❌ **WRONG**: Accessing BarcodeMaster SQLite directly
✅ **RIGHT**: Always use BarcodeMaster API endpoints

### **4. Ignoring API State**
❌ **WRONG**: Assuming BarcodeMaster API is always available
✅ **RIGHT**: Graceful degradation when API is offline

---

## 🔍 Integration Verification Process

### **Before Making Changes:**
1. Check BarcodeMaster SYSTEM_MAP.md for API contracts
2. Verify data format compatibility
3. Test with BarcodeMaster running AND stopped
4. Ensure changes don't break existing integration

### **After Making Changes:**
1. Test complete workflow: BarcodeMaster → BarcodeMatch → BarcodeMaster
2. Verify session creation/completion cycle
3. Check work hours validation
4. Test error scenarios

---

## 💡 Remember

**BarcodeMatch is a DEPENDENT system:**
- It cannot function without BarcodeMaster
- It must respect BarcodeMaster's rules
- It inherits configurations, not creates them
- It's part of a larger workflow, not standalone

**When in doubt:**
- Check BarcodeMaster's implementation
- Maintain format compatibility
- Respect the integration boundaries
- Test the complete workflow

---

*Always reference both SYSTEM_MAP.md files when making changes*
*Last Updated: 2025-01-07*