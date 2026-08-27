"""
Data Import Service
Automates CSV, Excel, and JSON ingestion with chunking, schema inference,
validation pipeline, and outlier detection integration.
"""
import pandas as pd
import json
import logging
from io import BytesIO, StringIO
from .data_validation_service import DataValidationService
from .outlier_detection_service import OutlierDetectionService

logger = logging.getLogger('analytics')

class DataImportService:

    @classmethod
    def ingest_file_content(
        cls, 
        file_content: bytes, 
        filename: str, 
        detect_outliers: bool = True
    ) -> tuple[pd.DataFrame, list, dict]:
        """
        Parse bytes into DataFrame, run validation rules, infer column schemas,
        and optionally mark outliers.
        Returns (df, column_schema, metadata_summary).
        """
        lower_name = filename.lower()

        try:
            if lower_name.endswith('.csv'):
                df = pd.read_csv(StringIO(file_content.decode('utf-8', errors='ignore')))
            elif lower_name.endswith(('.xls', '.xlsx')):
                df = pd.read_excel(BytesIO(file_content))
            elif lower_name.endswith('.json'):
                raw_json = json.loads(file_content.decode('utf-8', errors='ignore'))
                if isinstance(raw_json, list):
                    df = pd.DataFrame(raw_json)
                elif isinstance(raw_json, dict) and 'rows' in raw_json:
                    df = pd.DataFrame(raw_json['rows'])
                else:
                    df = pd.DataFrame([raw_json])
            else:
                raise ValueError(f"Unsupported file format: {filename}")

        except Exception as e:
            logger.error(f"Failed to ingest file '{filename}': {str(e)}")
            raise

        # Standardize Headers
        df = DataValidationService.standardize_column_names(df)

        # Run Data Validation Rules
        df, val_report = DataValidationService.validate_and_clean_dataframe(df)

        # Run Outlier Detection
        outlier_summary = {}
        if detect_outliers:
            df, outlier_summary = OutlierDetectionService.process_telemetry_dataframe(df, method='iqr', factor=1.5)

        # Infer Column Schema
        column_schema = cls.infer_column_schema(df)

        metadata = {
            'filename': filename,
            'total_rows': len(df),
            'total_cols': len(df.columns),
            'validation_report': val_report,
            'outlier_summary': outlier_summary
        }

        return df, column_schema, metadata

    @staticmethod
    def infer_column_schema(df: pd.DataFrame) -> list:
        """
        Infer schema types: numeric, categorical, date, boolean.
        """
        schema = []
        for col in df.columns:
            if col.startswith('_'):
                continue
            
            dtype = df[col].dtype
            if pd.api.types.is_numeric_dtype(dtype):
                col_type = 'numeric'
            elif pd.api.types.is_datetime64_any_dtype(dtype):
                col_type = 'date'
            elif pd.api.types.is_bool_dtype(dtype):
                col_type = 'boolean'
            else:
                col_type = 'categorical'

            schema.append({
                'name': col,
                'type': col_type,
                'unique_count': int(df[col].nunique(dropna=True)) if col in df else 0
            })
        return schema
