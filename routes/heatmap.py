# backend/routes/heatmap.py
from flask import jsonify
from flask_smorest import Blueprint
from flask.views import MethodView

from models import Event
from utils.heatmap import get_heatmap_data, get_heatmap_summary, TUNISIAN_GOVERNORATES

blp = Blueprint("heatmap", __name__, url_prefix="/api/heatmap")


class HeatmapData(MethodView):
    """Endpoint to get heatmap data with scores per governorate"""
    
    def get(self):
        """Get heatmap data from database events"""
        # Get all approved events from database
        events = Event.query.filter_by(status='approved').all()
        
        # Convert to dictionaries
        events_data = [event.to_dict() for event in events]
        
        # Calculate heatmap data
        heatmap_data = get_heatmap_data(events_data)
        summary = get_heatmap_summary(events_data)
        
        return jsonify({
            "success": True,
            "summary": summary,
            "governorates": heatmap_data,
            # Also provide as array format for easier frontend consumption
            "data": [
                {
                    "governorate": gov,
                    "score": heatmap_data[gov]["score"],
                    "color": heatmap_data[gov]["color"],
                    "events_count": heatmap_data[gov]["events_count"],
                    "events": heatmap_data[gov]["events"]
                }
                for gov in TUNISIAN_GOVERNORATES
            ]
        }), 200


class HeatmapStats(MethodView):
    """Endpoint to get heatmap statistics"""
    
    def get(self):
        """Get statistics about events distribution"""
        events = Event.query.filter_by(status='approved').all()
        events_data = [event.to_dict() for event in events]
        summary = get_heatmap_summary(events_data)
        
        # Get top governorates by event count
        heatmap_data = get_heatmap_data(events_data)
        top_governorates = sorted(
            [(gov, data['score']) for gov, data in heatmap_data.items()],
            key=lambda x: x[1],
            reverse=True
        )[:10]  # Top 10
        
        return jsonify({
            "success": True,
            "summary": summary,
            "top_governorates": [
                {"governorate": gov, "events_count": count}
                for gov, count in top_governorates
            ]
        }), 200


# Register views
blp.add_url_rule("/", view_func=HeatmapData.as_view("heatmap_data"))
blp.add_url_rule("/stats", view_func=HeatmapStats.as_view("heatmap_stats"))
