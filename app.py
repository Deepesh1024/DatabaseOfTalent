# app.py - Integrated Flask Application
from flask import Flask, render_template, request, jsonify, session, send_from_directory
from flask_session import Session
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime
from typing import Dict, List, Tuple
from bson import ObjectId
import json
import os

app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = 'flask_session'   # ← ADD THIS LINE
Session(app)
CORS(app)

# ============================================================================
# MONGODB CONFIGURATION
# ============================================================================
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


# ============================================================================
# DOT RECOMMENDATION SYSTEM
# ============================================================================
class DOTRecommendationSystem:
    """
    Scoring & ranking system for DOT-style profiles.
    """

    def __init__(self):
        self.last_results = None
        self.dot_profiles_cache = None

    def load_dot_profiles(self, filepath: str = 'data.json') -> List[Dict]:
        """Load DOT profiles from JSON file"""
        try:
            if not os.path.exists(filepath):
                raise FileNotFoundError(f"File {filepath} not found")
            
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, dict) and 'dot_profiles' in data:
                profiles = data['dot_profiles']
            elif isinstance(data, list):
                profiles = data
            else:
                raise ValueError("Invalid data.json format. Expected {'dot_profiles': [...]} or [...]")
            
            self.dot_profiles_cache = profiles
            return profiles
        
        except Exception as e:
            raise Exception(f"Error loading DOT profiles: {str(e)}")

    def _get_weights(self, job_req: Dict) -> Dict[str, float]:
        default_weights = {
            "skills": 0.30,
            "experience": 0.15,
            "screening": 0.15,
            "github": 0.15,
            "coding": 0.15,
            "trust": 0.10,
            "fraud_penalty": 0.10,
        }
        user_w = job_req.get("weights") or {}
        w = {k: float(user_w.get(k, v)) for k, v in default_weights.items()}

        pos_keys = ["skills", "experience", "screening", "github", "coding", "trust"]
        pos_sum = sum(max(w[k], 0.0) for k in pos_keys)
        if pos_sum > 0:
            for k in pos_keys:
                w[k] = max(w[k], 0.0) / pos_sum
        w["fraud_penalty"] = min(max(w["fraud_penalty"], 0.0), 0.5)
        return w

    def _score_skills(self, profile: Dict, job_req: Dict) -> float:
        required_skills = set(job_req.get("required_skills", []))
        nice_to_have = set(job_req.get("nice_to_have_skills", []))
        verified = set(profile.get("verified_skills", []))
        rejected = set(profile.get("skills_rejected", []))

        if not required_skills and not nice_to_have:
            return 0.5

        required_covered = len(required_skills & verified)
        required_total = len(required_skills) if required_skills else 1
        nice_covered = len(nice_to_have & verified)
        nice_total = len(nice_to_have) if nice_to_have else 1

        required_score = required_covered / required_total
        nice_score = nice_covered / nice_total if nice_to_have else 0.0

        rejected_required = len(required_skills & rejected)
        reject_penalty = 0.15 * (rejected_required / max(required_total, 1))

        score = 0.8 * required_score + 0.2 * nice_score - reject_penalty
        return max(0.0, min(1.0, score))

    def _score_experience(self, profile: Dict, job_req: Dict) -> float:
        meta = profile.get("candidate_meta", {})
        years = float(meta.get("experience_years", 0.0))
        min_years = float(job_req.get("min_experience_years", 0.0))
        target_years = float(job_req.get("target_experience_years", max(min_years, 3.0)))

        if years <= 0 and min_years <= 0:
            return 0.5

        if years < min_years:
            return max(0.0, years / max(min_years, 0.1))

        if years <= target_years:
            return 0.7 + 0.3 * ((years - min_years) / max(target_years - min_years, 0.1))

        over = years - target_years
        return max(0.8, 1.0 - 0.05 * min(over, 5))

    def _score_screening(self, profile: Dict) -> float:
        rounds = profile.get("rounds", {})
        scr = rounds.get("screening_round", {})
        if not scr:
            return 0.5

        keys = ["problem_understanding", "communication_clarity", "logical_reasoning"]
        vals = [float(scr.get(k, 0.0)) for k in keys]
        if not any(vals):
            return 0.5
        base = sum(vals) / len(vals)

        red_flags = scr.get("red_flags", []) or []
        penalty = 0.1 * min(len(red_flags), 3)
        return max(0.0, min(1.0, base - penalty))

    def _score_github(self, profile: Dict) -> float:
        rounds = profile.get("rounds", {})
        gh = rounds.get("github_analysis", {})
        if not gh:
            return 0.5

        originality = float(gh.get("originality_score", 0.0))
        code_quality = float(gh.get("code_quality", 0.0))
        commit_consistency = float(gh.get("commit_consistency", 0.0))

        vals = [originality, code_quality, commit_consistency]
        if not any(vals):
            return 0.5
        return max(0.0, min(1.0, sum(vals) / len(vals)))

    def _score_coding(self, profile: Dict) -> float:
        rounds = profile.get("rounds", {})
        dsa = rounds.get("dsa_coding_round", {})
        if not dsa:
            return 0.5

        ps = float(dsa.get("problem_solving_score", 0.0))
        tc = float(dsa.get("time_complexity_awareness", 0.0))
        ec = float(dsa.get("edge_case_handling", 0.0))

        vals = [ps, tc, ec]
        if not any(vals):
            return 0.5
        base = sum(vals) / len(vals)

        anti = dsa.get("anti_cheat_signals", {}) or {}
        cp = bool(anti.get("copy_paste_detected", False))
        kv = anti.get("keystroke_variance", "normal")

        fraud_penalty = 0.0
        if cp:
            fraud_penalty += 0.25
        if isinstance(kv, str) and kv.lower() in ["suspicious", "very_low", "very_high"]:
            fraud_penalty += 0.10

        return max(0.0, min(1.0, base - fraud_penalty))

    def _score_trust(self, profile: Dict) -> float:
        crv = profile.get("cross_round_validation", {}) or {}
        trust = float(crv.get("trust_score", 0.0))
        claim_align = float(crv.get("skill_claim_alignment", 0.0))
        reasoning_consistency = float(crv.get("reasoning_consistency", 0.0))

        vals = [trust, claim_align, reasoning_consistency]
        if not any(vals):
            return 0.5
        return max(0.0, min(1.0, (trust * 0.5 + claim_align * 0.25 + reasoning_consistency * 0.25)))

    def _fraud_penalty(self, profile: Dict) -> float:
        rounds = profile.get("rounds", {})
        dsa = rounds.get("dsa_coding_round", {})
        anti = dsa.get("anti_cheat_signals", {}) or {}

        cp = bool(anti.get("copy_paste_detected", False))
        kv = anti.get("keystroke_variance", "normal")

        penalty = 0.0
        if cp:
            penalty += 0.6
        if isinstance(kv, str) and kv.lower() in ["suspicious", "very_low", "very_high"]:
            penalty += 0.2

        resume = rounds.get("resume_analysis", {}) or {}
        over_flags = resume.get("overclaim_flags", []) or []
        penalty += 0.05 * min(len(over_flags), 4)

        return max(0.0, min(1.0, penalty))

    def calculate_match_score(self, profile: Dict, job_req: Dict) -> Tuple[float, Dict]:
        weights = self._get_weights(job_req)

        skills_score = self._score_skills(profile, job_req)
        exp_score = self._score_experience(profile, job_req)
        screening_score = self._score_screening(profile)
        github_score = self._score_github(profile)
        coding_score = self._score_coding(profile)
        trust_score = self._score_trust(profile)
        fraud_p = self._fraud_penalty(profile)

        positive = (
            weights["skills"] * skills_score
            + weights["experience"] * exp_score
            + weights["screening"] * screening_score
            + weights["github"] * github_score
            + weights["coding"] * coding_score
            + weights["trust"] * trust_score
        )

        negative = weights["fraud_penalty"] * fraud_p

        final_score = max(0.0, min(1.0, positive - negative))
        percentage = final_score * 100.0

        detail = {
            "skills_score": round(skills_score, 3),
            "experience_score": round(exp_score, 3),
            "screening_score": round(screening_score, 3),
            "github_score": round(github_score, 3),
            "coding_score": round(coding_score, 3),
            "trust_score": round(trust_score, 3),
            "fraud_penalty_raw": round(fraud_p, 3),
            "weights": weights,
            "final_score": round(final_score, 4),
            "match_percentage": round(percentage, 2),
        }
        return percentage, detail

    def generate_recommendation_text(self, score: float, detail: Dict, profile: Dict) -> str:
        strengths = []
        gaps = []

        if detail["skills_score"] >= 0.75:
            strengths.append("skills match")
        elif detail["skills_score"] < 0.5:
            gaps.append("core skills")

        if detail["experience_score"] >= 0.75:
            strengths.append("relevant experience")
        elif detail["experience_score"] < 0.5:
            gaps.append("experience level")

        if detail["coding_score"] >= 0.75:
            strengths.append("problem solving & coding")
        elif detail["coding_score"] < 0.5:
            gaps.append("coding depth")

        if detail["trust_score"] >= 0.75:
            strengths.append("high cross-round trust")
        elif detail["trust_score"] < 0.5:
            gaps.append("signal consistency")

        if score >= 80:
            base = "🌟 EXCELLENT MATCH - Strong candidate"
        elif score >= 65:
            base = "✅ GOOD MATCH - Solid candidate"
        elif score >= 50:
            base = "⚠️ PARTIAL MATCH - Candidate shows potential"
        else:
            base = "❌ POOR MATCH - Limited fit for this role"

        parts = [base]
        if strengths:
            parts.append(f"key strengths in {', '.join(strengths)}")
        if gaps:
            parts.append(f"notable gaps in {', '.join(gaps)}")
        notes = profile.get("notes")
        if notes:
            parts.append(f"notes: {notes}")

        return ". ".join(parts)

    def rank_candidates(self, job_req: Dict, dot_profiles: List[Dict]) -> Dict:
        results = []
        for prof in dot_profiles:
            score, detail = self.calculate_match_score(prof, job_req)
            dot_id = prof.get("dot_id", "UNKNOWN")
            results.append((dot_id, score, detail, prof))

        results.sort(key=lambda x: x[1], reverse=True)

        ranking_list = []
        insights = {}

        for idx, (dot_id, score, detail, prof) in enumerate(results, start=1):
            recommendation = self.generate_recommendation_text(score, detail, prof)
            candidate_analysis = {
                "rank": idx,
                "overall_score": round(score, 2),
                "match_percentage": f"{score:.1f}%",
                "component_scores": detail,
                "final_verdict": prof.get("final_verdict"),
                "verified_skills": prof.get("verified_skills", []),
                "skills_rejected": prof.get("skills_rejected", []),
                "candidate_meta": prof.get("candidate_meta", {}),
                "recommendation": recommendation,
            }
            ranking_list.append((dot_id, candidate_analysis))
            insights[dot_id] = detail

        job_analysis = {
            "required_skills": job_req.get("required_skills", []),
            "nice_to_have_skills": job_req.get("nice_to_have_skills", []),
            "min_experience_years": job_req.get("min_experience_years", 0),
            "target_experience_years": job_req.get("target_experience_years", 0),
            "primary_domain": job_req.get("primary_domain"),
        }

        final = {
            "ranking": ranking_list,
            "insights": insights,
            "job_requirements_analysis": job_analysis,
        }
        self.last_results = final
        return final


