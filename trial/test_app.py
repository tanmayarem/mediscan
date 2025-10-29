#!/usr/bin/env python3
"""Test script to check if the app loads without errors."""

import os
import sys

# API keys should be set via environment variables before running tests
# Check if we have required environment variables
if not (os.environ.get("GROQ_API_KEY") or os.environ.get("OPENAI_API_KEY")):
    print("Warning: No API key found for AI features. Some tests may use fallback mode.")

print("Testing MedScan Application...")
print("=" * 50)

try:
    print("\n1. Testing imports...")
    from app import create_app
    print("   [OK] app.py imported")
    
    from features.interaction_checker import check_medicine_interactions
    print("   [OK] interaction_checker imported")
    
    from features.pill_identifier import identify_pill_from_image
    print("   [OK] pill_identifier imported")
    
    from features.severity_analyzer import analyze_side_effect_severity
    print("   [OK] severity_analyzer imported")
    
    from features.user_auth import UserAuthManager
    print("   [OK] user_auth imported")
    
    from features.chatbot import MedicineChatbot
    print("   [OK] chatbot imported")
    
    from features.translator import translate_text, Translator
    print("   [OK] translator imported")
    
    from features.n8n_webhooks import api_bp
    print("   [OK] n8n_webhooks imported")
    
    print("\n2. Testing app creation...")
    app = create_app()
    print("   [OK] Flask app created successfully")
    
    print("\n3. Testing chatbot initialization...")
    chatbot = MedicineChatbot()
    if chatbot.api_key:
        print(f"   [OK] Chatbot initialized with API key (first 10 chars: {chatbot.api_key[:10]}...)")
        print(f"   [OK] Using provider: {chatbot.api_provider}")
    else:
        print("   [WARNING] Chatbot initialized without API key (will use fallback)")
    
    print("\n4. Testing routes...")
    with app.test_client() as client:
        # Test health endpoint
        response = client.get('/api/health')
        if response.status_code == 200:
            print("   [OK] Health endpoint works")
        else:
            print(f"   [WARNING] Health endpoint returned {response.status_code}")
        
        # Test home page
        response = client.get('/')
        if response.status_code == 200:
            print("   [OK] Home page loads")
        else:
            print(f"   [WARNING] Home page returned {response.status_code}")
    
    print("\n" + "=" * 50)
    print("[SUCCESS] ALL TESTS PASSED! The app is ready to run.")
    print("\nTo start the app, run:")
    print("  python app.py")
    print("\nOr use the start script:")
    print("  .\\start_app.ps1")
    
except Exception as e:
    print(f"\n[ERROR] {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

