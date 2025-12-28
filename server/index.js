require('dotenv').config();
const express = require('express');
const cors = require('cors');
const { MongoClient, ObjectId } = require('mongodb');
const path = require('path');

const app = express();
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, '..')));

app.get("/", (req, res) => {
  res.sendFile(path.join(__dirname, "form.html"));
});

// MongoDB Configuration
const MONGO_URI = process.env.MONGO_URI || 'mongodb+srv://DoT:deepesh@cluster0.kuklpl0.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0';
const DB_NAME = 'dot_database';
const COLLECTION_NAME = 'registrations';

let mongoClient = null;
let db = null;
let collection = null;

async function connectToMongoDB() {
  try {
    console.log('\n' + '='.repeat(70));
    console.log('Connecting to MongoDB Atlas...');
    console.log('='.repeat(70));

    mongoClient = new MongoClient(MONGO_URI);
    await mongoClient.connect();
    await mongoClient.db('admin').command({ ping: 1 });

    db = mongoClient.db(DB_NAME);
    collection = db.collection(COLLECTION_NAME);

    const count = await collection.countDocuments();

    console.log('✓ Successfully connected to MongoDB!');
    console.log('✓ Database:', DB_NAME);
    console.log('✓ Collection:', COLLECTION_NAME);
    console.log('✓ Current documents:', count);
    console.log('='.repeat(70) + '\n');

    return true;
  } catch (error) {
    console.error('✗ MongoDB connection failed!');
    console.error('Error:', error.message);
    return false;
  }
}

app.post('/register', async (req, res) => {
  try {
    if (!mongoClient || !collection) {
      return res.status(500).json({ 
        success: false, 
        error: 'Database not connected' 
      });
    }

    const payload = req.body || {};

    // ====================================================================
    // DETAILED DATA LOGGING - Shows exactly what's being pushed
    // ====================================================================
    console.log('\n' + '='.repeat(70));
    console.log('📥 NEW REGISTRATION REQUEST RECEIVED');
    console.log('='.repeat(70));
    console.log('⏰ Timestamp:', new Date().toISOString());
    console.log('📍 IP Address:', req.ip || req.connection.remoteAddress);
    console.log('\n📦 RAW REQUEST BODY:');
    console.log(JSON.stringify(payload, null, 2));
    console.log('\n' + '-'.repeat(70));

    // Validation
    const required = ['full_name', 'personal_email'];
    for (const f of required) {
      if (!payload[f] || !payload[f].trim()) {
        console.log('❌ VALIDATION FAILED:', f, 'is required');
        console.log('='.repeat(70) + '\n');
        return res.status(400).json({ 
          success: false, 
          error: f + ' is required'
        });
      }
    }

    // Prepare document
    const insertPayload = {
      full_name: payload.full_name.trim(),
      personal_email: payload.personal_email.trim(),
      company_name: (payload.company_name || '').trim(),
      company_email: (payload.company_email || '').trim(),
      accepted_terms: !!payload.accepted_terms,
      newsletter_opt_in: !!payload.newsletter_opt_in,
      created_at: new Date().toISOString()
    };

    // ====================================================================
    // PRINT FORMATTED DATA BEING PUSHED TO MONGODB
    // ====================================================================
    console.log('\n📤 DATA BEING PUSHED TO MONGODB:');
    console.log('-'.repeat(70));
    console.log('👤 Full Name:        ', insertPayload.full_name);
    console.log('📧 Personal Email:   ', insertPayload.personal_email);
    console.log('🏢 Company Name:     ', insertPayload.company_name || '(not provided)');
    console.log('📧 Company Email:    ', insertPayload.company_email || '(not provided)');
    console.log('✅ Terms Accepted:   ', insertPayload.accepted_terms ? 'YES' : 'NO');
    console.log('📰 Newsletter:       ', insertPayload.newsletter_opt_in ? 'YES' : 'NO');
    console.log('🕐 Created At:       ', insertPayload.created_at);
    console.log('-'.repeat(70));
    console.log('\n🗄️  MongoDB Details:');
    console.log('   Database:   ', DB_NAME);
    console.log('   Collection: ', COLLECTION_NAME);
    console.log('\n📋 Complete Document (JSON):');
    console.log(JSON.stringify(insertPayload, null, 2));
    console.log('\n⏳ Inserting into MongoDB...');

    // Insert into MongoDB
    const result = await collection.insertOne(insertPayload);

    // ====================================================================
    // PRINT SUCCESS CONFIRMATION
    // ====================================================================
    const totalDocs = await collection.countDocuments();
    console.log('\n✅ SUCCESS! Registration saved to MongoDB');
    console.log('-'.repeat(70));
    console.log('🆔 Document ID:', result.insertedId.toString());
    console.log('📊 Total Documents:', totalDocs);
    console.log('='.repeat(70) + '\n');

    return res.json({ 
      success: true, 
      data: [{...insertPayload, _id: result.insertedId.toString()}],
      message: 'Registration successful'
    });

  } catch (err) {
    console.error('\n❌ ERROR OCCURRED:');
    console.error('-'.repeat(70));
    console.error('Error Message:', err.message);
    console.error('Stack Trace:', err.stack);
    console.error('='.repeat(70) + '\n');

    return res.status(500).json({ 
      success: false, 
      error: err.message 
    });
  }
});