# Initialize system
recommendation_system = DOTRecommendationSystem()


# ============================================================================
# ROUTES - MAIN APPLICATION
# ============================================================================

@app.route('/')
def index():
    """Serve the main HTML page (index.html)"""
    return render_template('index.html')


@app.route('/form')
def registration_form():
    """Serve the registration form page (form.html)"""
    return send_from_directory('.', 'form.html')


@app.route('/api')
def api_info():
    """API information endpoint"""
    return jsonify({
        'status': 'DOT Recommendation System',
        'endpoints': {
            '/': 'GET - Main web interface',
            '/form': 'GET - Registration form',
            '/register': 'POST - User registration',
            '/registrations': 'GET - View all registrations',
            '/analyze': 'POST - Analyze candidates with job requirements',
            '/export': 'GET - Export last analysis results',
            '/profiles': 'GET - View loaded DOT profiles',
            '/reload': 'POST - Reload data.json file',
            '/health': 'GET - System health check'
        }
    })


# ============================================================================
# ROUTES - REGISTRATION SYSTEM
# ============================================================================

@app.route('/register', methods=['POST', 'OPTIONS'])
def register():
    """Handle user registration"""

    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response

    if client is None:
        return jsonify({
            'success': False,
            'error': 'Database connection not available'
        }), 500

    try:
        data = request.get_json()

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

        required_fields = ['full_name', 'personal_email']
        for field in required_fields:
            if not data.get(field):
                print(f"\n❌ VALIDATION FAILED: {field} is required")
                print("=" * 70 + "\n")
                return jsonify({
                    'success': False,
                    'error': f'{field} is required'
                }), 400

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

        result = collection.insert_one(registration_doc)

        total_docs = collection.count_documents({})
        print("\n✅ SUCCESS! Registration saved")
        print("-" * 70)
        print(f"🆔 Document ID: {result.inserted_id}")
        print(f"📊 Total Documents: {total_docs}")
        print("=" * 70 + "\n")

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


