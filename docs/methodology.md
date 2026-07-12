# Research Methodology

## LLM Energy Analysis - Grant 2026

### Research Question

**What is the measurable energy cost of maintaining data sovereignty through local LLM inference compared to cloud-based solutions?**

---

## 1. Overview

This research quantifies the operational energy cost of data sovereignty by comparing the energy efficiency of local LLM inference against cloud-based APIs. The methodology establishes a measurable framework for comparing joules-per-token between local hardware and cloud providers.

---

## 2. Hardware Configuration

### Local Test Bench

**Purpose**: Eliminate variables that could skew power metrics

**Components**:
- **GPU**: NVIDIA RTX 5060 Ti (16GB VRAM)
  - Rationale: Sufficient VRAM to run 8B parameter models entirely in video memory, preventing power-draining data offloads to system RAM
  
- **CPU**: AMD Ryzen 9 5900XT (16-core)
  - Rationale: Ensures background processes don't bottleneck inference pipeline
  
- **Cooling**: Liquid CPU cooler + high-airflow case fans
  - Rationale: Maintains consistent temperature baseline during sustained testing (thermal throttling alters power consumption)
  
- **Power Monitoring**: Shelly Smart Plug with power metering
  - Rationale: Hardware-level measurement captures exact wattage at the wall

### Measurement Precision

- **Polling Interval**: 1-second intervals
- **Integration Method**: Trapezoidal integration for accurate energy calculation
- **Baseline**: Idle power subtracted from active measurements
- **Resolution**: ±0.1W accuracy

---

## 3. Software Stack

### Local Inference
- **Framework**: Ollama
- **Models**: LLaMA 3 (8B parameters), Mistral, others as available
- **Quantization**: 8-bit quantization to fit in VRAM
- **Configuration**: Temperature 0.7, consistent across all tests

### Cloud APIs
- **Providers**: OpenAI (GPT-3.5, GPT-4), Anthropic (Claude 3)
- **Configuration**: Identical temperature and max tokens settings
- **Cost Tracking**: Per-request token usage and pricing
- **Energy Attribution**: Based on published provider sustainability reports

---

## 4. Experimental Protocol

### Phase 1: Baseline Measurement (60 seconds)
1. System idle state (no active workloads)
2. Power readings at 1-second intervals
3. Calculate average idle power consumption
4. Purpose: Establish baseline for subtraction from active measurements

### Phase 2: Thermal Stabilization (3 warm-up queries)
1. Execute warm-up prompts to load model into memory
2. Allow GPU/CPU to reach steady-state temperature
3. Wait for cooling period (30 seconds)
4. Purpose: Eliminate model loading overhead and thermal ramp-up from measurements

### Phase 3: Local LLM Testing
1. For each model:
   - Execute standardized prompt set
   - Monitor power consumption continuously during generation
   - Record: input tokens, output tokens, generation time, power draw
   - Calculate: joules consumed, joules per token
   - Cool down period: 30 seconds between tests
2. Repeat 3 times for statistical validity

### Phase 4: Cloud API Testing
1. For each provider/model combination:
   - Execute identical prompt set
   - Record: input tokens, output tokens, response time, cost
   - Apply energy attribution from provider data
   - Calculate: estimated joules per token
2. Respect rate limits (1-second delay between requests)
3. Repeat 3 times for statistical validity

---

## 5. Test Prompts

Standardized prompts covering diverse workloads:

1. **Code Generation** (3 prompts)
   - Function implementations, class definitions, SQL queries
   - Tests computational reasoning

2. **Text Summarization** (3 prompts)
   - Various text lengths
   - Tests compression capabilities

3. **Question Answering** (7 prompts)
   - Factual, reasoning, technical questions
   - Tests knowledge retrieval

4. **Creative Writing** (3 prompts)
   - Stories, poetry, product descriptions
   - Tests generative capabilities

5. **Technical Documentation** (3 prompts)
   - API docs, troubleshooting guides, instructions
   - Tests structured output

