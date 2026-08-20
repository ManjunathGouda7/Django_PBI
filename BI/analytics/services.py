import os
import json
import pandas as pd
import numpy as np
from django.conf import settings

# In-memory DataFrame cache: {dataset_id: DataFrame}
_df_cache = {}

class DatasetEngine:
    @staticmethod
    def infer_column_schema(df):
        columns = []
        for col in df.columns:
            dtype = df[col].dtype
            col_name = str(col).strip()

            if pd.api.types.is_numeric_dtype(dtype):
                col_type = 'numeric'
            elif pd.api.types.is_datetime64_any_dtype(dtype):
                col_type = 'date'
            else:
                sample_vals = df[col].dropna().head(10).astype(str)
                is_date = False
                try:
                    if not sample_vals.empty:
                        pd.to_datetime(sample_vals, format='mixed', errors='raise')
                        is_date = True
                except Exception:
                    is_date = False

                if is_date:
                    col_type = 'date'
                else:
                    col_type = 'categorical'

            unique_count = int(df[col].nunique())
            null_count = int(df[col].isnull().sum())
            sample_values = [str(x) for x in df[col].dropna().unique()[:5]]

            min_val = None
            max_val = None
            if col_type == 'numeric':
                min_val = float(df[col].min()) if not df[col].dropna().empty else None
                max_val = float(df[col].max()) if not df[col].dropna().empty else None

            columns.append({
                'name': col_name,
                'type': col_type,
                'unique_count': unique_count,
                'null_count': null_count,
                'samples': sample_values,
                'min': min_val,
                'max': max_val
            })
        return columns

    @staticmethod
    def load_dataframe(dataset):
        cache_key = dataset.id
        if cache_key in _df_cache:
            return _df_cache[cache_key].copy()

        possible_paths = [
            os.path.join(settings.BASE_DIR.parent, 'data', 'GRL.25MPLA.json'),
            os.path.join(settings.BASE_DIR, 'data', 'GRL.25MPLA.json'),
            os.path.join(settings.BASE_DIR, 'GRL.25MPLA.json')
        ]

        if dataset.file_type == 'mongodb':
            import pymongo
            url = dataset.connection_url or "mongodb://192.168.100.123:27017"
            db_name = dataset.db_name or "GRL"
            coll_name = dataset.collection_name or "25MPLA"

            try:
                client = pymongo.MongoClient(url, serverSelectionTimeoutMS=500)
                db = client[db_name]
                coll = db[coll_name]
                docs = list(coll.find({}, {'_id': False}).limit(10000))
                if docs:
                    df = pd.json_normalize(docs)
                    _df_cache[cache_key] = df
                    return df.copy()
            except Exception as e:
                print(f"MongoDB server ({url}) not reachable. Using local fallback.")

            for j_path in possible_paths:
                if os.path.exists(j_path):
                    df = pd.read_json(j_path)
                    if '_id' in df.columns:
                        df = df.drop(columns=['_id'])
                    _df_cache[cache_key] = df
                    return df.copy()

        if not dataset.file:
            for j_path in possible_paths:
                if os.path.exists(j_path):
                    df = pd.read_json(j_path)
                    if '_id' in df.columns:
                        df = df.drop(columns=['_id'])
                    _df_cache[cache_key] = df
                    return df.copy()

            # Synthetic sample dataset fallback for CI/Test environments
            mock_df = pd.DataFrame({
                'Board': ['GTPT106', 'GTPT118', 'TPR129_GTPT', 'TPR131_GTPT', 'GTPT142', 'GTPT106', 'GTPT118', 'TPR129_GTPT'],
                'Power': [10.5, 12.0, 15.2, 14.8, 11.2, 25.0, 9.8, 13.4],
                'PFO_mW': [120.0, 145.0, 180.0, 160.0, 130.0, 320.0, 110.0, 150.0],
                'Rectified_Power_W': [1.2, 1.45, 1.8, 1.6, 1.3, 3.2, 1.1, 1.5],
                'PowerMode': ['Normal', 'High', 'Normal', 'Low', 'Normal', 'High', 'Low', 'Normal'],
                'Timestamp': ['2026-08-10 10:00:00', '2026-08-10 10:01:00', '2026-08-10 10:02:00', '2026-08-10 10:03:00', '2026-08-10 10:04:00', '2026-08-10 10:05:00', '2026-08-10 10:06:00', '2026-08-10 10:07:00']
            })
            _df_cache[cache_key] = mock_df
            return mock_df.copy()

        filepath = dataset.file.path
        if not os.path.exists(filepath):
            mock_df = pd.DataFrame({
                'Board': ['GTPT106', 'GTPT118', 'TPR129_GTPT', 'TPR131_GTPT', 'GTPT142'],
                'Power': [10.5, 12.0, 15.2, 14.8, 11.2],
                'PFO_mW': [120.0, 145.0, 180.0, 160.0, 130.0],
                'Rectified_Power_W': [1.2, 1.45, 1.8, 1.6, 1.3],
                'PowerMode': ['Normal', 'High', 'Normal', 'Low', 'Normal'],
                'Timestamp': ['2026-08-10 10:00:00', '2026-08-10 10:01:00', '2026-08-10 10:02:00', '2026-08-10 10:03:00', '2026-08-10 10:04:00']
            })
            _df_cache[cache_key] = mock_df
            return mock_df.copy()

        if dataset.file_type == 'json' or filepath.endswith('.json'):
            df = pd.read_json(filepath)
            if '_id' in df.columns:
                df = df.drop(columns=['_id'])
        elif dataset.file_type == 'csv' or filepath.endswith('.csv'):
            df = pd.read_csv(filepath)
        elif dataset.file_type == 'excel' or filepath.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(filepath)
        else:
            df = pd.read_csv(filepath)

        _df_cache[cache_key] = df
        return df.copy()

    @staticmethod
    def load_dataframe_chunks(dataset, chunksize=10000):
        """
        Memory-efficient streaming generator for massive CSV telemetry datasets.
        Yields DataFrames in streaming chunks of specified size.
        """
        if dataset.file and os.path.exists(dataset.file.path) and (dataset.file_type == 'csv' or dataset.file.path.endswith('.csv')):
            for chunk in pd.read_csv(dataset.file.path, chunksize=chunksize):
                yield chunk
        else:
            df = DatasetEngine.load_dataframe(dataset)
            if df.empty:
                yield df
            else:
                for i in range(0, len(df), chunksize):
                    yield df.iloc[i:i + chunksize]



    @staticmethod
    def clear_cache(dataset_id=None):
        """
        Clears in-memory DataFrame cache for dataset updates.
        """
        global _df_cache
        if dataset_id:
            _df_cache.pop(dataset_id, None)
        else:
            _df_cache.clear()

    @staticmethod
    def get_mongodb_collections(connection_url="mongodb://192.168.100.123:27017", db_name="GRL"):

        import pymongo
        try:
            client = pymongo.MongoClient(connection_url, serverSelectionTimeoutMS=3000)
            dbs = client.list_database_names()
            collections = []
            if db_name in dbs:
                collections = client[db_name].list_collection_names()
            return {'status': 'success', 'databases': dbs, 'collections': collections}
        except Exception as e:
            return {'status': 'error', 'message': str(e), 'databases': ['GRL'], 'collections': ['25MPLA']}

    @staticmethod
    def push_json_to_mongodb(connection_url="mongodb://192.168.100.123:27017", db_name="GRL", collection_name="25MPLA", json_filepath=None):
        import pymongo
        if not json_filepath:
            json_filepath = os.path.join(settings.BASE_DIR.parent, 'data', 'GRL.25MPLA.json')

        if not os.path.exists(json_filepath):
            raise FileNotFoundError(f"JSON data file not found at {json_filepath}")

        client = pymongo.MongoClient(connection_url, serverSelectionTimeoutMS=5000)
        db = client[db_name]
        coll = db[collection_name]

        with open(json_filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if isinstance(data, list) and len(data) > 0:
            chunk_size = 5000
            inserted_count = 0
            for i in range(0, len(data), chunk_size):
                chunk = data[i:i + chunk_size]
                for doc in chunk:
                    if '_id' in doc and not isinstance(doc['_id'], dict):
                        del doc['_id']
                res = coll.insert_many(chunk)
                inserted_count += len(res.inserted_ids)
            return inserted_count
        return 0

    @staticmethod
    def query_widget_data(dataset, widget, filters=None):
        df = DatasetEngine.load_dataframe(dataset)

        if filters:
            for col, filter_val in filters.items():
                if col in df.columns:
                    if isinstance(filter_val, list) and len(filter_val) > 0:
                        df = df[df[col].astype(str).isin([str(v) for v in filter_val])]
                    elif isinstance(filter_val, dict):
                        if 'min' in filter_val and filter_val['min'] is not None:
                            df = df[df[col] >= float(filter_val['min'])]
                        if 'max' in filter_val and filter_val['max'] is not None:
                            df = df[df[col] <= float(filter_val['max'])]
                    elif filter_val is not None and filter_val != '':
                        df = df[df[col].astype(str) == str(filter_val)]

        visual_type = widget.visual_type
        x_col = widget.x_axis
        y_col = widget.y_axis
        agg = widget.aggregation.upper() if widget.aggregation else 'SUM'

        if df.empty:
            return {
                'labels': [],
                'datasets': [{'label': y_col or 'Value', 'data': []}],
                'raw_table': [],
                'kpi_value': 0
            }

        agg_map = {'SUM': 'sum', 'AVG': 'mean', 'COUNT': 'count', 'MIN': 'min', 'MAX': 'max'}
        agg_func = agg_map.get(agg, 'sum')

        if visual_type == 'kpi':
            kpi_val = 0
            if y_col and y_col in df.columns:
                series = pd.to_numeric(df[y_col], errors='coerce').dropna()
                if agg == 'SUM':
                    kpi_val = float(series.sum())
                elif agg == 'AVG':
                    kpi_val = float(series.mean()) if len(series) > 0 else 0.0
                elif agg == 'COUNT':
                    kpi_val = int(df[y_col].count())
                elif agg == 'MIN':
                    kpi_val = float(series.min()) if len(series) > 0 else 0.0
                elif agg == 'MAX':
                    kpi_val = float(series.max()) if len(series) > 0 else 0.0
            else:
                kpi_val = len(df)

            return {
                'kpi_value': round(kpi_val, 2),
                'kpi_label': f"{agg} of {y_col}" if y_col else "Total Records",
                'total_records': len(df)
            }

        if visual_type == 'table':
            if x_col and y_col and x_col in df.columns and y_col in df.columns:
                grouped = df.groupby(x_col)[y_col].agg(agg_func).reset_index()
                grouped.columns = [x_col, f"{agg} of {y_col}"]
                records = grouped.round(2).to_dict(orient='records')
            else:
                records = df.head(100).fillna('').to_dict(orient='records')
            return {
                'table_headers': list(records[0].keys()) if records else [],
                'raw_table': records
            }

        if visual_type == 'scatter':
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            if not (x_col and x_col in df.columns):
                x_col = numeric_cols[0] if numeric_cols else (df.columns[0] if not df.empty else None)
            if not (y_col and y_col in df.columns):
                y_col = numeric_cols[1] if len(numeric_cols) > 1 else (numeric_cols[0] if numeric_cols else (df.columns[-1] if not df.empty else None))

            if x_col and y_col and x_col in df.columns and y_col in df.columns:
                try:

                    group_col = widget.group_by if (widget.group_by and widget.group_by in df.columns) else None
                    if not group_col:
                        for candidate in ['Board', 'PowerMode', 'Power', 'DUT', 'CRX', 'RUN']:
                            if candidate in df.columns:
                                group_col = candidate
                                break

                    colors = ['#00A4EF', '#002060', '#F25022', '#7FBA00', '#FFB900', '#6B69D6', '#E3008C', '#10b981', '#a855f7', '#ec4899']
                    datasets = []

                    if group_col:
                        groups = df[group_col].dropna().unique()[:15]
                        for i, g_val in enumerate(groups):
                            sub_df = df[df[group_col] == g_val][[x_col, y_col]].dropna()
                            x_nums = pd.to_numeric(sub_df[x_col], errors='coerce')
                            y_nums = pd.to_numeric(sub_df[y_col], errors='coerce')
                            valid_mask = x_nums.notnull() & y_nums.notnull() & (x_nums >= -5) & (y_nums >= -1000) & (y_nums <= 1000)

                            x_arr = np.round(x_nums[valid_mask].head(2500).to_numpy(), 2).tolist()
                            y_arr = np.round(y_nums[valid_mask].head(2500).to_numpy(), 2).tolist()

                            points = [{'x': x, 'y': y} for x, y in zip(x_arr, y_arr)]
                            if points:
                                datasets.append({
                                    'label': str(g_val),
                                    'data': points,
                                    'color': colors[i % len(colors)]
                                })
                    else:
                        sub_df = df[[x_col, y_col]].dropna()
                        x_nums = pd.to_numeric(sub_df[x_col], errors='coerce')
                        y_nums = pd.to_numeric(sub_df[y_col], errors='coerce')
                        valid_mask = x_nums.notnull() & y_nums.notnull() & (x_nums >= -5) & (y_nums >= -1000) & (y_nums <= 1000)

                        x_arr = np.round(x_nums[valid_mask].head(4000).to_numpy(), 2).tolist()
                        y_arr = np.round(y_nums[valid_mask].head(4000).to_numpy(), 2).tolist()

                        points = [{'x': x, 'y': y} for x, y in zip(x_arr, y_arr)]
                        datasets.append({
                            'label': f"{y_col} vs {x_col}",
                            'data': points,
                            'color': '#00A4EF'
                        })

                    # Calculate Target Specification Limits (Upper & Lower Bounds)
                    target_upper = None
                    target_lower = None
                    anomalies = []
                    all_y = pd.to_numeric(df[y_col], errors='coerce').dropna()
                    if not all_y.empty:
                        y_mean = float(all_y.mean())
                        y_std = float(all_y.std())
                        target_upper = round(y_mean + 2 * y_std, 2)
                        target_lower = round(max(0, y_mean - 2 * y_std), 2)

                    return {
                        'labels': [],
                        'datasets': datasets,
                        'x_col': x_col,
                        'y_col': y_col,
                        'group_col': group_col or '',
                        'target_upper': target_upper,
                        'target_lower': target_lower
                    }
                except Exception as e:
                    print(f"Scatter plot error: {e}")

        if not x_col or x_col not in df.columns:
            x_col = df.columns[0]
        if not y_col or y_col not in df.columns:
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            y_col = numeric_cols[0] if len(numeric_cols) > 0 else df.columns[1]

        if y_col in df.columns and not pd.api.types.is_numeric_dtype(df[y_col]):
            agg_func = 'count'

        try:
            grouped = df.groupby(x_col)[y_col].agg(agg_func).reset_index()
            grouped = grouped.sort_values(by=y_col, ascending=False).head(20)

            labels = [str(val) for val in grouped[x_col].tolist()]
            values = [round(float(val), 2) for val in grouped[y_col].tolist()]

            return {
                'labels': labels,
                'datasets': [{
                    'label': f"{agg} of {y_col}",
                    'data': values
                }],
                'x_col': x_col,
                'y_col': y_col,
                'agg': agg
            }
        except Exception as e:
            return {
                'error': str(e),
                'labels': [],
                'datasets': [{'label': 'Error', 'data': []}]
            }

import re

class DatasetValidator:
    ALLOWED_EXTENSIONS = {'.csv', '.xlsx', '.xls', '.json'}
    
    @staticmethod
    def validate_file_extension(filename):
        ext = os.path.splitext(filename)[1].lower()
        if ext not in DatasetValidator.ALLOWED_EXTENSIONS:
            raise ValueError(f"Unsupported file extension '{ext}'. Allowed extensions: {', '.join(sorted(DatasetValidator.ALLOWED_EXTENSIONS))}")
        return True

    @staticmethod
    def validate_file_size(file_obj, max_mb=None):
        if max_mb is None:
            max_mb = getattr(settings, 'MAX_UPLOAD_SIZE_MB', 50)
        size_mb = file_obj.size / (1024 * 1024)
        if size_mb > max_mb:
            raise ValueError(f"File size ({size_mb:.1f} MB) exceeds maximum allowed limit of {max_mb} MB")
        return True

    @staticmethod
    def validate_and_parse(file_obj, file_type):
        filename = getattr(file_obj, 'name', 'file')
        DatasetValidator.validate_file_extension(filename)
        DatasetValidator.validate_file_size(file_obj)

        try:
            file_obj.seek(0)
            if file_type == 'json' or filename.lower().endswith('.json'):
                df = pd.read_json(file_obj)
            elif file_type == 'excel' or filename.lower().endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file_obj)
            else:
                df = pd.read_csv(file_obj)
            file_obj.seek(0)
            
            if df.empty:
                raise ValueError("Uploaded dataset file is empty.")
            
            cleaned_df = DatasetValidator.sanitize_columns(df)
            return cleaned_df
        except Exception as e:
            file_obj.seek(0)
            if isinstance(e, ValueError):
                raise e
            raise ValueError(f"Corrupt or invalid dataset file content: {str(e)}")

    @staticmethod
    def sanitize_columns(df):
        sanitized_cols = []
        for col in df.columns:
            clean = re.sub(r'<[^>]*>', '', str(col)).strip()
            clean = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', clean)
            sanitized_cols.append(clean if clean else 'unnamed_column')
        df.columns = sanitized_cols
        return df

