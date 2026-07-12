# LLM Energy Analysis - Grant 2026 Research Project

## Project Overview

This project quantifies the operational energy cost of data sovereignty by comparing the energy efficiency of local LLM inference against cloud-based APIs. The goal is to provide a data-driven analysis of the trade-offs between strict data privacy and energy consumption.

## Research Question

**What is the measurable energy cost of maintaining data sovereignty through local LLM inference compared to cloud-based solutions?**

## System Requirements

### Hardware
- NVIDIA RTX 5060 Ti (16GB VRAM)
- AMD Ryzen 9 5900XT CPU
- Shelly Smart Plug (WiFi/Bluetooth) for power metering
- Adequate cooling (liquid CPU cooler, case fans)

### Software
- Python 3.10 or higher
- Ollama (for local LLM inference)
- Windows 11 / Linux

## Installation

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Ollama

Download and install Ollama from: https://ollama.ai

Pull the models you want to test:
```bash
ollama pull llama3
ollama pull llama3:70b
ollama pull mistral
```

### 3. Configure the System

Copy the example configuration:
```bash
copy .env.example .env
```

Edit `config.yaml` and `.env` with your settings:
- Shelly Smart Plug IP address
- OpenAI API key
- Anthropic API key
- Model preferences
- Test parameters

### 4. Verify Shelly Plug Connection

```bash
python src/test_connection.py
```

## Quick Start

### Run a Complete Benchmark

```bash
python src/run_benchmark.py
```

This will:
1. Measure idle power baseline
2. Run standardized prompts through local Ollama models
3. Run identical prompts through cloud APIs
4. Save all results to CSV files in `data/results/`

### Analyze Results

```bash
python src/analyze_results.py
```

### Generate Graphs

```bash
python src/generate_graphs.py
```

### Launch Dashboard

```bash
python src/dashboard.py
```

Then open your browser to `http://localhost:5000`

## Project Structure

```
grant-2026-llm-energy-analysis/
├── README.md                      # This file
├── requirements.txt               # Python dependencies
├── config.yaml                    # Main configuration
├── .env.example                   # API keys template
│
├── src/
│   ├── power_monitor.py          # Shelly Smart Plug integration
│   ├── local_llm_benchmark.py    # Ollama benchmark suite
│   ├── cloud_benchmark.py        # Cloud API benchmark suite
│   ├── run_benchmark.py          # Main orchestrator
│   ├── analyze_results.py        # Data analysis
│   ├── generate_graphs.py        # Visualization
│   ├── dashboard.py              # Real-time monitoring
│   └── test_connection.py        # Connection testing utility
│
├── data/
│   ├── prompts.json              # Standardized test prompts
│   ├── results/                  # CSV output files
│   └── graphs/                   # Generated visualizations
│
├── docs/
│   ├── methodology.md            # Research methodology
│   ├── setup_guide.md            # Detailed setup instructions
│   └── api_documentation.md      # API reference
│
└── reports/
    └── generate_report.py        # Grant report generator
```

## Data Files

### Results CSVs
- `local_benchmark_YYYYMMDD_HHMMSS.csv` - Local inference results
- `cloud_benchmark_YYYYMMDD_HHMMSS.csv` - Cloud API results
- `power_log_YYYYMMDD_HHMMSS.csv` - Detailed power measurements

### CSV Format

**Local Benchmark:**
```
timestamp,model,prompt_id,prompt_category,input_tokens,output_tokens,total_tokens,generation_time_sec,tokens_per_sec,power_start_w,power_end_w,power_avg_w,energy_joules,joules_per_token,temperature_c
```

**Cloud Benchmark:**
```
timestamp,provider,model,prompt_id,prompt_category,input_tokens,output_tokens,total_tokens,response_time_sec,cost_usd,estimated_energy_joules,joules_per_token
```

## Key Metrics

### Local Inference
- **Joules per token**: Total energy consumed / tokens generated
- **Average power draw**: Watts during active generation
- **Tokens per second**: Generation speed
- **Idle baseline**: Background power consumption

### Cloud APIs
- **Cost per token**: USD spent per token
- **Attributed energy**: Based on provider sustainability reports
- **Response latency**: Time to first/last token
- **Data center PUE**: Power Usage Effectiveness overhead

## Methodology

1. **Baseline Measurement**: Record idle system power for 60 seconds
2. **Thermal Stabilization**: Run warm-up queries to reach steady-state temperature
3. **Controlled Testing**: Execute standardized prompts with 30-second cooling periods
4. **Data Collection**: Log power readings at 1-second intervals
5. **Cloud Comparison**: Run identical prompts through cloud APIs
6. **Analysis**: Calculate energy per token and compare local vs cloud

## Research Applications

This data supports:
- Energy efficiency analysis for on-premise AI deployment
- Privacy cost quantification (energy trade-off for data sovereignty)
- Carbon footprint comparison (local hardware vs data centers)
- Infrastructure planning for secure AI workloads
- Grant reporting and academic publication

## Safety Notes

- Monitor system temperatures during extended testing
- Ensure adequate cooling before running benchmarks
- The Shelly plug measures total system power (not just GPU)
- Allow cooling periods between intensive tests
- Back up data regularly

## Troubleshooting

### Shelly Plug Not Connecting
- Verify IP address in `config.yaml`
- Ensure plug is on the same network
- Check firewall settings
- Try accessing `http://<PLUG_IP>/status` in a browser

### Ollama Connection Failed
- Verify Ollama is running: `ollama list`
- Check default port (11434)
- Restart Ollama service if needed

### Cloud API Errors
- Verify API keys in `.env`
- Check rate limits
- Ensure sufficient API credits

## Contributing

This is a research project for the Grayson Jackson Signature Grant 2026. For questions or collaboration, contact the researcher.

## License

This project is for academic research purposes.

## Acknowledgments

- University of Arkansas at Little Rock
- Signature Experience Grant Program
- Open source communities (Ollama, Python ecosystem)
