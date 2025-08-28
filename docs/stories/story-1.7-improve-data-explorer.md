# Story 1.7: Improve Data Explorer Tab

**Status**: ✅ READY FOR DEVELOPMENT  
**Epic**: Epic 1 - System Optimization  
**Priority**: LOW  
**Estimated Points**: 5  

## User Story

**As a** user exploring datasets,  
**I want** an intuitive data exploration interface,  
**So that** I can quickly understand table contents and relationships.

## Background & Context

The Data Explorer tab currently provides basic table viewing capabilities but lacks advanced filtering, search, and relationship visualization features. Users need better tools to understand data structure, quality, and relationships without writing SQL.

## Acceptance Criteria

- [ ] Advanced filtering UI supports multiple conditions
- [ ] Column-level search and filtering works efficiently
- [ ] Data export available in CSV, Excel, JSON formats
- [ ] Table relationship visualizer shows foreign keys
- [ ] Pagination handles large tables smoothly
- [ ] Column statistics display inline
- [ ] Data preview updates dynamically

## Technical Tasks

### 1. Build Advanced Filtering UI
- [ ] Design multi-condition filter interface
- [ ] Implement filter builder with AND/OR logic
- [ ] Add support for different operators:
  - [ ] Equals, not equals
  - [ ] Contains, starts with, ends with
  - [ ] Greater than, less than, between
  - [ ] In list, not in list
  - [ ] Is null, is not null
  - [ ] Regular expression matching
- [ ] Create filter templates for common patterns
- [ ] Add filter save/load functionality
- [ ] Implement filter history
- [ ] Add clear all filters option

### 2. Implement Column-Level Search
- [ ] Add search box per column header
- [ ] Implement type-aware search:
  - [ ] Text: fuzzy matching, case sensitivity options
  - [ ] Numeric: range search, threshold search
  - [ ] Date: date range picker, relative dates
  - [ ] Boolean: checkbox filter
- [ ] Add search highlighting in results
- [ ] Implement search suggestions
- [ ] Create column value autocomplete
- [ ] Add search performance indicators

### 3. Create Data Export System
- [ ] Add export button with format selection
- [ ] Implement CSV export with options:
  - [ ] Delimiter selection
  - [ ] Quote character options
  - [ ] Header inclusion toggle
- [ ] Add Excel export with formatting:
  - [ ] Multiple sheets support
  - [ ] Cell formatting preservation
  - [ ] Formula support
- [ ] Implement JSON export options:
  - [ ] Array vs object format
  - [ ] Pretty print option
  - [ ] Nested structure support
- [ ] Add filtered vs full data export choice
- [ ] Implement background export for large datasets

### 4. Build Table Relationship Visualizer
- [ ] Create ERD-style relationship diagram
- [ ] Detect foreign key relationships
- [ ] Implement interactive graph visualization:
  - [ ] Zoom and pan controls
  - [ ] Node clustering for complex schemas
  - [ ] Edge labels with cardinality
- [ ] Add relationship details panel
- [ ] Implement navigation from diagram to data
- [ ] Create relationship validation tool
- [ ] Add export diagram functionality

### 5. Implement Smart Pagination
- [ ] Create pagination controls with page size options
- [ ] Implement server-side pagination for large tables
- [ ] Add jump to page functionality
- [ ] Create infinite scroll option
- [ ] Implement virtual scrolling for performance
- [ ] Add row number display
- [ ] Create keyboard navigation support

### 6. Add Inline Column Statistics
- [ ] Display statistics in column headers:
  - [ ] Data type indicator
  - [ ] Null percentage
  - [ ] Unique value count
  - [ ] Min/max for numeric columns
  - [ ] Most frequent value
- [ ] Add expandable statistics panel
- [ ] Create mini visualizations (sparklines)
- [ ] Implement column profiling on demand
- [ ] Add data quality indicators

## Integration Verification

- [ ] **IV1**: Existing table display functionality preserved
- [ ] **IV2**: DuckDB query generation remains compatible
- [ ] **IV3**: Performance acceptable for large datasets
- [ ] **IV4**: Export formats compatible with common tools
- [ ] **IV5**: Filter state persists across sessions

## Technical Implementation Notes

### Advanced Filter Builder Architecture