class SmartNarrativeEngine:
    @staticmethod
    def generate_widget_narrative(df, widget):
        bullets = []
        if df.empty:
            return ["Dataset is empty; no insights available."]

        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()

        x_col = widget.x_axis if widget.x_axis in df.columns else (cat_cols[0] if cat_cols else df.columns[0])
        y_col = widget.y_axis if widget.y_axis in df.columns else (num_cols[0] if num_cols else df.columns[-1])

        if y_col in df.columns and pd.api.types.is_numeric_dtype(df[y_col]):
            total_val = float(df[y_col].sum())
            avg_val = float(df[y_col].mean())
            max_val = float(df[y_col].max())
            min_val = float(df[y_col].min())

            bullets.append(f"The total aggregated **{y_col}** across all recorded entries is **{total_val:,.2f}**, with an average of **{avg_val:,.2f}** per entry.")
            bullets.append(f"Peak observed **{y_col}** value reached **{max_val:,.2f}**, while the lowest recorded point was **{min_val:,.2f}**.")

            if x_col in df.columns:
                grouped = df.groupby(x_col)[y_col].sum()
                if not grouped.empty:
                    top_cat = str(grouped.idxmax())
                    top_val = float(grouped.max())
                    pct_share = (top_val / total_val * 100) if total_val != 0 else 0
                    bullets.append(f"**{top_cat}** represents the top contributor for **{x_col}**, generating **{top_val:,.2f}** ({pct_share:.1f}% share of total).")

            # Outliers check
            std_val = df[y_col].std()
            if std_val > 0:
                z_scores = np.abs((df[y_col] - avg_val) / std_val)
                outliers = int((z_scores > 2.5).sum())
                if outliers > 0:
                    bullets.append(f"Detected **{outliers} statistical outlier point(s)** exhibiting more than 2.5 standard deviations from baseline mean.")
        else:
            bullets.append(f"Analyzed {len(df):,} total records grouped across category **{x_col}**.")

        return bullets

