# Setup Guide

## LLM Energy Analysis - Quick Start

This guide will walk you through setting up the complete benchmark system.

---

## Prerequisites

- **Operating System**: Windows 11 (Linux also supported)
- **Python**: Version 3.10 or higher
- **Hardware**: System with dedicated GPU (NVIDIA RTX 5060 Ti recommended)
- **Network**: Shelly Smart Plug on same network
- **Internet**: For cloud API testing

---

## Step 1: Install Python Dependencies

Open a terminal in the project directory and run:

```bash
pip install -r requirements.txt
```

This installs all required packages:
- Ollama Python client
- OpenAI and Anthropic API clients
- Data analysis libraries (pandas, numpy)
- Visualization libraries (matplotlib, seaborn)
- Flask for dashboard
- Supporting utilities

---

## Step 2: Install and Configure Ollama

### Install Ollama

1. Download from: https://ollama.ai
2. Run the installer
3. Verify installation:
   ```bash
   ollama --version
   ```

### Pull Models

Download the models you want to test:

```bash
ollama pull llama3
ollama pull mistral
```

**Recommended for RTX 5060 Ti (16GB VRAM)**:
- `llama3` (8B parameters)
- `mistral` (7B parameters)
- `llama3:70b` (if you want to test larger models, may run slower)

### Verify Ollama

```bash
ollama list
```

You should see your downloaded models listed.

---

## Step 3: Configure Shelly Smart Plug

### Find Your Plug's IP Address

1. Open the Shelly app on your phone
2. Find your smart plug
3. Note the IP address (e.g., 192.168.1.100)

### Test Connection

Open a web browser and navigate to:
```
http://YOUR_PLUG_IP/status
```

You should see JSON data with power readings.

### Update Configuration

Edit `config.yaml`:

```yaml
shelly:
  ip_address: "192.168.1.100"  # Replace with your plug's IP
```

---

## Step 4: Configure Cloud APIs (Optional)

### Get API Keys

**OpenAI**:
1. Go to: https://platform.openai.com/api-keys
2. Create a new API key
3. Copy the key (starts with `sk-`)

**Anthropic**:
1. Go to: https://console.anthropic.com/settings/keys
2. Create a new API key
3. Copy the key (starts with `sk-ant-`)

### Add Keys to Environment

1. Copy the example file:
   ```bash
   copy .env.example .env
   ```

2. Edit `.env` and add your keys:
   ```
   OPENAI_API_KEY=sk-your-openai-key-here
   ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here
   ```

3. Save the file

**Note**: Cloud APIs are optional. You can run local-only benchmarks without them.

---

## Step 5: Configure Models and Settings

Edit `config.yaml` to customize:

### Ollama Models

```yaml
ollama:
  models:
    - "llama3"
    - "mistral"
```

Add or remove models as needed.

### Cloud Models

```yaml
cloud:
  openai:
    enabled: true  # Set to false to disable
    models:
      - "gpt-4"
      - "gpt-3.5-turbo"
```

### Benchmark Settings

```yaml
benchmark:
  idle_baseline_duration: 60  # Seconds for baseline measurement
  warmup_queries: 3           # Warmup queries before measurement
  cooling_period: 30          # Seconds between tests
  repetitions: 3              # Times to repeat each prompt
```

Adjust based on your needs:
- **Quick test**: `repetitions: 1`, `cooling_period: 10`
- **Full research**: `repetitions: 3`, `cooling_period: 30`

---

## Step 6: Test Connections

Before running the full benchmark, test all connections:

```bash
python src/test_connection.py
```

This will verify:
- ✅ Shelly Smart Plug connection
- ✅ Ollama availability and models
- ✅ Cloud API authentication

Fix any issues before proceeding.

---

## Step 7: Run Your First Benchmark

### Option 1: Full Benchmark (Recommended)

```bash
python src/run_benchmark.py
```

This will:
1. Measure baseline power (60 seconds)
2. Run local LLM tests with power monitoring
3. Run cloud API tests
4. Save results to CSV files

**Duration**: 30-60 minutes depending on models and repetitions

### Option 2: Quick Test

1. Edit `config.yaml`:
   ```yaml
   benchmark:
     repetitions: 1
     cooling_period: 10
   ```

