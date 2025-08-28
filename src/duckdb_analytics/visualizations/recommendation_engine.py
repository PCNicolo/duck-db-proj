"""Smart chart recommendation engine."""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from .chart_types import ChartType


@dataclass 
class ChartRecommendation:
    """Chart recommendation with score and reasoning."""
    chart_type: ChartType
    score: float
    reason: str
    config: Dict[str, Any]
    columns_used: List[str]


class ChartRecommendationEngine:
    """Engine for recommending optimal chart types based on data analysis."""
    
    def __init__(self):
        self.min_score_threshold = 0.3
        
    def analyze_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze data structure and patterns."""
        analysis = {
            'row_count': len(df),
            'columns': self._analyze_columns(df),
            'patterns': self._detect_patterns(df), 
            'relationships': self._find_relationships(df),
            'data_quality': self._assess_data_quality(df)
        }
        return analysis
    
    def recommend_charts(self, df: pd.DataFrame, 
                        max_recommendations: int = 5) -> List[ChartRecommendation]:
        """Generate ranked chart recommendations."""
        analysis = self.analyze_data(df)
        recommendations = []
        
        # Time series detection
        if analysis['patterns']['has_time_series']:
            recommendations.extend(self._recommend_time_series(df, analysis))
        
        # Categorical analysis
        if analysis['patterns']['has_categories']:
            recommendations.extend(self._recommend_categorical(df, analysis))
        
        # Correlation analysis  
        if analysis['patterns']['has_correlations']:
            recommendations.extend(self._recommend_correlation(df, analysis))
        
        # Distribution analysis
        if analysis['patterns']['has_distributions']:
            recommendations.extend(self._recommend_distribution(df, analysis))
        
        # Hierarchical data
        if analysis['patterns']['has_hierarchy']:
            recommendations.extend(self._recommend_hierarchical(df, analysis))
        
        # Flow/process data
        if analysis['patterns']['has_flow_data']:
            recommendations.extend(self._recommend_flow(df, analysis))
        
        # KPI data
        if analysis['patterns']['has_kpi_data']:
            recommendations.extend(self._recommend_kpi(df, analysis))
        
        # Filter and rank recommendations
        filtered_recs = [r for r in recommendations if r.score >= self.min_score_threshold]
        sorted_recs = sorted(filtered_recs, key=lambda x: x.score, reverse=True)
        
        return sorted_recs[:max_recommendations]
    
    def _analyze_columns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze column types and characteristics."""
        columns = {}
        
        for col in df.columns:
            col_info = {
                'name': col,
                'dtype': str(df[col].dtype),
                'null_count': df[col].isnull().sum(),
                'unique_count': df[col].nunique(),
                'is_numeric': pd.api.types.is_numeric_dtype(df[col]),
                'is_datetime': pd.api.types.is_datetime64_any_dtype(df[col]),
                'is_categorical': df[col].nunique() < len(df) * 0.1 and df[col].nunique() < 20,
                'sample_values': df[col].dropna().head(5).tolist()
            }
            
            # Detect potential time columns
            if not col_info['is_datetime']:
                col_info['potential_time'] = self._is_potential_time_column(df[col])
            
            columns[col] = col_info
            
        return columns
    
    def _detect_patterns(self, df: pd.DataFrame) -> Dict[str, bool]:
        """Detect data patterns for chart recommendations."""
        columns = self._analyze_columns(df)
        
        patterns = {
            'has_time_series': any(col['is_datetime'] or col.get('potential_time', False) 
                                 for col in columns.values()),
            'has_categories': any(col['is_categorical'] for col in columns.values()),
            'has_correlations': len([c for c in columns.values() if c['is_numeric']]) >= 2,
            'has_distributions': any(col['is_numeric'] and col['unique_count'] > 10 
                                   for col in columns.values()),
            'has_hierarchy': self._detect_hierarchy_columns(df, columns),
            'has_flow_data': self._detect_flow_data(df, columns),
            'has_kpi_data': self._detect_kpi_data(df, columns),
            'has_geographic': self._detect_geographic_data(df, columns)
        }
        
        return patterns
    
    def _find_relationships(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Find relationships between columns."""
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        relationships = {
            'correlations': {},
            'strong_correlations': [],
            'categorical_numeric_pairs': []
        }
        
        if len(numeric_cols) >= 2:
            corr_matrix = df[numeric_cols].corr()
            relationships['correlations'] = corr_matrix.to_dict()
            
            # Find strong correlations (>0.7 or <-0.7)
            for i in range(len(numeric_cols)):
                for j in range(i+1, len(numeric_cols)):
                    corr_val = corr_matrix.iloc[i, j]
                    if abs(corr_val) > 0.7:
                        relationships['strong_correlations'].append({
                            'col1': numeric_cols[i],
                            'col2': numeric_cols[j], 
                            'correlation': corr_val
                        })
        
        # Find categorical-numeric pairs
        cat_cols = df.select_dtypes(include=['object', 'category']).columns
        for cat_col in cat_cols:
            if df[cat_col].nunique() <= 20:  # Reasonable number of categories
                for num_col in numeric_cols:
                    relationships['categorical_numeric_pairs'].append({
                        'categorical': cat_col,
                        'numeric': num_col
                    })
        
        return relationships
    
    def _assess_data_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Assess data quality metrics."""
        return {
            'completeness': 1 - (df.isnull().sum().sum() / (len(df) * len(df.columns))),
            'row_count': len(df),
            'column_count': len(df.columns),
            'has_duplicates': df.duplicated().any()
        }
    
    def _recommend_time_series(self, df: pd.DataFrame, 
                             analysis: Dict[str, Any]) -> List[ChartRecommendation]:
        """Recommend time series visualizations."""
        recommendations = []
        time_cols = [col for col, info in analysis['columns'].items() 
                    if info['is_datetime'] or info.get('potential_time', False)]
        numeric_cols = [col for col, info in analysis['columns'].items() 
                       if info['is_numeric']]
        
        if time_cols and numeric_cols:
            # Line chart recommendation
            recommendations.append(ChartRecommendation(
                chart_type=ChartType.HEATMAP,  # For time-based patterns
                score=0.95,
                reason="Time series data detected with numeric values",
                config={
                    'x': time_cols[0],
                    'y': numeric_cols[0] if len(numeric_cols) == 1 else 'multiple',
                    'chart_subtype': 'line'
                },
                columns_used=time_cols + numeric_cols[:3]
            ))
        
        return recommendations
    
    def _recommend_categorical(self, df: pd.DataFrame,
                             analysis: Dict[str, Any]) -> List[ChartRecommendation]:
        """Recommend categorical visualizations.""" 
        recommendations = []
        cat_cols = [col for col, info in analysis['columns'].items() if info['is_categorical']]
        numeric_cols = [col for col, info in analysis['columns'].items() if info['is_numeric']]
        
        if cat_cols and numeric_cols:
            # Bar chart for category + value
            recommendations.append(ChartRecommendation(
                chart_type=ChartType.TREEMAP,
                score=0.85,
                reason="Categorical data with numeric values detected",
                config={
                    'labels': cat_cols[0],
                    'values': numeric_cols[0]
                },
                columns_used=[cat_cols[0], numeric_cols[0]]
            ))
            
        return recommendations
    
    def _recommend_correlation(self, df: pd.DataFrame,
                             analysis: Dict[str, Any]) -> List[ChartRecommendation]:
        """Recommend correlation visualizations."""
        recommendations = []
        strong_corrs = analysis['relationships']['strong_correlations']
        numeric_cols = [col for col, info in analysis['columns'].items() if info['is_numeric']]
        
        if len(numeric_cols) >= 2:
            # Heatmap for correlation matrix
            recommendations.append(ChartRecommendation(
                chart_type=ChartType.HEATMAP,
                score=0.80,
                reason=f"Found correlations between {len(numeric_cols)} numeric columns",
                config={
                    'correlation_matrix': True,
                    'columns': numeric_cols
                },
                columns_used=numeric_cols
            ))
            
            # Scatter matrix for multiple numeric columns
            if len(numeric_cols) >= 3:
                recommendations.append(ChartRecommendation(
                    chart_type=ChartType.SCATTER_MATRIX,
                    score=0.75,
                    reason=f"Multiple numeric columns suitable for scatter matrix",
                    config={
                        'dimensions': numeric_cols[:6]  # Limit to 6 for readability
                    },
                    columns_used=numeric_cols[:6]
                ))
        
        return recommendations
    
    def _recommend_distribution(self, df: pd.DataFrame,
                              analysis: Dict[str, Any]) -> List[ChartRecommendation]:
        """Recommend distribution visualizations."""
        recommendations = []
        numeric_cols = [col for col, info in analysis['columns'].items() 
                       if info['is_numeric'] and info['unique_count'] > 10]
        cat_cols = [col for col, info in analysis['columns'].items() if info['is_categorical']]
        
        if numeric_cols:
            # Box plot for distribution analysis
            config = {'y': numeric_cols[0]}
            score = 0.70
            reason = f"Distribution analysis for {numeric_cols[0]}"
            
            if cat_cols:
                config['x'] = cat_cols[0]
                score = 0.80
                reason = f"Distribution of {numeric_cols[0]} by {cat_cols[0]}"
            
            recommendations.append(ChartRecommendation(
                chart_type=ChartType.BOX_PLOT,
                score=score,
                reason=reason,
                config=config,
                columns_used=[numeric_cols[0]] + ([cat_cols[0]] if cat_cols else [])
            ))
        
        return recommendations
    
    def _recommend_hierarchical(self, df: pd.DataFrame,
                              analysis: Dict[str, Any]) -> List[ChartRecommendation]:
        """Recommend hierarchical visualizations."""
        recommendations = []
        
        # This is a simplified detection - in practice would be more sophisticated
        cat_cols = [col for col, info in analysis['columns'].items() if info['is_categorical']]
        numeric_cols = [col for col, info in analysis['columns'].items() if info['is_numeric']]
        
        if len(cat_cols) >= 2 and numeric_cols:
            recommendations.append(ChartRecommendation(
                chart_type=ChartType.TREEMAP,
                score=0.65,
                reason="Multiple categorical columns suggest hierarchical structure",
                config={
                    'labels': cat_cols[1],
                    'parents': cat_cols[0],
                    'values': numeric_cols[0]
                },
                columns_used=cat_cols[:2] + [numeric_cols[0]]
            ))
        
        return recommendations
    
    def _recommend_flow(self, df: pd.DataFrame,
                       analysis: Dict[str, Any]) -> List[ChartRecommendation]:
        """Recommend flow/process visualizations."""
        recommendations = []
        
        # Detect source-target-value pattern
        cols = list(df.columns)
        if len(cols) >= 3:
            # Look for columns that might represent flow data
            potential_sources = []
            potential_targets = []
            potential_values = []
            
            for col, info in analysis['columns'].items():
                if info['is_categorical']:
                    potential_sources.append(col)
                    potential_targets.append(col)
                elif info['is_numeric']:
                    potential_values.append(col)
            
            if len(potential_sources) >= 2 and potential_values:
                recommendations.append(ChartRecommendation(
                    chart_type=ChartType.SANKEY,
                    score=0.60,
                    reason="Detected potential flow data pattern",
                    config={
                        'source': potential_sources[0],
                        'target': potential_sources[1], 
                        'value': potential_values[0]
                    },
                    columns_used=[potential_sources[0], potential_sources[1], potential_values[0]]
                ))
        
        return recommendations
    
    def _recommend_kpi(self, df: pd.DataFrame,
                      analysis: Dict[str, Any]) -> List[ChartRecommendation]:
        """Recommend KPI visualizations.""" 
        recommendations = []
        
        # Simple KPI detection - single numeric value or aggregatable data
        numeric_cols = [col for col, info in analysis['columns'].items() if info['is_numeric']]
        
        if len(df) == 1 and numeric_cols:
            # Single row suggests KPI data
            for col in numeric_cols[:3]:  # Limit to 3 gauges
                recommendations.append(ChartRecommendation(
                    chart_type=ChartType.GAUGE,
                    score=0.75,
                    reason=f"Single value suitable for gauge display: {col}",
                    config={
                        'value_column': col,
                        'title': col.replace('_', ' ').title()
                    },
                    columns_used=[col]
                ))
        
        return recommendations
    
    def _is_potential_time_column(self, series: pd.Series) -> bool:
        """Check if a column might contain time data."""
        if series.dtype == 'object':
            sample = series.dropna().astype(str).head(10)
            # Simple check for common date patterns
            time_indicators = ['date', 'time', 'year', 'month', 'day']
            return any(indicator in series.name.lower() for indicator in time_indicators)
        return False
    
    def _detect_hierarchy_columns(self, df: pd.DataFrame, 
                                columns: Dict[str, Any]) -> bool:
        """Detect if data has hierarchical structure."""
        cat_cols = [col for col, info in columns.items() if info['is_categorical']]
        return len(cat_cols) >= 2
    
    def _detect_flow_data(self, df: pd.DataFrame,
                         columns: Dict[str, Any]) -> bool:
        """Detect flow/process data patterns."""
        col_names = [col.lower() for col in df.columns]
        flow_indicators = ['source', 'target', 'from', 'to', 'start', 'end', 'origin', 'destination']
        return any(indicator in ' '.join(col_names) for indicator in flow_indicators)
    
    def _detect_kpi_data(self, df: pd.DataFrame,
                        columns: Dict[str, Any]) -> bool:
        """Detect KPI-style data."""
        # Single row with numeric data suggests KPI
        if len(df) == 1:
            numeric_count = sum(1 for info in columns.values() if info['is_numeric'])
            return numeric_count > 0
        return False
    
    def _detect_geographic_data(self, df: pd.DataFrame,
                              columns: Dict[str, Any]) -> bool:
        """Detect geographic data patterns."""
        col_names = [col.lower() for col in df.columns]
        geo_indicators = ['lat', 'lon', 'latitude', 'longitude', 'country', 'state', 'city', 'region']
        return any(indicator in ' '.join(col_names) for indicator in geo_indicators)