# Quality Metrics & Performance Monitoring Guide

## Overview

Healthcare Chatbot system includes comprehensive quality and performance metrics to measure:
- **Output Quality**: Relevance, coherence, coverage of responses
- **System Performance**: Latency, throughput, error rates
- **User Experience**: Overall quality scores, per-user metrics

---

## 1. Output Quality Metrics

### Quality Dimensions

#### **Relevance Score** (0-1)
- Measures semantic similarity between user query and chatbot response
- Uses embedding-based cosine similarity
- **Example**: Query "Em bị đau đầu" → Response with medical advice = high relevance (0.88)
- **Poor Example**: Query "Em bị đau đầu" → Response about weather = low relevance

#### **Coherence Score** (0-1)
- Evaluates linguistic quality, structure, and sentence flow
- Penalizes extremely short or overly fragmented responses
- Ideal: 10-20 words per sentence
- **Example**: "Bạn có thể bị viêm họng. Uống nước ấm." = 1.0
- **Poor Example**: "Ok." = 0.4

#### **Coverage Score** (0-1)
- Measures how well response addresses the query
- Looks for medical keywords and semantic overlap
- Higher for medical queries with medical advice in response
- **Example**: Medical query with treatment options = 0.8-1.0
- **Non-medical**: "Cơm không ngon" with dietary suggestions = 0.67

#### **Response Time** (milliseconds)
- Tracks latency from request to response
- Penalizes responses > 5000ms
- Target: < 2000ms for good UX
- Weighted 10% in overall score

### Overall Quality Score

```
Overall = 0.35×Relevance + 0.20×Coherence + 0.35×Coverage + 0.10×TimeScore
```

**Interpretation**:
- 0.9+ : Excellent response
- 0.8-0.9 : Good response
- 0.7-0.8 : Acceptable response
- < 0.7 : Needs improvement

---

## 2. System Performance Metrics

### Key Indicators

#### **Request Metrics**
- `total_requests`: Total API calls received
- `successful_requests`: Requests with status < 400
- `error_count`: Failed requests
- `error_rate_percent`: Error rate percentage

#### **Latency Metrics**
```json
{
  "avg": 1475.0,      // Average response time (ms)
  "p95": 2150.0,      // 95th percentile latency
  "p99": 2150.0,      // 99th percentile latency
  "min": 800.0,       // Fastest response
  "max": 2150.0       // Slowest response
}
```

**Target SLOs**:
- Average: < 1500ms
- P95: < 2500ms
- P99: < 3500ms
- Error rate: < 1%

#### **Quality Aggregates**
```json
{
  "avg_score": 0.812,     // Average quality score across all responses
  "min_score": 0.716,     // Lowest quality score
  "max_score": 0.940,     // Highest quality score
  "measurements": 20      // Number of measured responses
}
```

#### **Throughput & Availability**
- `throughput_req_per_sec`: Requests per second
- `uptime_seconds`: System uptime
- `active_users`: Unique users in current session

---

## 3. Using the Metrics API

### Endpoint: `GET /metrics`

Returns comprehensive system and quality metrics:

```bash
curl http://localhost:8000/metrics
```

**Response Example**:
```json
{
  "status": "ok",
  "timestamp": "2026-05-06T10:30:45.123456",
  "system": {
    "total_requests": 20,
    "successful_requests": 20,
    "error_rate_percent": 0.0,
    "active_users": 5,
    "latency_ms": {
      "avg": 1475.0,
      "p95": 2150.0,
      "p99": 2150.0,
      "min": 800.0,
      "max": 2150.0
    },
    "quality": {
      "avg_score": 0.812,
      "min_score": 0.716,
      "max_score": 0.940,
      "measurements": 20
    },
    "throughput_req_per_sec": 2.0,
    "uptime_seconds": 10.1
  },
  "data": {
    "users_with_plans": 5,
    "total_plan_items": 23,
    "users_with_memory": 5
  }
}
```

### Endpoint: `POST /chat`

Returns quality metrics in chat response:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_1",
    "message": "Em bị đau đầu"
  }'
```

**Response Example**:
```json
{
  "response": "Bạn có thể bị viêm họng hoặc cảm cúm...",
  "routing": {
    "intent": "symptom_analysis",
    "confidence": 0.95
  },
  "user_id": "user_1",
  "metrics": {
    "quality": {
      "relevance_score": 0.883,
      "coherence_score": 1.0,
      "response_time_ms": 1300.0,
      "coverage_score": 1.0
    },
    "overall_score": 0.933,
    "response_time_ms": 1300.0
  }
}
```

---

## 4. Quality Metrics Test Suite

### Running Tests

```bash
python test_quality_metrics.py
```

**Test Coverage**:
1. **Individual Response Quality** - Tests 5 healthcare scenarios
2. **System Aggregation** - Simulates 20 requests, tracks metrics
3. **Response Type Comparison** - Compares good/poor/off-topic responses

### Example Test Results

```
Test Case 1: Em bị đau đầu từ sáng nay, có sốt 38.5 độ C
  Relevance: 0.883 | Coherence: 1.0 | Coverage: 1.0 | Overall: 0.933

