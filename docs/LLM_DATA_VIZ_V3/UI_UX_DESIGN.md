# UI/UX Design Mockups

## Design Principles
1. **Fast & Responsive** - Every action should feel instant
2. **Minimal Clicks** - Common tasks in 1-2 clicks
3. **Visual Feedback** - Always show what's happening
4. **Keyboard Friendly** - Shortcuts for power users (me)
5. **Clean but Dense** - Show lots of info without clutter

## Overall Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│ 📊 Data Investigation Platform           [Project: sales_analysis ▼] │
├───────────────────────────┬─────────────────────────────────────────┤
│                           │                                         │
│     SIDEBAR (250px)       │            MAIN CANVAS                  │
│                           │                                         │
│  [🔄 Refresh] [➕ New]     │    ┌─────────────────────────────┐     │
│                           │    │                             │     │
│  📁 Data Files            │    │      (Content Area)        │     │
│  ├─ sales.csv (10k)       │    │                             │     │
│  ├─ customers.parquet (5k)│    │                             │     │
│  └─ products.csv (500)    │    └─────────────────────────────┘     │
│                           │                                         │
│  🔗 Relationships         │    ┌─────────────────────────────┐     │
│  • sales → customers      │    │     Query Bar / Tabs        │     │
│  • sales → products       │    └─────────────────────────────┘     │
│                           │                                         │
│  📊 Quick Actions         │                                         │
│  [Profile All]            │                                         │
│  [Find Patterns]          │                                         │
│  [Export Session]         │                                         │
│                           │                                         │
├───────────────────────────┴─────────────────────────────────────────┤
│ Status: Ready | Queries: 15 | Session: 2h 15m | Memory: 245 MB     │
└─────────────────────────────────────────────────────────────────────┘
```

## Component Designs

### 1. Project Selector (Top Bar)
```
┌──────────────────────────────────────────────────────┐
│ Current Project: [sales_analysis ▼]  [➕ New] [⚙️]   │
│                  ├─ sales_analysis                   │
│                  ├─ customer_churn                   │
│                  ├─ product_performance              │
│                  └─ [+ Create New Project]           │
└──────────────────────────────────────────────────────┘
```

### 2. Data File Panel (Sidebar)
```
┌─────────────────────────┐
│ 📁 Data Files           │
│ ┌─────────────────────┐ │
│ │ Drag files here     │ │
│ │   or click to       │ │
│ │     browse          │ │
│ └─────────────────────┘ │
│                         │
│ ▼ sales.csv            │
│   10,000 rows × 8 cols │
│   [👁️] [📊] [🗑️]       │
│                         │
│ ▼ customers.parquet    │
│   5,000 rows × 12 cols │
│   [👁️] [📊] [🗑️]       │
└─────────────────────────┘

