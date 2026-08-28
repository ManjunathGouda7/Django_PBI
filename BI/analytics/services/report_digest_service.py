import logging
from typing import List, Dict, Any
from django.core.mail import send_mail
from django.conf import settings
from analytics.models import Dashboard

logger = logging.getLogger(__name__)

class ReportDigestService:
    """
    Automated Email & Executive Digest Dispatcher.
    Renders executive dashboard summaries and dispatches email reports to subscribers.
    """

    @classmethod
    def send_dashboard_digest(cls, dashboard: Dashboard, recipient_list: List[str], sender: str = None) -> Dict[str, Any]:
        """
        Builds and dispatches an executive digest email for a specific dashboard.
        """
        if not recipient_list:
            raise ValueError("Recipient list cannot be empty.")

        dataset = dashboard.dataset
        row_count = dataset.row_count if dataset else 0
        widget_count = dashboard.widgets.count()

        subject = f"📊 Executive Digest: Apex BI Studio - {dashboard.title}"
        body = f"""
Hello Executive Team,

Here is your automated analytical digest for dashboard: '{dashboard.title}'.

--------------------------------------------------
Dashboard Summary:
- Title: {dashboard.title}
- Linked Dataset: {dataset.name if dataset else 'N/A'} ({row_count:,} records)
- Total Canvas Visuals: {widget_count}
- Last Updated: {dashboard.updated_at.strftime('%Y-%m-%d %H:%M UTC')}
--------------------------------------------------

To access the interactive report, please open Apex BI Studio:
http://127.0.0.1:8000/

Best regards,
Apex BI Studio Automated Reporting Engine
        """.strip()

        from_email = sender or getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@apexbi.studio')

        try:
            sent_count = send_mail(
                subject=subject,
                message=body,
                from_email=from_email,
                recipient_list=recipient_list,
                fail_silently=False
            )
            logger.info(f"Digest email sent for dashboard '{dashboard.title}' to {recipient_list}")
            return {
                'status': 'success',
                'recipients': recipient_list,
                'sent_count': sent_count,
                'message': f"Executive digest successfully sent to {len(recipient_list)} recipients."
            }
        except Exception as e:
            logger.error(f"Failed sending email digest: {str(e)}")
            return {
                'status': 'error',
                'recipients': recipient_list,
                'sent_count': 0,
                'message': f"Email dispatch warning: {str(e)} (logged)"
            }
