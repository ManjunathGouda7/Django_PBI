import json
from typing import Dict, Any
from analytics.models import Dashboard, Widget

class TemplateExporter:
    """
    Power BI Template (.pbit / JSON) Exporter & Importer.
    Serializes dashboard visual layouts, themes, and field bindings for portability.
    """

    @classmethod
    def export_dashboard_template(cls, dashboard: Dashboard) -> Dict[str, Any]:
        """
        Serializes a dashboard object and all its child widgets into a clean .pbit JSON payload.
        """
        widgets_payload = []
        for w in dashboard.widgets.all():
            widgets_payload.append({
                'title': w.title,
                'visual_type': w.visual_type,
                'x_axis': w.x_axis,
                'y_axis': w.y_axis,
                'group_by': w.group_by,
                'aggregation': w.aggregation,
                'width': w.width,
                'height': w.height,
                'format_config': w.format_config or {}
            })

        template = {
            'pbi_template_version': '2.0',
            'dashboard_title': dashboard.title,
            'description': dashboard.description or '',
            'created_at': dashboard.created_at.isoformat() if dashboard.created_at else '',
            'linked_dataset': dashboard.dataset.name if dashboard.dataset else None,
            'visuals_count': len(widgets_payload),
            'widgets': widgets_payload
        }
        return template

    @classmethod
    def import_dashboard_template(cls, template_json: Dict[str, Any], target_dashboard: Dashboard) -> Dashboard:
        """
        Applies a .pbit JSON template structure onto a target dashboard object.
        """
        widgets_data = template_json.get('widgets', [])
        
        # Clear existing widgets
        target_dashboard.widgets.all().delete()

        for idx, wdata in enumerate(widgets_data):
            Widget.objects.create(
                dashboard=target_dashboard,
                title=wdata.get('title', f"Visual {idx+1}"),
                visual_type=wdata.get('visual_type', 'scatter'),
                x_axis=wdata.get('x_axis', ''),
                y_axis=wdata.get('y_axis', ''),
                group_by=wdata.get('group_by', ''),
                aggregation=wdata.get('aggregation', 'mean'),
                width=wdata.get('width', 6),
                height=wdata.get('height', 5),
                format_config=wdata.get('format_config', {})
            )

        if 'dashboard_title' in template_json:
            target_dashboard.title = template_json['dashboard_title']
            target_dashboard.save()

        return target_dashboard
