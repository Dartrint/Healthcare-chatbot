# Healthcare AI Agent — Trợ Lý Y Tế Thông Minh

Healthcare AI Agent là một nền tảng trợ lý y tế hiện đại, được xây dựng với kiến trúc dịch vụ mô-đun và sẵn sàng cho việc triển khai sản xuất. Dự án này sử dụng các công nghệ tiên tiến như FastAPI, LangGraph và FAISS để cung cấp trải nghiệm chatbot y tế thông minh, bao gồm chẩn đoán triệu chứng, lập kế hoạch chăm sóc và quản lý bộ nhớ ngữ nghĩa.

## Tính Năng Chính

- **Trợ Lý Y Tế Thông Minh**: Hỗ trợ chẩn đoán triệu chứng, tư vấn y tế và lập kế hoạch chăm sóc sức khỏe.
- **Kiến Trúc Dịch Vụ Mô-Đun**: Tách biệt rõ ràng giữa các dịch vụ như RAG, symptom triage, planner và memory.
- **Bộ Nhớ Ngữ Nghĩa**: Sử dụng FAISS để lưu trữ và truy xuất thông tin ngữ nghĩa, kết hợp với dataset RAG fallback.
- **Giao Diện Người Dùng**: Streamlit UI cho việc thử nghiệm nhanh và tương tác trực tiếp.
- **Triển Khai Dễ Dàng**: Docker-ready với persistent memory và plans.
- **API RESTful**: FastAPI backend với các endpoint mạnh mẽ cho tích hợp.

## Kiến Trúc Hệ Thống

```
User → FastAPI → HealthcareAgent → LangGraph StateGraph
                                 ├── RouterService (định tuyến yêu cầu)
                                 ├── RAGService (truy xuất thông tin)
                                 ├── SymptomService (phân tích triệu chứng)
                                 ├── PlannerService (lập kế hoạch)
                                 └── VectorMemoryService (quản lý bộ nhớ vector)
```

Hệ thống sử dụng LangGraph để orchestrate workflow, đảm bảo luồng xử lý logic và hiệu quả.

## Cấu Trúc Dự Án

- `app/api.py`: REST API, middleware và routes.
- `app/agents/healthcare_agent.py`: Điểm nhập chính cho orchestration agent.
- `app/graphs/healthcare_graph.py`: Định nghĩa LangGraph state graph và flow.
- `app/services/`: Lớp dịch vụ bao gồm:
  - `chat_memory.py`: Quản lý bộ nhớ chat.
  - `embedding.py`: Xử lý embedding.
  - `llm.py`: Tích hợp LLM (Groq hoặc local).
  - `mcp_gateway.py`: Cổng MCP.
  - `memory.py`: Quản lý bộ nhớ.
  - `planner.py`: Dịch vụ lập kế hoạch.
  - `quality_metrics.py`: Đo lường chất lượng.
  - `rag.py`: Retrieval-Augmented Generation.
  - `router.py`: Định tuyến.
  - `symptom.py`: Phân tích triệu chứng.
- `app/config.py`: Cấu hình môi trường và đường dẫn.
- `main.py`: Điểm khởi chạy uvicorn.
- `streamlit_app.py`: Giao diện Streamlit cho demo.
- `requirements.txt`: Danh sách dependencies.
- `memory_store/`: Lưu trữ FAISS và JSON cho bộ nhớ.
- `data/`: Nguồn dữ liệu cho RAG.
- `tools/`: Các công cụ bổ sung.

## Công Nghệ Sử Dụng

- **Python 3.13+**: Ngôn ngữ chính.
- **FastAPI**: Framework backend RESTful.
- **Uvicorn**: ASGI server.
- **Streamlit**: Giao diện web nhanh.
- **Groq LLM**: Model ngôn ngữ lớn cho inference.
- **LangGraph**: Orchestration cho workflow.
- **FAISS**: Vector database cho semantic search.
- **SentenceTransformers**: Embedding models.
- **python-dotenv**: Quản lý biến môi trường.

## Cài Đặt

