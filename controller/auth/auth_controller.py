import datetime
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from models.db import db
from models.user_model import User
from flask import current_app
from controller.auth.auth_middleware import token_required

auth_bp = Blueprint('auth_bp', __name__, url_prefix="/auth")

# AUTH ROUTES
# REGISTER
@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.json
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role", "user")
    organization = data.get("organization_name", None)
    
    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
        
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 409
        
    hashed_pw = generate_password_hash(password)
    user = User(
        name=name,
        email=email,
        password=hashed_pw,
        role=role,
        organization_name=organization
    )
    db.session.add(user)
    db.session.commit()
    
    return jsonify({"message": "User registered successfully", "id": user.id}), 201

# LOGIN
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")
    
    user = User.query.filter_by(email=email).first()
    
    if not user or not check_password_hash(user.password, password):
        return jsonify({"error": "Invalid email or password"}), 401
        
    payload = {
        "id": user.id,
        "email": user.email,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }
    
    token = jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm="HS256")
    
    return jsonify({
        "message": "Login successful",
        "token": token,
        "user": user.to_dict() 
    }), 200

# PROTECTED ROUTES 
# PROFILE 
@auth_bp.route('/profile', methods=['GET'])
@token_required
def profile(current_user):

    return jsonify({
        "message": "Access granted",
        "user": current_user.to_dict() 
    }), 200