# backend/routes/auth.py
import os
import requests
from flask import jsonify, request, current_app
from flask_smorest import Blueprint, abort
from flask.views import MethodView
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from flask_bcrypt import Bcrypt
from sqlalchemy.exc import IntegrityError

from db import db
from models import User

blp = Blueprint("auth", __name__, url_prefix="/api/auth")
bcrypt = Bcrypt() # Initialize here, bound to app later

def verify_okta_2fa(username):
    """
    Trigger/Verify Okta 2FA. 
    This is a simplified implementation. In production, you'd likely use 
    Okta's Factors API to trigger a push or verify a code.
    
    Requires OKTA_ORG_URL and OKTA_API_TOKEN env vars.
    """
    okta_url = os.getenv("OKTA_ORG_URL")
    okta_token = os.getenv("OKTA_API_TOKEN")
    
    if not okta_url or not okta_token:
        # If not configured, skip 2FA (or fail secure, depending on policy)
        print("⚠️ Okta not configured, skipping 2FA")
        return True 

    # Example: Look up user in Okta
    try:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"SSWS {okta_token}"
        }
        
        # 1. Find Okta User ID (assuming username matches authentication email/login)
        user_resp = requests.get(f"{okta_url}/api/v1/users?q={username}&limit=1", headers=headers)
        if not user_resp.ok or not user_resp.json():
            return False # User not found in Okta
            
        user_id = user_resp.json()[0]['id']
        
        # 2. Check for active Factors (Push, TOTP)
        # For this demo, we'll assume if we found the user, and they have 'Okta Verify'
        # we would trigger it. Since we can't interactively wait for Push in this API call 
        # easily without a polling mechanism or callback, we will just verify user existence 
        # and checking if they have an enrolled factor as a proof of concept.
        
        factors_resp = requests.get(f"{okta_url}/api/v1/users/{user_id}/factors", headers=headers)
        if factors_resp.ok:
            factors = factors_resp.json()
            encrolled = [f for f in factors if f['status'] == 'ACTIVE']
            if encrolled:
                # Real implementation would trigger verify here
                # resp = requests.post(f"{okta_url}/api/v1/users/{user_id}/factors/{factor_id}/verify")
                return True
                
        return False
        
    except Exception as e:
        print(f"Okta Error: {str(e)}")
        return False


@blp.route("/register")
class UserRegister(MethodView):
    def post(self):
        """Register a new user"""
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")
        
        if not username or not password:
            abort(400, message="Username and password required")
            
        if User.query.filter_by(username=username).first():
            abort(409, message="Username already exists")
            
        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        
        user = User(username=username, password_hash=hashed_pw)
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            abort(500, message="Database error")
            
        return jsonify({"success": True, "message": "User registered successfully"}), 201


@blp.route("/login")
class UserLogin(MethodView):
    def post(self):
        """Login and get JWT token (with optional Okta 2FA)"""
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")
        
        user = User.query.filter_by(username=username).first()
        
        if user and bcrypt.check_password_hash(user.password_hash, password):
            # Step 2: Okta 2FA Check
            # Only enforces if Okta is configured in env
            if os.getenv("OKTA_ORG_URL"):
                if not verify_okta_2fa(username):
                    abort(401, message="2FA Verification Failed (Okta)")
            
            # Create JWT
            access_token = create_access_token(identity=user.id, additional_claims={"role": user.role, "username": user.username})
            return jsonify({
                "success": True, 
                "access_token": access_token,
                "user": {"id": user.id, "username": user.username, "role": user.role}
            }), 200
            
        abort(401, message="Invalid credentials")

@blp.route("/me")
class UserMe(MethodView):
    @jwt_required()
    def get(self):
        """Get current user details"""
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user:
            abort(404, message="User not found")
            
        return jsonify({
            "success": True,
            "user": {
                "id": user.id,
                "username": user.username, 
                "role": user.role,
                "created_at": user.created_at.isoformat()
            }
        })