**Total**: 20 standardized prompts × 3 repetitions = 60 measurements per model

---

## 6. Energy Attribution for Cloud APIs

### Data Sources
- **OpenAI**: Published sustainability reports (~0.0006-0.0015 kWh per 1000 tokens)
- **Anthropic**: Similar published data
- **PUE Factor**: 1.2 (typical data center Power Usage Effectiveness)

### Calculation
```
Joules per token = (kWh per token × 3600 J/Wh) × PUE factor
```

### Limitations
- Cloud estimates based on provider-reported averages
- Actual values may vary by region, time of day, server utilization
- Data center overhead (cooling, networking) included via PUE

---

## 7. Data Collection

### Metrics Recorded

**Local Inference**:
- Timestamp
- Model name
- Prompt ID and category
- Input tokens, output tokens, total tokens
- Generation time (seconds)
- Tokens per second
- Power consumption: start, end, average (Watts)
- Energy consumed (Joules)
- Joules per token
- System temperature (if available)

**Cloud Inference**:
- Timestamp
- Provider and model
- Prompt ID and category
- Input tokens, output tokens, total tokens
- Response time (seconds)
- Cost (USD)
- Estimated energy (Joules, from provider data)
- Joules per token

### Data Format
- **Storage**: CSV files with timestamps
- **Naming**: `local_benchmark_YYYYMMDD_HHMMSS.csv`
- **Encoding**: UTF-8

---

## 8. Analysis Methods

### Statistical Measures
- **Mean**: Average joules per token
- **Median**: Central tendency measure
- **Standard Deviation**: Variability indicator
- **Repetition Averaging**: 3 runs per prompt reduce noise

### Comparative Analysis
1. **Energy Efficiency**: Local J/token vs Cloud J/token
2. **Cost Analysis**: Cloud operational cost vs local capital cost
3. **Performance**: Response time comparison
4. **Category Analysis**: Energy by task type

### Visualization
- Bar charts: Local vs Cloud comparison
- Horizontal bars: Energy by model
- Line plots: Power consumption over time
- Scatter plots: Privacy-energy tradeoff

---

## 9. Validity Considerations

### Internal Validity
- **Controlled Variables**: Same prompts, same configuration
- **Thermal Management**: Cooling periods prevent thermal throttling
- **Repetition**: Multiple runs reduce measurement noise
- **Baseline Subtraction**: Isolates inference energy from idle consumption

### External Validity
- **Model Selection**: Popular, representative models
- **Prompt Diversity**: Multiple task categories
- **Real-World Conditions**: Typical hardware and configurations

### Measurement Reliability
- **Hardware Accuracy**: Smart plug ±0.1W
- **Timestamp Precision**: Millisecond-level timing
- **Energy Integration**: Trapezoidal method reduces discretization error

---

## 10. Limitations

1. **Token Counting**: Approximation for local models (no native tokenizer access)
2. **Cloud Energy**: Based on provider-reported averages, not direct measurement
3. **System Overhead**: Total system power measured (not just GPU)
4. **Model Variability**: Different model architectures may have different efficiency characteristics
5. **Network Latency**: Cloud response times include network overhead

---

## 11. Ethical Considerations

- **Energy Transparency**: Full disclosure of measurement methodology
- **Data Privacy**: No sensitive data used in prompts
- **Reproducibility**: All code and configurations publicly available
- **Academic Integrity**: Honest reporting of both successes and limitations

---

## 12. Expected Outcomes

This methodology will produce:
1. Precise joules-per-token measurements for local inference
2. Comparative analysis with cloud provider energy attribution
3. Cost-benefit analysis of data sovereignty vs cloud convenience
4. Publication-quality visualizations for grant reporting
5. Reproducible framework for future energy studies

---

## References

- OpenAI Sustainability Reports
- Anthropic Environmental Impact Documentation
- IEEE Standards for Power Measurement
- SPEC Power and Performance Benchmarks
