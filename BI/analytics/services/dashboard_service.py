"""
Dashboard Service
Handles chart aggregation, cross-filtering, 2-sigma thresholds,
and formatted Chart.js payloads for visual widgets.
"""
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger('analytics')

class DashboardService:

    @classmethod
    def compute_widget_chart_data(
        cls, 
        df: pd.DataFrame, 
        widget_config: dict, 
        filter_outliers: bool = False
    ) -> dict:
        """
        Compute Chart.js formatted data payload for a widget.
        Options:
        - filter_outliers: Exclude rows where _is_outlier == True
        """
        if df.empty:
            return {'labels': [], 'datasets': []}

        data_df = df.copy()

        # Apply Outlier Filter if requested
        if filter_outliers and '_is_outlier' in data_df.columns:
            data_df = data_df[data_df['_is_outlier'] == False]

        vtype = widget_config.get('visual_type', 'scatter').lower()
        x_col = widget_config.get('x_axis')
        y_col = widget_config.get('y_axis')
        group_col = widget_config.get('group_by') or widget_config.get('series')

        if vtype == 'scatter':
            return cls._build_scatter_payload(data_df, x_col, y_col, group_col)
        elif vtype in ('bar', 'column', 'line', 'area'):
            return cls._build_categorical_payload(data_df, x_col, y_col, group_col, vtype)
        elif vtype in ('pie', 'donut', 'doughnut'):
            return cls._build_pie_payload(data_df, x_col, y_col)
        else:
            return cls._build_scatter_payload(data_df, x_col, y_col, group_col)

    @staticmethod
    def _build_scatter_payload(df: pd.DataFrame, x_col: str, y_col: str, group_col: str) -> dict:
        if not x_col or x_col not in df.columns or not y_col or y_col not in df.columns:
            # Fallback to first numerical columns
            nums = df.select_dtypes(include=[np.number]).columns.tolist()
            x_col = x_col if x_col in df.columns else (nums[0] if len(nums) > 0 else df.columns[0])
            y_col = y_col if y_col in df.columns else (nums[1] if len(nums) > 1 else x_col)

        datasets = []
        palette = ['#00A4EF', '#1E3A8A', '#F97316', '#10B981', '#F59E0B', '#8B5CF6', '#EC4899', '#06B6D4']

        board_col = 'Board' if 'Board' in df.columns else group_col

        if group_col and group_col in df.columns:
            groups = df.groupby(group_col)
            for idx, (name, group_data) in enumerate(groups):
                pts = []
                for _, row in group_data.iterrows():
                    b_val = str(row[board_col]) if board_col and board_col in row else 'N/A'
                    pts.append({
                        'x': float(row[x_col]) if pd.notnull(row[x_col]) else 0,
                        'y': float(row[y_col]) if pd.notnull(row[y_col]) else 0,
                        'board': b_val,
                        'is_outlier': bool(row.get('_is_outlier', False))
                    })
                datasets.append({
                    'label': str(name),
                    'data': pts,
                    'color': palette[idx % len(palette)]
                })
        else:
            pts = []
            for _, row in df.iterrows():
                b_val = str(row[board_col]) if board_col and board_col in row else 'N/A'
                pts.append({
                    'x': float(row[x_col]) if pd.notnull(row[x_col]) else 0,
                    'y': float(row[y_col]) if pd.notnull(row[y_col]) else 0,
                    'board': b_val,
                    'is_outlier': bool(row.get('_is_outlier', False))
                })
            datasets.append({
                'label': f'{x_col} vs {y_col}',
                'data': pts,
                'color': palette[0]
            })

        return {
            'x_col': x_col,
            'y_col': y_col,
            'group_col': group_col,
            'datasets': datasets
        }

    @staticmethod
    def _build_categorical_payload(df: pd.DataFrame, x_col: str, y_col: str, group_col: str, vtype: str) -> dict:
        if not x_col or x_col not in df.columns:
            x_col = df.columns[0]
        
        if y_col and y_col in df.columns:
            grouped = df.groupby(x_col)[y_col].mean().reset_index()
            labels = [str(v) for v in grouped[x_col]]
            values = [float(v) for v in grouped[y_col]]
        else:
            counts = df[x_col].value_counts().reset_index()
            counts.columns = [x_col, 'count']
            labels = [str(v) for v in counts[x_col]]
            values = [int(v) for v in counts['count']]

        return {
            'labels': labels,
            'datasets': [{'label': y_col or 'Count', 'data': values}],
            'x_col': x_col,
            'y_col': y_col
        }

    @staticmethod
    def _build_pie_payload(df: pd.DataFrame, x_col: str, y_col: str) -> dict:
        if not x_col or x_col not in df.columns:
            x_col = df.columns[0]
        
        counts = df[x_col].value_counts().head(10).reset_index()
        counts.columns = [x_col, 'count']
        
        return {
            'labels': [str(v) for v in counts[x_col]],
            'datasets': [{'data': [int(v) for v in counts['count']]}],
            'x_col': x_col
        }