class SQLDatabaseConnector:
    @staticmethod
    def execute_live_query(engine_type, host, port, db_name, username, password, query, limit=5000):
        query_strip = query.strip()
        if not query_strip.lower().startswith('select'):
            raise ValueError("Only read-only SELECT queries are permitted for live database connectors.")

        if engine_type == 'sqlite' or host == 'local':
            import sqlite3
            db_path = db_name if db_name and os.path.exists(db_name) else os.path.join(settings.BASE_DIR, 'db.sqlite3')
            conn = sqlite3.connect(db_path)
            df = pd.read_sql_query(query_strip, conn)
            conn.close()
            return df.head(limit)

        try:
            import sqlalchemy
            conn_str = f"{engine_type}://{username}:{password}@{host}:{port}/{db_name}"
            engine = sqlalchemy.create_engine(conn_str, connect_args={'connect_timeout': 5})
            df = pd.read_sql_query(query_strip, engine)
            return df.head(limit)
        except ImportError:
            raise ValueError(f"Driver for '{engine_type}' database engine is not installed.")
        except Exception as e:
            raise ValueError(f"Database connection or execution failed: {str(e)}")

class RESTDataConnector:
    @staticmethod
    def fetch_json_feed(endpoint_url, method='GET', headers=None, json_path=None):
        import urllib.request
        req = urllib.request.Request(endpoint_url, headers=headers or {'User-Agent': 'APEX-BI-Studio/2.0'})
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                payload = json.loads(response.read().decode('utf-8'))
                
                if json_path and isinstance(payload, dict) and json_path in payload:
                    payload = payload[json_path]
                
                if isinstance(payload, list):
                    df = pd.json_normalize(payload)
                elif isinstance(payload, dict):
                    df = pd.json_normalize([payload])
                else:
                    raise ValueError("REST API response format must resolve to a JSON list or dictionary.")
                return df
        except Exception as e:
            raise ValueError(f"Failed to ingest REST API feed from {endpoint_url}: {str(e)}")

