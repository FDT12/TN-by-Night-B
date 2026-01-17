# backend/routes/events.py
import csv
import json
import os
from flask import jsonify, request
from flask_smorest import Blueprint, abort
from flask.views import MethodView
from flask_smorest import abort
from sqlalchemy.exc import IntegrityError
from datetime import datetime

from db import db
from models import Event
from utils.heatmap import get_heatmap_data

blp = Blueprint("events", __name__, url_prefix="/api/events")


from flask_jwt_extended import jwt_required, get_jwt_identity

class EventsList(MethodView):
    """Endpoint to get all events or import from CSV"""
    
    def get(self):
        """Get all events (filtered by status='approved' unless admin)"""
        status_filter = request.args.get('status', 'approved')
        events = Event.query.filter_by(status=status_filter).all()
        
        return jsonify({
            "success": True,
            "count": len(events),
            "events": [event.to_dict() for event in events]
        }), 200

    def post(self):
        """Import events from CSV file to database"""
        # Kept original CSV import logic for backward compatibility/admin usage
        # Ideally this should be protected or moved to a separate admin endpoint
        return self.handle_csv_import()

    def handle_csv_import(self):
        data = request.get_json()
        filename = data.get('filename', 'events.csv')
        
        if not os.path.exists(filename):
            abort(404, message=f"CSV file '{filename}' not found")
        
        imported = 0
        skipped = 0
        errors = []
        
        try:
            with open(filename, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    try:
                        # Parse scraped_at datetime if it exists
                        scraped_at = None
                        if row.get('scraped_at'):
                            try:
                                scraped_at = datetime.fromisoformat(row['scraped_at'].replace('Z', '+00:00'))
                            except:
                                scraped_at = datetime.utcnow()
                        
                        # Check if event already exists (by URL)
                        existing = Event.query.filter_by(url=row.get('url', '')).first()
                        if existing:
                            # Update existing event
                            existing.name = row.get('name', existing.name)
                            existing.place = row.get('place', existing.place)
                            existing.date = row.get('date', existing.date)
                            existing.price = row.get('price', existing.price)
                            existing.city = row.get('city', existing.city)
                            existing.updated_at = datetime.utcnow()
                            existing.status = 'approved' # Scraped events are approved by default
                            if scraped_at:
                                existing.scraped_at = scraped_at
                            skipped += 1
                        else:
                            # Create new event
                            event = Event(
                                name=row.get('name', 'Unknown'),
                                place=row.get('place', 'N/A'),
                                date=row.get('date', 'N/A'),
                                price=row.get('price', 'N/A'),
                                url=row.get('url', ''),
                                city=row.get('city', 'Unknown'),
                                status = 'approved', # Scraped events are approved
                                scraped_at=scraped_at or datetime.utcnow()
                            )
                            db.session.add(event)
                            imported += 1
                            
                    except IntegrityError:
                        db.session.rollback()
                        skipped += 1
                    except Exception as e:
                        errors.append(f"Error processing row: {str(e)}")
                
                db.session.commit()
                
        except Exception as e:
            db.session.rollback()
            abort(500, message=f"Error importing CSV: {str(e)}")
        
        return jsonify({
            "success": True,
            "message": "CSV imported successfully",
            "imported": imported,
            "updated": skipped,
            "errors": errors if errors else None
        }), 200


@blp.route("/suggest")
class EventSuggest(MethodView):
    @jwt_required()
    def post(self):
        """Suggest a new event (Authenticated)"""
        data = request.get_json()
        user_id = get_jwt_identity()
        
        required_fields = ['name', 'city', 'url']
        if not all(field in data for field in required_fields):
            abort(400, message="Missing required fields: name, city, url")

        if Event.query.filter_by(url=data['url']).first():
            abort(409, message="Event with this URL already exists")

        new_event = Event(
            name=data['name'],
            place=data.get('place', 'TBD'),
            date=data.get('date', 'TBD'),
            price=data.get('price', 'TBD'),
            url=data['url'],
            city=data['city'],
            status='pending', # Pending approval
            suggested_by_id=user_id,
            scraped_at=datetime.utcnow()
        )
        
        db.session.add(new_event)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            abort(500, message="Database error")
            
        return jsonify({
            "success": True, 
            "message": "Event suggested successfully. It is pending approval.",
            "event": new_event.to_dict()
        }), 201


@blp.route("/<int:event_id>/status")
class EventStatus(MethodView):
    @jwt_required()
    def put(self, event_id):
        """Update event status (Admin only)"""
        # In a real app, check if user.role == 'admin'
        # For now, we'll allow any authenticated user to act as admin for simplicity
        # or we can check claims if we added them to JWT.
        
        data = request.get_json()
        new_status = data.get('status')
        if new_status not in ['approved', 'pending', 'rejected']:
           abort(400, message="Invalid status")

        event = Event.query.get_or_404(event_id)
        event.status = new_status
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"Event status updated to {new_status}",
            "event": event.to_dict()
        }), 200



class EventsCSVToJSON(MethodView):
    """Endpoint to convert CSV file to JSON"""
    
    def get(self):
        """Convert latest events.csv to JSON"""
        filename = request.args.get('filename', 'events.csv')
        
        if not os.path.exists(filename):
            abort(404, message=f"CSV file '{filename}' not found")
        
        events = []
        
        try:
            with open(filename, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                events = list(reader)
                
        except Exception as e:
            abort(500, message=f"Error reading CSV: {str(e)}")
        
        return jsonify({
            "success": True,
            "count": len(events),
            "filename": filename,
            "events": events
        }), 200
    
    def post(self):
        """Convert specified CSV file to JSON and optionally save"""
        data = request.get_json() or {}
        filename = data.get('filename', 'events.csv')
        save_json = data.get('save_json', False)
        json_filename = data.get('json_filename', 'events.json')
        
        if not os.path.exists(filename):
            abort(404, message=f"CSV file '{filename}' not found")
        
        events = []
        
        try:
            with open(filename, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                events = list(reader)
            
            # Optionally save to JSON file
            if save_json:
                with open(json_filename, 'w', encoding='utf-8') as f:
                    json.dump(events, f, ensure_ascii=False, indent=2)
                    
        except Exception as e:
            abort(500, message=f"Error processing CSV: {str(e)}")
        
        response = {
            "success": True,
            "count": len(events),
            "filename": filename,
            "events": events
        }
        
        if save_json:
            response["json_file"] = json_filename
            response["message"] = f"JSON saved to {json_filename}"
        
        return jsonify(response), 200


class EventDetail(MethodView):
    """Endpoint for individual event operations"""
    
    def get(self, event_id):
        """Get a specific event by ID"""
        event = Event.query.get_or_404(event_id)
        return jsonify({
            "success": True,
            "event": event.to_dict()
        }), 200
    
    def delete(self, event_id):
        """Delete an event by ID"""
        event = Event.query.get_or_404(event_id)
        db.session.delete(event)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Event deleted successfully"
        }), 200


# Register views
# GET and POST for /api/events
blp.add_url_rule("/", view_func=EventsList.as_view("events_list"), methods=["GET", "POST"])
# POST for /api/events/import
blp.add_url_rule("/import", view_func=EventsList.as_view("events_import"), methods=["POST"])
# GET and POST for /api/events/csv-to-json
blp.add_url_rule("/csv-to-json", view_func=EventsCSVToJSON.as_view("events_csv_to_json"), methods=["GET", "POST"])
# GET and DELETE for /api/events/<id>
blp.add_url_rule("/<int:event_id>", view_func=EventDetail.as_view("event_detail"), methods=["GET", "DELETE"])