```python
class AdvancedFilterBuilder:
    def __init__(self):
        self.filters = []
        self.logical_operator = 'AND'  # AND or OR
    
    def add_filter(self, column, operator, value):
        filter_obj = {
            'column': column,
            'operator': operator,
            'value': value,
            'data_type': self.get_column_type(column)
        }
        self.filters.append(filter_obj)
    
    def to_sql_where_clause(self):
        conditions = []
        for f in self.filters:
            condition = self._build_condition(f)
            conditions.append(condition)
        
        return f" {self.logical_operator} ".join(conditions)
    
    def _build_condition(self, filter_obj):
        column = filter_obj['column']
        operator = filter_obj['operator']
        value = filter_obj['value']
        
        operator_map = {
            'equals': '=',
            'not_equals': '!=',
            'contains': 'LIKE',
            'greater_than': '>',
            'less_than': '<',
            'between': 'BETWEEN',
            'in': 'IN',
            'is_null': 'IS NULL',
            'regex': '~'
        }
        
        # Build SQL condition based on operator
        if operator == 'contains':
            return f"{column} LIKE '%{value}%'"
        elif operator == 'between':
            return f"{column} BETWEEN {value[0]} AND {value[1]}"
        elif operator == 'in':
            values = ', '.join([f"'{v}'" for v in value])
            return f"{column} IN ({values})"
        elif operator == 'is_null':
            return f"{column} IS NULL"
        else:
            sql_op = operator_map.get(operator, '=')
            return f"{column} {sql_op} '{value}'"
```

### Table Relationship Visualization

```python
class RelationshipVisualizer:
    def generate_erd(self, schema):
        graph = {
            'nodes': [],
            'edges': []
        }
        
        # Create nodes for tables
        for table in schema.tables:
            node = {
                'id': table.name,
                'label': table.name,
                'columns': [
                    {
                        'name': col.name,
                        'type': col.type,
                        'is_primary': col.is_primary_key,
                        'is_foreign': col.is_foreign_key
                    }
                    for col in table.columns
                ]
            }
            graph['nodes'].append(node)
        
        # Create edges for relationships
        for relationship in schema.relationships:
            edge = {
                'source': relationship.source_table,
                'target': relationship.target_table,
                'label': relationship.column,
                'type': relationship.cardinality  # 1:1, 1:N, N:M
            }
            graph['edges'].append(edge)
        
        return graph
```

### Column Statistics Display

```python
def render_column_statistics(df, column_name):
    col_data = df[column_name]
    stats = {}
    
    # Basic statistics
    stats['type'] = str(col_data.dtype)
    stats['non_null'] = col_data.notna().sum()
    stats['null'] = col_data.isna().sum()
    stats['null_pct'] = (stats['null'] / len(col_data)) * 100
    stats['unique'] = col_data.nunique()
    stats['unique_pct'] = (stats['unique'] / len(col_data)) * 100
    
    # Type-specific statistics
    if pd.api.types.is_numeric_dtype(col_data):
        stats['min'] = col_data.min()
        stats['max'] = col_data.max()
        stats['mean'] = col_data.mean()
        stats['median'] = col_data.median()
        stats['std'] = col_data.std()
    elif pd.api.types.is_string_dtype(col_data):
        stats['min_length'] = col_data.str.len().min()
        stats['max_length'] = col_data.str.len().max()
        stats['most_common'] = col_data.value_counts().iloc[0] if len(col_data.value_counts()) > 0 else None
    elif pd.api.types.is_datetime64_any_dtype(col_data):
        stats['min_date'] = col_data.min()
        stats['max_date'] = col_data.max()
        stats['date_range'] = stats['max_date'] - stats['min_date']
    
    return stats
```

### Export Configuration

```yaml
export_options:
  csv:
    delimiter: [",", ";", "|", "\t"]
    quote_char: ['"', "'", "none"]
    line_terminator: ["\n", "\r\n"]
    encoding: ["utf-8", "latin-1", "ascii"]
    include_header: true
    include_index: false
  
  excel:
    sheet_name: "Data Export"
    include_header: true
    include_index: false
    freeze_panes: true
    auto_column_width: true
    cell_formatting: true
  
  json:
    format: ["records", "columns", "values", "table"]
    orient: ["columns", "records", "index"]
    pretty_print: true
    indent: 2
    ensure_ascii: false
```

## Definition of Done

- [ ] All acceptance criteria met
- [ ] Filtering handles 10+ simultaneous conditions
- [ ] Export completes in <10s for 100K rows
- [ ] Relationship diagram renders for 50+ tables
- [ ] Pagination smooth for 1M+ row tables
- [ ] Column statistics calculate in <1s
- [ ] All features keyboard accessible
- [ ] Mobile responsive design implemented

## Dependencies

- Data grid library (AG-Grid or similar)
- Graph visualization library (vis.js, D3.js)
- Export libraries (pandas, openpyxl)
- Virtual scrolling library
- Statistical computation libraries

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Performance with complex filters | HIGH | Index commonly filtered columns |
| Large dataset exports timing out | MEDIUM | Implement streaming exports |
| Relationship detection accuracy | MEDIUM | Allow manual relationship definition |
| Browser memory with large grids | HIGH | Implement virtual scrolling |

---
**Story Validated**: ✅ Ready for Development