from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId
import os

app = Flask(__name__, static_folder='.')
CORS(app)

# MongoDB Configuration
MONGO_URI = "mongodb+srv://DoT:deepesh@cluster0.kuklpl0.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DB_NAME = "dot_database"
COLLECTION_NAME = "registrations"

# Initialize MongoDB
try:
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]
    client.admin.command('ping')
    print("=" * 70)
    print("✓ Successfully connected to MongoDB!")
    print(f"✓ Database: {DB_NAME}")
    print(f"✓ Collection: {COLLECTION_NAME}")
    print("=" * 70)
except Exception as e:
    print(f"✗ Failed to connect to MongoDB: {e}")
    client = None

# Serve the HTML frontend
@app.route('/')
def index():
    return send_from_directory('.', 'form.html')

@app.route('/register', methods=['POST', 'OPTIONS'])
def register():
    """Handle user registration"""

    # Handle preflight CORS
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response

    # Check MongoDB connection
    if client is None:
        return jsonify({
            'success': False,
            'error': 'Database connection not available'
        }), 500

    try:
        data = request.get_json()

        # ====================================================================
        # DETAILED LOGGING - Show what's being pushed
        # ====================================================================
        print("\n" + "=" * 70)
        print("📥 NEW REGISTRATION REQUEST")
        print("=" * 70)
        print(f"⏰ Timestamp: {datetime.utcnow().isoformat()}")
        print(f"📍 IP: {request.remote_addr}")
        print("\n📦 RAW DATA:")
        print(f"  Full Name: {data.get('full_name')}")
        print(f"  Personal Email: {data.get('personal_email')}")
        print(f"  Company: {data.get('company_name')}")
        print(f"  Company Email: {data.get('company_email')}")
        print(f"  Terms Accepted: {data.get('accepted_terms')}")
        print(f"  Newsletter: {data.get('newsletter_opt_in')}")

        # Validate required fields
        required_fields = ['full_name', 'personal_email']
        for field in required_fields:
            if not data.get(field):
                print(f"\n❌ VALIDATION FAILED: {field} is required")
                print("=" * 70 + "\n")
                return jsonify({
                    'success': False,
                    'error': f'{field} is required'
                }), 400

        # Prepare document
        registration_doc = {
            'full_name': data.get('full_name'),
            'personal_email': data.get('personal_email'),
            'company_name': data.get('company_name', ''),
            'company_email': data.get('company_email', ''),
            'accepted_terms': data.get('accepted_terms', False),
            'newsletter_opt_in': data.get('newsletter_opt_in', False),
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }

        # ====================================================================
        # SHOW DATA BEING PUSHED TO MONGODB
        # ====================================================================
        print("\n📤 DATA BEING PUSHED TO MONGODB:")
        print("-" * 70)
        print(f"👤 Full Name:       {registration_doc['full_name']}")
        print(f"📧 Personal Email:  {registration_doc['personal_email']}")
        print(f"🏢 Company:         {registration_doc['company_name'] or '(not provided)'}")
        print(f"📧 Company Email:   {registration_doc['company_email'] or '(not provided)'}")
        print(f"✅ Terms:           {'YES' if registration_doc['accepted_terms'] else 'NO'}")
        print(f"📰 Newsletter:      {'YES' if registration_doc['newsletter_opt_in'] else 'NO'}")
        print(f"🕐 Created:         {registration_doc['created_at'].isoformat()}")
        print("-" * 70)
        print(f"\n🗄️  Target: {DB_NAME}.{COLLECTION_NAME}")
        print("\n⏳ Inserting into MongoDB...")

        # Insert into MongoDB
        result = collection.insert_one(registration_doc)

        # ====================================================================
        # SUCCESS CONFIRMATION
        # ====================================================================
        total_docs = collection.count_documents({})
        print("\n✅ SUCCESS! Registration saved")
        print("-" * 70)
        print(f"🆔 Document ID: {result.inserted_id}")
        print(f"📊 Total Documents: {total_docs}")
        print("=" * 70 + "\n")

        # Prepare response
        registration_doc['_id'] = str(result.inserted_id)
        registration_doc['created_at'] = registration_doc['created_at'].isoformat()
        registration_doc['updated_at'] = registration_doc['updated_at'].isoformat()

        return jsonify({
            'success': True,
            'message': 'Registration successful',
            'data': registration_doc
        }), 201

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("=" * 70 + "\n")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/registrations', methods=['GET'])
def get_registrations():
    """Get all registrations"""

    if client is None:
        return jsonify({
            'success': False,
            'error': 'Database connection not available'
        }), 500

    try:
        registrations = list(collection.find().sort('created_at', -1))

        print(f"\n📋 Retrieved {len(registrations)} registrations")

        # Convert ObjectId and datetime to strings
        for reg in registrations:
            reg['_id'] = str(reg['_id'])
            reg['created_at'] = reg['created_at'].isoformat()
            reg['updated_at'] = reg['updated_at'].isoformat()

        return jsonify({
            'success': True,
            'count': len(registrations),
            'data': registrations
        }), 200

    except Exception as e:
        print(f"Error fetching registrations: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    mongo_status = 'connected' if client is not None else 'disconnected'

    count = 0
    if client is not None:
        try:
            count = collection.count_documents({})
        except:
            pass

    print(f"\n🏥 Health check - MongoDB: {mongo_status}, Documents: {count}")

    return jsonify({
        'status': 'ok',
        'mongodb': mongo_status,
        'database': DB_NAME,
        'collection': COLLECTION_NAME,
        'total_registrations': count
    }), 200

if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("🚀 DOT REGISTRATION SERVER - Flask + MongoDB")
    print("=" * 70)
    print(f"\n📡 Server starting on http://localhost:5000")
    print(f"\nEndpoints:")
    print(f"  GET    http://localhost:5000/              - Frontend")
    print(f"  POST   http://localhost:5000/register      - Save registration")
    print(f"  GET    http://localhost:5000/registrations - View all")
    print(f"  GET    http://localhost:5000/health        - Health check")
    print("\n" + "=" * 70 + "\n")
    print("🎯 Ready to accept registrations!\n")

    app.run(host='0.0.0.0', port=5032, debug=True)
