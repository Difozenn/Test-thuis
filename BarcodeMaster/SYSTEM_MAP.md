# Project Datalog System Interconnection Map

## 🧠 **Core System Overview**
Project Datalog is a barcode management system with client-server architecture featuring real-time session tracking, workflow management, and comprehensive analytics.

---

## 🕒 **Work Hours Logic System**

### **Core Configuration**
- **Location**: `database/db_log_api.py:55-64` (WORK_HOURS global variable)
- **Format**: Per-day start/end times + break times + work_days array
```python
WORK_HOURS = {
    'monday': {'start': 7.5, 'end': 16},      # 07:30-16:00
    'tuesday': {'start': 7.5, 'end': 16},     # 07:30-16:00
    'wednesday': {'start': 7.5, 'end': 16},   # 07:30-16:00
    'thursday': {'start': 7.5, 'end': 16},    # 07:30-16:00
    'friday': {'start': 7.5, 'end': 15},      # 07:30-15:00
    'break_start': 12,    # 12:00
    'break_end': 12.5,    # 12:30
    'work_days': [0, 1, 2, 3, 4]  # Monday to Friday
}
```

### **🔗 Direct Dependencies**

#### **1. Session Validation**
- **Function**: `get_current_work_status()` (`db_log_api.py:119-144`)
- **Connected Features**:
  - Scanner panel session start validation
  - BarcodeMatch session validation
  - Real-time work status display
  - Session creation API endpoints

#### **2. Work Time Calculations**
- **Function**: `calculate_work_minutes()` (`db_log_api.py:66-117`)
- **Connected Features**:
  - Session duration calculations in database
  - Idle time analysis between user handoffs
  - Project total work time calculations
  - All statistics API endpoints

#### **3. Frontend Work Time Logic**
- **Scanner Panel**: `gui/panels/scanner_panel.py:379-410`
  - 30-second cache refresh from API
  - Work status validation before operations
  - Dynamic end time display per current day
- **Project Logs**: `database/templates/logs_project.html:1297-1372`
  - JavaScript `calculateWorkMinutes()` function
  - Real-time work time calculations in timeline

#### **4. Settings Interface**
- **Location**: `database/templates/settings.html`
- **API**: `GET/POST /api/settings/work-hours`
- **Features**:
  - Per-day time configuration interface
  - Real-time hours calculation and validation
  - Live summary dashboard updates

---

## 🔄 **Session Management System**

### **Core Session Types**
1. **SCANNER**: BarcodeMASTER main user (always starts workflow chain)
2. **XLSX_UPDATED**: Auto-triggered for secondary users when files generated
3. **MANUAL**: Right-click menu sessions in BarcodeMatch

### **🔗 Session Dependencies**

#### **1. Workflow Chain Logic**
- **Trigger Point**: SCANNER session start → triggers OPEN events for configured users
- **User Order**: Defined in `config.json:scanner_panel_open_event_users`
- **Chain Rules**:
  - SCANNER session always starts the chain
  - Other users follow configured order
  - Project start time = first SCANNER session timestamp

#### **2. Database Schema**
- **Primary Table**: `sessions` (session_id, user, start_time, end_time, session_type, status, work_duration_minutes)
- **Supporting Tables**: `logs`, `project_sessions`
- **Critical Fields**: `work_duration_minutes` (calculated using work hours logic)

#### **3. API Endpoints**
- **Session Management**:
  - `POST /session/start` - Start new session with work time validation
  - `POST /session/end` - End session with work time calculation
  - `POST /session/xlsx_updated` - Auto-trigger for secondary users
- **Statistics APIs** (all use session work_duration_minutes):
  - `/api/statistics/productivity-metrics`
  - `/api/statistics/user-efficiency`
  - `/api/statistics/bottleneck-analysis`
  - `/api/statistics/time-insights`
  - `/api/statistics/workflow-efficiency`

---

## 🎯 **Frontend System**

### **🎨 Design System Dependencies**
- **Base Template**: `database/templates/base.html`
  - CSS Variables: `--primary-blue`, `--secondary-blue`, `--dark-blue`
  - Navigation structure and layout patterns
- **Consistent Styling Classes**:
  - `.enterprise-card` - Main container cards
  - `.enterprise-grid` - Grid layouts
  - `.metric-header`, `.metric-content` - Dashboard elements
  - `.status-badge` - Status indicators
  - `.btn-primary`, `.btn-secondary` - Button styling

### **🔗 Page Dependencies**

#### **1. Dashboard** (`/dashboard`)
- **Data Sources**: User stats, project metrics, workflow status
- **Real-time Updates**: Project status, session tracking
- **Dependencies**: Session data, work hours for time calculations

#### **2. Project Logs** (`/logs/<project>`)
- **Core Logic**: `logs_project.html:1000-1400` (JavaScript calculations)
- **Dependencies**: 
  - Session data for work time calculations
  - Work hours configuration for accurate timeline
  - User configuration for workflow display

#### **3. Statistics** (`/statistics`)
- **Data Sources**: All statistics API endpoints
- **Dependencies**: Session work_duration_minutes, user efficiency calculations

#### **4. Settings** (`/settings`)
- **Sections**: Work hours configuration (expandable for future settings)
- **Dependencies**: Work hours API, real-time validation

---

## ⚙️ **Configuration System**

### **🔗 Configuration Dependencies**