Test Case 2: Tôi bị mẩn ngứa khắp người
  Relevance: 0.876 | Coherence: 0.4 | Coverage: 0.8 | Overall: 0.739

System Metrics (20 simulated requests):
  Avg Latency: 1475.00 ms
  P95 Latency: 2150.00 ms
  Avg Quality: 0.812
  Error Rate: 0.00%
```

---

## 5. Implementation Details

### Classes & Methods

#### `QualityMetricsCalculator`
```python
calculator = QualityMetricsCalculator()

# Calculate all metrics for a response
quality = calculator.calculate_quality(
    query="Em bị đau đầu",
    response="Bạn có thể bị viêm họng...",
    response_time_ms=1300,
    confidence_score=0.95  # Optional
)

# Individual metric calculations
relevance = calculator.calculate_relevance(query, response)
coherence = calculator.calculate_coherence(response)
coverage = calculator.calculate_coverage(query, response)
```

#### `SystemMetrics`
```python
system = SystemMetrics()

# Record individual request
system.record_request(duration_ms=1300, success=True, user_id="user_1")

# Record quality score
system.record_quality_score(0.933)

# Get aggregated metrics
summary = system.get_summary()
```

#### `OutputQuality` Data Class
```python
@dataclass
class OutputQuality:
    relevance_score: float
    coherence_score: float
    response_time_ms: float
    coverage_score: float
    confidence_score: Optional[float] = None
    
    # Calculate weighted overall score
    overall_score() -> float
    
    # Convert to dictionary
    to_dict() -> dict
```

### Medical Keywords Database

The calculator recognizes three medical keyword categories:
- **Symptoms**: đau, sốt, ho, buồn nôn, mệt mỏi, chóng mặt, ngứa, sưng
- **Treatments**: uống, bôi, tiêm, phẫu thuật, liệu pháp, thuốc, điều trị
- **Advice**: nên, không nên, cần, tránh, hạn chế, khuyến cáo, lưu ý

These help distinguish medical vs non-medical queries for better coverage scoring.

---

## 6. Monitoring & Alerting

### Recommended Dashboards

**Real-time Monitoring**:
- Pull `/metrics` endpoint every 30 seconds
- Track trends: Average latency, quality scores, error rates
- Alert if:
  - Error rate > 1%
  - P95 latency > 2500ms
  - Average quality < 0.75

**Daily Reports**:
- Quality distribution (histogram of quality scores)
- User satisfaction by intent type
- Latency trending over time
- Top/bottom performing response types

### Sample Alert Thresholds

```python
ALERTS = {
    "error_rate_high": error_rate > 0.01,
    "latency_degraded": p95_latency > 2500,
    "quality_declining": avg_quality < 0.75,
    "throughput_low": throughput_req_per_sec < 0.5,
}
```

---

## 7. Troubleshooting

### Low Relevance Scores
- **Cause**: Embedding model not capturing semantic meaning
- **Solution**: Check embedding model quality, consider fine-tuning
- **Example**: Out-of-domain queries may have lower relevance

### Low Coherence Scores
- **Cause**: Response text is too fragmented or extremely short
- **Solution**: Improve prompt engineering to generate more structured responses
- **Example**: Single-word responses will have coherence = 0.4

### Low Coverage Scores
- **Cause**: Response missing key medical keywords or context
- **Solution**: Ensure RAG retrieves relevant medical information
- **Example**: Non-medical questions naturally have lower coverage

### High Latency
- **Cause**: LLM inference slow, embedding calculations expensive
- **Solution**: Optimize model size, use caching, scale horizontally
- **Target**: Sub-2000ms for good user experience

---

## 8. Integration with CI/CD

### Quality Gates

Add metrics checks to deployment pipeline:

```yaml
# Example: Only deploy if quality metrics pass
quality_score_min: 0.75
error_rate_max: 0.01
latency_p95_max: 2500
```

### Performance Tracking

Store metrics over time for trending:

```python
# Log metrics periodically
import json
from datetime import datetime

def log_metrics():
    metrics = get_metrics()
    timestamp = datetime.now().isoformat()
    with open(f"logs/metrics-{timestamp}.json", "w") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
```

---

## 9. Quick Start Checklist

- [ ] Enable `/metrics` endpoint (already done in `api.py`)
- [ ] Add quality tracking to `/chat` endpoint (already done)
- [ ] Run `test_quality_metrics.py` to verify installation
- [ ] Set up periodic metrics collection (every 30-60 seconds)
- [ ] Create monitoring dashboard
- [ ] Define alerting thresholds
- [ ] Monitor quality scores by intent type
- [ ] Track trends over time for continuous improvement

---

## References

- Quality Metrics: `app/services/quality_metrics.py`
- API Integration: `app/api.py`
- Test Suite: `test_quality_metrics.py`
