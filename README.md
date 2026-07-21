# Healthcare AI Agent — Trợ Lý Y Tế Thông Minh

Hệ thống trợ lý y tế AI sử dụng **LangGraph** để điều phối luồng hội thoại, **FAISS** cho bộ nhớ vector, và **RAG** để truy vấn kiến thức y khoa. Hỗ trợ chat văn bản, nhập liệu giọng nói, quản lý kế hoạch chăm sóc sức khỏe, và tìm kiếm thông tin y tế từ web.

---

## Kiến trúc tổng quan

```
┌─────────────┐     ┌──────────┐     ┌──────────────────────────────────────┐
│  Streamlit  │────▶│ FastAPI  │────▶│        LangGraph StateGraph          │
│  (UI)       │◀────│ (API)    │◀────│                                      │
└─────────────┘     └──────────┘     │  route → {rag, symptom, planner,    │
                                      │           chat}                     │
                                      └──────────┬───────────────────────────┘
                                                 │
                          ┌──────────────────────┼──────────────────────────┐
                          ▼                      ▼                          ▼
                   ┌──────────┐          ┌──────────────┐          ┌──────────────┐
                   │ RAG      │          │ Symptom      │          │ Planner      │
                   │ (+Web)   │          │ (LLM phân    │          │ (quản lý     │
                   │          │          │  tích triệu  │          │  task)       │
                   │          │          │  chứng)      │          │              │
                   └──────────┘          └──────────────┘          └──────────────┘
                          │                      │                        │
                          ▼                      ▼                        ▼
                   ┌──────────┐          ┌──────────────┐          ┌──────────────┐
                   │ Memory   │          │ LLM (Groq/   │          │ MCP Gateway  │
                   │ (FAISS)  │          │ Ollama)      │          │ (thời tiết,  │
                   │          │          │              │          │  web search) │
                   └──────────┘          └──────────────┘          └──────────────┘
```

### Luồng xử lý một yêu cầu chat

1. **API nhận request** (`POST /chat`) → gọi `HealthcareAgent.chat(user_id, message)`
2. **Agent** khởi tạo `HealthcareGraph` và gọi `graph.run()`
3. **RouterService** phân loại ý định người dùng dựa trên:
   - Lịch sử hội thoại (6 message gần nhất)
   - Bộ nhớ vector (3 kết quả tương đồng nhất từ FAISS)
   - Ý định của message trước đó
4. **StateGraph** rẽ nhánh dựa trên ý định:

| Intent | Nhánh      | Xử lý                                                                 |
|--------|------------|-----------------------------------------------------------------------|
| `RAG`  | Medical    | Tra cứu RAG (bệnh, thuốc, điều trị) + web search y tế + LLM tổng hợp |
| `SYMPTOM` | Sức khỏe cá nhân | Phân tích triệu chứng, đưa ra lời khuyên                               |
| `PLANNER` | Kế hoạch   | Tạo task mới, hiển thị kế hoạch, hướng dẫn xoá/hoàn thành qua UI     |
| `CHAT` | Trò chuyện | Hội thoại thông thường + tra cứu thời tiết/thời gian/web              |

5. **Memory** được lưu tự động sau mỗi lượt chat (FAISS + JSON metadata)

---

## Cấu trúc thư mục

```
Healthcare-chatbot/
├── app/
│   ├── api.py                    # REST API (FastAPI) — endpoints, middleware
│   ├── config.py                 # Biến môi trường, đường dẫn
│   ├── schemas.py                # Pydantic models
│   ├── agents/
│   │   └── healthcare_agent.py   # Lớp agent chính, interface cho graph
│   ├── graphs/
│   │   └── healthcare_graph.py   # LangGraph StateGraph + 4 nhánh xử lý
│   └── services/
│       ├── embedding.py          # Tạo embedding vector (SentenceTransformers)
│       ├── llm.py                # Tích hợp LLM (Groq / Ollama)
│       ├── memory.py             # VectorMemoryService (FAISS + JSON)
│       ├── mcp_gateway.py        # Cổng tool: thời tiết, thời gian, web search
│       ├── planner.py            # Quản lý kế hoạch / task / reminder
│       ├── quality_metrics.py    # Đo lường chất lượng hệ thống
│       ├── rag.py                # Retrieval-Augmented Generation (dataset y tế)
│       ├── router.py             # Phân loại ý định hội thoại
│       ├── symptom.py            # Phân tích triệu chứng sức khỏe
│       ├── tracer.py             # Decorator tracing (LangChain)
│       └── voice_chat.py         # Speech-to-text + Text-to-speech
├── data/
│   ├── real_healthcare_data.csv  # Dataset y tế (bệnh, triệu chứng, điều trị)
│   └── who_healthcare_data.csv   # Dataset từ WHO
├── memory_store/                 # FAISS index + JSON metadata (tự động tạo)
├── .env.example                  # Mẫu cấu hình môi trường
├── .gitignore
├── docker-compose.yml            # Docker Compose
├── Dockerfile
├── main.py                       # Entry point FastAPI (uvicorn)
├── requirements.txt
└── streamlit_app.py              # Giao diện người dùng (Streamlit)
```

---

## Tính năng chi tiết

