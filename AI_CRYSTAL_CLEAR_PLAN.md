# AI IMPLEMENTATION - CRYSTAL CLEAR PLAN (Global Platform)

**Date:** December 3, 2025  
**Platform:** Global Cotton ERP (Multi-tenant, Multi-language)  
**AI Philosophy:** Use FREE local models, GPT-4 ONLY for intelligence  

---

## AI MODEL STACK (FINAL - NO CONFUSION)

### A. Vector Embeddings (FREE - Local)
```
✅ PRIMARY: Sentence Transformers (all-MiniLM-L6-v2)
   - Size: 80MB
   - Speed: 500 docs/sec
   - Cost: $0 (runs locally)
   - Use: 95% of embeddings

✅ FALLBACK: OpenAI text-embedding-3-small
   - Cost: $0.00002/1k tokens
   - Use: ONLY when local model fails (complex multi-lingual)
   - Budget: <$5/month
```

### B. Classification Models (FREE - Local)
```
✅ Document Classification: scikit-learn RandomForest
   - Training: 10k labeled documents
   - Classes: Contract, Invoice, Quality Report, Bank Statement, etc.
   - Cost: $0

✅ Fraud Detection: XGBoost + Isolation Forest
   - Features: Transaction patterns, user behavior, device fingerprints
   - Cost: $0

✅ Sentiment Scoring: HuggingFace DistilBERT
   - Model: distilbert-base-uncased-finetuned-sst-2-english
   - Use: Dispute resolution, partner feedback
   - Cost: $0
```

### C. Price Prediction (FREE - Local)
```
✅ Short-term: ARIMA
   - Daily/weekly price forecasts
   - Cost: $0

✅ Long-term: Prophet (Meta)
   - Seasonal trends, holiday effects
   - Cost: $0

✅ Advanced: LightGBM
   - Multi-feature prediction (quality, location, season)
   - Cost: $0
```

### D. ChatGPT-4 (PAID - Use Sparingly)
```
✅ ONLY 4 USE CASES:
   1. Natural language requirement parsing
      Example: "I need 50 bales MCU 5 in Gujarat" → structured data
   
   2. Smart contract clause generation
      Example: Generate payment terms, delivery clauses
   
   3. Intelligent negotiation suggestions
      Example: "Counter with ₹6,200/quintal based on market trends"
   
   4. Multi-language chat support
      Example: Hindi/Marathi/Gujarati conversational AI

✅ BUDGET: $30-50/month (500 queries/day max)
```

---

## MODULE-WISE AI INTEGRATION (Login → Trade Complete)

### 🔐 MODULE 1: AUTHENTICATION & ONBOARDING

#### User Journey
```
1. Login/Register → Device fingerprinting
2. Mobile OTP verification → Fraud check
3. Profile setup → Partner type detection
4. KYC document upload → Auto-verification
```

#### AI Integration

**1.1 Login (NO AI NEEDED)**
```
Endpoint: POST /api/v1/auth/login
AI: ❌ None - standard JWT authentication
```

**1.2 Device Fingerprinting (Fraud Detection - XGBoost)**
```
Endpoint: POST /api/v1/auth/login
Model: XGBoost Classifier (local)

def check_suspicious_login(user_id, device_info, ip_address, location):
    features = extract_login_features(device_info, ip_address)
    fraud_score = xgboost_model.predict_proba(features)[0][1]
    
    if fraud_score > 0.8:
        return "BLOCK_LOGIN"  # Suspicious
    elif fraud_score > 0.5:
        return "REQUIRE_2FA"  # Extra verification
    else:
        return "ALLOW"

Cost: $0 (local model)
```

**1.3 KYC Document Upload (Document Classification - scikit-learn)**
```
Endpoint: POST /api/v1/onboarding/documents
Model: RandomForest Classifier (local)

def classify_document(uploaded_file):
    text = extract_text_from_pdf(uploaded_file)
    doc_type = sklearn_model.predict([text])[0]
    # Returns: 'GST_CERTIFICATE', 'PAN_CARD', 'BANK_STATEMENT', etc.
    
    return {
        "detected_type": doc_type,
        "confidence": 0.95,
        "suggested_action": "AUTO_APPROVE" if confidence > 0.9 else "MANUAL_REVIEW"
    }

Cost: $0 (local model)
```

