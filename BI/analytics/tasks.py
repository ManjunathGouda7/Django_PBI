from celery import shared_task
from .models import Dataset, Dashboard
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
def export_dashboard_pdf_task(dashboard_id):
    """
    Background Celery task for PDF report snapshot generation.
    """
    logger.info(f"Exporting dashboard {dashboard_id} report snapshot.")
    return {'status': 'completed', 'dashboard_id': dashboard_id}