[👁️] = Preview data
[📊] = Show profile  
[🗑️] = Remove file
```

### 3. Data Profile Card (Modal/Overlay)
```
┌────────────────────────────────────────────────┐
│ 📊 Data Profile: sales.csv                [✕] │
├────────────────────────────────────────────────┤
│ Overview:                                      │
│ • 10,000 rows × 8 columns                     │
│ • 125 KB file size                            │
│ • Loaded 2 minutes ago                        │
│                                                │
│ Columns:                                       │
│ ┌──────────────┬────────┬──────┬────────────┐│
│ │ Column       │ Type   │ Null │ Unique     ││
│ ├──────────────┼────────┼──────┼────────────┤│
│ │ order_id     │ INT    │ 0%   │ 10,000     ││
│ │ customer_id  │ INT    │ 0%   │ 2,341      ││
│ │ amount       │ FLOAT  │ 2%   │ 8,234      ││
│ │ order_date   │ DATE   │ 0%   │ 365        ││
│ └──────────────┴────────┴──────┴────────────┘│
│                                                │
│ Insights:                                      │
│ ⚠️ 2% null values in amount column            │
│ 📈 Strong weekly seasonality detected         │
│ 🔍 customer_id could join with customers.id   │
│                                                │
│ [Explore Data] [Clean Data] [Close]           │
└────────────────────────────────────────────────┘
```

### 4. Main Query Interface (Tab: Query)
```
┌─────────────────────────────────────────────────┐
│ Tabs: [Query] [Visualize] [History] [Export]   │
├─────────────────────────────────────────────────┤
│                                                 │
│ 💭 Ask in plain English:                       │
│ ┌─────────────────────────────────────────────┐│
│ │ Show me total sales by month for top 10    ││
│ │ customers                                   ││
│ └─────────────────────────────────────────────┘│
│ [Generate SQL ⚡] [Clear]  ☑️ Show thinking    │
│                                                 │
│ 📝 Generated SQL:                              │
│ ┌─────────────────────────────────────────────┐│
│ │ WITH top_customers AS (                     ││
│ │   SELECT customer_id,                       ││
│ │          SUM(amount) as total               ││
│ │   FROM sales                                ││
│ │   GROUP BY customer_id                      ││
│ │   ORDER BY total DESC                       ││
│ │   LIMIT 10                                  ││
│ │ )                                           ││
│ │ SELECT DATE_TRUNC('month', s.order_date),   ││
│ │        s.customer_id,                       ││
│ │        SUM(s.amount) as monthly_sales       ││
│ │ FROM sales s                                ││
│ │ JOIN top_customers tc ON...                 ││
│ └─────────────────────────────────────────────┘│
│ [▶️ Run] [📋 Copy] [💾 Save]   Confidence: 85% │
│                                                 │
│ Results (250 rows):                            │
│ ┌─────────────────────────────────────────────┐│
│ │ month      │ customer_id │ monthly_sales   ││
│ ├────────────┼─────────────┼─────────────────┤│
│ │ 2024-01    │ C1234      │ $12,450         ││
│ │ 2024-01    │ C5678      │ $10,230         ││
│ │ ...        │ ...        │ ...             ││
│ └─────────────────────────────────────────────┘│
│ [📊 Visualize] [⬇️ Export CSV]                 │
└─────────────────────────────────────────────────┘
```

### 5. Visualization Tab
```
┌─────────────────────────────────────────────────┐
│ Tabs: [Query] [Visualize] [History] [Export]   │
├─────────────────────────────────────────────────┤
│                                                 │
│ Chart Type: [Auto ▼] [Line|Bar|Scatter|Map]    │
│                                                 │
│ ┌─────────────────────────────────────────────┐│
│ │                                             ││
│ │         Monthly Sales Trend                 ││
│ │     ═══════════════════════════            ││
│ │ $50k ┤                      ╱╲              ││
│ │      │                    ╱    ╲            ││
│ │ $40k ┤                  ╱      ╲           ││
│ │      │                ╱          ╲         ││
│ │ $30k ┤              ╱              ╲       ││
│ │      │            ╱                  ╲     ││
│ │ $20k ┤        ╱                        ╲   ││
│ │      │    ╱                              ╲ ││
│ │ $10k ┤╱                                    ││
│ │      └────┬────┬────┬────┬────┬────┬────┤││
│ │        Jan  Feb  Mar  Apr  May  Jun  Jul  ││
│ │                                             ││
│ │ [🔍 Zoom] [📷 Export] [⚙️ Settings]        ││
│ └─────────────────────────────────────────────┘│
│                                                 │
│ Quick Insights:                                │
│ • 📈 23% growth trend over period              │
│ • 🔴 Significant dip in April (-15%)          │
│ • ⭐ Best month: June ($48,234)                │
└─────────────────────────────────────────────────┘
```

### 6. Query History Tab
```
┌─────────────────────────────────────────────────┐
│ Tabs: [Query] [Visualize] [History] [Export]   │
├─────────────────────────────────────────────────┤
│                                                 │
│ 🕐 Query History          [🔍 Search] [🏷️ Filter]│
│                                                 │
│ Today                                          │
│ ├─ 2:45 PM - Top customers by revenue         │
│ │  SELECT customer_id, SUM(amount)...         │
│ │  [Run] [Edit] [📊]                          │
│ │                                              │
│ ├─ 2:30 PM - Monthly sales trend              │
│ │  WITH monthly_sales AS (SELECT...           │
│ │  [Run] [Edit] [📊]                          │
│ │                                              │
│ Yesterday                                      │
│ ├─ 5:15 PM - Product performance analysis     │
│ │  SELECT p.product_name, COUNT(*)...         │
│ │  [Run] [Edit] [📊]                          │
│ │                                              │
│ Sessions                                       │
│ ├─ 📁 Customer Churn Investigation (15 queries)│
│ ├─ 📁 Q4 Revenue Analysis (23 queries)        │
│ └─ 📁 Product Launch Review (8 queries)       │
│                                                 │
│ [Save Session] [Load Session] [Clear History]  │
└─────────────────────────────────────────────────┘
```

### 7. Export Tab
```
┌─────────────────────────────────────────────────┐
│ Tabs: [Query] [Visualize] [History] [Export]   │
├─────────────────────────────────────────────────┤
│                                                 │
│ 📤 Export Options                              │
│                                                 │
│ ┌───────────────────────────────────────────┐ │
│ │ 📄 HTML Report                            │ │
│ │ Self-contained interactive report         │ │
│ │ ☑️ Include data                           │ │
│ │ ☑️ Include visualizations                 │ │
│ │ ☑️ Include query history                  │ │
│ │ [Generate HTML]                           │ │
│ └───────────────────────────────────────────┘ │
│                                                 │
│ ┌───────────────────────────────────────────┐ │
│ │ 📓 Jupyter Notebook                       │ │
│ │ Reproducible analysis with code           │ │
│ │ ☑️ Include markdown explanations          │ │
│ │ ☑️ Add data loading code                  │ │
│ │ [Export Notebook]                         │ │
│ └───────────────────────────────────────────┘ │
│                                                 │
│ ┌───────────────────────────────────────────┐ │
│ │ 📊 Raw Data                               │ │
│ │ Export query results                      │ │
│ │ Format: [CSV ▼] [Parquet|JSON|Excel]      │ │
│ │ [Export Data]                             │ │
│ └───────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

### 8. Quick Actions & Shortcuts

```
Keyboard Shortcuts:
─────────────────────
Cmd+N    - New project
Cmd+O    - Open project  
Cmd+S    - Save session
Cmd+Enter - Run query
Cmd+K    - Quick search
Cmd+E    - Export
Cmd+/    - Show shortcuts

Right-Click Context Menus:
──────────────────────────
On Table Name:
├─ Preview Data
├─ Show Profile
├─ Query This Table
└─ Remove

On Column Name:
├─ Show Distribution
├─ Find Patterns
├─ Check for Nulls
└─ Suggest Cleaning

On Query Result:
├─ Visualize
├─ Export as CSV
├─ Save Query
└─ Copy to Clipboard
```

## Mobile Responsive? 
**No.** This is a desktop tool for data analysis. Trying to do this on a phone would be painful.

## Dark Mode?
**Maybe later.** Start with a clean light theme. Dark mode can be a user preference saved in project settings.

## Interactive Elements

### Drag & Drop
- Files into sidebar → Auto-load
- Columns into query builder → Generate SQL
- Charts to rearrange dashboard

### Hover States
- Table names → Show row count
- Column names → Show data type and nulls
- Query history → Show first few rows of results

### Loading States
```
Query Running:
[████████░░░░░░░] 52% | Estimated: 3s

File Loading:
⏳ Processing customers.csv... (2.3 MB)

Profile Generating:
🔍 Analyzing data patterns...
```

### Error States
```
┌─────────────────────────────────────┐
│ ⚠️ Query Error                      │
│                                     │
│ Column 'sale_date' not found.      │
│ Did you mean 'order_date'?         │
│                                     │
│ [Try Suggestion] [Edit Query]       │
└─────────────────────────────────────┘
```

## Color Scheme (Simple)

```css
/* Keep it minimal and readable */
--primary: #2563eb;      /* Blue for actions */
--success: #10b981;      /* Green for success */
--warning: #f59e0b;      /* Orange for warnings */
--danger: #ef4444;       /* Red for errors */
--text: #1f2937;         /* Dark gray for text */
--bg: #ffffff;           /* White background */
--border: #e5e7eb;       /* Light gray borders */
--hover: #f3f4f6;        /* Light gray hover */
```

## Implementation Priority

### Must Have (MVP)
1. ✅ Project selector
2. ✅ File drag & drop
3. ✅ Query interface
4. ✅ Results table
5. ✅ Basic export

### Should Have
6. ⭕ Visualization tab
7. ⭕ Query history
8. ⭕ Data profiling modal

### Nice to Have
9. ○ Keyboard shortcuts
10. ○ Right-click menus
11. ○ Advanced visualizations
12. ○ Session management

## Design Decisions

### Why Streamlit?
- Already using it
- Fast to build
- Handles reactivity well
- Good enough for personal tool

### Why Not React/Vue?
- Overkill for personal project
- More complexity to maintain
- Streamlit can do everything needed

### Future UI Considerations
If I use this daily and want more:
- Consider Gradio for better components
- Maybe FastAPI + HTMX for more control
- Electron app for true desktop experience
- But probably not - Streamlit is fine