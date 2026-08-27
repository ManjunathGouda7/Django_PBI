"""
Outlier Detection Service
Implements IQR, Z-Score, and Modified MAD (Median Absolute Deviation) algorithms
for telemetry metrics processing.
"""
import numpy as np
import pandas as pd
import logging

logger = logging.getLogger('outliers')

class OutlierDetectionService:

    @staticmethod
    def detect_outliers_iqr(series: pd.Series, factor: float = 1.5) -> pd.Series:
        """
        Detect outliers using Interquartile Range (IQR).
        Returns boolean series where True = outlier.
        """
        if series.dropna().empty:
            return pd.Series(False, index=series.index)
        
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        
        lower_bound = q1 - (factor * iqr)
        upper_bound = q3 + (factor * iqr)
        
        outliers = (series < lower_bound) | (series > upper_bound)
        return outliers

    @staticmethod
    def detect_outliers_zscore(series: pd.Series, threshold: float = 3.0) -> pd.Series:
        """
        Detect outliers using Standard Z-Score (|Z| > threshold).
        """
        if series.dropna().empty or series.std() == 0:
            return pd.Series(False, index=series.index)
        
        z_scores = np.abs((series - series.mean()) / series.std())
        return z_scores > threshold

    @staticmethod
    def detect_outliers_mad(series: pd.Series, threshold: float = 3.5) -> pd.Series:
        """
        Detect outliers using Modified Z-Score based on Median Absolute Deviation (MAD).
        Robust against skewed data distributions.
        """
        if series.dropna().empty:
            return pd.Series(False, index=series.index)
        
        median = series.median()
        mad = (series - median).abs().median()
        if mad == 0:
            return pd.Series(False, index=series.index)
        
        modified_z = 0.6745 * (series - median).abs() / mad
        return modified_z > threshold

    @classmethod
    def process_telemetry_dataframe(
        cls, 
        df: pd.DataFrame, 
        numeric_cols: list = None, 
        method: str = 'iqr', 
        factor: float = 1.5
    ) -> tuple[pd.DataFrame, dict]:
        """
        Process DataFrame, add '_is_outlier' column, and compute summary stats.
        """
        if df.empty:
            return df, {'total_rows': 0, 'outlier_count': 0, 'outlier_pct': 0.0}

        df_copy = df.copy()
        
        if not numeric_cols:
            numeric_cols = df_copy.select_dtypes(include=[np.number]).columns.tolist()

        outlier_mask = pd.Series(False, index=df_copy.index)
        col_outlier_summary = {}

        for col in numeric_cols:
            if col not in df_copy.columns:
                continue
            
            series = pd.to_numeric(df_copy[col], errors='coerce')
            
            if method == 'zscore':
                mask = cls.detect_outliers_zscore(series, threshold=factor)
            elif method == 'mad':
                mask = cls.detect_outliers_mad(series, threshold=factor)
            else:
                mask = cls.detect_outliers_iqr(series, factor=factor)
            
            col_outlier_summary[col] = int(mask.sum())
            outlier_mask = outlier_mask | mask

        df_copy['_is_outlier'] = outlier_mask

        total_rows = len(df_copy)
        outlier_count = int(outlier_mask.sum())
        outlier_pct = round((outlier_count / total_rows * 100), 2) if total_rows > 0 else 0.0

        summary = {
            'total_rows': total_rows,
            'outlier_count': outlier_count,
            'outlier_pct': outlier_pct,
            'column_breakdown': col_outlier_summary,
            'method_used': method,
            'threshold_factor': factor
        }

        logger.info(f"Outlier Detection ({method}): Found {outlier_count}/{total_rows} outliers ({outlier_pct}%)")
        return df_copy, summary