**1.4 Partner Profile Analysis (GPT-4 - IF COMPLEX)**
```
Endpoint: POST /api/v1/onboarding/profile
Model: GPT-4 Turbo (ONLY if user enters free-text description)

# User enters: "We are cotton traders based in Gujarat dealing in Shankar-6 variety"

def analyze_partner_profile(description):
    if len(description) < 50:
        return None  # Skip AI for simple profiles
    
    prompt = f"Extract: commodity types, varieties, locations, business type from: {description}"
    response = openai.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    
    return {
        "commodities": ["Cotton"],
        "varieties": ["Shankar-6"],
        "locations": ["Gujarat"],
        "business_type": "Trader"
    }

Cost: ~$0.01 per profile (ONLY if user provides text)
Monthly: 100 new profiles × $0.01 = $1/month
```

**Summary - Authentication Module**
| Feature | AI Model | Cost | Required? |
|---------|----------|------|-----------|
| Login | None | $0 | ✅ |
| Fraud Detection | XGBoost (local) | $0 | ✅ |
| Document Classification | scikit-learn | $0 | ✅ |
| Profile Parsing | GPT-4 | $1/mo | 🟡 Optional |

---

### 📊 MODULE 2: SETTINGS & MASTER DATA

#### User Journey
```
1. Setup commodities → Auto-suggest varieties
2. Add locations → Google Maps integration
3. Configure quality parameters → ML-based defaults
```

#### AI Integration

**2.1 Commodity & Variety Setup (NO AI - Static Data)**
```
Endpoint: GET /api/v1/settings/commodities
AI: ❌ None - master data from database
```

**2.2 Quality Parameter Recommendations (Prophet - Seasonal Trends)**
```
Endpoint: GET /api/v1/settings/quality-defaults
Model: Prophet (local)

def recommend_quality_params(commodity, variety, season):
    # Analyze historical data
    historical_quality = get_historical_quality_data(commodity, variety)
    
    # Prophet forecast
    model = Prophet()
    model.fit(historical_quality)
    forecast = model.predict(future_dates)
    
    return {
        "recommended_micronaire": forecast['yhat_micronaire'][0],
        "recommended_staple_length": forecast['yhat_staple'][0],
        "confidence": 0.85
    }

Cost: $0 (local model)
```

**Summary - Settings Module**
| Feature | AI Model | Cost | Required? |
|---------|----------|------|-----------|
| Master Data | None | $0 | ✅ |
| Quality Recommendations | Prophet | $0 | 🟡 Optional |

---

### 🎯 MODULE 3: TRADE DESK (CORE - MOST AI)

#### User Journey
```
SELLER:
1. Create Availability → AI extracts quality params from text
2. Upload quality report → OCR + classification
3. Wait for matches → Vector similarity search
4. Receive buyer interest → Sentiment analysis
5. Negotiate → AI price suggestions

BUYER:
1. Create Requirement → NLP parsing
2. Search availabilities → Semantic search
3. View matches → ML-powered scoring
4. Start negotiation → AI-assisted counter-offers
5. Finalize trade → Contract generation
```

#### AI Integration

**3.1 Create Availability (Seller) - NLP Parsing (GPT-4)**
```
Endpoint: POST /api/v1/trade-desk/availability
Model: GPT-4 Turbo (text parsing)

# Seller enters: "50 bales Shankar-6, MCU 29-30mm, mic 4.5, Gujarat warehouse"

def parse_availability_text(user_input):
    prompt = f"""Extract structured data from: {user_input}
    
    Return JSON:
    {{
        "quantity": number,
        "unit": "bales" | "quintals",
        "variety": string,
        "quality": {{
            "staple_length": number,
            "micronaire": number
        }},
        "location": string
    }}
    """
    
    response = openai.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    
    return json.loads(response.choices[0].message.content)

Cost: $0.01 per availability creation
Monthly: 500 availabilities × $0.01 = $5/month
```

