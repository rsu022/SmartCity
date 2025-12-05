import jwt
from functools import wraps
from flask import request, jsonify, current_app
from models.user_model import User

#middleware function 
def token_required(f): 
    @wraps(f)
    def decorated(*args, **kwargs): 
        token = None
        auth_header= request.headers.get('Authorization')         
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        
        if not token:
            return jsonify({"error": "Token is missing!"}), 401

        try:             
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])             
            user_id = data.get("id")
            current_user = User.query.get(user_id)

            if not current_user: 
                return jsonify({"error": "Invalid user"}), 401

        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
        except Exception as e:
            return jsonify({"error": f"Token validation failed: {str(e)}"}), 401
        
        return f(current_user, *args, **kwargs)

    return decorated