class WhatIfScenarioEngine:
    @staticmethod
    def simulate_scenario(df, adjustments):
        """
        adjustments format: [
            {"column": "Sales", "multiplier": 1.15, "addition": 0},
            {"column": "Cost", "multiplier": 1.05, "addition": 100}
        ]
        """
        df_sim = df.copy()
        scenario_metrics = {}

        for adj in adjustments:
            col = adj.get('column')
            mult = float(adj.get('multiplier', 1.0))
            add = float(adj.get('addition', 0.0))

            if col in df_sim.columns and pd.api.types.is_numeric_dtype(df_sim[col]):
                original_sum = float(df[col].sum())
                df_sim[col] = (df_sim[col] * mult) + add
                simulated_sum = float(df_sim[col].sum())
                delta = simulated_sum - original_sum
                pct_change = (delta / original_sum * 100) if original_sum != 0 else 0

                scenario_metrics[col] = {
                    'baseline_total': round(original_sum, 2),
                    'simulated_total': round(simulated_sum, 2),
                    'delta': round(delta, 2),
                    'pct_change': round(pct_change, 2)
                }

        return df_sim, scenario_metrics

class CustomerSegmentationEngine:
    @staticmethod
    def rfm_clustering(df, customer_id_col, date_col, monetary_col, n_clusters=3):
        if customer_id_col not in df.columns or monetary_col not in df.columns:
            raise ValueError("Customer ID and Monetary columns must exist in dataset.")

        df_rfm = df.dropna(subset=[customer_id_col, monetary_col]).copy()
        
        # Calculate Frequency & Monetary
        rfm_summary = df_rfm.groupby(customer_id_col).agg(
            frequency=(customer_id_col, 'count'),
            monetary=(monetary_col, 'sum')
        ).reset_index()

        # Recency calculation
        if date_col in df.columns:
            try:
                df_rfm['temp_date'] = pd.to_datetime(df_rfm[date_col], errors='coerce')
                max_date = df_rfm['temp_date'].max()
                recency_df = df_rfm.groupby(customer_id_col)['temp_date'].max().reset_index()
                recency_df['recency'] = (max_date - recency_df['temp_date']).dt.days
                rfm_summary = rfm_summary.merge(recency_df[[customer_id_col, 'recency']], on=customer_id_col, how='left')
            except:
                rfm_summary['recency'] = 30
        else:
            rfm_summary['recency'] = 30

        rfm_summary['recency'] = rfm_summary['recency'].fillna(30)

        # Pure Python / Numpy K-Means fallback
        X = rfm_summary[['recency', 'frequency', 'monetary']].values
        # Normalize features
        mean = np.mean(X, axis=0)
        std = np.std(X, axis=0) + 1e-9
        X_norm = (X - mean) / std

        # Initialize k-means centroids
        np.random.seed(42)
        random_indices = np.random.choice(len(X_norm), size=min(n_clusters, len(X_norm)), replace=False)
        centroids = X_norm[random_indices]

        for _ in range(10):
            distances = np.linalg.norm(X_norm[:, np.newaxis] - centroids, axis=2)
            cluster_labels = np.argmin(distances, axis=1)
            for k in range(len(centroids)):
                if (cluster_labels == k).any():
                    centroids[k] = X_norm[cluster_labels == k].mean(axis=0)

        rfm_summary['cluster'] = [f"Segment {c+1}" for c in cluster_labels]
        return rfm_summary.head(1000).to_dict(orient='records')

