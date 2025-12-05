# 🤖 ML-Project Backend API

This repository contains the Flask backend for a system designed to detect and manage environmental issues (specifically **potholes** and **waste**) using machine learning models. 

It features robust user authentication, efficient data retrieval using SQLAlchemy, and a defined set of RESTful API endpoints for interaction.

---

## 🚀 Project Setup

Follow these steps to get a local copy of the project running on your machine.

### Prerequisites

You'll need the following installed:

* **Python 3.8+**
* **PostgreSQL Database** (running locally or remotely)
* **Git**

### 1. Clone the Repository

First, download the project code:

```bash
git clone <repository-url>
cd ML-Project
```


### 2. Set up Virtual Environment
Create and activate a virtual environment to manage dependencies.
```
OS,Command to Create Venv,Command to Activate Venv
Linux/macOS (Bash),python3 -m venv venv,source venv/bin/activate
Windows (Command Prompt),python -m venv venv,venv\Scripts\activate
Windows (PowerShell),python -m venv venv,.\venv\Scripts\Activate.ps1
```

### . Install Dependencies
Install all required Python packages from the requirements.txt file:

```bash
pip install -r requirements.txt
```

### 4. Configuration
You must update the config.py file with your own database and security keys.

## Key Configuration Variables:
```python
class Config:
    # 🔑 IMPORTANT: Update this with your actual PostgreSQL connection string.
    SQLALCHEMY_DATABASE_URI = 'postgresql://<user>:<password>@<host>:<port>/<db_name>'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 🔐 CRITICAL: Change this to a long, random secret key for security.
    SECRET_KEY = 'YOUR_SUPER_SECRET_KEY'
    
    # Path where detection images are stored
    DETECTION_IMAGE_FOLDER = 'storage/uploads'
  
```

### 🐘 Database Management (Migrations)
This project uses Flask-Migrate to handle database changes.

## 1.Initialize Migration Repository (Run only once):
```bash
flask db init
```

## 2.Create Initial Migration Script:
```bash
flask db migrate -m "Initial database setup"
```

## 3. Apply Migrations to DB:
```bash
flask db upgrade
```

### 🏃 Running the Application
Ensure your virtual environment is active, and then run the main application file:

```bash
python app.py
```
The server will start running, typically accessible at http://127.0.0.1:5000/.

### 🗺️ API Endpoints Reference
All endpoints prefixed with /api/detections/ and /auth/ are available.


## 🔑 Authentication Routes (`/auth`)

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| **`POST`** | `/auth/register` | Creates a new user account. | No |
| **`POST`** | `/auth/login` | Authenticates a user and returns a JWT Bearer Token. | No |
| **`GET`** | `/auth/profile` | Retrieves the authenticated user's details. | Yes |

## 🧠 ML Inference Route (`/detection`)

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| **`POST`** | `/detection/detects` | Runs ML detection on an uploaded image file (form-data). | No |

## 💾 Detection & CRUD Routes (`/api/detections`)

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| **`POST`** | `/api/detections/` | Uploads, runs ML, and saves the detection record. | Yes |
| **`GET`** | `/api/detections/my` | Get all detections submitted by the current user. | Yes |
| **`GET`** | `/api/detections/my/<int:id>` | Get a single detection record by ID. | Yes |
| **`PUT`** | `/api/detections/my/<int:id>` | Update the location of a specific detection. | Yes |
| **`DELETE`**| `/api/detections/my/<int:id>` | Delete a single detection record. | Yes |
| **`GET`** | `/api/detections/user/<int:user_id>` | **(Optimized)** Get all detection records for a specific User ID. | Yes |