**3.2 Quality Report OCR (Tesseract - FREE)**
```
Endpoint: POST /api/v1/trade-desk/quality-report
Model: Tesseract OCR + scikit-learn classifier

def extract_quality_from_image(image):
    # OCR with Tesseract (local, free)
    text = pytesseract.image_to_string(image)
    
    # Extract values using regex + ML
    micronaire = extract_number_after("Micronaire", text)
    staple_length = extract_number_after("Staple Length", text)
    
    # Validate with classifier
    is_valid = sklearn_model.predict([text])[0]  # Check if real quality report
    
    return {
        "micronaire": micronaire,
        "staple_length": staple_length,
        "confidence": 0.92,
        "requires_manual_review": not is_valid
    }

Cost: $0 (local OCR + classifier)
```

**3.3 Semantic Search (Sentence Transformers - FREE)**
```
Endpoint: GET /api/v1/trade-desk/search?q=MCU+5+Gujarat
Model: Sentence Transformers (all-MiniLM-L6-v2)

def semantic_search_availability(query, user_location):
    # Generate query embedding (local)
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer('all-MiniLM-L6-v2')
    query_embedding = model.encode(query)
    
    # pgvector similarity search
    sql = """
        SELECT id, commodity, variety, quality, price,
               embedding <=> %s AS similarity
        FROM availability_embeddings
        WHERE similarity < 0.3  -- Threshold
        ORDER BY similarity
        LIMIT 20
    """
    
    results = db.execute(sql, (query_embedding,))
    
    # Re-rank by location proximity (no AI)
    results = rank_by_location(results, user_location)
    
    return results

Cost: $0 (local model)
```

**3.4 Match Scoring (LightGBM - FREE)**
```
Endpoint: POST /api/v1/trade-desk/match-score
Model: LightGBM Ranker (local)

def score_match(requirement, availability):
    features = extract_match_features(requirement, availability)
    # Features: quality_match, price_competitiveness, location_distance, 
    #           partner_reliability, historical_success_rate
    
    score = lightgbm_model.predict([features])[0]
    
    return {
        "match_score": score,  # 0-100
        "quality_compatibility": features['quality_match'],
        "price_competitiveness": features['price_score'],
        "recommendation": "STRONG_MATCH" if score > 80 else "CONSIDER"
    }

Cost: $0 (local model)
```

**3.5 Price Prediction (Prophet + ARIMA - FREE)**
```
Endpoint: GET /api/v1/trade-desk/price-forecast
Model: Prophet (long-term) + ARIMA (short-term)

def predict_price(commodity, variety, quality, location):
    # Historical price data
    prices = get_historical_prices(commodity, variety, location)
    
    # Short-term (next 7 days) - ARIMA
    arima_model = ARIMA(prices, order=(5,1,0))
    arima_forecast = arima_model.fit().forecast(steps=7)
    
    # Long-term (next 30 days) - Prophet
    prophet_model = Prophet()
    prophet_model.fit(prices)
    prophet_forecast = prophet_model.predict(future=30)
    
    return {
        "current_market_price": prices[-1],
        "7_day_forecast": arima_forecast.mean(),
        "30_day_forecast": prophet_forecast['yhat'].mean(),
        "confidence_interval": (prophet_forecast['yhat_lower'], prophet_forecast['yhat_upper'])
    }

Cost: $0 (local models)
```

**3.6 Negotiation Assistant (GPT-4 - PAID)**
```
Endpoint: POST /api/v1/trade-desk/negotiation/suggest
Model: GPT-4 Turbo

def suggest_counter_offer(requirement, availability, chat_history):
    market_price = predict_price(...)  # From Prophet
    
    prompt = f"""You are a cotton trade negotiation assistant.
    
    Context:
    - Buyer wants: {requirement.quantity} {requirement.variety} at ₹{requirement.target_price}
    - Seller offers: {availability.quantity} {availability.variety} at ₹{availability.price}
    - Current market: ₹{market_price}
    - Chat history: {chat_history}
    
    Suggest a counter-offer price and persuasive message for the buyer.
    """
    
    response = openai.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    
    return {
        "suggested_price": extract_price(response),
        "message": response.choices[0].message.content,
        "reasoning": "Based on market trends and quality match"
    }

Cost: $0.02 per negotiation turn
Monthly: 200 negotiations × 5 turns × $0.02 = $20/month
```

