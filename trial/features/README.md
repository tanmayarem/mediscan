# MedScan Advanced Features

This directory contains all the advanced features for the MedScan medicine identification system.

## Features Overview

### 1. Medicine Interaction Checker (`interaction_checker.py`)
- **Purpose**: Detects dangerous combinations of medicines
- **How it works**: Uses RxNav API (free, no API key) to check drug interactions
- **Usage**:
  ```python
  from features.interaction_checker import check_medicine_interactions
  result = check_medicine_interactions(["Ibuprofen", "Aspirin"])
  ```

### 2. Pill Identifier (`pill_identifier.py`)
- **Purpose**: Identifies pills from images using AI vision
- **How it works**: Uses computer vision models to match pill features
- **Status**: Basic implementation - requires model training for production
- **Usage**:
  ```python
  from features.pill_identifier import identify_pill_from_image
  matches = identify_pill_from_image("pill.jpg", medicine_database)
  ```

### 3. Side Effect Severity Analyzer (`severity_analyzer.py`)
- **Purpose**: Categorizes side effects by severity (mild/moderate/severe)
- **How it works**: Uses keyword matching and NLP classification
- **Usage**:
  ```python
  from features.severity_analyzer import analyze_side_effect_severity
  result = analyze_side_effect_severity("Nausea, Dizziness, Severe allergic reaction")
  ```

### 4. User Authentication & Personalization (`user_auth.py`)
- **Purpose**: Manages user accounts, medical profiles, and allergies
- **Features**:
  - User registration/login
  - Medical profile (age, weight, height, etc.)
  - Allergies tracking
  - Automatic allergy conflict checking
- **Usage**:
  ```python
  from features.user_auth import UserAuthManager
  manager = UserAuthManager("database.db")
  manager.register_user("username", "email", "password")
  ```

### 5. AI Chatbot (`chatbot.py`)
- **Purpose**: Provides AI-powered answers to medicine-related queries
- **How it works**: Uses OpenAI API or Groq API (configurable)
- **Features**:
  - Internet access for current information
  - Context-aware responses
  - Fallback mode when API not available
- **Usage**:
  ```python
  from features.chatbot import get_chatbot_response
  response = get_chatbot_response("What are side effects of Paracetamol?", context={})
  ```

### 6. Multilingual Support (`translator.py`)
- **Purpose**: Translates content to Malayalam, Tamil, and Hindi
- **How it works**: Uses Google Translate API or LibreTranslate
- **Supported Languages**: English, Malayalam, Tamil, Hindi
- **Usage**:
  ```python
  from features.translator import translate_text
  translated = translate_text("Hello", "hi")  # Translates to Hindi
  ```

### 7. N8N Webhook Integration (`n8n_webhooks.py`)
- **Purpose**: Provides API endpoints for n8n workflow automation
- **Endpoints**:
  - `/api/interactions/check` - Check medicine interactions
  - `/api/pill/identify` - Identify pill from image
  - `/api/severity/analyze` - Analyze side effect severity
  - `/api/chatbot/query` - Chatbot query
  - `/api/translate` - Translate text
  - `/api/health` - Health check

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

For optional AI features:
```bash
pip install openai  # For chatbot
pip install torch transformers  # For pill identifier (optional, large download)
```

### 2. Configure API Keys (Optional)

Set environment variables:
```bash
# Windows PowerShell
$env:OPENAI_API_KEY = "your-key-here"
$env:GOOGLE_TRANSLATE_API_KEY = "your-key-here"

# Linux/Mac
export OPENAI_API_KEY="your-key-here"
export GOOGLE_TRANSLATE_API_KEY="your-key-here"
```

### 3. Database Setup

The user authentication system automatically creates its own tables in the existing `medicine.db` database. No additional setup needed.

### 4. Run the Application

```bash
python app.py
```

The app will be available at `http://localhost:5000`

## Feature Configuration

### Chatbot API Providers

You can use different providers:

1. **OpenAI** (recommended):
   - Set `OPENAI_API_KEY` environment variable
   - Uses GPT-4o-mini (cost-effective)

2. **Groq** (fast, free tier):
   - Set `GROQ_API_KEY` environment variable
   - Uses Llama 3.1 (fast inference)

3. **Fallback Mode**:
   - Works without API key
   - Provides basic rule-based responses

### Translation Providers

1. **Google Translate API** (requires API key):
   - Set `GOOGLE_TRANSLATE_API_KEY`
   - Most accurate, paid service

2. **LibreTranslate** (free, open-source):
   - No API key needed
   - Self-hosted or use public instance

## Testing Individual Features

```python
# Test interaction checker
from features.interaction_checker import check_medicine_interactions
result = check_medicine_interactions(["Ibuprofen", "Aspirin"])
print(result)

# Test severity analyzer
from features.severity_analyzer import analyze_side_effect_severity
result = analyze_side_effect_severity("Nausea, Dizziness, Severe allergic reaction")
print(result)

# Test translator
from features.translator import translate_text
translated = translate_text("Hello", "hi")
print(translated)  # "नमस्ते"
```

## API Documentation

See [API_ENDPOINTS.md](./API_ENDPOINTS.md) for detailed API documentation.

## N8N Integration

See [N8N_SETUP_GUIDE.md](./N8N_SETUP_GUIDE.md) for complete n8n setup instructions.

## Troubleshooting

### Interaction Checker Not Working
- RxNav API is free and doesn't require API key
- Check internet connection
- Verify medicine names are spelled correctly (use generic names)

### Pill Identifier Not Accurate
- Current implementation uses placeholder matching
- For production, you need to:
  1. Train a custom CNN model on pill datasets
  2. Or use pre-trained models and fine-tune on pill images
  3. Prepare feature database with pill images

### Chatbot Not Responding
- Check if API key is set correctly
- Verify internet connection
- Falls back to rule-based responses if API unavailable

### Translation Not Working
- Google Translate requires API key and billing
- LibreTranslate works without API key
- Check internet connection

## Future Enhancements

- [ ] Train custom pill identification model
- [ ] Add more languages (Bengali, Telugu, etc.)
- [ ] Improve interaction checker accuracy
- [ ] Add expiry date extraction from images
- [ ] Implement fake medicine detection
- [ ] Add offline mode support
- [ ] Voice input support
- [ ] AR overlays for pill visualization

## Contributing

When adding new features:
1. Add feature module in this directory
2. Update `app.py` to integrate
3. Create templates if needed
4. Update this README
5. Add API endpoints to `n8n_webhooks.py` if needed

## License

Same as main project.

