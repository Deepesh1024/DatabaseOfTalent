from flask import Flask, render_template_string, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime, timezone
from bson import ObjectId
import traceback


# MongoDB Configuration
MONGO_URI = "mongodb+srv://DoT:deepesh@cluster0.kuklpl0.mongodb.net/?appName=Cluster0"
DB_NAME = "dot_database"
COLLECTION_NAME = "registrations"


# Initialize Flask App
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})


# Global variables
mongo_client = None
mongo_db = None
mongo_collection = None
connection_error = None


def init_mongodb():
    """Initialize MongoDB connection"""
    global mongo_client, mongo_db, mongo_collection, connection_error
    try:
        print("\n" + "="*70)
        print("Connecting to MongoDB...")
        print(f"Database: {DB_NAME}")
        print(f"Collection: {COLLECTION_NAME}")
        print("="*70)


        mongo_client = MongoClient(MONGO_URI)

        # Test connection
        mongo_client.admin.command('ping')
        print("✓ Ping successful!")


        # Set up database and collection
        mongo_db = mongo_client[DB_NAME]
        mongo_collection = mongo_db[COLLECTION_NAME]


        # Test query
        count = mongo_collection.count_documents({})
        print(f"✓ Found {count} documents")
        print("="*70 + "\n")


        connection_error = None
        return True


    except Exception as e:
        connection_error = str(e)
        print("\n" + "="*70)
        print("✗ MongoDB CONNECTION FAILED")
        print(f"Error: {connection_error}")
        print("="*70 + "\n")
        return False


