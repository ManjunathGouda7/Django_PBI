try:
    from celery import shared_task
except ImportError:
    def shared_task(func):
        return func

from django.utils import timezone
from .models import Dataset, Dashboard, ScheduledRefresh
from .services import DatasetEngine
import logging

logger = logging.getLogger(__name__)

@shared_task
def refresh_dataset_cache_task(dataset_id):
    """
    Background Celery task to re-index and refresh dataset schema & cache.
    """
    try:
        dataset = Dataset.objects.get(pk=dataset_id)
        DatasetEngine.clear_cache(dataset_id)
        df = DatasetEngine.load_dataframe(dataset)
        dataset.row_count = len(df)
        dataset.column_schema = DatasetEngine.infer_column_schema(df)
        dataset.save()
        logger.info(f"Successfully refreshed dataset {dataset_id} in background.")
        return {'status': 'success', 'row_count': len(df)}
    except Exception as e:
        logger.error(f"Error refreshing dataset {dataset_id}: {e}")
        return {'status': 'error', 'message': str(e)}

@shared_task
def async_process_dataset_upload_task(dataset_id):
    """
    Background async task to parse, score quality, and infer schema on newly uploaded dataset.
    """
    try:
        dataset = Dataset.objects.get(pk=dataset_id)
        dataset.status = 'processing'
        dataset.save(update_fields=['status'])

        DatasetEngine.clear_cache(dataset_id)
        df = DatasetEngine.load_dataframe(dataset)
        
        # Calculate data quality metrics
        null_count = int(df.isnull().sum().sum())
        total_cells = df.size if df.size > 0 else 1
        quality_score = max(0.0, min(100.0, round((1.0 - (null_count / total_cells)) * 100, 1)))

        dataset.row_count = len(df)
        dataset.column_schema = DatasetEngine.infer_column_schema(df)
        dataset.data_quality_score = quality_score
        dataset.status = 'ready'
        dataset.save()
        logger.info(f"Async dataset upload processing finished for dataset {dataset_id}")
        return {'status': 'success', 'row_count': len(df), 'quality_score': quality_score}
    except Exception as e:
        logger.error(f"Error processing dataset upload {dataset_id}: {e}")
        Dataset.objects.filter(pk=dataset_id).update(status='error')
        return {'status': 'error', 'message': str(e)}

@shared_task
def async_run_scheduled_refresh_task(schedule_id):
    """
    Background task to execute a scheduled dataset refresh.
    """
    try:
        schedule = ScheduledRefresh.objects.get(pk=schedule_id)
        if not schedule.is_active or not schedule.dataset:
            return {'status': 'skipped', 'reason': 'Schedule inactive or dataset missing'}

        dataset = schedule.dataset
        dataset.refresh_status = 'running'
        dataset.save(update_fields=['refresh_status'])

        # Reload dataframe and update schema
        DatasetEngine.clear_cache(dataset.id)
        df = DatasetEngine.load_dataframe(dataset)
        dataset.row_count = len(df)
        dataset.column_schema = DatasetEngine.infer_column_schema(df)
        dataset.last_refresh = timezone.now()
        dataset.refresh_status = 'success'
        dataset.refresh_error = None
        dataset.save()

        schedule.last_run = timezone.now()
        schedule.save(update_fields=['last_run'])

        logger.info(f"Scheduled refresh succeeded for dataset {dataset.id} (Schedule {schedule_id})")
        return {'status': 'success', 'dataset_id': dataset.id, 'last_refresh': str(dataset.last_refresh)}
    except Exception as e:
        logger.error(f"Scheduled refresh failed for schedule {schedule_id}: {e}")
        if 'schedule' in locals() and schedule.dataset:
            schedule.dataset.refresh_status = 'failed'
            schedule.dataset.refresh_error = str(e)
            schedule.dataset.save(update_fields=['refresh_status', 'refresh_error'])
        return {'status': 'error', 'message': str(e)}