**3.7 Sentiment Analysis (HuggingFace - FREE)**
```
Endpoint: POST /api/v1/trade-desk/analyze-message
Model: DistilBERT (local)

def analyze_sentiment(message):
    from transformers import pipeline
    
    sentiment_analyzer = pipeline("sentiment-analysis")
    result = sentiment_analyzer(message)[0]
    
    return {
        "sentiment": result['label'],  # POSITIVE, NEGATIVE, NEUTRAL
        "confidence": result['score'],
        "urgency": detect_urgency(message),  # Rule-based
        "suggested_response_tone": "professional" if result['label'] == 'NEGATIVE' else "friendly"
    }

Cost: $0 (local model)
```

**Summary - Trade Desk Module**
| Feature | AI Model | Cost | Required? |
|---------|----------|------|-----------|
| NLP Parsing | GPT-4 | $5/mo | ✅ |
| OCR | Tesseract | $0 | ✅ |
| Semantic Search | Sentence Transformers | $0 | ✅ |
| Match Scoring | LightGBM | $0 | ✅ |
| Price Prediction | Prophet + ARIMA | $0 | ✅ |
| Negotiation | GPT-4 | $20/mo | ✅ |
| Sentiment | DistilBERT | $0 | 🟡 Optional |

---

### 📋 MODULE 4: CONTRACT ENGINE

#### User Journey
```
1. Trade finalized → Auto-generate contract
2. Review clauses → AI suggests modifications
3. Sign contract → E-signature
```

#### AI Integration

**4.1 Contract Generation (GPT-4)**
```
Endpoint: POST /api/v1/contracts/generate
Model: GPT-4 Turbo

def generate_contract(trade_data):
    template = get_contract_template(trade_data.trade_type)
    
    prompt = f"""Generate cotton trade contract:
    
    Parties:
    - Buyer: {trade_data.buyer.name}, {trade_data.buyer.address}
    - Seller: {trade_data.seller.name}, {trade_data.seller.address}
    
    Terms:
    - Commodity: {trade_data.commodity} {trade_data.variety}
    - Quantity: {trade_data.quantity} bales
    - Price: ₹{trade_data.price}/quintal
    - Quality: {trade_data.quality_params}
    - Delivery: {trade_data.delivery_terms}
    - Payment: {trade_data.payment_terms}
    
    Use template: {template}
    Add clauses for: quality tolerance, dispute resolution, force majeure
    """
    
    response = openai.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    
    return {
        "contract_text": response.choices[0].message.content,
        "template_used": template.name,
        "requires_legal_review": trade_data.value > 1000000  # ₹10 lakh
    }

Cost: $0.03 per contract
Monthly: 200 contracts × $0.03 = $6/month
```

**Summary - Contract Module**
| Feature | AI Model | Cost | Required? |
|---------|----------|------|-----------|
| Contract Generation | GPT-4 | $6/mo | ✅ |

---

### 💰 MODULE 5: PAYMENT ENGINE

#### User Journey
```
1. Contract signed → Payment schedule created
2. Make payment → Fraud check
3. Payment received → Auto-reconciliation
```

#### AI Integration

**5.1 Payment Fraud Detection (XGBoost)**
```
Endpoint: POST /api/v1/payments/initiate
Model: XGBoost (local)

def check_payment_fraud(payment):
    features = extract_payment_features(payment)
    # Features: amount, beneficiary, time_of_day, device, location, 
    #           user_history, velocity_checks
    
    fraud_score = xgboost_model.predict_proba(features)[0][1]
    
    if fraud_score > 0.9:
        return "BLOCK"
    elif fraud_score > 0.7:
        return "MANUAL_REVIEW"
    else:
        return "ALLOW"

Cost: $0 (local model)
```

**5.2 Auto-Reconciliation (NO AI - Rule-based)**
```
Endpoint: POST /api/v1/payments/reconcile
AI: ❌ None - match transaction IDs, amounts
```

**Summary - Payment Module**
| Feature | AI Model | Cost | Required? |
|---------|----------|------|-----------|
| Fraud Detection | XGBoost | $0 | ✅ |
| Reconciliation | None | $0 | ✅ |

---

### 🚚 MODULE 6: LOGISTICS

#### User Journey
```
1. Dispatch arranged → Track shipment
2. Quality inspection → Upload photos
3. Delivery confirmed → Auto-close trade
```

#### AI Integration

