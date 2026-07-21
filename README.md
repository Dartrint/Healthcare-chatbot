# Healthcare AI Chatbot

An intelligent healthcare assistant leveraging **LangGraph**, **RAG (Retrieval-Augmented Generation)**, and **FAISS** vector memory to provide medical information, symptom analysis, and personalized health planning.

## 🎯 Key Features

### 1. **Intelligent Conversation Routing**
- Automatic intent classification using LLM and vector memory
- 4 specialized branches: Medical RAG, Symptom Analysis, Health Planning, General Chat
- Context-aware responses based on conversation history

### 2. **Medical Knowledge RAG**
- Comprehensive dataset of 25+ common conditions (WHO, CDC, NIH sources)
- Covers symptoms, causes, prevention, and treatment
- Web search fallback (Tavily API) for up-to-date information

### 3. **Symptom Analysis**
- Personal health assessment based on user-reported symptoms
- Severity evaluation and medical advice recommendations
- Privacy-focused: data stored locally with FAISS

### 4. **Health Planning & Reminders**
- Create and manage health-related tasks
- Medication reminders and appointment tracking
- Interactive UI for task completion and deletion

### 5. **Voice Interaction**
- Speech-to-Text: Upload audio files for transcription
- Text-to-Speech: Automatic voice responses
- Supports WAV, MP3, OGG formats

### 6. **Semantic Memory (FAISS)**
- Vector-based conversation history storage
- Semantic similarity search for context retrieval
- Persistent memory across sessions

## 🏗️ Architecture

```
User Interface (Streamlit)
         ↓
    FastAPI REST API
         ↓
  LangGraph StateGraph
    ↓         ↓         ↓         ↓
  RAG    Symptom   Planner    Chat
   ↓         ↓         ↓         ↓
FAISS    LLM      MCP Tools  Memory
       (Groq)   (Weather,
               Web Search)
```

## 🛠️ Tech Stack

| Technology | Purpose |
|-----------|---------|
| **Python 3.13+** | Core language |
| **FastAPI** | REST API framework |
| **LangGraph** | Conversation orchestration |
| **FAISS** | Vector database for semantic search |
| **SentenceTransformers** | Text embedding (all-MiniLM-L6-v2) |
| **Groq / Ollama** | LLM inference |
| **Streamlit** | User interface |
| **Tavily API** | Web search integration |

## 📁 Project Structure

```
Healthcare-chatbot/
├── app/
│   ├── api.py                    # FastAPI endpoints
│   ├── agents/
│   │   └── healthcare_agent.py   # Main agent class
│   ├── graphs/
│   │   └── healthcare_graph.py   # LangGraph state machine
│   └── services/
│       ├── router.py             # Intent classification
│       ├── rag.py                # Medical knowledge retrieval
│       ├── symptom.py            # Symptom analysis
│       ├── planner.py            # Task management
│       ├── memory.py             # FAISS vector memory
│       ├── llm.py                # LLM integration
│       ├── voice_chat.py         # Speech services
│       └── mcp_gateway.py        # External tools (weather, search)
├── data/
│   ├── real_healthcare_data.csv  # Medical dataset
│   └── who_healthcare_data.csv   # WHO data
├── streamlit_app.py              # UI application
├── main.py                       # API entry point
└── requirements.txt
```

## 🚀 Quick Start

### Installation

```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/macOS

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Copy `.env.example` to `.env` and add your API keys:

```env
GROQ_API_KEY=your_groq_api_key_here
LLM_PROVIDER=groq
LLM_MODEL=llama-3.1-8b-instant
TAVILY_API_KEY=your_tavily_api_key_here  # Optional
```

### Running

```bash
# Start FastAPI backend
python main.py
# → http://127.0.0.1:8000
# → http://127.0.0.1:8000/docs (API documentation)

# Start Streamlit UI (separate terminal)
streamlit run streamlit_app.py
```

### Docker

```bash
docker compose up --build
```

## 📊 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/chat` | Send chat message |
| GET | `/plan/{user_id}` | View user's health plan |
| POST | `/plan/complete` | Mark task as complete |
| DELETE | `/plan/{user_id}/{task_id}` | Delete specific task |
| GET | `/reminders/{user_id}` | Get today's reminders |
| POST | `/voice/transcribe` | Audio to text |
| POST | `/voice/synthesize` | Text to audio |
| GET | `/memory/{user_id}` | View conversation history |
| GET | `/metrics` | System statistics |

## 💡 Use Cases

- **Medical Information Lookup**: Ask about diseases, symptoms, treatments
- **Personal Health Assistant**: Track symptoms and get preliminary advice
- **Medication Management**: Set reminders and track adherence
- **Health Education**: Learn about prevention and healthy habits
- **Voice Accessibility**: Hands-free interaction for accessibility

## 🔒 Privacy & Security

- All user data stored locally in FAISS vector database
- No external data transmission except API calls (Groq, Tavily)
- Sensitive files (.env, memory_store/) excluded from version control
- Medical advice is informational only - always consult healthcare professionals

## 📝 Data Sources

Medical information curated from:
- **WHO** (World Health Organization)
- **CDC** (Centers for Disease Control and Prevention)
- **NIH** (National Institutes of Health)

## 🤝 Contributing

This project demonstrates:
- Advanced LLM orchestration with LangGraph
- RAG implementation for domain-specific knowledge
- Vector database integration for semantic search
- Microservices architecture with FastAPI
- Real-time conversational AI
- Healthcare-focused application development

---

**Disclaimer**: This chatbot provides general health information only and is not a substitute for professional medical advice, diagnosis, or treatment.