2. Reduce prompts (edit `data/prompts.json` to include only first 5 prompts)

3. Run: `python src/run_benchmark.py`

**Duration**: 10-15 minutes

---

## Step 8: Analyze Results

### View Analysis Summary

```bash
python src/analyze_results.py
```

This displays:
- Token statistics
- Energy consumption metrics
- Cost analysis (for cloud)
- Comparative analysis (local vs cloud)

### Generate Graphs

```bash
python src/generate_graphs.py
```

Creates publication-quality visualizations in `data/graphs/`:
- Energy comparison charts
- Cost analysis
- Performance metrics
- Privacy-energy tradeoff

---

## Common Issues and Solutions

### Issue: Ollama Connection Failed

**Solution**:
```bash
# Check if Ollama is running
ollama list

# Restart Ollama (Windows)
# Close Ollama from system tray and restart

# Verify port
netstat -an | findstr "11434"
```

### Issue: Shelly Plug Not Found

**Solution**:
1. Verify IP address in config.yaml
2. Ensure plug is on same network
3. Check firewall settings
4. Try ping: `ping YOUR_PLUG_IP`
5. Access via browser: `http://YOUR_PLUG_IP/status`

### Issue: Cloud API Authentication Failed

**Solution**:
1. Verify API keys in `.env` file
2. Check for extra spaces or quotes
3. Ensure keys are active (not revoked)
4. Check API credit balance
5. Review rate limits

### Issue: Out of Memory Error

**Solution**:
1. Use smaller models (8B instead of 70B)
2. Reduce max_tokens in config.yaml
3. Close other GPU-intensive applications
4. Check VRAM usage: `nvidia-smi`

### Issue: Thermal Throttling

**Solution**:
1. Improve system cooling
2. Increase cooling_period in config.yaml
3. Monitor temperatures during tests
4. Clean dust from fans/radiators

---

## Project Structure

```
Grant 2026/
├── README.md                   # Project overview
├── requirements.txt            # Python dependencies
├── config.yaml                 # Main configuration
├── .env                        # API keys (create from .env.example)
│
├── src/                        # Source code
│   ├── power_monitor.py       # Shelly plug integration
│   ├── local_llm_benchmark.py # Ollama benchmarks
│   ├── cloud_benchmark.py     # Cloud API benchmarks
│   ├── run_benchmark.py       # Main orchestrator
│   ├── analyze_results.py     # Data analysis
│   ├── generate_graphs.py     # Visualization
│   └── test_connection.py     # Connection testing
│
├── data/
│   ├── prompts.json           # Test prompts
│   ├── results/               # CSV output files
│   └── graphs/                # Generated visualizations
│
└── docs/
    ├── methodology.md         # Research methodology
    └── setup_guide.md         # This file
```

---

## Next Steps

1. **Customize Prompts**: Edit `data/prompts.json` for your specific use cases
2. **Adjust Models**: Add/remove models in `config.yaml`
3. **Run Experiments**: Execute benchmarks with different configurations
4. **Analyze Data**: Use the analysis and visualization tools
5. **Document Findings**: Create your grant report using the generated graphs

---

## Support

For issues or questions:
- Check the troubleshooting section above
- Review `docs/methodology.md` for detailed explanations
- Examine the code comments in `src/` files
- Test individual components with their standalone scripts

---

## Tips for Best Results

1. **Thermal Management**: Ensure adequate cooling before long benchmark runs
2. **Background Processes**: Close unnecessary applications during testing
3. **Power Stability**: Use a stable power source (avoid battery operation)
4. **Multiple Runs**: Run benchmarks multiple times for consistency
5. **Document Everything**: Take notes on any anomalies or special conditions
6. **Backup Data**: Keep copies of CSV results before rerunning tests

---

## Research Workflow

1. **Setup** → Test connections → Configure settings
2. **Baseline** → Measure idle power → Document conditions
3. **Local Tests** → Run warmups → Execute benchmarks → Cool down
4. **Cloud Tests** → Run parallel tests → Track costs
5. **Analysis** → Load data → Generate statistics → Create graphs
6. **Reporting** → Use graphs → Document methodology → Present findings

---

Good luck with your research! 🚀
