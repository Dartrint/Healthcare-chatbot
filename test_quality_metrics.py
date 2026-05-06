"""Test script for quality metrics measurement."""

from app.services.quality_metrics import QualityMetricsCalculator, SystemMetrics
import time
import json
from tabulate import tabulate


# Sample healthcare queries and expected responses for testing
TEST_CASES = [
    {
        "query": "Em bị đau đầu từ sáng nay, có sốt 38.5 độ C",
        "response": "Bạn đang có triệu chứng viêm họng hoặc cảm cúm. Các triệu chứng đau đầu kèm sốt thường chỉ dứt trong 3-5 ngày. Khuyến cáo: Uống nước ấm, dùng paracetamol khi cần, nghỉ ngơi đầy đủ. Nếu sốt cao trên 39 độ C hoặc kéo dài hơn 5 ngày, bạn nên gặp bác sĩ.",
    },
    {
        "query": "Tôi bị mẩn ngứa khắp người",
        "response": "Bạn vui lòng mô tả chi tiết hơn: mẩn xuất hiện bao lâu? Có ngứa, sưng, hoặc chảy máu không? Mẩn có hình dạng như thế nào? Điều này sẽ giúp chẩn đoán chính xác hơn.",
    },
    {
        "query": "Làm sao để giảm cân hiệu quả?",
        "response": "Để giảm cân an toàn, bạn nên: 1) Ăn uống cân bằng, giảm carbs và chất béo, 2) Tập thể dục 30 phút/ngày, 3) Uống đủ nước, 4) Tránh đồ ăn nhiều đường. Giảm cân khoảng 0.5-1 kg/tuần là an toàn. Nếu có bệnh lý, tư vấn bác sĩ trước.",
    },
    {
        "query": "Cơm không ngon",
        "response": "Vâng, tôi hiểu bạn cảm thấy mất ngon miệng. Tuy nhiên, điều này không phải triệu chứng y tế đặc biệt. Bạn có thể ăn những thứ yêu thích hơn hoặc gọi bác sĩ nếu mất ngon miệng kéo dài trên 2 tuần.",
    },
    {
        "query": "Em bị viêm họng, cổ họng đau rát",
        "response": "Viêm họng là bệnh phổ biến. Các triệu chứng chính: cổ họng đau, nuốt khó, có thể sốt. Cách chữa: uống nước muối ấm, dùng kháng sinh nếu viêm do vi khuẩn, chuyên gia khuyến cáo dùng amoxicillin. Nếu không khỏi sau 7 ngày, gặp bác sĩ.",
    },
]


def test_individual_responses():
    """Test quality metrics for individual responses."""
    print("\n" + "="*80)
    print("TESTING INDIVIDUAL RESPONSE QUALITY")
    print("="*80 + "\n")
    
    calculator = QualityMetricsCalculator()
    results = []
    
    for i, case in enumerate(TEST_CASES, 1):
        query = case["query"]
        response = case["response"]
        
        # Simulate response time (in milliseconds)
        response_time = 1200 + i * 100  # 1.2s to 1.6s
        
        quality = calculator.calculate_quality(
            query=query,
            response=response,
            response_time_ms=response_time,
        )
        
        results.append({
            "ID": i,
            "Query": query[:40] + "..." if len(query) > 40 else query,
            "Relevance": f"{quality.relevance_score:.3f}",
            "Coherence": f"{quality.coherence_score:.3f}",
            "Coverage": f"{quality.coverage_score:.3f}",
            "Latency (ms)": int(response_time),
            "Overall Score": f"{quality.overall_score():.3f}",
        })
        
        print(f"\nTest Case {i}:")
        print(f"Query: {query}")
        print(f"Response: {response[:100]}...")
        print(f"\nQuality Metrics:")
        print(f"  - Relevance Score:  {quality.relevance_score:.3f}")
        print(f"  - Coherence Score:  {quality.coherence_score:.3f}")
        print(f"  - Coverage Score:   {quality.coverage_score:.3f}")
        print(f"  - Response Time:    {response_time:.0f}ms")
        print(f"  - Overall Score:    {quality.overall_score():.3f}")
        print(f"\nDetailed Metrics:")
        print(json.dumps(quality.to_dict(), indent=2, ensure_ascii=False))
    
    # Summary table
    print("\n" + "="*80)
    print("SUMMARY TABLE")
    print("="*80)
    print(tabulate(results, headers="keys", tablefmt="grid"))
    
    return results


