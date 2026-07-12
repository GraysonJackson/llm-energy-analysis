"""
Benchmark Orchestrator - Main Entry Point

This script orchestrates the complete benchmark process:
1. Measure baseline idle power
2. Run local LLM benchmarks with power monitoring
3. Run cloud API benchmarks
4. Save all results to CSV files
"""

import os
import sys
import json
import yaml
import logging
import time
from datetime import datetime
from pathlib import Path

# Import local modules
from power_monitor import PowerMonitor
from local_llm_benchmark import LocalLLMBenchmark
from cloud_benchmark import CloudBenchmark

# Configure logging
def setup_logging(config):
    """Setup logging configuration."""
    log_level = config.get('logging', {}).get('level', 'INFO')
    log_format = config.get('logging', {}).get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log_file = config.get('logging', {}).get('file', 'data/benchmark.log')
    
    # Create log directory if needed
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    
    # Configure logging to both file and console
    logging.basicConfig(
        level=getattr(logging, log_level),
        format=log_format,
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )

logger = logging.getLogger(__name__)


def load_config(config_path='config.yaml'):
    """Load configuration from YAML file."""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        logger.info(f"Configuration loaded from {config_path}")
        return config
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)


def load_prompts(prompts_path='data/prompts.json'):
    """Load test prompts from JSON file."""
    try:
        with open(prompts_path, 'r') as f:
            data = json.load(f)
        prompts = data.get('prompts', [])
        logger.info(f"Loaded {len(prompts)} prompts from {prompts_path}")
        return prompts
    except Exception as e:
        logger.error(f"Failed to load prompts: {e}")
        sys.exit(1)


def create_output_dirs(config):
    """Create output directories for results and graphs."""
    results_dir = config.get('output', {}).get('results_dir', 'data/results')
    graphs_dir = config.get('output', {}).get('graphs_dir', 'data/graphs')
    
    Path(results_dir).mkdir(parents=True, exist_ok=True)
    Path(graphs_dir).mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Output directories created: {results_dir}, {graphs_dir}")


def generate_timestamp(config):
    """Generate timestamp string for file naming."""
    fmt = config.get('output', {}).get('timestamp_format', '%Y%m%d_%H%M%S')
    return datetime.now().strftime(fmt)


def run_baseline_measurement(power_monitor, config):
    """Measure baseline idle power consumption."""
    logger.info("=" * 60)
    logger.info("PHASE 1: BASELINE MEASUREMENT")
    logger.info("=" * 60)
    
    duration = config.get('benchmark', {}).get('idle_baseline_duration', 60)
    
    print(f"\n📊 Measuring baseline idle power for {duration} seconds...")
    print("Please ensure no heavy workloads are running.\n")
    
    baseline_stats = power_monitor.measure_baseline(duration)
    
    print(f"\n✅ Baseline measurement complete!")
    print(f"   Average Power: {baseline_stats['avg_power_w']:.2f} W")
    print(f"   Min: {baseline_stats['min_power_w']:.2f} W, Max: {baseline_stats['max_power_w']:.2f} W")
    
    # Save baseline data
    timestamp = generate_timestamp(config)
    results_dir = config.get('output', {}).get('results_dir', 'data/results')
    baseline_file = os.path.join(results_dir, f'baseline_{timestamp}.csv')
    power_monitor.export_to_csv(baseline_file)
    
    logger.info(f"Baseline data saved to {baseline_file}")
    
    return baseline_stats


