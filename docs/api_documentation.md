# API Documentation

## LLM Energy Analysis - Grant 2026

This document provides comprehensive API documentation for all modules in the LLM Energy Analysis project.

---

## Table of Contents

1. [PowerMonitor](#powermonitor)
2. [LocalLLMBenchmark](#localllmbenchmark)
3. [CloudBenchmark](#cloudbenchmark)
4. [BenchmarkAnalyzer](#benchmarkanalyzer)
5. [GraphGenerator](#graphgenerator)
6. [GrantReportGenerator](#grantreportgenerator)
7. [Dashboard API](#dashboard-api)
8. [Configuration](#configuration)
9. [Data Formats](#data-formats)

---

## PowerMonitor

**Module:** `src/power_monitor.py`

Interfaces with Shelly Smart Plug for real-time power monitoring.

### Class: `PowerMonitor`

#### Constructor

```python
PowerMonitor(ip_address: str, polling_interval: float = 1.0, timeout: int = 5)
```

**Parameters:**
- `ip_address` (str): IP address of Shelly Smart Plug
- `polling_interval` (float): Seconds between power readings (default: 1.0)
- `timeout` (int): HTTP request timeout in seconds (default: 5)

#### Methods

##### `test_connection() -> bool`

Test connection to the Shelly plug.

**Returns:** `True` if connection successful, `False` otherwise

**Example:**
```python
monitor = PowerMonitor("192.168.1.100")
if monitor.test_connection():
    print("Connected!")
```

##### `get_current_power() -> Optional[float]`

Get current power consumption in Watts.

**Returns:** Power in Watts, or `None` if error

**Example:**
```python
power = monitor.get_current_power()
print(f"Current power: {power}W")
```

##### `start_monitoring()`

Start continuous power monitoring in background thread.

**Example:**
```python
monitor.start_monitoring()
# Monitoring runs in background
```

##### `stop_monitoring() -> Dict`

Stop monitoring and return statistics.

**Returns:** Dictionary with:
- `duration`: Total monitoring time (seconds)
- `readings`: Number of measurements
- `avg_power`: Average power (W)
- `min_power`: Minimum power (W)
- `max_power`: Maximum power (W)
- `total_energy`: Total energy consumed (Joules)

**Example:**
```python
stats = monitor.stop_monitoring()
print(f"Average power: {stats['avg_power']:.2f}W")
```

##### `measure_baseline(duration: int = 60) -> Dict`

Measure idle power consumption baseline.

**Parameters:**
- `duration` (int): Measurement duration in seconds (default: 60)

**Returns:** Dictionary with baseline statistics

**Example:**
```python
baseline = monitor.measure_baseline(duration=60)
print(f"Baseline power: {baseline['avg_power']:.2f}W")
```

##### `monitor_during_task(task_func, *args, **kwargs)`

Monitor power consumption during a specific task.

**Parameters:**
- `task_func`: Function to execute
- `*args`: Arguments to pass to function
- `**kwargs`: Keyword arguments to pass to function

**Returns:** Tuple of (task_result, power_stats)

**Example:**
```python
def inference_task():
    return model.generate("Hello world")

result, stats = monitor.monitor_during_task(inference_task)
print(f"Energy used: {stats['total_energy']:.2f}J")
```

##### `export_to_csv(filepath: str)`

Export power measurements to CSV file.

**Parameters:**
- `filepath` (str): Path to output CSV file

**Example:**
```python
monitor.export_to_csv("data/results/power_log.csv")
```

---

## LocalLLMBenchmark

**Module:** `src/local_llm_benchmark.py`

Benchmarks local LLM inference using Ollama.

### Class: `LocalLLMBenchmark`

#### Constructor

```python
LocalLLMBenchmark(host: str = "http://localhost:11434", 
                  power_monitor: Optional[PowerMonitor] = None)
```

**Parameters:**
- `host` (str): Ollama server URL (default: "http://localhost:11434")
- `power_monitor` (Optional[PowerMonitor]): PowerMonitor instance for energy tracking

#### Methods

##### `test_connection() -> bool`

Test connection to Ollama server.

**Returns:** `True` if connected, `False` otherwise

##### `list_models() -> List[str]`

Get list of available models.

**Returns:** List of model names

**Example:**
```python
benchmark = LocalLLMBenchmark()
models = benchmark.list_models()
print(f"Available models: {models}")
```

##### `count_tokens(text: str, model: str) -> int`

Estimate token count for text.

**Parameters:**
- `text` (str): Input text
- `model` (str): Model name

**Returns:** Approximate token count

##### `generate(model: str, prompt: str, **options) -> Dict`

Generate text using specified model.

**Parameters:**
- `model` (str): Model name
- `prompt` (str): Input prompt
- `**options`: Additional generation options (temperature, max_tokens, etc.)

**Returns:** Dictionary with:
- `response`: Generated text
- `generation_time`: Time taken (seconds)
- `input_tokens`: Estimated input tokens
- `output_tokens`: Estimated output tokens

**Example:**
```python
result = benchmark.generate(
    model="llama3",
    prompt="Explain quantum computing",
    temperature=0.7,
    max_tokens=500
)
print(result['response'])
```

##### `benchmark_prompt(model: str, prompt: str, prompt_id: str, category: str) -> Dict`

Benchmark a single prompt with power monitoring.

**Parameters:**
- `model` (str): Model name
- `prompt` (str): Input prompt
- `prompt_id` (str): Unique identifier for prompt
- `category` (str): Prompt category

**Returns:** Dictionary with complete metrics including power/energy data

##### `run_warmup(model: str, count: int = 3)`

Run warmup queries to stabilize temperature.

**Parameters:**
- `model` (str): Model name
- `count` (int): Number of warmup queries (default: 3)

##### `benchmark_model(model: str, prompts: List[Dict], repetitions: int = 1) -> List[Dict]`

Benchmark model with multiple prompts.

**Parameters:**
- `model` (str): Model name
- `prompts` (List[Dict]): List of prompt dictionaries
- `repetitions` (int): Times to repeat each prompt (default: 1)

**Returns:** List of benchmark results

##### `export_to_csv(results: List[Dict], filepath: str)`

Export results to CSV file.

**Parameters:**
- `results` (List[Dict]): Benchmark results
- `filepath` (str): Output file path

---

## CloudBenchmark

**Module:** `src/cloud_benchmark.py`

Benchmarks cloud-based LLM APIs (OpenAI, Anthropic).

### Class: `CloudBenchmark`

#### Constructor

```python
CloudBenchmark(config: Dict)
```

**Parameters:**
- `config` (Dict): Configuration dictionary with API settings

#### Methods

##### `test_connections() -> Dict[str, bool]`

Test connections to all enabled cloud providers.

**Returns:** Dictionary mapping provider names to connection status

**Example:**
```python
benchmark = CloudBenchmark(config)
status = benchmark.test_connections()
print(f"OpenAI: {status['openai']}")
print(f"Anthropic: {status['anthropic']}")
```

##### `generate_openai(model: str, prompt: str, **kwargs) -> Dict`

Generate text using OpenAI API.

**Parameters:**
- `model` (str): Model name (e.g., "gpt-4", "gpt-3.5-turbo")
- `prompt` (str): Input prompt
- `**kwargs`: Additional API parameters

**Returns:** Dictionary with response, tokens, time, and cost

##### `generate_anthropic(model: str, prompt: str, **kwargs) -> Dict`

Generate text using Anthropic API.

**Parameters:**
- `model` (str): Model name (e.g., "claude-3-opus-20240229")
- `prompt` (str): Input prompt
- `**kwargs`: Additional API parameters

**Returns:** Dictionary with response, tokens, time, and cost

##### `benchmark_prompt(provider: str, model: str, prompt: str, prompt_id: str, category: str) -> Dict`

Benchmark a single prompt on cloud provider.

**Parameters:**
- `provider` (str): "openai" or "anthropic"
- `model` (str): Model name
- `prompt` (str): Input prompt
- `prompt_id` (str): Unique identifier
- `category` (str): Prompt category

**Returns:** Dictionary with metrics including estimated energy and cost

##### `benchmark_providers(prompts: List[Dict], repetitions: int = 1) -> List[Dict]`

Benchmark all enabled providers with given prompts.

**Parameters:**
- `prompts` (List[Dict]): List of prompt dictionaries
- `repetitions` (int): Times to repeat each prompt (default: 1)

**Returns:** List of all benchmark results

##### `export_to_csv(results: List[Dict], filepath: str)`

Export results to CSV file.

---

## BenchmarkAnalyzer

**Module:** `src/analyze_results.py`

Analyzes benchmark results and generates statistics.

### Class: `BenchmarkAnalyzer`

#### Constructor

```python
BenchmarkAnalyzer(results_dir: str = 'data/results')
```

**Parameters:**
- `results_dir` (str): Directory containing CSV result files

#### Methods

##### `load_latest_results() -> bool`

Load the most recent benchmark results.

**Returns:** `True` if results loaded successfully, `False` otherwise

##### `analyze_local_results() -> Dict`

Analyze local benchmark results.

**Returns:** Dictionary with:
- `avg_joules_per_token`: Average energy per token
- `median_joules_per_token`: Median energy per token
- `std_joules_per_token`: Standard deviation
- `avg_generation_time`: Average generation time
- `avg_tokens_per_sec`: Average throughput
- `avg_power_w`: Average power consumption
- `total_prompts`: Number of prompts tested
- `total_tokens`: Total tokens generated
- `total_energy_joules`: Total energy consumed

##### `analyze_cloud_results() -> Dict`

Analyze cloud benchmark results.

**Returns:** Dictionary with similar metrics plus cost analysis

##### `compare_local_vs_cloud() -> Dict`

Compare local and cloud results.

**Returns:** Dictionary with comparative metrics

##### `print_summary()`

Print formatted summary to console.

---

## GraphGenerator

**Module:** `src/generate_graphs.py`

Generates visualizations from benchmark data.

### Class: `GraphGenerator`

#### Constructor

```python
GraphGenerator(analyzer: BenchmarkAnalyzer, output_dir: str = 'data/graphs')
```

**Parameters:**
- `analyzer` (BenchmarkAnalyzer): Initialized analyzer with loaded data
- `output_dir` (str): Directory for graph output

#### Methods

##### `plot_energy_comparison()`

Create bar chart comparing local vs cloud energy efficiency.

##### `plot_energy_by_model()`

Create horizontal bar chart of energy consumption by model.

##### `plot_cost_analysis()`

Create cost analysis visualization for cloud APIs.

##### `plot_performance_comparison()`

Create performance metrics comparison chart.

##### `plot_energy_by_category()`

Create chart showing energy by prompt category.

##### `plot_power_timeline()`

Create timeline plot of power consumption.

##### `plot_tradeoff_analysis()`

Create scatter plot showing privacy-energy tradeoff.

##### `generate_all_graphs()`

Generate all available graphs.

**Example:**
```python
analyzer = BenchmarkAnalyzer()
analyzer.load_latest_results()
generator = GraphGenerator(analyzer)
generator.generate_all_graphs()
```

---

## GrantReportGenerator

**Module:** `reports/generate_report.py`

Generates comprehensive grant reports.

### Class: `GrantReportGenerator`

#### Constructor

```python
GrantReportGenerator(config_path: str = 'config.yaml', 
                     output_dir: str = 'reports')
```

**Parameters:**
- `config_path` (str): Path to configuration file
- `output_dir` (str): Output directory for reports

#### Methods

##### `generate_markdown_report() -> str`

Generate comprehensive Markdown report.

**Returns:** Path to generated report file

##### `generate_html_report() -> str`

Generate HTML version of report.

**Returns:** Path to generated HTML file

##### `print_summary()`

Print data summary to console.

**Example:**
```python
generator = GrantReportGenerator()
md_path = generator.generate_markdown_report()
html_path = generator.generate_html_report()
print(f"Reports generated: {md_path}, {html_path}")
```

---

## Dashboard API

**Module:** `src/dashboard.py`

Flask-based REST API for real-time monitoring.

### Endpoints

#### `GET /`

Serve the dashboard web interface.

#### `GET /api/status`

Get current monitoring status.

**Response:**
```json
{
  "active": true,
  "current_benchmark": "llama3",
  "current_power": 245.5,
  "avg_power": 240.2,
  "peak_power": 260.1,
  "power_history": [240.1, 241.2, ...],
  "uptime": 3600
}
```

#### `GET /api/results`

Get benchmark results and statistics.

**Response:**
```json
{
  "stats": {
    "total_tokens": 15000,
    "total_energy": 5420.5,
    "avg_joules_per_token": 0.3614,
    "avg_tokens_per_sec": 25.4,
    "total_tests": 20,
    "latest_model": "llama3"
  },
  "recent": [...]
}
```

#### `POST /api/power/start`

Start power monitoring.

**Request Body:**
```json
{
  "benchmark": "llama3_test"
}
```

#### `POST /api/power/stop`

Stop power monitoring.

#### `POST /api/power/reading`

Add a power reading (for external integration).

**Request Body:**
```json
{
  "power": 245.5
}
```

---

## Configuration

### config.yaml Structure

```yaml
shelly:
  ip_address: "192.168.1.100"
  polling_interval: 1.0
  timeout: 5

ollama:
  host: "http://localhost:11434"
  models:
    - "llama3"
    - "mistral"
  timeout: 300
  temperature: 0.7

cloud:
  openai:
    enabled: true
    models:
      - "gpt-4"
      - "gpt-3.5-turbo"
    max_tokens: 1000
  anthropic:
    enabled: true
    models:
      - "claude-3-opus-20240229"
    max_tokens: 1000

benchmark:
  idle_baseline_duration: 60
  warmup_queries: 3
  cooling_period: 30
  repetitions: 3

output:
  results_dir: "data/results"
  graphs_dir: "data/graphs"
  timestamp_format: "%Y%m%d_%H%M%S"
```

### Environment Variables (.env)

```
OPENAI_API_KEY=sk-your-key-here
ANTHROPIC_API_KEY=sk-ant-your-key-here
LOG_LEVEL=INFO
```

---

## Data Formats

### Local Benchmark CSV

Columns:
- `timestamp`: ISO 8601 timestamp
- `model`: Model name
- `prompt_id`: Unique prompt identifier
- `prompt_category`: Category (code_generation, etc.)
- `input_tokens`: Input token count
- `output_tokens`: Output token count
- `total_tokens`: Total tokens
- `generation_time_sec`: Generation time in seconds
- `tokens_per_sec`: Throughput
- `power_start_w`: Starting power (W)
- `power_end_w`: Ending power (W)
- `power_avg_w`: Average power (W)
- `energy_joules`: Total energy consumed (J)
- `joules_per_token`: Energy per token
- `temperature_c`: System temperature (if available)

### Cloud Benchmark CSV

Columns:
- `timestamp`: ISO 8601 timestamp
- `provider`: "openai" or "anthropic"
- `model`: Model name
- `prompt_id`: Unique prompt identifier
- `prompt_category`: Category
- `input_tokens`: Input token count
- `output_tokens`: Output token count
- `total_tokens`: Total tokens
- `response_time_sec`: Response time
- `cost_usd`: Cost in USD
- `estimated_energy_joules`: Estimated energy (J)
- `joules_per_token`: Energy per token

### Power Log CSV

Columns:
- `timestamp`: ISO 8601 timestamp
- `power_w`: Power reading in Watts

---

## Usage Examples

### Complete Workflow

```python
import yaml
from src.power_monitor import PowerMonitor
from src.local_llm_benchmark import LocalLLMBenchmark
from src.cloud_benchmark import CloudBenchmark
from src.analyze_results import BenchmarkAnalyzer
from src.generate_graphs import GraphGenerator

# Load configuration
with open('config.yaml') as f:
    config = yaml.safe_load(f)

# Initialize power monitor
monitor = PowerMonitor(config['shelly']['ip_address'])
if not monitor.test_connection():
    raise ConnectionError("Cannot connect to Shelly plug")

# Measure baseline
baseline = monitor.measure_baseline(60)
print(f"Baseline power: {baseline['avg_power']:.2f}W")

# Initialize local benchmark
local_bench = LocalLLMBenchmark(power_monitor=monitor)

# Load prompts
with open('data/prompts.json') as f:
    prompts_data = json.load(f)

# Run benchmarks
results = local_bench.benchmark_model(
    model="llama3",
    prompts=prompts_data['prompts'],
    repetitions=3
)

# Export results
local_bench.export_to_csv(results, 'data/results/local_benchmark.csv')

# Analyze results
analyzer = BenchmarkAnalyzer()
analyzer.load_latest_results()
analyzer.print_summary()

# Generate graphs
generator = GraphGenerator(analyzer)
generator.generate_all_graphs()
```

---

## Error Handling

All methods that can fail return `None` or raise exceptions:

- **ConnectionError**: Network/API connection failures
- **ValueError**: Invalid parameters or data
- **FileNotFoundError**: Missing files or directories
- **KeyError**: Missing configuration keys

**Example:**
```python
try:
    monitor = PowerMonitor("192.168.1.100")
    if not monitor.test_connection():
        print("Connection failed")
except Exception as e:
    print(f"Error: {e}")
```

---

## Performance Considerations

- Power monitoring runs in background thread (non-blocking)
- CSV exports are buffered for efficiency
- Large datasets are processed in chunks
- Dashboard updates via polling (configurable interval)

---

## Best Practices

1. **Always test connections** before running benchmarks
2. **Measure baseline** before each benchmark session
3. **Allow cooling periods** between intensive tests
4. **Monitor temperatures** during extended runs
5. **Backup results** before rerunning benchmarks
6. **Use consistent configuration** across all tests

---

## Support and Troubleshooting

For issues or questions:
- Check connection with `test_connection()` methods
- Verify configuration in `config.yaml`
- Review logs in `data/benchmark.log`
- Ensure adequate system cooling
- Verify API keys in `.env` file

---

*Last updated: July 2026*
*Grant 2026 - University of Arkansas at Little Rock*