def test_system_aggregation():
    """Test system-level metrics aggregation."""
    print("\n" + "="*80)
    print("TESTING SYSTEM METRICS AGGREGATION")
    print("="*80 + "\n")
    
    calculator = QualityMetricsCalculator()
    system = SystemMetrics()
    
    # Simulate 20 requests with varying quality
    print("Simulating 20 requests with varying response times and quality...\n")
    
    for i, case in enumerate(TEST_CASES * 4, 1):  # Repeat test cases 4 times
        query = case["query"]
        response = case["response"]
        response_time = 800 + (i % 10) * 150  # Vary response time
        
        quality = calculator.calculate_quality(
            query=query,
            response=response,
            response_time_ms=response_time,
        )
        
        # Record metrics
        system.record_request(response_time, success=(i % 22 != 0), user_id=f"user_{i % 5}")
        system.record_quality_score(quality.overall_score())
        
        print(f"Request {i}: latency={response_time:.0f}ms, quality={quality.overall_score():.3f}")
    
    # Get system summary
    summary = system.get_summary()
    
    print("\n" + "="*80)
    print("SYSTEM METRICS SUMMARY")
    print("="*80)
    print(json.dumps(summary, indent=2))
    
    # Pretty print key metrics
    print("\n" + "-"*80)
    print("KEY PERFORMANCE INDICATORS")
    print("-"*80)
    print(f"Total Requests:        {summary['total_requests']}")
    print(f"Successful Requests:   {summary['successful_requests']}")
    print(f"Error Rate:            {summary['error_rate_percent']:.2f}%")
    print(f"Active Users:          {summary['active_users']}")
    print(f"\nLatency Metrics (ms):")
    print(f"  - Average:           {summary['latency_ms']['avg']:.2f}")
    print(f"  - P95:               {summary['latency_ms']['p95']:.2f}")
    print(f"  - P99:               {summary['latency_ms']['p99']:.2f}")
    print(f"  - Min:               {summary['latency_ms']['min']:.2f}")
    print(f"  - Max:               {summary['latency_ms']['max']:.2f}")
    print(f"\nQuality Metrics:")
    print(f"  - Average Score:     {summary['quality']['avg_score']:.3f}")
    print(f"  - Min Score:         {summary['quality']['min_score']:.3f}")
    print(f"  - Max Score:         {summary['quality']['max_score']:.3f}")
    print(f"  - Measurements:      {summary['quality']['measurements']}")
    print(f"\nThroughput:            {summary['throughput_req_per_sec']:.2f} req/sec")
    print(f"Uptime:                {summary['uptime_seconds']:.2f} seconds")


def compare_response_qualities():
    """Compare quality of different response types."""
    print("\n" + "="*80)
    print("COMPARING RESPONSE QUALITY TYPES")
    print("="*80 + "\n")
    
    calculator = QualityMetricsCalculator()
    
    # Good response
    good_response = {
        "query": "Em bị đau đầu",
        "response": "Bạn có thể bị viêm họng, cảm cúm hoặc stress. Triệu chứng đau đầu thường kéo dài 2-3 ngày. Khuyến cáo: uống nước ấm, dùng paracetamol nếu cần, nghỉ ngơi đầy đủ. Nếu đau thường xuyên, gặp bác sĩ.",
    }
    
    # Poor response
    poor_response = {
        "query": "Em bị đau đầu",
        "response": "Ok",
    }
    
    # Off-topic response
    offtopic_response = {
        "query": "Em bị đau đầu",
        "response": "Thời tiết hôm nay rất đẹp. Bạn nên đi tham quan các địa điểm du lịch nổi tiếng.",
    }
    
    responses = [
        ("Good Response", good_response),
        ("Poor Response (Too Short)", poor_response),
        ("Off-topic Response", offtopic_response),
    ]
    
    comparison_results = []
    
    for label, case in responses:
        quality = calculator.calculate_quality(
            query=case["query"],
            response=case["response"],
            response_time_ms=1000,
        )
        
        comparison_results.append({
            "Response Type": label,
            "Relevance": f"{quality.relevance_score:.3f}",
            "Coherence": f"{quality.coherence_score:.3f}",
            "Coverage": f"{quality.coverage_score:.3f}",
            "Overall": f"{quality.overall_score():.3f}",
        })
        
        print(f"\n{label}:")
        print(f"  Query: {case['query']}")
        print(f"  Response: {case['response'][:80]}...")
        print(f"  Overall Score: {quality.overall_score():.3f}")
    
    print("\n" + "-"*80)
    print("COMPARISON TABLE")
    print("-"*80)
    print(tabulate(comparison_results, headers="keys", tablefmt="grid"))


if __name__ == "__main__":
    print("\n╔" + "="*78 + "╗")
    print("║" + " "*20 + "HEALTHCARE CHATBOT QUALITY METRICS TEST SUITE" + " "*13 + "║")
    print("╚" + "="*78 + "╝")
    
    try:
        test_individual_responses()
        test_system_aggregation()
        compare_response_qualities()
        
        print("\n" + "="*80)
        print("✓ ALL TESTS COMPLETED SUCCESSFULLY")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n✗ ERROR DURING TESTING: {e}")
        import traceback
        traceback.print_exc()