def run_local_benchmarks(local_benchmark, power_monitor, prompts, config):
    """Run local LLM benchmarks with power monitoring."""
    logger.info("=" * 60)
    logger.info("PHASE 2: LOCAL LLM BENCHMARKS")
    logger.info("=" * 60)
    
    models = config.get('ollama', {}).get('models', [])
    warmup_count = config.get('benchmark', {}).get('warmup_queries', 3)
    cooling_period = config.get('benchmark', {}).get('cooling_period', 30)
    repetitions = config.get('benchmark', {}).get('repetitions', 1)
    
    if not models:
        logger.warning("No Ollama models configured, skipping local benchmarks")
        return []
    
    all_results = []
    
    for model in models:
        print(f"\n🤖 Benchmarking local model: {model}")
        print(f"   {len(prompts)} prompts × {repetitions} repetitions = {len(prompts) * repetitions} tests")
        
        # Warmup
        print(f"\n🔥 Running {warmup_count} warmup queries...")
        local_benchmark.run_warmup(model, warmup_count)
        
        print(f"\n⏳ Cooling for {cooling_period} seconds before measurement...")
        time.sleep(cooling_period)
        
        # Run benchmarks
        print(f"\n▶️  Starting benchmark measurements...")
        results = local_benchmark.benchmark_model(
            model=model,
            prompts=prompts,
            power_monitor=power_monitor,
            cooling_period=cooling_period,
            repetitions=repetitions
        )
        
        all_results.extend(results)
        
        print(f"\n✅ Model {model} complete: {len(results)} results")
    
    # Save results
    timestamp = generate_timestamp(config)
    results_dir = config.get('output', {}).get('results_dir', 'data/results')
    output_file = os.path.join(results_dir, f'local_benchmark_{timestamp}.csv')
    local_benchmark.export_to_csv(all_results, output_file)
    
    logger.info(f"Local benchmark results saved to {output_file}")
    
    return all_results


def run_cloud_benchmarks(cloud_benchmark, prompts, config):
    """Run cloud API benchmarks."""
    logger.info("=" * 60)
    logger.info("PHASE 3: CLOUD API BENCHMARKS")
    logger.info("=" * 60)
    
    repetitions = config.get('benchmark', {}).get('repetitions', 1)
    
    # Test connections first
    print("\n☁️  Testing cloud API connections...")
    status = cloud_benchmark.test_connections()
    
    if not any(status.values()):
        logger.warning("No cloud APIs available, skipping cloud benchmarks")
        print("⚠️  No cloud APIs connected. Skipping cloud benchmarks.")
        return []
    
    for provider, connected in status.items():
        if connected:
            print(f"   ✅ {provider}: Connected")
        else:
            print(f"   ❌ {provider}: Not available")
    
    # Run benchmarks
    print(f"\n▶️  Running cloud benchmarks ({len(prompts)} prompts × {repetitions} repetitions)...")
    results = cloud_benchmark.benchmark_providers(prompts, repetitions)
    
    # Save results
    timestamp = generate_timestamp(config)
    results_dir = config.get('output', {}).get('results_dir', 'data/results')
    output_file = os.path.join(results_dir, f'cloud_benchmark_{timestamp}.csv')
    cloud_benchmark.export_to_csv(results, output_file)
    
    logger.info(f"Cloud benchmark results saved to {output_file}")
    
    print(f"\n✅ Cloud benchmarks complete: {len(results)} results")
    
    return results


def print_summary(baseline_stats, local_results, cloud_results):
    """Print summary of benchmark results."""
    print("\n" + "=" * 60)
    print("BENCHMARK SUMMARY")
    print("=" * 60)
    
    # Baseline
    print(f"\n📊 Baseline:")
    print(f"   Idle Power: {baseline_stats.get('avg_power_w', 0):.2f} W")
    
    # Local benchmarks
    print(f"\n🤖 Local LLM Benchmarks:")
    print(f"   Total Tests: {len(local_results)}")
    
    if local_results:
        successful = [r for r in local_results if r.get('success')]
        print(f"   Successful: {len(successful)}")
        
        if successful:
            total_tokens = sum(r.get('total_tokens', 0) for r in successful)
            total_energy = sum(r.get('energy_joules', 0) for r in successful)
            avg_joules_per_token = total_energy / total_tokens if total_tokens > 0 else 0
            
            print(f"   Total Tokens: {total_tokens:,}")
            print(f"   Total Energy: {total_energy:.2f} J ({total_energy/3600:.4f} Wh)")
            print(f"   Avg J/token: {avg_joules_per_token:.4f}")
    
    # Cloud benchmarks
    print(f"\n☁️  Cloud API Benchmarks:")
    print(f"   Total Tests: {len(cloud_results)}")
    
    if cloud_results:
        successful = [r for r in cloud_results if r.get('success')]
        print(f"   Successful: {len(successful)}")
        
        if successful:
            total_tokens = sum(r.get('total_tokens', 0) for r in successful)
            total_cost = sum(r.get('cost_usd', 0) for r in successful)
            total_energy = sum(r.get('estimated_energy_joules', 0) for r in successful)
            
            print(f"   Total Tokens: {total_tokens:,}")
            print(f"   Total Cost: ${total_cost:.2f}")
            print(f"   Est. Energy: {total_energy:.2f} J ({total_energy/3600:.4f} Wh)")
    
    print("\n" + "=" * 60)