### 1. Chat thông minh với định tuyến tự động (`/chat`)
- Phân loại ý định người dùng thành 4 nhánh
- Kết hợp lịch sử hội thoại + bộ nhớ vector để đưa ra câu trả lời chính xác
- Hỗ trợ tiếng Việt

### 2. Tra cứu kiến thức y khoa (RAG)
- 25+ bệnh lý phổ biến từ WHO, CDC, NIH
- Dữ liệu: triệu chứng, nguyên nhân, phòng ngừa, điều trị
- Fallback: tìm kiếm web y tế (Tavily) khi dataset không đủ

### 3. Phân tích triệu chứng cá nhân
- Nhập triệu chứng → nhận tư vấn sức khỏe sơ bộ
- Cảnh báo nếu triệu chứng nghiêm trọng (cần gặp bác sĩ)

### 4. Quản lý kế hoạch chăm sóc sức khỏe
- Tạo task: "Nhắc tôi uống thuốc lúc 8h sáng"
- Xem kế hoạch, đánh dấu hoàn thành, xoá task (qua UI buttons)
- Reminder theo ngày

### 5. Voice Chat
- **Speech-to-Text**: Upload file audio → nhận text
- **Text-to-Speech**: Tự động phát giọng nói phản hồi
- Hỗ trợ: WAV, MP3, OGG

### 6. Bộ nhớ ngữ nghĩa (FAISS)
- Lưu trữ lịch sử chat dưới dạng embedding vector
- Truy xuất thông tin tương đồng theo ngữ nghĩa
- Persist giữa các lần chạy (file `.faiss` + `.json`)

### 7. Tra cứu thời gian thực
- Thời tiết (mô phỏng / thực tế)
- Thời gian hiện tại
- Web search (Tavily API) cho thông tin cập nhật

### 8. API Endpoints

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/` | Trang chủ + danh sách endpoints |
| GET | `/health` | Kiểm tra trạng thái |
| GET | `/metrics` | Thống kê hệ thống (bộ nhớ, kế hoạch) |
| POST | `/chat` | Gửi tin nhắn chat |
| GET | `/plan/{user_id}` | Xem kế hoạch người dùng |
| POST | `/plan/complete` | Đánh dấu task hoàn thành |
| POST | `/plan/batch-complete` | Hoàn thành nhiều task |
| POST | `/plan/batch-delete` | Xoá nhiều task |
| DELETE | `/plan/{user_id}` | Xoá toàn bộ kế hoạch |
| DELETE | `/plan/{user_id}/{task_id}` | Xoá một task |
| GET | `/reminders/{user_id}` | Lấy reminder hôm nay |
| GET | `/memory/{user_id}` | Xem lịch sử memory |
| DELETE | `/memory/{user_id}` | Xoá memory |
| GET | `/voice/status` | Kiểm tra voice service |
| POST | `/voice/transcribe` | Chuyển audio → text |
| POST | `/voice/synthesize` | Chuyển text → audio |

---

## Cài đặt & Chạy

### Yêu cầu
- Python 3.13+
- pip / venv

### Cài đặt

```bash
# Clone & cd vào thư mục

# Tạo virtual environment
python -m venv .venv
.venv\Scripts\activate    # Windows
source .venv/bin/activate  # Linux/macOS

# Cài dependencies
pip install -r requirements.txt
```

### Cấu hình

Copy `.env.example` thành `.env` và điền API key:

```env
GROQ_API_KEY=gsk_...             # Bắt buộc cho LLM
LLM_PROVIDER=groq                 # hoặc ollama
LLM_MODEL=llama-3.1-8b-instant
TAVILY_API_KEY=tvly-...           # Tùy chọn (web search)
```

### Chạy

```bash
# Backend API
python main.py
# → http://127.0.0.1:8000
# → http://127.0.0.1:8000/docs (Swagger)

# Giao diện Streamlit (terminal khác)
streamlit run streamlit_app.py
```

### Docker

```bash
docker compose up --build
```

---

## Công nghệ sử dụng

| Công nghệ | Mục đích |
|-----------|----------|
| Python 3.13+ | Ngôn ngữ chính |
| FastAPI | REST API framework |
| LangGraph | Orchestration luồng hội thoại (StateGraph) |
| FAISS | Vector database, semantic search |
| SentenceTransformers | Embedding model (all-MiniLM-L6-v2) |
| Groq / Ollama | LLM inference |
| Tavily | Web search API |
| Streamlit | Giao diện người dùng |
| SpeechRecognition | Speech-to-text |
| gTTS | Text-to-speech |

---

## Dataset y tế

Dữ liệu được tổng hợp từ các nguồn uy tín:
- **WHO** (World Health Organization)
- **CDC** (Centers for Disease Control and Prevention)
- **NIH** (National Institutes of Health)

Bao gồm 25+ bệnh lý: tiểu đường, tim mạch, ung thư, sốt rét, lao, viêm gan, COVID-19, hen suyễn, v.v.

---

## Ghi chú

- Voice chat là tùy chọn: hệ thống hoạt động bình thường nếu không cài SpeechRecognition/gTTS
- Dataset y tế tự động tạo nếu chưa có khi RAGService khởi tạo
- Bộ nhớ vector được lưu trong `memory_store/` — giữ context qua các phiên
- File `.faiss` và `.json` trong `memory_store/` được .gitignore bỏ qua