1. **Tạo Virtual Environment**:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Trên Windows
   pip install -r requirements.txt
   ```

2. **Cấu Hình Môi Trường**:
   Tạo file `.env` ở thư mục gốc với nội dung sau:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   LLM_PROVIDER=groq
   LLM_MODEL=llama-3.1-8b-instant
   EMBEDDING_MODEL=all-MiniLM-L6-v2
   API_HOST=127.0.0.1
   API_PORT=8000
   ```

   Nếu sử dụng local LLM:
   ```env
   LLM_PROVIDER=local
   LOCAL_LLM_PATH=C:\path\to\your\local-model.bin
   ```

   > Lưu ý: Local provider hiện tại chỉ hỗ trợ cấu hình; cần cài đặt runtime bổ sung cho inference local.

## Chạy Ứng Dụng

### Backend (FastAPI)

```bash
python main.py
```

Hoặc trực tiếp với uvicorn:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Ứng dụng sẽ chạy tại `http://127.0.0.1:8000`.

### Giao Diện Demo (Streamlit)

```bash
streamlit run streamlit_app.py
```

Truy cập giao diện tại địa chỉ được cung cấp bởi Streamlit.

### Docker

Sử dụng Docker Compose để chạy toàn bộ stack:
```bash
docker-compose up --build
```

## API Endpoints

- `GET /`: Trang chủ.
- `POST /chat`: Gửi tin nhắn chat.
- `GET /metrics`: Lấy số liệu về người dùng và tasks.
- Các endpoint khác cho quản lý memory và plans.

Tham khảo `app/api.py` để biết chi tiết.

## Cải Tiến Gần Đây

1. Tinh gọn `app/config.py` chỉ còn cấu hình môi trường.
2. Cải thiện `app/services/llm.py` để đọc đúng `LLM_PROVIDER` và `LOCAL_LLM_PATH`.
3. Thêm endpoint `GET /metrics` để đo lường.
4. `main.py` hỗ trợ cấu hình `API_HOST`/`API_PORT` từ `.env`.
5. Kiến trúc rõ ràng, dễ bảo trì và mở rộng.

## Đóng Góp

Chúng tôi hoan nghênh đóng góp! Vui lòng tạo issue hoặc pull request trên GitHub.

## Giấy Phép

Dự án này được phân phối dưới giấy phép MIT.

Sau khi chạy, truy cập:

* `http://127.0.0.1:8000/health`
* `http://127.0.0.1:8000/docs`
* `http://127.0.0.1:8000/metrics`

### Frontend

```bash
python -m streamlit run streamlit_app.py
```

## API endpoints

| Method | Endpoint               | Mô tả |
| ------ | ---------------------- | ----- |
| GET    | `/health`              | Kiểm tra trạng thái dịch vụ |
| GET    | `/metrics`             | Thống kê memory và plan |
| POST   | `/chat`                | Gửi truy vấn chat |
| GET    | `/chat`                | Hướng dẫn dùng chat query |
| GET    | `/plan/{user_id}`      | Lấy kế hoạch của user |
| POST   | `/plan/complete`       | Hoàn thành task |
| DELETE | `/plan/{user_id}`      | Xóa toàn bộ kế hoạch |
| DELETE | `/plan/{user_id}/{task_id}` | Xóa task cụ thể |
| GET    | `/reminders/{user_id}` | Lấy nhắc nhở cho hôm nay |
| GET    | `/memory/{user_id}`    | Xem history memory |
| DELETE | `/memory/{user_id}`    | Xóa memory user |

## Docker / Production

### Docker build

```bash
docker build -t healthcare-agent .
```

### Run container

```bash
docker run -p 8000:8000 -v %CD%/memory_store:/app/memory_store --env-file .env healthcare-agent
```

### Docker Compose

```bash
docker compose up --build
```

## Hướng dẫn debug nhanh

* Nếu `fastapi` hoặc `langgraph` chưa cài, chạy `pip install -r requirements.txt`.
* Nếu hệ thống không có dataset, RAG sẽ trả fallback thông báo.
* `memory_store/` chứa cả file `.faiss` và `.json`, giúp giữ context người dùng giữa các lần chạy.

## Ghi chú chất lượng

* Dữ liệu người dùng lưu bằng FAISS + metadata JSON để đảm bảo truy vấn nhanh và dễ khôi phục.
* Kiến trúc dịch vụ tách rõ controller (`app/api.py`) và business logic (`app/services/*`).
* Mô-đun LLM có thể mở rộng thêm `transformers` / `llama_cpp` để chạy local.