class RowLevelSecurityEngine:
    @staticmethod
    def apply_rls_filters(df, dataset, user):
        if not user or not user.is_authenticated or user.is_staff:
            return df

        from .models import RowLevelSecurityRule
        rules = RowLevelSecurityRule.objects.filter(dataset=dataset, is_active=True)
        user_rules = rules.filter(user=user)
        
        if not user_rules.exists() and hasattr(user, 'profile'):
            user_rules = rules.filter(role=user.profile.role)

        if not user_rules.exists():
            return df

        df_filtered = df.copy()
        for rule in user_rules:
            col = rule.column_name
            val = rule.filter_value
            op = rule.operator

            if col in df_filtered.columns:
                if op == 'eq':
                    df_filtered = df_filtered[df_filtered[col].astype(str) == str(val)]
                elif op == 'ne':
                    df_filtered = df_filtered[df_filtered[col].astype(str) != str(val)]
                elif op == 'gt':
                    df_filtered = df_filtered[pd.to_numeric(df_filtered[col], errors='coerce') > float(val)]
                elif op == 'lt':
                    df_filtered = df_filtered[pd.to_numeric(df_filtered[col], errors='coerce') < float(val)]
                elif op == 'in':
                    vals = [v.strip() for v in val.split(',')]
                    df_filtered = df_filtered[df_filtered[col].astype(str).isin(vals)]

        return df_filtered