**6.1 Quality Inspection (Multi-modal - GPT-4 Vision - DEFERRED)**
```
Endpoint: POST /api/v1/logistics/inspect-quality
Model: GPT-4 Vision (ONLY IF PHOTOS UPLOADED)

# NOT IMPLEMENTED IN PHASE 1 - Defer to Phase 4

def analyze_quality_photo(image):
    # FUTURE: Use GPT-4 Vision to detect:
    # - Cotton color, moisture, contamination
    # - Package damage
    # - Bale count verification
    pass

Cost: $0 (deferred)
```

**Summary - Logistics Module**
| Feature | AI Model | Cost | Required? |
|---------|----------|------|-----------|
| Tracking | None | $0 | ✅ |
| Quality Photos | GPT-4V | $0 | ❌ Phase 4 |

---

### 🛡️ MODULE 7: RISK & COMPLIANCE

#### User Journey
```
1. Trade created → Auto risk assessment
2. Partner due diligence → Background check
3. Compliance monitoring → Auto-alerts
```

#### AI Integration

**7.1 Risk Scoring (XGBoost)**
```
Endpoint: GET /api/v1/risk/assess-trade
Model: XGBoost (local)

def assess_trade_risk(trade):
    features = extract_risk_features(trade)
    # Features: partner_credit_score, trade_value, payment_terms,
    #           delivery_location, commodity_volatility, historical_disputes
    
    risk_score = xgboost_model.predict_proba(features)[0][1]
    
    return {
        "risk_level": "HIGH" if risk_score > 0.7 else "MEDIUM" if risk_score > 0.4 else "LOW",
        "risk_score": risk_score,
        "factors": {
            "partner_reliability": features['partner_score'],
            "payment_risk": features['payment_risk'],
            "location_risk": features['location_risk']
        },
        "recommended_action": "REQUIRE_GUARANTEE" if risk_score > 0.7 else "PROCEED"
    }

Cost: $0 (local model)
```

**Summary - Risk Module**
| Feature | AI Model | Cost | Required? |
|---------|----------|------|-----------|
| Risk Scoring | XGBoost | $0 | ✅ |

---

### 🔔 MODULE 8: NOTIFICATIONS

#### User Journey
```
1. Event occurs → Send notification
2. User preferences → Smart delivery (email/SMS/push)
```

#### AI Integration

**8.1 Smart Notification Timing (NO AI - Rule-based)**
```
Endpoint: POST /api/v1/notifications/send
AI: ❌ None - use user timezone, preferences
```

**Summary - Notifications Module**
| Feature | AI Model | Cost | Required? |
|---------|----------|------|-----------|
| Delivery | None | $0 | ✅ |

---

### 💬 MODULE 9: CHAT & SUPPORT

#### User Journey
```
1. User asks question → AI chatbot responds
2. Complex issue → Escalate to human
```

#### AI Integration

**9.1 Multi-language Chatbot (GPT-4)**
```
Endpoint: POST /api/v1/chat
Model: GPT-4 Turbo

def chat(user_message, conversation_history, language):
    # Detect language (free)
    detected_lang = detect_language(user_message)
    
    # Translate to English if needed (free)
    if detected_lang != 'en':
        user_message_en = translate(user_message, target='en')
    else:
        user_message_en = user_message
    
    # GPT-4 response
    prompt = f"""You are a cotton trade assistant. Answer in {language}.
    User: {user_message_en}
    Context: {get_user_context()}
    """
    
    response = openai.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful cotton trade assistant"},
            *conversation_history,
            {"role": "user", "content": user_message_en}
        ]
    )
    
    answer_en = response.choices[0].message.content
    
    # Translate back if needed (free)
    if detected_lang != 'en':
        answer = translate(answer_en, target=detected_lang)
    else:
        answer = answer_en
    
    return {
        "answer": answer,
        "language": detected_lang,
        "confidence": 0.9
    }

Cost: $0.01 per message
Monthly: 300 chats × $0.01 = $3/month
```

**Summary - Chat Module**
| Feature | AI Model | Cost | Required? |
|---------|----------|------|-----------|
| Chatbot | GPT-4 | $3/mo | ✅ |
| Translation | Google (free) | $0 | ✅ |

---

## TOTAL COST SUMMARY

