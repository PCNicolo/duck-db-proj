"""Data Profiling and Summary Statistics for DuckDB Analytics Dashboard."""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import time
import logging

logger = logging.getLogger(__name__)

class ColumnType(Enum):
    """Column data types for profiling."""
    NUMERIC = "numeric"
    TEXT = "text"
    DATE = "date"
    BOOLEAN = "boolean"
    UNKNOWN = "unknown"

@dataclass
class ColumnProfile:
    """Profile data for a single column."""
    name: str
    type: ColumnType
    statistics: Dict[str, Any]
    quality_metrics: Dict[str, Any]
    patterns: Dict[str, Any]
    sample_values: List[Any]

@dataclass
class DataProfile:
    """Complete data profile for a table."""
    table_name: str
    row_count: int
    column_count: int
    column_profiles: List[ColumnProfile]
    overall_quality: Dict[str, Any]
    relationships: List[Dict[str, Any]]
    created_at: float
    processing_time: float

class SummaryStatsGenerator:
    """Generate smart summary statistics based on column types."""
    
    def __init__(self, db_connection):
        self.db_connection = db_connection
        
    def generate_statistics(self, table_name: str, sample_size: int = 10000) -> Dict[str, Any]:
        """Generate comprehensive summary statistics for a table."""
        start_time = time.time()
        
        try:
            # Get table schema
            table_info = self.db_connection.get_table_info(table_name)
            columns = table_info.get('columns', [])
            row_count = table_info.get('row_count', 0)
            
            if not columns:
                raise ValueError(f"No columns found in table {table_name}")
                
            # Sample data for analysis
            sample_query = f"SELECT * FROM {table_name} LIMIT {sample_size}"
            df = pd.read_sql(sample_query, self.db_connection.get_connection())
            
            column_stats = {}
            
            for column in columns:
                col_name = column['name']
                col_type = self._detect_column_type(df[col_name], column.get('type', ''))
                
                if col_type == ColumnType.NUMERIC:
                    column_stats[col_name] = self._generate_numeric_stats(df[col_name], col_name, table_name)
                elif col_type == ColumnType.TEXT:
                    column_stats[col_name] = self._generate_text_stats(df[col_name], col_name, table_name)
                elif col_type == ColumnType.DATE:
                    column_stats[col_name] = self._generate_date_stats(df[col_name], col_name, table_name)
                elif col_type == ColumnType.BOOLEAN:
                    column_stats[col_name] = self._generate_boolean_stats(df[col_name], col_name, table_name)
                else:
                    column_stats[col_name] = self._generate_generic_stats(df[col_name], col_name, table_name)
                    
                column_stats[col_name]['type'] = col_type.value
                column_stats[col_name]['sql_type'] = column.get('type', 'unknown')
                
            processing_time = time.time() - start_time
            
            return {
                'table_name': table_name,
                'total_rows': row_count,
                'sampled_rows': len(df),
                'total_columns': len(columns),
                'column_statistics': column_stats,
                'processing_time': processing_time,
                'generated_at': time.time()
            }
            
        except Exception as e:
            logger.error(f"Error generating statistics for {table_name}: {str(e)}")
            raise
            
    def _detect_column_type(self, series: pd.Series, sql_type: str) -> ColumnType:
        """Detect the semantic column type."""
        sql_type_lower = sql_type.lower()
        
        # Check SQL type first
        if any(t in sql_type_lower for t in ['int', 'float', 'double', 'decimal', 'numeric']):
            return ColumnType.NUMERIC
        elif any(t in sql_type_lower for t in ['date', 'time', 'timestamp']):
            return ColumnType.DATE
        elif 'bool' in sql_type_lower:
            return ColumnType.BOOLEAN
        elif any(t in sql_type_lower for t in ['varchar', 'text', 'string', 'char']):
            return ColumnType.TEXT
            
        # Fallback to pandas detection
        if pd.api.types.is_numeric_dtype(series):
            return ColumnType.NUMERIC
        elif pd.api.types.is_datetime64_any_dtype(series):
            return ColumnType.DATE
        elif pd.api.types.is_bool_dtype(series):
            return ColumnType.BOOLEAN
        else:
            return ColumnType.TEXT
            
    def _generate_numeric_stats(self, series: pd.Series, col_name: str, table_name: str) -> Dict[str, Any]:
        """Generate statistics for numeric columns."""
        try:
            # Convert to numeric, handling errors
            numeric_series = pd.to_numeric(series, errors='coerce')
            
            # Basic statistics
            stats = {
                'count': len(numeric_series),
                'unique': numeric_series.nunique(),
                'missing': numeric_series.isnull().sum(),
                'mean': numeric_series.mean(),
                'median': numeric_series.median(),
                'std_dev': numeric_series.std(),
                'min': numeric_series.min(),
                'max': numeric_series.max(),
                'q1': numeric_series.quantile(0.25),
                'q3': numeric_series.quantile(0.75),
                'range': numeric_series.max() - numeric_series.min() if not numeric_series.empty else 0
            }
            
            # Quality metrics
            completeness = (stats['count'] - stats['missing']) / stats['count'] if stats['count'] > 0 else 0
            uniqueness = stats['unique'] / stats['count'] if stats['count'] > 0 else 0
            
            # Outlier detection using IQR method
            q1, q3 = stats['q1'], stats['q3']
            iqr = q3 - q1
            outlier_count = 0
            if iqr > 0:
                lower_bound = q1 - 1.5 * iqr
                upper_bound = q3 + 1.5 * iqr
                outliers = numeric_series[(numeric_series < lower_bound) | (numeric_series > upper_bound)]
                outlier_count = len(outliers)
            
            # Distribution analysis
            distribution_type = "normal"
            if not numeric_series.dropna().empty:
                skewness = numeric_series.skew()
                if abs(skewness) > 1:
                    distribution_type = "right-skewed" if skewness > 0 else "left-skewed"
                    
            return {
                **stats,
                'completeness': completeness,
                'uniqueness': uniqueness, 
                'outlier_count': outlier_count,
                'distribution_type': distribution_type,
                'skewness': numeric_series.skew() if not numeric_series.dropna().empty else 0,
                'kurtosis': numeric_series.kurtosis() if not numeric_series.dropna().empty else 0
            }
            
        except Exception as e:
            logger.error(f"Error generating numeric stats for {col_name}: {str(e)}")
            return self._generate_generic_stats(series, col_name, table_name)
            
    def _generate_text_stats(self, series: pd.Series, col_name: str, table_name: str) -> Dict[str, Any]:
        """Generate statistics for text columns."""
        try:
            # Convert to string
            text_series = series.astype(str)
            non_null_series = text_series[text_series.notna()]
            
            # Basic statistics
            stats = {
                'count': len(text_series),
                'unique': text_series.nunique(),
                'missing': text_series.isnull().sum(),
                'mode': text_series.mode().iloc[0] if not text_series.mode().empty else None,
                'mode_frequency': (text_series == text_series.mode().iloc[0]).sum() if not text_series.mode().empty else 0
            }
            
            # Length statistics
            if not non_null_series.empty:
                lengths = non_null_series.str.len()
                stats.update({
                    'min_length': lengths.min(),
                    'max_length': lengths.max(),
                    'avg_length': lengths.mean(),
                    'median_length': lengths.median()
                })
            else:
                stats.update({
                    'min_length': 0,
                    'max_length': 0,
                    'avg_length': 0,
                    'median_length': 0
                })
            
            # Pattern analysis
            if not non_null_series.empty:
                # Check for common patterns
                patterns = {
                    'contains_digits': non_null_series.str.contains(r'\d').sum(),
                    'contains_letters': non_null_series.str.contains(r'[a-zA-Z]').sum(),
                    'contains_special_chars': non_null_series.str.contains(r'[^a-zA-Z0-9\s]').sum(),
                    'all_uppercase': non_null_series.str.isupper().sum(),
                    'all_lowercase': non_null_series.str.islower().sum(),
                    'starts_with_number': non_null_series.str.match(r'^\d').sum()
                }
            else:
                patterns = {key: 0 for key in ['contains_digits', 'contains_letters', 'contains_special_chars',
                                              'all_uppercase', 'all_lowercase', 'starts_with_number']}
            
            # Quality metrics
            completeness = (stats['count'] - stats['missing']) / stats['count'] if stats['count'] > 0 else 0
            uniqueness = stats['unique'] / stats['count'] if stats['count'] > 0 else 0
            
            return {
                **stats,
                **patterns,
                'completeness': completeness,
                'uniqueness': uniqueness
            }
            
        except Exception as e:
            logger.error(f"Error generating text stats for {col_name}: {str(e)}")
            return self._generate_generic_stats(series, col_name, table_name)
            
    def _generate_date_stats(self, series: pd.Series, col_name: str, table_name: str) -> Dict[str, Any]:
        """Generate statistics for date columns."""
        try:
            # Convert to datetime if not already
            if not isinstance(series.dtype, pd.DatetimeTZDtype) and series.dtype != 'datetime64[ns]':
                date_series = pd.to_datetime(series, errors='coerce')
            else:
                date_series = series
            
            # Basic statistics
            stats = {
                'count': len(date_series),
                'unique': date_series.nunique(),
                'missing': date_series.isnull().sum(),
                'min_date': date_series.min(),
                'max_date': date_series.max()
            }
            
            # Date range analysis
            if stats['min_date'] is not pd.NaT and stats['max_date'] is not pd.NaT:
                date_range = stats['max_date'] - stats['min_date']
                stats['date_range_days'] = date_range.days
                
                # Frequency analysis
                if not date_series.dropna().empty:
                    # Group by different time periods
                    freq_analysis = {
                        'unique_years': date_series.dt.year.nunique(),
                        'unique_months': date_series.dt.to_period('M').nunique(),
                        'unique_weeks': date_series.dt.to_period('W').nunique(),
                        'unique_days': date_series.dt.date.nunique()
                    }
                    stats.update(freq_analysis)
                    
                    # Seasonality patterns
                    weekday_dist = date_series.dt.dayofweek.value_counts().to_dict()
                    month_dist = date_series.dt.month.value_counts().to_dict()
                    
                    stats['weekday_distribution'] = weekday_dist
                    stats['month_distribution'] = month_dist
                    
            # Quality metrics
            completeness = (stats['count'] - stats['missing']) / stats['count'] if stats['count'] > 0 else 0
            uniqueness = stats['unique'] / stats['count'] if stats['count'] > 0 else 0
            
            return {
                **stats,
                'completeness': completeness,
                'uniqueness': uniqueness
            }
            
        except Exception as e:
            logger.error(f"Error generating date stats for {col_name}: {str(e)}")
            return self._generate_generic_stats(series, col_name, table_name)
            
    def _generate_boolean_stats(self, series: pd.Series, col_name: str, table_name: str) -> Dict[str, Any]:
        """Generate statistics for boolean columns."""
        try:
            # Basic statistics
            stats = {
                'count': len(series),
                'unique': series.nunique(), 
                'missing': series.isnull().sum()
            }
            
            # Boolean distribution
            value_counts = series.value_counts()
            
            # Count various representations of True/False
            true_count = 0
            false_count = 0
            
            for val, count in value_counts.items():
                if val in [True, 1, 'true', 'True']:
                    true_count += count
                elif val in [False, 0, 'false', 'False']:
                    false_count += count
            
            total_valid = true_count + false_count
            
            stats.update({
                'true_count': true_count,
                'false_count': false_count,
                'true_ratio': true_count / total_valid if total_valid > 0 else 0,
                'false_ratio': false_count / total_valid if total_valid > 0 else 0
            })
            
            # Quality metrics
            completeness = (stats['count'] - stats['missing']) / stats['count'] if stats['count'] > 0 else 0
            
            return {
                **stats,
                'completeness': completeness,
                'uniqueness': 2 / stats['count'] if stats['count'] > 0 else 0  # Boolean has max 2 unique values
            }
            
        except Exception as e:
            logger.error(f"Error generating boolean stats for {col_name}: {str(e)}")
            return self._generate_generic_stats(series, col_name, table_name)
            
    def _generate_generic_stats(self, series: pd.Series, col_name: str, table_name: str) -> Dict[str, Any]:
        """Generate generic statistics for unknown column types."""
        try:
            stats = {
                'count': len(series),
                'unique': series.nunique(),
                'missing': series.isnull().sum(),
                'mode': series.mode().iloc[0] if not series.mode().empty else None
            }
            
            # Quality metrics
            completeness = (stats['count'] - stats['missing']) / stats['count'] if stats['count'] > 0 else 0
            uniqueness = stats['unique'] / stats['count'] if stats['count'] > 0 else 0
            
            return {
                **stats,
                'completeness': completeness,
                'uniqueness': uniqueness
            }
            
        except Exception as e:
            logger.error(f"Error generating generic stats for {col_name}: {str(e)}")
            return {
                'count': 0,
                'unique': 0,
                'missing': 0,
                'completeness': 0,
                'uniqueness': 0,
                'error': str(e)
            }