# ============================================================================
# ROUTES - RECOMMENDATION SYSTEM
# ============================================================================

@app.route('/profiles')
def view_profiles():
    """View all loaded DOT profiles"""
    try:
        profiles = recommendation_system.load_dot_profiles()
        return jsonify({
            'success': True,
            'total_profiles': len(profiles),
            'profiles': profiles
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/reload', methods=['POST'])
def reload_profiles():
    """Manually reload data.json"""
    try:
        profiles = recommendation_system.load_dot_profiles()
        return jsonify({
            'success': True,
            'message': 'Profiles reloaded successfully',
            'total_profiles': len(profiles)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        data = request.get_json(force=True)
        job_requirements = data.get('job_requirements') or {}

        if not job_requirements:
            return jsonify({'error': 'Missing job_requirements in request body'}), 400

        try:
            dot_profiles = recommendation_system.load_dot_profiles()
        except Exception as e:
            return jsonify({'error': f'Failed to load DOT profiles: {str(e)}'}), 500

        if not dot_profiles:
            return jsonify({'error': 'No profiles found in data.json'}), 400

        recommendations = recommendation_system.rank_candidates(job_requirements, dot_profiles)

        session['last_analysis'] = {
            'timestamp': datetime.now().isoformat(),
            'job_requirements': job_requirements,
            'dot_profiles_count': len(dot_profiles),
            'results': recommendations
        }

        return jsonify({
            'success': True,
            'profiles_analyzed': len(dot_profiles),
            'recommendations': recommendations
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/export')
def export():
    if 'last_analysis' not in session:
        return jsonify({'error': 'No analysis data found'}), 404

    analysis_data = session['last_analysis']
    results = analysis_data['results']

    export_data = {
        'timestamp': analysis_data['timestamp'],
        'job_analysis': results['job_requirements_analysis'],
        'total_profiles_analyzed': analysis_data['dot_profiles_count'],
        'candidates': []
    }

    for dot_id, analysis in results['ranking']:
        export_data['candidates'].append({
            'dot_id': dot_id,
            'rank': analysis['rank'],
            'score': analysis['overall_score'],
            'match_percentage': analysis['match_percentage'],
            'final_verdict': analysis.get('final_verdict'),
            'verified_skills': analysis.get('verified_skills', []),
            'skills_rejected': analysis.get('skills_rejected', []),
            'candidate_meta': analysis.get('candidate_meta', {}),
            'recommendation': analysis.get('recommendation'),
            'component_scores': analysis.get('component_scores', {}),
        })

    return jsonify(export_data)


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
        'total_registrations': count,
        'recommendation_system': 'active'
    }), 200


# ============================================================================
# APPLICATION STARTUP
# ============================================================================

if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("🚀 DOT INTEGRATED SYSTEM - Flask + MongoDB")
    print("=" * 70)
    print(f"\n📡 Server starting on http://localhost:8000")
    print(f"\n🌐 Frontend Endpoints:")
    print(f"  GET    http://localhost:8000/              - Main Dashboard (index.html)")
    print(f"  GET    http://localhost:8000/form          - Registration Form (form.html)")
    print(f"\n📝 Registration Endpoints:")
    print(f"  POST   http://localhost:8000/register      - Save registration")
    print(f"  GET    http://localhost:8000/registrations - View all registrations")
    print(f"\n🎯 Recommendation Endpoints:")
    print(f"  POST   http://localhost:8000/analyze       - Analyze candidates")
    print(f"  GET    http://localhost:8000/profiles      - View DOT profiles")
    print(f"  GET    http://localhost:8000/export        - Export analysis")
    print(f"  POST   http://localhost:8000/reload        - Reload data.json")
    print(f"\n🔧 System Endpoints:")
    print(f"  GET    http://localhost:8000/api           - API documentation")
    print(f"  GET    http://localhost:8000/health        - Health check")
    print("\n" + "=" * 70 + "\n")
    print("✅ System ready!")
    print("📊 Recommendation System: Active")
    print(f"🗄️  MongoDB: {'Connected' if client else 'Disconnected'}\n")

    app.run(host='0.0.0.0', port=80, debug=False)