# HTML Template - Complete Dashboard
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DOT Registration Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: 'Inter', sans-serif;
            background: #0a0a0a;
            color: #ffffff;
            padding: 40px 20px;
            min-height: 100vh;
        }


        .container { max-width: 1400px; margin: 0 auto; }


        .header {
            text-align: center;
            margin-bottom: 40px;
            padding-bottom: 30px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }


        .header h1 {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 3rem;
            color: #ffffff;
            margin-bottom: 10px;
            letter-spacing: 2px;
        }


        .header p { color: #666666; font-size: 1.1rem; letter-spacing: 1px; }


        .connection-status {
            display: inline-block;
            padding: 10px 20px;
            margin-top: 15px;
            border-radius: 4px;
            font-size: 0.9rem;
            font-weight: 600;
        }


        .connection-status.connected {
            background: rgba(0, 255, 0, 0.1);
            color: #00ff00;
            border: 1px solid rgba(0, 255, 0, 0.3);
        }


        .connection-status.error {
            background: rgba(255, 0, 0, 0.1);
            color: #ff4444;
            border: 1px solid rgba(255, 0, 0, 0.3);
        }


        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }


        .stat-card {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 30px;
            transition: all 0.3s ease;
        }


        .stat-card:hover {
            background: rgba(255, 255, 255, 0.05);
            transform: translateY(-5px);
        }


        .stat-card h3 {
            font-family: 'Space Grotesk', sans-serif;
            color: #666666;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 2px;
            margin-bottom: 15px;
        }


        .stat-card .value {
            font-size: 2.5rem;
            font-weight: 700;
            color: #ffffff;
        }


        .controls {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            flex-wrap: wrap;
            gap: 15px;
        }


        .btn {
            padding: 15px 30px;
            background: #ffffff;
            color: #000000;
            border: none;
            font-family: 'Space Grotesk', sans-serif;
            font-weight: 600;
            letter-spacing: 1px;
            text-transform: uppercase;
            cursor: pointer;
            transition: all 0.3s ease;
            font-size: 0.9rem;
        }


        .btn:hover {
            background: #000000;
            color: #ffffff;
            box-shadow: 0 0 0 2px #ffffff;
        }


        .table-container {
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.1);
            overflow-x: auto;
        }


        table { width: 100%; border-collapse: collapse; }
        thead { background: rgba(255, 255, 255, 0.05); }


        th {
            padding: 20px;
            text-align: left;
            font-family: 'Space Grotesk', sans-serif;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-size: 0.85rem;
            color: #999999;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }


        td {
            padding: 20px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            color: #cccccc;
        }


        tr:hover { background: rgba(255, 255, 255, 0.03); }


        .badge {
            display: inline-block;
            padding: 5px 12px;
            background: rgba(0, 255, 0, 0.1);
            color: #00ff00;
            font-size: 0.75rem;
            font-weight: 600;
            letter-spacing: 1px;
            text-transform: uppercase;
            border: 1px solid rgba(0, 255, 0, 0.3);
        }


        .badge.no {
            background: rgba(255, 0, 0, 0.1);
            color: #ff4444;
            border-color: rgba(255, 0, 0, 0.3);
        }


        .loading {
            text-align: center;
            padding: 60px;
            color: #666666;
            font-size: 1.2rem;
        }


        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }


        .pulse { animation: pulse 2s ease-in-out infinite; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>DOT DASHBOARD</h1>
            <p>Registration Data Management</p>
            <div class="connection-status" id="connectionStatus">● Connecting...</div>
        </div>


        <div class="stats-grid">
            <div class="stat-card">
                <h3>Total Registrations</h3>
                <div class="value" id="totalCount">-</div>
            </div>
            <div class="stat-card">
                <h3>Newsletter Subscribers</h3>
                <div class="value" id="newsletterCount">-</div>
            </div>
            <div class="stat-card">
                <h3>Unique Companies</h3>
                <div class="value" id="companyCount">-</div>
            </div>
            <div class="stat-card">
                <h3>Today's Registrations</h3>
                <div class="value" id="todayCount">-</div>
            </div>
        </div>


        <div class="controls">
            <button class="btn" onclick="refreshData()">↻ Refresh Data</button>
        </div>


        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>Full Name</th>
                        <th>Personal Email</th>
                        <th>Company</th>
                        <th>Company Email</th>
                        <th>Terms</th>
                        <th>Newsletter</th>
                        <th>Registered</th>
                    </tr>
                </thead>
                <tbody id="dataTable">
                    <tr>
                        <td colspan="7" class="loading pulse">Loading data...</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>


    <script>
        let allData = [];


        async function fetchData() {
            console.log('Fetching data from /api/registrations...');


            try {
                const response = await fetch('/api/registrations');
                console.log('Response status:', response.status);


                const result = await response.json();
                console.log('Response data:', result);


                if (result.success) {
                    allData = result.data;
                    updateConnectionStatus(true, result.source || 'MongoDB');
                    updateStats();
                    renderTable();
                    console.log('Successfully loaded', allData.length, 'registrations');
                } else {
                    console.error('Error:', result.error);
                    updateConnectionStatus(false, result.error);
                    showError(result.error);
                }
            } catch (error) {
                console.error('Fetch error:', error);
                updateConnectionStatus(false, error.message);
                showError('Network error: ' + error.message);
            }
        }


        function updateConnectionStatus(connected, message = '') {
            const statusEl = document.getElementById('connectionStatus');
            if (connected) {
                statusEl.textContent = `● Connected (${message})`;
                statusEl.className = 'connection-status connected';
            } else {
                statusEl.textContent = `● Error: ${message}`;
                statusEl.className = 'connection-status error';
            }
        }


        function updateStats() {
            document.getElementById('totalCount').textContent = allData.length;


            const newsletterSubs = allData.filter(r => r.newsletter_opt_in).length;
            document.getElementById('newsletterCount').textContent = newsletterSubs;


            const uniqueCompanies = new Set(allData.map(r => r.company_name || 'N/A')).size;
            document.getElementById('companyCount').textContent = uniqueCompanies;


            const today = new Date().toISOString().split('T')[0];
            const todayRegs = allData.filter(r => {
                if (!r.created_at) return false;
                const regDate = new Date(r.created_at).toISOString().split('T')[0];
                return regDate === today;
            }).length;
            document.getElementById('todayCount').textContent = todayRegs;
        }


        function renderTable() {
            const tbody = document.getElementById('dataTable');


            if (allData.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="7" style="text-align: center; padding: 40px; color: #666;">
                            <h3>No Data Available</h3>
                            <p>No registrations found in the database</p>
                        </td>
                    </tr>
                `;
                return;
            }


            tbody.innerHTML = allData.map(row => `
                <tr>
                    <td><strong>${row.full_name || 'N/A'}</strong></td>
                    <td>${row.personal_email || 'N/A'}</td>
                    <td>${row.company_name || 'N/A'}</td>
                    <td>${row.company_email || 'N/A'}</td>
                    <td><span class="badge ${row.accepted_terms ? '' : 'no'}">${row.accepted_terms ? 'Yes' : 'No'}</span></td>
                    <td><span class="badge ${row.newsletter_opt_in ? '' : 'no'}">${row.newsletter_opt_in ? 'Yes' : 'No'}</span></td>
                    <td>${row.created_at ? new Date(row.created_at).toLocaleString() : 'N/A'}</td>
                </tr>
            `).join('');
        }


        function showError(message) {
            const tbody = document.getElementById('dataTable');
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" style="text-align: center; padding: 40px;">
                        <div style="color: #ff4444;">
                            <h3>⚠ Error Loading Data</h3>
                            <p style="margin-top: 10px; color: #cccccc;">${message}</p>
                            <button class="btn" onclick="refreshData()" style="margin-top: 20px;">Try Again</button>
                        </div>
                    </td>
                </tr>
            `;
        }


        function refreshData() {
            console.log('Refreshing data...');
            document.getElementById('dataTable').innerHTML = `
                <tr>
                    <td colspan="7" class="loading pulse">Refreshing...</td>
                </tr>
            `;
            fetchData();
        }


        // Initialize
        console.log('Dashboard initialized');
        fetchData();
    </script>
</body>
</html>
"""


@app.route('/')
def dashboard():
    """Main dashboard page"""
    return render_template_string(DASHBOARD_HTML)


@app.route('/api/registrations', methods=['GET'])
def get_registrations():
    """Get all registrations from MongoDB"""
    print("\n=== API Request: GET /api/registrations ===")


    if mongo_collection is None:
        print("ERROR: MongoDB not connected")
        return jsonify({
            'success': False,
            'error': connection_error or 'MongoDB not connected',
            'data': []
        }), 500


    try:
        print("Fetching from MongoDB...")
        registrations = list(mongo_collection.find().sort('created_at', -1))
        print(f"✓ Found {len(registrations)} registrations")


        # Convert ObjectId and datetime to strings
        for reg in registrations:
            # Convert _id
            if '_id' in reg and isinstance(reg['_id'], ObjectId):
                reg['_id'] = str(reg['_id'])

            # Convert datetime fields
            for field in ['created_at', 'updated_at']:
                if field in reg:
                    if isinstance(reg[field], datetime):
                        reg[field] = reg[field].isoformat()


        print(f"✓ Returning {len(registrations)} registrations")
        print(f"Sample data: {registrations[0] if registrations else 'No data'}")


        return jsonify({
            'success': True,
            'count': len(registrations),
            'data': registrations,
            'source': 'MongoDB'
        }), 200


    except Exception as e:
        error_msg = str(e)
        print(f"ERROR: {error_msg}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': error_msg,
            'data': []
        }), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    is_connected = mongo_collection is not None

    doc_count = 0
    if is_connected:
        try:
            doc_count = mongo_collection.count_documents({})
        except:
            pass

    return jsonify({
        'status': 'ok',
        'mongodb_connected': is_connected,
        'database': DB_NAME,
        'collection': COLLECTION_NAME,
        'document_count': doc_count,
        'connection_error': connection_error if not is_connected else None,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }), 200


if __name__ == '__main__':
    print("\n" + "="*70)
    print("🚀 DOT REGISTRATION DASHBOARD")
    print("="*70)


    # Initialize MongoDB
    init_mongodb()


    print("\nStarting Flask server...")
    print(f"Dashboard URL: http://localhost:5033")
    print(f"Health Check:  http://localhost:5033/health")
    print(f"API Endpoint:  http://localhost:5033/api/registrations")
    print("\nPress CTRL+C to stop\n")
    print("="*70 + "\n")


    app.run(host='0.0.0.0', port=5033, debug=True, use_reloader=False)