#### **1. Main Configuration** (`config.json`)
```json
{
    "user": "NESTING",
    "scanner_panel_open_event_users": ["NESTING", "OPUS", "KL GANNOMAT"],
    "scanner_user_to_processing_type_map": {
        "OPUS": "HOPS_PROCESSING",
        "KL GANNOMAT": "MDB_PROCESSING"
    },
    "dashboard_display_users": ["NESTING", "OPUS", "KL GANNOMAT"]
}
```

#### **2. Configuration Impact Areas**
- **User Order Changes**: Affects workflow chain, statistics grouping, dashboard display
- **Processing Type Changes**: Affects session categorization, file path mappings
- **Display Changes**: Affects dashboard user cards, statistics filtering

---

## 🏗️ **Architecture Components**

### **🔗 Core Applications**

#### **1. Project Datalog Main Application**
- **Location**: `gui/app.py` (main GUI application)
- **Panels**: Scanner panel, admin panel, settings panel
- **Session Type**: SCANNER (always starts workflow)
- **Dependencies**: Config file, database API, work hours validation

#### **2. Database API Server**
- **Location**: `database/db_log_api.py`
- **Port**: 5001 (configurable)
- **Features**: Session management, statistics, work hours API
- **Dependencies**: SQLite database, work hours configuration

#### **3. Background Services**
- **Import Service**: `services/background_import_service.py`
- **File Monitoring**: Watches for _updated XLSX files
- **Auto-triggers**: XLSX_UPDATED sessions for secondary users

---

## ⚠️ **Critical Change Impact Matrix**

### **When Changing Work Hours Logic:**
1. ✅ **Session Validation**: Update `get_current_work_status()`
2. ✅ **Statistics Calculations**: Verify all `/api/statistics/*` endpoints
3. ✅ **Frontend Calculations**: Update JavaScript `calculateWorkMinutes()`
4. ✅ **Settings Interface**: Ensure proper loading/saving
5. ✅ **Scanner Panel Cache**: 30-second refresh picks up changes
6. ✅ **Database Calculations**: All `work_duration_minutes` calculations

### **⚡ VERIFICATION CHECKLIST - Work Hours Format Changes:**
When changing data format (e.g., single start/end → per-day start/end):

**1. Find ALL consumers of the data:**
```bash
grep -r "work_hours\[" /path/to/project  # Find direct access
grep -r "\.get('start'" /path/to/project  # Find dictionary access
```

**2. Update ALL of these locations:**
- [ ] Validation functions (`_check_work_status`)
- [ ] Display functions (`_update_work_hours_display`)
- [ ] Default/fallback values
- [ ] API response handlers
- [ ] Error handling branches
- [ ] Test data and mocks

**3. Verify format consistency:**
- [ ] API returns new format
- [ ] Frontend expects new format
- [ ] Cache stores new format
- [ ] Defaults use new format
- [ ] Display logic uses new format

**4. Test the complete flow:**
- [ ] Normal operation (happy path)
- [ ] API failure (fallback to defaults)
- [ ] Cache refresh after settings change
- [ ] Display updates correctly
- [ ] No crashes on format mismatch

### **When Changing Session Types:**
1. ✅ **Workflow Chain**: Update triggering logic
2. ✅ **Project Start Time**: Verify SCANNER session logic
3. ✅ **User Sequence**: Check configuration order
4. ✅ **Statistics Grouping**: Update filtering and categorization
5. ✅ **BarcodeMatch Compatibility**: XLSX_UPDATED and MANUAL only

### **When Changing User Configuration:**
1. ✅ **Chain Order**: Update workflow sequence
2. ✅ **OPEN Event Triggering**: Verify configured users
3. ✅ **Processing Type Mappings**: Update file path logic
4. ✅ **Dashboard Display**: Update user cards and statistics
5. ✅ **Path Configurations**: Verify user-specific directories

### **When Changing Design System:**
1. ✅ **CSS Variables**: Update across all templates
2. ✅ **Component Classes**: Maintain consistency across pages
3. ✅ **Form Styling**: Keep inputs and buttons uniform
4. ✅ **Layout Patterns**: Use established grid and card systems
5. ✅ **Navigation**: Maintain base template structure

---

## 🔍 **Testing Scenarios**

### **Work Hours Testing:**
1. **Different Days**: Test Monday-Thursday vs Friday schedules
2. **Break Time**: Verify 12:00-12:30 exclusion in calculations
3. **Weekend**: Confirm no work allowed on Saturday/Sunday
4. **Time Boundaries**: Test before/after work hours validation

### **Session Flow Testing:**
1. **SCANNER Start**: Verify triggers OPEN events for others
2. **User Sequence**: Test configured order is followed
3. **XLSX_UPDATED**: Verify auto-triggering from file generation
4. **MANUAL**: Test right-click menu functionality

### **Statistics Accuracy:**
1. **Work Duration**: Verify excludes breaks and non-work hours
2. **Idle Time**: Check gaps between user handoffs
3. **Project Timeline**: Ensure SCANNER start = project start
4. **User Efficiency**: Validate items/hour calculations

---

## 📝 **Development Guidelines**

### **Before Making Changes:**
1. **Check This Map**: Identify all connected features
2. **Review Dependencies**: Understand impact areas
3. **Plan Testing**: Cover all affected components
4. **Maintain Consistency**: Follow design and logic patterns

### **After Making Changes:**
1. **Update This Map**: Document new dependencies
2. **Test All Connections**: Verify no regressions
3. **Update Documentation**: Keep system knowledge current
4. **Validate Consistency**: Ensure design and behavior alignment

---

*Last Updated: 2025-01-07*
*Next Review: When adding new features or making architectural changes*