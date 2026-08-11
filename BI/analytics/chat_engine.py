# BI/analytics/chat_engine.py
import re
import os
import json
import pandas as pd
import numpy as np
from django.conf import settings
from .services import DatasetEngine

class DataChatEngine:
    """
    Intelligent Data Analytics & Chat Engine for querying CSV, JSON, Excel, and MongoDB datasets.
    Executes real-time Pandas operations and generates rich text explanations, KPI cards,
    structured summary tables, and suggested prompt follow-ups.
    """

    @staticmethod
    def process_query(dataset, query_text):
        if not query_text or not query_text.strip():
            return {
                'response': "Please enter a question or request about your dataset.",
                'kpis': [],
                'table': None,
                'suggested_prompts': ["Summarize this dataset", "Show missing values", "Top 5 rows"]
            }

        text = query_text.strip()
        lower_text = text.lower()

        try:
            df = DatasetEngine.load_dataframe(dataset)
        except Exception as e:
            return {
                'response': f"⚠️ Unable to load dataset '{dataset.name}': {str(e)}",
                'kpis': [],
                'table': None,
                'suggested_prompts': ["Check dataset file"]
            }

        if df.empty:
            return {
                'response': f"The dataset **{dataset.name}** is currently empty or contains no records.",
                'kpis': [{'label': 'Total Rows', 'value': 0}],
                'table': None,
                'suggested_prompts': ["Upload another dataset", "Check MongoDB connection"]
            }

        # 1. Dataset Overview / Summary Query
        if any(k in lower_text for k in ['summarize', 'summary', 'overview', 'about', 'dataset info', 'describe', 'explain']):
            return DataChatEngine._generate_summary(dataset, df)

        # 2. Chart / Plot / Visualization Query
        if any(k in lower_text for k in ['plot', 'chart', 'graph', 'visualize', 'visual', 'scatter', 'draw']):
            return DataChatEngine._generate_chart_info(dataset, df, text, lower_text)

        # 3. Missing Values / Data Quality Query
        if any(k in lower_text for k in ['null', 'missing', 'quality', 'clean', 'blank', 'health', 'dup', 'duplicate']):
            return DataChatEngine._generate_data_health(dataset, df)

        # 4. Top / Highest / Bottom / Lowest Rows
        if any(k in lower_text for k in ['top', 'highest', 'max', 'bottom', 'lowest', 'min', 'first', 'last', 'rank']):
            return DataChatEngine._generate_top_bottom_rows(dataset, df, text, lower_text)

        # 5. Aggregations (Average, Sum, Count, Min, Max)
        if any(k in lower_text for k in ['average', 'avg', 'mean', 'sum', 'total', 'count', 'maximum', 'minimum']):
            return DataChatEngine._generate_aggregation(dataset, df, text, lower_text)

        # 5. Group breakdown / Distribution query
        if any(k in lower_text for k in ['by', 'group', 'breakdown', 'distribution', 'category', 'categorize']):
            return DataChatEngine._generate_group_breakdown(dataset, df, text, lower_text)

        # 6. Search / Filter query for specific values
        if any(k in lower_text for k in ['show', 'filter', 'where', 'find', 'search']):
            return DataChatEngine._generate_filtered_search(dataset, df, text, lower_text)

        # Fallback: Intelligent Column Matching & General Query Answer
        return DataChatEngine._generate_smart_fallback(dataset, df, text, lower_text)

    @staticmethod
    def _generate_summary(dataset, df):
        num_rows = len(df)
        num_cols = len(df.columns)
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()

        kpis = [
            {'label': 'Total Records', 'value': f"{num_rows:,}"},
            {'label': 'Total Columns', 'value': num_cols},
            {'label': 'Numeric Fields', 'value': len(numeric_cols)},
            {'label': 'Categorical Fields', 'value': len(categorical_cols)}
        ]

        # Build column breakdown table
        cols_info = []
        for col in df.columns:
            dtype = str(df[col].dtype)
            null_cnt = int(df[col].isnull().sum())
            uniq_cnt = int(df[col].nunique())

            sample_str = ", ".join([str(x) for x in df[col].dropna().unique()[:3]])
            if len(sample_str) > 40:
                sample_str = sample_str[:37] + "..."

            cols_info.append({
                'Column Name': col,
                'Data Type': dtype,
                'Unique Values': uniq_cnt,
                'Missing Count': null_cnt,
                'Sample Values': sample_str or 'N/A'
            })

        table_headers = ['Column Name', 'Data Type', 'Unique Values', 'Missing Count', 'Sample Values']
        table_rows = cols_info[:15]

        resp = f"📊 **Dataset Summary for '{dataset.name}'**\n\n"
        resp += f"- **Format**: `{dataset.file_type.upper()}`\n"
        resp += f"- **Total Rows**: **{num_rows:,}** rows\n"
        resp += f"- **Total Columns**: **{num_cols}** columns\n"
        if numeric_cols:
            resp += f"- **Key Metrics**: {', '.join([f'`{c}`' for c in numeric_cols[:5]])}\n"
        if categorical_cols:
            resp += f"- **Dimensions**: {', '.join([f'`{c}`' for c in categorical_cols[:5]])}\n"

        prompts = [
            "What is the average of numerical columns?",
            "Show missing values health check",
            "Show top 10 records",
            f"Breakdown by {categorical_cols[0]}" if categorical_cols else "Show numerical breakdown"
        ]

        return {
            'response': resp,
            'kpis': kpis,
            'table': {'headers': table_headers, 'rows': table_rows},
            'suggested_prompts': prompts
        }

    @staticmethod
    def _generate_chart_info(dataset, df, text, lower_text):
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()

        kpis = [
            {'label': 'Dataset Format', 'value': dataset.file_type.upper()},
            {'label': 'Total Records', 'value': f"{len(df):,}"},
            {'label': 'Plottable Metrics', 'value': len(numeric_cols)},
            {'label': 'Dimensions', 'value': len(categorical_cols)}
        ]

        chart_options = []
        if numeric_cols and len(numeric_cols) >= 2:
            chart_options.append({
                'Chart Type': 'Scatter Plot 📈',
                'X Axis': numeric_cols[0],
                'Y Axis': numeric_cols[1],
                'Group By': categorical_cols[0] if categorical_cols else 'None'
            })
        if numeric_cols and categorical_cols:
            chart_options.append({
                'Chart Type': 'Bar / Column Chart 📊',
                'X Axis': categorical_cols[0],
                'Y Axis': numeric_cols[0],
                'Group By': 'Aggregation (AVG/SUM)'
            })
        chart_options.append({
            'Chart Type': 'KPI Summary Card 🏆',
            'X Axis': 'N/A',
            'Y Axis': numeric_cols[0] if numeric_cols else df.columns[0],
            'Group By': 'Total Count / Sum'
        })

        resp = f"📊 **Chart & Visualization Engine for '{dataset.name}'**\n\n"
        resp += f"You can plot interactive charts and query metrics directly from your dataset! Here are recommended plot options based on your dataset columns:\n\n"
        if numeric_cols:
            resp += f"- **Numerical Metrics**: {', '.join([f'`{c}`' for c in numeric_cols[:5]])}\n"
        if categorical_cols:
            resp += f"- **Categorical Dimensions**: {', '.join([f'`{c}`' for c in categorical_cols[:5]])}\n"

        prompts = []
        if numeric_cols and categorical_cols:
            prompts.append(f"Breakdown of {numeric_cols[0]} by {categorical_cols[0]}")
        if numeric_cols:
            prompts.append(f"Average of {numeric_cols[0]}")
            prompts.append(f"Top 5 highest {numeric_cols[0]}")
        prompts.append("Summarize this dataset")

        return {
            'response': resp,
            'kpis': kpis,
            'table': {'headers': ['Chart Type', 'X Axis', 'Y Axis', 'Group By'], 'rows': chart_options},
            'suggested_prompts': prompts
        }

    @staticmethod
    def _generate_data_health(dataset, df):

        num_rows = len(df)
        total_cells = num_rows * len(df.columns)
        total_missing = int(df.isnull().sum().sum())
        quality_score = round(max(0, 100 - (total_missing / max(1, total_cells) * 100)), 1)
        duplicate_rows = int(df.duplicated().sum())

        kpis = [
            {'label': 'Data Quality Score', 'value': f"{quality_score}%"},
            {'label': 'Total Missing Cells', 'value': f"{total_missing:,}"},
            {'label': 'Duplicate Rows', 'value': f"{duplicate_rows:,}"},
            {'label': 'Total Records', 'value': f"{num_rows:,}"}
        ]

        null_summary = []
        for col in df.columns:
            null_cnt = int(df[col].isnull().sum())
            null_pct = round((null_cnt / num_rows) * 100, 2)
            status = '✅ Clean' if null_cnt == 0 else ('⚠️ Moderate' if null_pct < 20 else '❌ High Missing')
            null_summary.append({
                'Column': col,
                'Missing Rows': null_cnt,
                'Missing %': f"{null_pct}%",
                'Status': status
            })

        null_summary.sort(key=lambda x: x['Missing Rows'], reverse=True)

        resp = f"🛡️ **Data Health & Quality Report for '{dataset.name}'**\n\n"
        resp += f"- **Quality Rating**: **{quality_score}%** clean data.\n"
        resp += f"- **Missing Data**: `{total_missing}` missing entries out of `{total_cells}` total data cells.\n"
        resp += f"- **Duplicates**: Found `{duplicate_rows}` duplicated rows.\n"

        return {
            'response': resp,
            'kpis': kpis,
            'table': {'headers': ['Column', 'Missing Rows', 'Missing %', 'Status'], 'rows': null_summary[:15]},
            'suggested_prompts': ["Summarize this dataset", "Show top 10 records", "Calculate averages"]
        }

    @staticmethod
    def _generate_top_bottom_rows(dataset, df, text, lower_text):
        is_bottom = any(k in lower_text for k in ['bottom', 'lowest', 'min', 'least'])
        
        # Extract requested count (e.g. "top 5", "top 10")
        match = re.search(r'\b(\d+)\b', text)
        limit = int(match.group(1)) if match else 5
        limit = min(50, max(1, limit))

        # Find matching column name in text
        target_col = DataChatEngine._find_matching_column(df, lower_text)
        if not target_col:
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            target_col = numeric_cols[0] if numeric_cols else df.columns[0]

        try:
            sorted_df = df.sort_values(by=target_col, ascending=is_bottom).head(limit)
            rows = sorted_df.fillna('').to_dict(orient='records')

            order_str = "lowest" if is_bottom else "highest"
            resp = f"🏆 **Top {limit} Records by `{target_col}` ({order_str})**\n\n"
            resp += f"Showing top {len(rows)} rows ordered by `{target_col}`:"

            first_val = sorted_df[target_col].iloc[0] if len(sorted_df) > 0 else 'N/A'
            kpis = [
                {'label': f"{order_str.title()} {target_col}", 'value': str(first_val)},
                {'label': 'Records Returned', 'value': len(rows)},
                {'label': 'Total Records', 'value': len(df)}
            ]

            headers = list(df.columns[:8])
            clean_rows = [{h: str(r.get(h, '')) for h in headers} for r in rows]

            return {
                'response': resp,
                'kpis': kpis,
                'table': {'headers': headers, 'rows': clean_rows},
                'suggested_prompts': [f"Show top {limit*2} records", f"Average of {target_col}", "Summarize dataset"]
            }
        except Exception as e:
            return DataChatEngine._generate_summary(dataset, df)

    @staticmethod
    def _generate_aggregation(dataset, df, text, lower_text):
        target_col = DataChatEngine._find_matching_column(df, lower_text)
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

        if not target_col and numeric_cols:
            target_col = numeric_cols[0]

        if not target_col or target_col not in df.columns:
            return {
                'response': f"Could not find numerical column to aggregate. Available columns: {', '.join(df.columns[:6])}",
                'kpis': [],
                'table': None,
                'suggested_prompts': ["Summarize this dataset", "Show missing values"]
            }

        series = pd.to_numeric(df[target_col], errors='coerce').dropna()
        if series.empty:
            return {
                'response': f"Column `{target_col}` contains no numerical values to calculate aggregation.",
                'kpis': [],
                'table': None,
                'suggested_prompts': ["Summarize this dataset"]
            }

        mean_val = round(float(series.mean()), 2)
        sum_val = round(float(series.sum()), 2)
        min_val = round(float(series.min()), 2)
        max_val = round(float(series.max()), 2)
        std_val = round(float(series.std()), 2) if len(series) > 1 else 0.0

        kpis = [
            {'label': f'Average ({target_col})', 'value': f"{mean_val:,}"},
            {'label': f'Total Sum', 'value': f"{sum_val:,}"},
            {'label': f'Min Value', 'value': f"{min_val:,}"},
            {'label': f'Max Value', 'value': f"{max_val:,}"}
        ]

        resp = f"📈 **Statistical Analysis for `{target_col}`**\n\n"
        resp += f"- **Average (Mean)**: **{mean_val:,}**\n"
        resp += f"- **Sum**: **{sum_val:,}**\n"
        resp += f"- **Minimum**: **{min_val:,}**\n"
        resp += f"- **Maximum**: **{max_val:,}**\n"
        resp += f"- **Standard Deviation**: **{std_val:,}**\n"
        resp += f"- **Sample Count**: **{len(series):,}** valid records\n"

        # Check for group dimension
        group_col = None
        for col in df.columns:
            if col != target_col and lower_text.find(col.lower()) != -1:
                group_col = col
                break

        table_data = None
        if group_col:
            grouped = df.groupby(group_col)[target_col].agg(['mean', 'sum', 'count']).reset_index()
            grouped.columns = [group_col, f'Average {target_col}', f'Sum {target_col}', 'Record Count']
            grouped = grouped.round(2).sort_values(by=f'Average {target_col}', ascending=False).head(15)
            table_rows = grouped.fillna('').to_dict(orient='records')
            table_data = {'headers': [group_col, f'Average {target_col}', f'Sum {target_col}', 'Record Count'], 'rows': table_rows}
            resp += f"\nBreakdown by **`{group_col}`** calculated below:"

        prompts = [
            f"Top 5 highest {target_col}",
            f"Breakdown of {target_col} by Board" if 'Board' in df.columns else "Summarize dataset",
            "Show data health check"
        ]

        return {
            'response': resp,
            'kpis': kpis,
            'table': table_data,
            'suggested_prompts': prompts
        }

    @staticmethod
    def _generate_group_breakdown(dataset, df, text, lower_text):
        cat_col = DataChatEngine._find_matching_column(df, lower_text)
        num_col = None

        if not cat_col:
            cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
            cat_col = cat_cols[0] if cat_cols else df.columns[0]

        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        for col in numeric_cols:
            if col.lower() != cat_col.lower() and col.lower() in lower_text:
                num_col = col
                break

        if not num_col and numeric_cols:
            num_col = numeric_cols[0]

        if num_col and num_col in df.columns:
            grouped = df.groupby(cat_col)[num_col].agg(['mean', 'sum', 'count']).reset_index()
            grouped.columns = [cat_col, f'Avg {num_col}', f'Total {num_col}', 'Count']
            grouped = grouped.round(2).sort_values(by=f'Avg {num_col}', ascending=False).head(15)
            table_rows = grouped.fillna('').to_dict(orient='records')
            headers = [cat_col, f'Avg {num_col}', f'Total {num_col}', 'Count']

            top_cat = grouped.iloc[0][cat_col] if not grouped.empty else 'N/A'
            top_val = grouped.iloc[0][f'Avg {num_col}'] if not grouped.empty else 'N/A'

            kpis = [
                {'label': f'Top Category ({cat_col})', 'value': str(top_cat)},
                {'label': f'Highest Avg {num_col}', 'value': str(top_val)},
                {'label': 'Categories Analyzed', 'value': len(grouped)}
            ]

            resp = f"📊 **Group Breakdown: `{num_col}` grouped by `{cat_col}`**\n\n"
            resp += f"Showing top category breakdowns sorted by average `{num_col}`:"
            return {
                'response': resp,
                'kpis': kpis,
                'table': {'headers': headers, 'rows': table_rows},
                'suggested_prompts': [f"Show top 5 {num_col}", f"Average of {num_col}", "Summarize dataset"]
            }

        # Categorical distribution value counts
        counts = df[cat_col].value_counts().reset_index()
        counts.columns = [cat_col, 'Frequency Count']
        counts['Percentage'] = (counts['Frequency Count'] / len(df) * 100).round(2).astype(str) + '%'
        table_rows = counts.head(15).to_dict(orient='records')

        kpis = [
            {'label': f'Most Frequent {cat_col}', 'value': str(counts.iloc[0][cat_col]) if not counts.empty else 'N/A'},
            {'label': 'Unique Categories', 'value': df[cat_col].nunique()},
            {'label': 'Total Records', 'value': len(df)}
        ]

        resp = f"📌 **Distribution of Categories for `{cat_col}`**"
        return {
            'response': resp,
            'kpis': kpis,
            'table': {'headers': [cat_col, 'Frequency Count', 'Percentage'], 'rows': table_rows},
            'suggested_prompts': ["Summarize this dataset", "Show missing values", "Top 5 records"]
        }

    @staticmethod
    def _generate_filtered_search(dataset, df, text, lower_text):
        col_matched = DataChatEngine._find_matching_column(df, lower_text)
        
        # Search for explicit string matches
        matches = []
        if col_matched:
            for val in df[col_matched].dropna().unique():
                val_str = str(val).lower()
                if val_str in lower_text or any(w in val_str for w in lower_text.split()):
                    matches.append((col_matched, val))

        if matches:
            target_col, target_val = matches[0]
            filtered_df = df[df[target_col].astype(str) == str(target_val)].head(20)
            rows = filtered_df.fillna('').to_dict(orient='records')
            headers = list(df.columns[:8])
            clean_rows = [{h: str(r.get(h, '')) for h in headers} for r in rows]

            kpis = [
                {'label': f'Filter Condition', 'value': f"{target_col} = '{target_val}'"},
                {'label': 'Matching Records', 'value': len(filtered_df)},
                {'label': 'Total Records', 'value': len(df)}
            ]

            resp = f"🔍 **Filtered Results for `{target_col}` = `{target_val}`**\n\nFound **{len(filtered_df):,}** matching records:"
            return {
                'response': resp,
                'kpis': kpis,
                'table': {'headers': headers, 'rows': clean_rows},
                'suggested_prompts': ["Summarize dataset", f"Average metrics for {target_val}", "Clear filter"]
            }

        # Fallback to top records preview
        preview_df = df.head(10).fillna('')
        headers = list(df.columns[:8])
        clean_rows = [{h: str(r.get(h, '')) for h in preview_df.to_dict(orient='records')}]

        return {
            'response': f"Showing top 10 records from **{dataset.name}**:",
            'kpis': [{'label': 'Total Records', 'value': len(df)}],
            'table': {'headers': headers, 'rows': clean_rows},
            'suggested_prompts': ["Summarize dataset", "Show missing values", "Calculate averages"]
        }

    @staticmethod
    def _generate_smart_fallback(dataset, df, text, lower_text):
        col = DataChatEngine._find_matching_column(df, lower_text)
        if col:
            if pd.api.types.is_numeric_dtype(df[col]):
                return DataChatEngine._generate_aggregation(dataset, df, text, lower_text)
            else:
                return DataChatEngine._generate_group_breakdown(dataset, df, text, lower_text)

        return DataChatEngine._generate_summary(dataset, df)

    @staticmethod
    def _find_matching_column(df, lower_text):
        for col in df.columns:
            if col.lower() in lower_text:
                return col
        return None