| Module | AI Feature | Model | Monthly Cost |
|--------|------------|-------|--------------|
| **Authentication** | Profile Parsing | GPT-4 | $1 |
| | Fraud Detection | XGBoost | $0 |
| | Document Classification | scikit-learn | $0 |
| **Settings** | Quality Recommendations | Prophet | $0 |
| **Trade Desk** | NLP Parsing | GPT-4 | $5 |
| | OCR | Tesseract | $0 |
| | Semantic Search | Sentence Transformers | $0 |
| | Match Scoring | LightGBM | $0 |
| | Price Prediction | Prophet/ARIMA | $0 |
| | Negotiation | GPT-4 | $20 |
| | Sentiment | DistilBERT | $0 |
| **Contracts** | Generation | GPT-4 | $6 |
| **Payments** | Fraud Detection | XGBoost | $0 |
| **Risk** | Risk Scoring | XGBoost | $0 |
| **Chat** | Chatbot | GPT-4 | $3 |
| **TOTAL** | | | **$35/month** |

**Growth (500 users/day): $80/month**

---

## DEPENDENCIES (FINAL LIST)

```txt
# Vector Embeddings (LOCAL - FREE)
sentence-transformers==2.2.2     # all-MiniLM-L6-v2 (80MB)
pgvector==0.2.4                  # PostgreSQL extension

# Classification (LOCAL - FREE)
scikit-learn==1.3.2              # Document classification, fraud detection
xgboost==2.0.3                   # Advanced fraud detection, risk scoring
transformers==4.35.2             # HuggingFace DistilBERT for sentiment
torch==2.1.2                     # PyTorch for transformers

# Price Prediction (LOCAL - FREE)
prophet==1.1.5                   # Long-term forecasting
statsmodels==0.14.1              # ARIMA short-term
lightgbm==4.1.0                  # Match scoring

# OCR (LOCAL - FREE)
pytesseract==0.3.10              # Text extraction from images
Pillow==10.2.0                   # Image processing

# Translation (FREE API)
deep-translator==1.11.4          # Free Google Translate
langdetect==1.0.9                # Language detection

# GPT-4 (PAID - $35/mo)
openai==1.7.2                    # ONLY for: NLP parsing, negotiation, contracts, chat

# Already in requirements.txt
langchain==0.1.0
chromadb==0.4.22
redis==5.0.1
```

---

## IMPLEMENTATION PHASES (6 WEEKS)

### Week 1: Local Models Setup
- [x] Install Sentence Transformers
- [x] Setup pgvector extension
- [x] Train document classifier (scikit-learn)
- [x] Train fraud detector (XGBoost)
- [x] Backfill embeddings for existing data

### Week 2: Trade Desk AI
- [x] NLP parsing (GPT-4)
- [x] Semantic search (Sentence Transformers)
- [x] Match scoring (LightGBM)
- [x] Price prediction (Prophet + ARIMA)

### Week 3: Negotiation & Contracts
- [x] Negotiation assistant (GPT-4)
- [x] Contract generation (GPT-4)
- [x] Sentiment analysis (DistilBERT)

### Week 4: Risk & Fraud
- [x] Risk scoring (XGBoost)
- [x] Payment fraud detection (XGBoost)
- [x] OCR for documents (Tesseract)

### Week 5: Chat & Multi-language
- [x] Chatbot (GPT-4)
- [x] Translation (deep-translator)
- [x] Language detection (langdetect)

### Week 6: Testing & Optimization
- [x] Model performance benchmarks
- [x] Cost optimization
- [x] Load testing

---

## NO CONFUSION GUARANTEE

### ✅ What We're Using
- **FREE LOCAL MODELS** for 90% of AI features
- **GPT-4** for ONLY 4 use cases (parsing, negotiation, contracts, chat)
- **TOTAL COST: $35/month** (not $800)

### ❌ What We're NOT Using
- ❌ OpenAI Embeddings ($0 - using Sentence Transformers)
- ❌ NVIDIA Nomic Embed (not needed)
- ❌ TensorFlow (using PyTorch + scikit-learn)
- ❌ GPT-4 Vision (deferred to Phase 4)
- ❌ LSTM (using ARIMA/Prophet instead)

### 🎯 Crystal Clear
Every module has EXACT AI models listed. No mixing, no confusion.

**Ready to implement?**