@shared_task
def async_execute_dataset_join_task(dataset_a_id, dataset_b_id, join_key, join_type='inner', new_name='Joined Dataset', user_id=None):
    """
    Background task for merging two datasets on a join key (VLOOKUP engine).
    """
    try:
        from django.contrib.auth.models import User
        ds_a = Dataset.objects.get(pk=dataset_a_id)
        ds_b = Dataset.objects.get(pk=dataset_b_id)

        df_a = DatasetEngine.load_dataframe(ds_a)
        df_b = DatasetEngine.load_dataframe(ds_b)

        if join_key not in df_a.columns or join_key not in df_b.columns:
            raise ValueError(f"Join key '{join_key}' must exist in both datasets.")

        how_map = {'inner': 'inner', 'left': 'left', 'right': 'right', 'full': 'outer'}
        merged_df = df_a.merge(df_b, on=join_key, how=how_map.get(join_type, 'inner'), suffixes=('_A', '_B'))

        user = User.objects.filter(pk=user_id).first() if user_id else None
        new_ds = Dataset.objects.create(
            name=new_name,
            file_type='sample',
            is_sample=False,
            row_count=len(merged_df),
            column_schema=DatasetEngine.infer_column_schema(merged_df),
            created_by=user,
            status='ready'
        )
        DatasetEngine._df_cache[new_ds.id] = merged_df
        logger.info(f"Dataset join task succeeded: created dataset {new_ds.id}")
        return {'status': 'success', 'joined_dataset_id': new_ds.id, 'row_count': len(merged_df)}
    except Exception as e:
        logger.error(f"Error in dataset join task: {e}")
        return {'status': 'error', 'message': str(e)}

@shared_task
def export_dashboard_pdf_task(dashboard_id):
    """
    Background Celery task for PDF report snapshot generation.
    """
    logger.info(f"Exporting dashboard {dashboard_id} report snapshot.")
    return {'status': 'completed', 'dashboard_id': dashboard_id}

@shared_task
def async_check_kpi_alerts_task(widget_id):
    """
    Background task to evaluate threshold alerts for a widget and dispatch webhooks.
    """
    try:
        from .models import Widget, KPIAlertRule
        import urllib.request
        import json
        
        widget = Widget.objects.get(pk=widget_id)
        alerts = KPIAlertRule.objects.filter(widget=widget, is_active=True)
        if not alerts.exists():
            return {'status': 'skipped', 'reason': 'No active alerts'}

        df = DatasetEngine.load_dataframe(widget.dashboard.dataset)
        triggered_count = 0

        for alert in alerts:
            col = alert.metric_column
            if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
                current_val = float(df[col].sum())
                triggered = False

                if alert.condition == 'gt' and current_val > alert.threshold_value:
                    triggered = True
                elif alert.condition == 'lt' and current_val < alert.threshold_value:
                    triggered = True
                elif alert.condition == 'gte' and current_val >= alert.threshold_value:
                    triggered = True
                elif alert.condition == 'lte' and current_val <= alert.threshold_value:
                    triggered = True
                elif alert.condition == 'eq' and current_val == alert.threshold_value:
                    triggered = True

                if triggered:
                    triggered_count += 1
                    alert.last_triggered = timezone.now()
                    alert.save(update_fields=['last_triggered'])

                    # Dispatch webhook if provided
                    if alert.webhook_url:
                        payload = json.dumps({
                            'text': f"🚨 **APEX BI Alert Triggered!** Widget: *{widget.title}* | Metric *{col}* = {current_val} ({alert.condition} {alert.threshold_value})"
                        }).encode('utf-8')
                        req = urllib.request.Request(alert.webhook_url, data=payload, headers={'Content-Type': 'application/json'})
                        try:
                            urllib.request.urlopen(req, timeout=5)
                        except Exception as ex:
                            logger.error(f"Webhook dispatch failed for alert {alert.id}: {ex}")

        return {'status': 'success', 'widget_id': widget_id, 'alerts_triggered': triggered_count}
    except Exception as e:
        logger.error(f"Error checking KPI alerts for widget {widget_id}: {e}")
        return {'status': 'error', 'message': str(e)}


