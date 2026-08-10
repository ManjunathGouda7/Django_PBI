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
                print(f"MongoDB server ({url}) not reachable. Using local data/GRL.25MPLA.json fallback.")

            json_path = os.path.join(settings.BASE_DIR.parent, 'data', 'GRL.25MPLA.json')
            if os.path.exists(json_path):
                df = pd.read_json(json_path)
                if '_id' in df.columns:
                    df = df.drop(columns=['_id'])
                _df_cache[cache_key] = df
                return df.copy()
            return pd.DataFrame()

        if not dataset.file:
            json_path = os.path.join(settings.BASE_DIR.parent, 'data', 'GRL.25MPLA.json')
            if os.path.exists(json_path):
                df = pd.read_json(json_path)
                if '_id' in df.columns:
                    df = df.drop(columns=['_id'])
                return df.copy()
            raise ValueError("Dataset file does not exist.")

        filepath = dataset.file.path
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")

        if dataset.file_type == 'json' or filepath.endswith('.json'):
            df = pd.read_json(filepath)
            if '_id' in df.columns:
                df = df.drop(columns=['_id'])
            return df.copy()
        elif dataset.file_type == 'csv' or filepath.endswith('.csv'):
            df = pd.read_csv(filepath)
        elif dataset.file_type == 'excel' or filepath.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(filepath)
        else:
            df = pd.read_csv(filepath)

        return df.copy()

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
                            valid_mask = x_nums.notnull() & y_nums.notnull() & (x_nums >= -5) & (y_nums.between(-1000, 1000))

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
                        valid_mask = x_nums.notnull() & y_nums.notnull() & (x_nums >= -5) & (y_nums.between(-1000, 1000))

                        x_arr = np.round(x_nums[valid_mask].head(4000).to_numpy(), 2).tolist()
                        y_arr = np.round(y_nums[valid_mask].head(4000).to_numpy(), 2).tolist()

                        points = [{'x': x, 'y': y} for x, y in zip(x_arr, y_arr)]
                        datasets.append({
                            'label': f"{y_col} vs {x_col}",
                            'data': points,
                            'color': '#00A4EF'
                        })

                    return {
                        'labels': [],
                        'datasets': datasets,
                        'x_col': x_col,
                        'y_col': y_col,
                        'group_col': group_col or ''
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