app.get('/registrations', async (req, res) => {
  try {
    if (!collection) {
      return res.status(500).json({ success: false, error: 'Not connected' });
    }

    console.log('\n📋 Fetching all registrations...');
    const data = await collection.find().sort({ created_at: -1 }).toArray();

    console.log('✅ Retrieved', data.length, 'registrations\n');

    // Print summary of all data
    console.log('='.repeat(70));
    console.log('📊 ALL REGISTRATIONS IN DATABASE');
    console.log('='.repeat(70));
    data.forEach((reg, index) => {
      console.log('\n[' + (index + 1) + '] ID:', reg._id.toString());
      console.log('    Name:', reg.full_name);
      console.log('    Email:', reg.personal_email);
      console.log('    Company:', reg.company_name || 'N/A');
      console.log('    Created:', reg.created_at);
    });
    console.log('\n' + '='.repeat(70) + '\n');

    return res.json({ 
      success: true, 
      count: data.length, 
      data: data.map(r => ({...r, _id: r._id.toString()}))
    });
  } catch (err) {
    console.error('Error fetching registrations:', err.message);
    return res.status(500).json({ success: false, error: err.message });
  }
});

app.get('/health', async (req, res) => {
  let count = 0;
  if (collection) {
    try { count = await collection.countDocuments(); } catch {}
  }

  console.log('\n🏥 Health check requested');
  console.log('   MongoDB:', collection ? '✅ Connected' : '❌ Disconnected');
  console.log('   Documents:', count + '\n');

  res.json({ 
    ok: true, 
    mongodb: collection ? 'connected' : 'disconnected',
    database: DB_NAME,
    collection: COLLECTION_NAME,
    total_documents: count,
    timestamp: new Date().toISOString()
  });
});

const PORT = process.env.PORT || 3000;

async function startServer() {
  console.log('\n' + '='.repeat(70));
  console.log('🚀 DOT REGISTRATION SERVER - ENHANCED DEBUG MODE');
  console.log('='.repeat(70));
  console.log('📍 This version prints detailed data logs');
  console.log('='.repeat(70) + '\n');

  await connectToMongoDB();

  app.listen(PORT, () => {
    console.log('='.repeat(70));
    console.log('✅ Server running on http://localhost:' + PORT);
    console.log('='.repeat(70));
    console.log('\n📡 Available Endpoints:');
    console.log('   POST   http://localhost:' + PORT + '/register       - Submit registration');
    console.log('   GET    http://localhost:' + PORT + '/registrations  - View all registrations');
    console.log('   GET    http://localhost:' + PORT + '/health         - Health check');
    console.log('\n💡 All registration data will be printed to this console');
    console.log('='.repeat(70) + '\n');
    console.log('🎯 Waiting for registration submissions...\n');
  });
}

startServer();