class DataProfiler:
    """Advanced data profiling engine."""
    
    def __init__(self, db_connection, query_engine):
        self.db_connection = db_connection
        self.query_engine = query_engine
        self.stats_generator = SummaryStatsGenerator(db_connection)
        
    def profile_table(self, table_name: str, sample_size: int = 10000) -> DataProfile:
        """Generate comprehensive data profile for a table."""
        start_time = time.time()
        
        try:
            # Get basic table info
            table_info = self.db_connection.get_table_info(table_name)
            columns = table_info.get('columns', [])
            row_count = table_info.get('row_count', 0)
            
            if not columns:
                raise ValueError(f"No columns found in table {table_name}")
                
            # Generate statistics
            stats_result = self.stats_generator.generate_statistics(table_name, sample_size)
            column_stats = stats_result['column_statistics']
            
            # Create column profiles
            column_profiles = []
            for column in columns:
                col_name = column['name']
                if col_name in column_stats:
                    col_stats = column_stats[col_name]
                    
                    # Extract sample values
                    sample_values = self._get_sample_values(table_name, col_name, 5)
                    
                    profile = ColumnProfile(
                        name=col_name,
                        type=ColumnType(col_stats.get('type', 'unknown')),
                        statistics=col_stats,
                        quality_metrics={
                            'completeness': col_stats.get('completeness', 0),
                            'uniqueness': col_stats.get('uniqueness', 0),
                            'validity': self._calculate_validity(col_stats)
                        },
                        patterns=self._extract_patterns(col_stats),
                        sample_values=sample_values
                    )
                    column_profiles.append(profile)
                    
            # Calculate overall quality
            overall_quality = self._calculate_overall_quality(column_profiles)
            
            # Analyze relationships (basic correlation for numeric columns)
            relationships = self._analyze_relationships(table_name, column_profiles[:5])  # Limit to first 5 for performance
            
            processing_time = time.time() - start_time
            
            return DataProfile(
                table_name=table_name,
                row_count=row_count,
                column_count=len(columns),
                column_profiles=column_profiles,
                overall_quality=overall_quality,
                relationships=relationships,
                created_at=time.time(),
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Error profiling table {table_name}: {str(e)}")
            raise
            
    def _get_sample_values(self, table_name: str, column_name: str, limit: int = 5) -> List[Any]:
        """Get sample values from a column."""
        try:
            query = f"""
            SELECT DISTINCT {column_name}
            FROM {table_name}
            WHERE {column_name} IS NOT NULL
            LIMIT {limit}
            """
            df = self.query_engine.execute_query(query)
            return df[column_name].tolist() if not df.empty else []
        except Exception as e:
            logger.error(f"Error getting sample values for {column_name}: {str(e)}")
            return []
            
    def _calculate_validity(self, col_stats: Dict[str, Any]) -> float:
        """Calculate validity score for a column."""
        validity_score = 1.0
        
        # Penalize high missing values
        completeness = col_stats.get('completeness', 1.0)
        validity_score *= completeness
        
        # Penalize outliers in numeric columns
        if 'outlier_count' in col_stats and col_stats.get('count', 0) > 0:
            outlier_ratio = col_stats['outlier_count'] / col_stats['count']
            validity_score *= (1.0 - min(outlier_ratio, 0.5))  # Cap penalty at 50%
            
        return max(validity_score, 0.0)
        
    def _extract_patterns(self, col_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Extract data patterns from column statistics."""
        patterns = {}
        
        # Distribution patterns for numeric columns
        if 'distribution_type' in col_stats:
            patterns['distribution'] = col_stats['distribution_type']
            
        if 'outlier_count' in col_stats and col_stats.get('count', 0) > 0:
            outlier_ratio = col_stats['outlier_count'] / col_stats['count']
            if outlier_ratio > 0.1:
                patterns['outliers'] = f"High outlier count: {col_stats['outlier_count']}"
                
        # Text patterns
        if 'contains_digits' in col_stats:
            total_count = col_stats.get('count', 0) - col_stats.get('missing', 0)  # Use non-null count
            if total_count > 0:
                digit_ratio = col_stats['contains_digits'] / total_count
                if digit_ratio > 0.8:
                    patterns['text_type'] = "alphanumeric"
                elif digit_ratio < 0.1:
                    patterns['text_type'] = "alphabetic"
                    
        # Date patterns
        if 'weekday_distribution' in col_stats:
            weekday_dist = col_stats['weekday_distribution']
            if weekday_dist:
                most_common_weekday = max(weekday_dist, key=weekday_dist.get)
                patterns['temporal'] = f"Most common weekday: {most_common_weekday}"
                
        return patterns
        
    def _calculate_overall_quality(self, column_profiles: List[ColumnProfile]) -> Dict[str, Any]:
        """Calculate overall data quality metrics."""
        if not column_profiles:
            return {'completeness': 0, 'uniqueness': 0, 'validity': 0}
            
        # Average quality metrics across columns
        completeness_scores = [cp.quality_metrics.get('completeness', 0) for cp in column_profiles]
        uniqueness_scores = [cp.quality_metrics.get('uniqueness', 0) for cp in column_profiles] 
        validity_scores = [cp.quality_metrics.get('validity', 0) for cp in column_profiles]
        
        return {
            'completeness': sum(completeness_scores) / len(completeness_scores),
            'uniqueness': sum(uniqueness_scores) / len(uniqueness_scores),
            'validity': sum(validity_scores) / len(validity_scores),
            'total_score': (
                sum(completeness_scores) + 
                sum(uniqueness_scores) + 
                sum(validity_scores)
            ) / (3 * len(column_profiles))
        }
        
    def _analyze_relationships(self, table_name: str, column_profiles: List[ColumnProfile]) -> List[Dict[str, Any]]:
        """Analyze relationships between columns."""
        relationships = []
        
        try:
            # Find numeric columns for correlation analysis
            numeric_columns = [cp.name for cp in column_profiles if cp.type == ColumnType.NUMERIC]
            
            if len(numeric_columns) >= 2:
                # Calculate pairwise correlations
                for i in range(len(numeric_columns)):
                    for j in range(i + 1, len(numeric_columns)):
                        col1, col2 = numeric_columns[i], numeric_columns[j]
                        
                        try:
                            query = f"""
                            SELECT CORR({col1}, {col2}) as correlation
                            FROM {table_name}
                            WHERE {col1} IS NOT NULL AND {col2} IS NOT NULL
                            """
                            df = self.query_engine.execute_query(query)
                            
                            if not df.empty and not pd.isna(df.iloc[0]['correlation']):
                                correlation = df.iloc[0]['correlation']
                                
                                if abs(correlation) > 0.5:  # Only include significant correlations
                                    relationships.append({
                                        'type': 'correlation',
                                        'column1': col1,
                                        'column2': col2,
                                        'strength': abs(correlation),
                                        'direction': 'positive' if correlation > 0 else 'negative',
                                        'value': correlation
                                    })
                        except Exception as e:
                            logger.warning(f"Error calculating correlation between {col1} and {col2}: {str(e)}")
                            
        except Exception as e:
            logger.error(f"Error analyzing relationships: {str(e)}")
            
        return relationships