class DAXFormulaParser:
    @staticmethod
    def evaluate_formula(df, formula):
        formula_clean = formula.strip()
        
        # SUM(ColumnName)
        if formula_clean.upper().startswith('SUM('):
            col = formula_clean[4:-1].strip('[]"\' ')
            if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
                return round(float(df[col].sum()), 2)
        # AVG(ColumnName) or AVERAGE(ColumnName)
        elif formula_clean.upper().startswith(('AVG(', 'AVERAGE(')):
            col = formula_clean.split('(')[1][:-1].strip('[]"\' ')
            if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
                return round(float(df[col].mean()), 2)
        # COUNT(ColumnName)
        elif formula_clean.upper().startswith('COUNT('):
            col = formula_clean[6:-1].strip('[]"\' ')
            if col in df.columns:
                return int(df[col].count())
        # DIVIDE(ColA, ColB)
        elif formula_clean.upper().startswith('DIVIDE('):
            parts = formula_clean[7:-1].split(',')
            if len(parts) == 2:
                col_a = parts[0].strip('[]"\' ')
                col_b = parts[1].strip('[]"\' ')
                val_a = float(df[col_a].sum()) if col_a in df.columns else 0.0
                val_b = float(df[col_b].sum()) if col_b in df.columns else 1.0
                return round(val_a / val_b, 4) if val_b != 0 else 0.0

        raise ValueError(f"Unsupported or invalid DAX expression: '{formula}'")

class AuditLogger:
    @staticmethod
    def log_action(user, action_type, resource_type, resource_id, details=None, request=None):
        try:
            from .models import ActivityLog
            ip_address = '127.0.0.1'
            user_agent = ''

            if request:
                x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
                if x_forwarded:
                    ip_address = x_forwarded.split(',')[0].strip()
                else:
                    ip_address = request.META.get('REMOTE_ADDR', '127.0.0.1')
                user_agent = request.META.get('HTTP_USER_AGENT', '')

            return ActivityLog.objects.create(
                user=user if user and user.is_authenticated else None,
                action_type=action_type,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details or {},
                ip_address=ip_address,
                user_agent=user_agent[:255] if user_agent else ''
            )
        except Exception as e:
            print(f"Error recording audit log: {e}")
            return None

clear_dataset_cache = DatasetEngine.clear_cache