"""Chart export functionality manager."""

import io
import base64
import json
from typing import Dict, Any, Optional, Union, BinaryIO
from pathlib import Path
import plotly.graph_objects as go
import plotly.io as pio
from datetime import datetime


class ChartExportManager:
    """Manages chart export functionality in multiple formats."""
    
    def __init__(self):
        self.supported_formats = ['png', 'svg', 'html', 'json', 'pdf']
        self.default_settings = {
            'png': {'width': 1200, 'height': 800, 'scale': 2},
            'svg': {'width': 1200, 'height': 800},
            'html': {'include_plotlyjs': True, 'div_id': None},
            'json': {'pretty': True},
            'pdf': {'width': 1200, 'height': 800, 'scale': 2}
        }
    
    def export_chart(self, fig: go.Figure, format_type: str,
                    settings: Optional[Dict[str, Any]] = None,
                    filename: Optional[str] = None) -> Union[bytes, str]:
        """Export chart to specified format."""
        if format_type not in self.supported_formats:
            raise ValueError(f"Unsupported format: {format_type}")
        
        # Merge settings with defaults
        export_settings = self.default_settings[format_type].copy()
        if settings:
            export_settings.update(settings)
        
        # Generate filename if not provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"chart_{timestamp}.{format_type}"
        
        return self._export_by_format(fig, format_type, export_settings, filename)
    
    def _export_by_format(self, fig: go.Figure, format_type: str, 
                         settings: Dict[str, Any], filename: str) -> Union[bytes, str]:
        """Export chart based on format type."""
        if format_type == 'png':
            return self._export_png(fig, settings)
        elif format_type == 'svg':
            return self._export_svg(fig, settings)
        elif format_type == 'html':
            return self._export_html(fig, settings)
        elif format_type == 'json':
            return self._export_json(fig, settings)
        elif format_type == 'pdf':
            return self._export_pdf(fig, settings)
    
    def _export_png(self, fig: go.Figure, settings: Dict[str, Any]) -> bytes:
        """Export chart as PNG."""
        return fig.to_image(
            format="png",
            width=settings.get('width', 1200),
            height=settings.get('height', 800),
            scale=settings.get('scale', 2)
        )
    
    def _export_svg(self, fig: go.Figure, settings: Dict[str, Any]) -> str:
        """Export chart as SVG."""
        return fig.to_image(
            format="svg",
            width=settings.get('width', 1200),
            height=settings.get('height', 800)
        ).decode('utf-8')
    
    def _export_html(self, fig: go.Figure, settings: Dict[str, Any]) -> str:
        """Export chart as HTML."""
        return fig.to_html(
            include_plotlyjs=settings.get('include_plotlyjs', True),
            div_id=settings.get('div_id'),
            config={
                'displayModeBar': settings.get('display_mode_bar', True),
                'responsive': settings.get('responsive', True)
            }
        )
    
    def _export_json(self, fig: go.Figure, settings: Dict[str, Any]) -> str:
        """Export chart configuration as JSON."""
        chart_json = fig.to_json()
        if settings.get('pretty', True):
            return json.dumps(json.loads(chart_json), indent=2)
        return chart_json
    
    def _export_pdf(self, fig: go.Figure, settings: Dict[str, Any]) -> bytes:
        """Export chart as PDF."""
        # Note: PDF export requires kaleido package
        try:
            return fig.to_image(
                format="pdf",
                width=settings.get('width', 1200),
                height=settings.get('height', 800),
                scale=settings.get('scale', 2)
            )
        except Exception as e:
            raise RuntimeError(f"PDF export requires kaleido package: {e}")
    
    def batch_export(self, charts: Dict[str, go.Figure], format_type: str,
                    settings: Optional[Dict[str, Any]] = None) -> Dict[str, Union[bytes, str]]:
        """Export multiple charts in batch."""
        results = {}
        
        for chart_name, fig in charts.items():
            try:
                filename = f"{chart_name}.{format_type}"
                result = self.export_chart(fig, format_type, settings, filename)
                results[chart_name] = result
            except Exception as e:
                results[chart_name] = f"Export failed: {e}"
        
        return results
    
    def get_export_options(self, format_type: str) -> Dict[str, Any]:
        """Get available export options for a format."""
        options = {
            'png': {
                'width': {'type': 'number', 'default': 1200, 'min': 400, 'max': 4000},
                'height': {'type': 'number', 'default': 800, 'min': 300, 'max': 3000},
                'scale': {'type': 'number', 'default': 2, 'min': 1, 'max': 5},
                'background': {'type': 'color', 'default': 'white'}
            },
            'svg': {
                'width': {'type': 'number', 'default': 1200, 'min': 400, 'max': 4000},
                'height': {'type': 'number', 'default': 800, 'min': 300, 'max': 3000},
                'background': {'type': 'color', 'default': 'white'}
            },
            'html': {
                'include_plotlyjs': {'type': 'boolean', 'default': True},
                'responsive': {'type': 'boolean', 'default': True},
                'display_mode_bar': {'type': 'boolean', 'default': True},
                'div_id': {'type': 'text', 'default': None}
            },
            'json': {
                'pretty': {'type': 'boolean', 'default': True},
                'include_data': {'type': 'boolean', 'default': True}
            },
            'pdf': {
                'width': {'type': 'number', 'default': 1200, 'min': 400, 'max': 4000},
                'height': {'type': 'number', 'default': 800, 'min': 300, 'max': 3000},
                'scale': {'type': 'number', 'default': 2, 'min': 1, 'max': 5}
            }
        }
        
        return options.get(format_type, {})
    
    def create_download_link(self, data: Union[bytes, str], filename: str, 
                           mime_type: str) -> str:
        """Create a base64 download link for the exported data."""
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        b64_data = base64.b64encode(data).decode()
        return f"data:{mime_type};base64,{b64_data}"
    
    def get_mime_type(self, format_type: str) -> str:
        """Get MIME type for format."""
        mime_types = {
            'png': 'image/png',
            'svg': 'image/svg+xml',
            'html': 'text/html',
            'json': 'application/json',
            'pdf': 'application/pdf'
        }
        return mime_types.get(format_type, 'application/octet-stream')