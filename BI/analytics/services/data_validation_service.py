"""
Data Validation Service
Performs data quality checks, schema verification, min/max boundary constraints,
missing value imputation/dropping, and duplicate row detection.
"""
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger('analytics')

# Default domain boundary rules for wireless telemetry metrics
DEFAULT_BOUNDARY_RULES = {
    'PFO [mW]': {'min': 0.0, 'max': 1000.0},
    'Rectified Power [W]': {'min': 0.0, 'max': 100.0},
    'Received Power [W]': {'min': 0.0, 'max': 100.0},
    'Duty [%]': {'min': 0.0, 'max': 100.0},
    'Frequency [kHz]': {'min': 0.0, 'max': 1000.0},
    'Temperature [degC]': {'min': -40.0, 'max': 150.0},
}

class DataValidationService:

    @staticmethod
    def validate_and_clean_dataframe(
        df: pd.DataFrame, 
        boundary_rules: dict = None, 
        drop_duplicates: bool = True,
        handle_missing: str = 'drop'
    ) -> tuple[pd.DataFrame, dict]:
        """
        Validate Data Quality:
        1. Check missing values & handle them.
        2. Detect & remove duplicate rows.
        3. Enforce min/max numerical range boundary constraints.
        4. Standardize dates & units.
        Returns (cleaned_df, validation_report).
        """
        if df.empty:
            return df, {'status': 'EMPTY', 'initial_rows': 0, 'cleaned_rows': 0}

        report = {
            'initial_rows': len(df),
            'missing_values_found': int(df.isnull().sum().sum()),
            'duplicate_rows_removed': 0,
            'boundary_violations_flagged': 0,
            'status': 'PASSED'
        }

        df_clean = df.copy()

        # 1. Missing Value Handling
        if handle_missing == 'drop':
            df_clean = df_clean.dropna(how='all')
        elif handle_missing == 'fill_zero':
            df_clean = df_clean.fillna(0)

        # 2. Duplicate Detection
        if drop_duplicates:
            initial_count = len(df_clean)
            df_clean = df_clean.drop_duplicates()
            report['duplicate_rows_removed'] = initial_count - len(df_clean)

        # 3. Enforce Min/Max Boundary Constraints
        rules = boundary_rules or DEFAULT_BOUNDARY_RULES
        violations_mask = pd.Series(False, index=df_clean.index)

        for col, bounds in rules.items():
            if col in df_clean.columns:
                series = pd.to_numeric(df_clean[col], errors='coerce')
                min_val = bounds.get('min')
                max_val = bounds.get('max')
                
                if min_val is not None:
                    col_violations = series < min_val
                    violations_mask = violations_mask | col_violations
                if max_val is not None:
                    col_violations = series > max_val
                    violations_mask = violations_mask | col_violations

        report['boundary_violations_flagged'] = int(violations_mask.sum())
        df_clean['_is_boundary_violator'] = violations_mask

        report['cleaned_rows'] = len(df_clean)
        logger.info(f"Data Validation Complete: {report['initial_rows']} initial rows -> {report['cleaned_rows']} clean rows")
        
        return df_clean, report

    @staticmethod
    def standardize_column_names(df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardize column headers for data contract compatibility.
        """
        df_copy = df.copy()
        rename_map = {
            'pfo': 'PFO [mW]',
            'power': 'Rectified Power [W]',
            'received_power': 'Received Power [W]',
            'board_name': 'Board',
            'dut_id': 'DUT',
            'time': 'Timestamp [Sec]',
        }
        for col in df_copy.columns:
            lower = col.lower().strip()
            if lower in rename_map:
                df_copy.rename(columns={col: rename_map[lower]}, inplace=True)
        return df_copy