def main():
    """Main benchmark orchestration."""
    print("\n" + "=" * 60)
    print("LLM ENERGY ANALYSIS - BENCHMARK SUITE")
    print("Grant 2026 - Grayson Jackson")
    print("=" * 60)
    
    # Load configuration
    config = load_config()
    setup_logging(config)
    
    logger.info("Benchmark suite started")
    
    # Create output directories
    create_output_dirs(config)
    
    # Load prompts
    prompts = load_prompts()
    
    # Initialize components
    print("\n🔧 Initializing components...")
    
    # Power monitor
    shelly_config = config.get('shelly', {})
    power_monitor = PowerMonitor(
        ip_address=shelly_config.get('ip_address', '192.168.1.100'),
        polling_interval=shelly_config.get('polling_interval', 1.0),
        timeout=shelly_config.get('timeout', 5)
    )
    
    # Test Shelly connection
    print("\n🔌 Testing Shelly Smart Plug connection...")
    if not power_monitor.test_connection():
        print("❌ Failed to connect to Shelly plug!")
        print(f"   Check IP address: {shelly_config.get('ip_address')}")
        response = input("\nContinue without power monitoring? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
        power_monitor = None
    else:
        print("✅ Shelly plug connected")
    
    # Local LLM benchmark
    ollama_config = config.get('ollama', {})
    local_benchmark = LocalLLMBenchmark(
        host=ollama_config.get('host', 'http://localhost:11434'),
        temperature=ollama_config.get('temperature', 0.7),
        top_p=ollama_config.get('top_p', 0.9),
        timeout=ollama_config.get('timeout', 300)
    )
    
    # Test Ollama connection
    print("\n🤖 Testing Ollama connection...")
    if not local_benchmark.test_connection():
        print("❌ Failed to connect to Ollama!")
        print("   Make sure Ollama is running: ollama list")
        local_benchmark = None
    else:
        models = local_benchmark.list_models()
        print(f"✅ Ollama connected ({len(models)} models available)")
    
    # Cloud benchmark
    cloud_benchmark = CloudBenchmark(config)
    
    print("\n✅ All components initialized")
    
    # Run benchmarks
    try:
        # Baseline measurement
        baseline_stats = {}
        if power_monitor:
            baseline_stats = run_baseline_measurement(power_monitor, config)
        else:
            logger.warning("Skipping baseline measurement (no power monitor)")
        
        # Local benchmarks
        local_results = []
        if local_benchmark:
            local_results = run_local_benchmarks(local_benchmark, power_monitor, prompts, config)
        else:
            logger.warning("Skipping local benchmarks (Ollama not available)")
        
        # Cloud benchmarks
        cloud_results = run_cloud_benchmarks(cloud_benchmark, prompts, config)
        
        # Print summary
        print_summary(baseline_stats, local_results, cloud_results)
        
        print("\n✅ Benchmark suite complete!")
        print(f"\nResults saved to: {config.get('output', {}).get('results_dir', 'data/results')}")
        print("\nNext steps:")
        print("  1. Run analysis: python src/analyze_results.py")
        print("  2. Generate graphs: python src/generate_graphs.py")
        print("  3. View dashboard: python src/dashboard.py")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Benchmark interrupted by user")
        logger.warning("Benchmark interrupted by user")
    
    except Exception as e:
        print(f"\n\n❌ Error during benchmark: {e}")
        logger.error(f"Benchmark failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
