"""
Connection Test Utility

Quick utility to test all system connections before running full benchmarks.
Tests: Shelly Smart Plug, Ollama, and Cloud APIs
"""

import sys
import yaml
from power_monitor import PowerMonitor
from local_llm_benchmark import LocalLLMBenchmark
from cloud_benchmark import CloudBenchmark


def test_shelly(config):
    """Test Shelly Smart Plug connection."""
    print("\n" + "="*60)
    print("TESTING SHELLY SMART PLUG")
    print("="*60)
    
    shelly_config = config.get('shelly', {})
    ip_address = shelly_config.get('ip_address', '192.168.1.100')
    
    print(f"\nConnecting to: {ip_address}")
    
    monitor = PowerMonitor(
        ip_address=ip_address,
        polling_interval=shelly_config.get('polling_interval', 1.0),
        timeout=shelly_config.get('timeout', 5)
    )
    
    if monitor.test_connection():
        power = monitor.get_current_power()
        if power is not None:
            print(f"✅ Connected successfully!")
            print(f"   Current power: {power:.2f} W")
            return True
        else:
            print("⚠️  Connected but failed to read power")
            return False
    else:
        print("❌ Connection failed!")
        print("\nTroubleshooting:")
        print(f"  1. Check IP address in config.yaml: {ip_address}")
        print("  2. Ensure plug is on same network")
        print("  3. Try accessing http://" + ip_address + "/status in browser")
        return False


def test_ollama(config):
    """Test Ollama connection."""
    print("\n" + "="*60)
    print("TESTING OLLAMA")
    print("="*60)
    
    ollama_config = config.get('ollama', {})
    host = ollama_config.get('host', 'http://localhost:11434')
    
    print(f"\nConnecting to: {host}")
    
    benchmark = LocalLLMBenchmark(
        host=host,
        temperature=ollama_config.get('temperature', 0.7),
        top_p=ollama_config.get('top_p', 0.9)
    )
    
    if benchmark.test_connection():
        models = benchmark.list_models()
        print(f"✅ Connected successfully!")
        print(f"   Available models: {len(models)}")
        for model in models:
            print(f"     - {model}")
        return True
    else:
        print("❌ Connection failed!")
        print("\nTroubleshooting:")
        print("  1. Install Ollama: https://ollama.ai")
        print("  2. Start Ollama service")
        print("  3. Pull models: ollama pull llama3")
        print("  4. Check status: ollama list")
        return False


def test_cloud_apis(config):
    """Test cloud API connections."""
    print("\n" + "="*60)
    print("TESTING CLOUD APIs")
    print("="*60)
    
    cloud_benchmark = CloudBenchmark(config)
    
    # Check if any APIs are configured
    openai_enabled = config.get('cloud', {}).get('openai', {}).get('enabled', False)
    anthropic_enabled = config.get('cloud', {}).get('anthropic', {}).get('enabled', False)
    
    if not openai_enabled and not anthropic_enabled:
        print("\n⚠️  No cloud APIs enabled in config.yaml")
        return False
    
    print("\nTesting connections...")
    status = cloud_benchmark.test_connections()
    
    success = False
    for provider, connected in status.items():
        if connected:
            print(f"  ✅ {provider}: Connected")
            success = True
        else:
            print(f"  ❌ {provider}: Failed")
    
    if not success:
        print("\nTroubleshooting:")
        print("  1. Copy .env.example to .env")
        print("  2. Add your API keys:")
        print("     - OPENAI_API_KEY=your-key-here")
        print("     - ANTHROPIC_API_KEY=your-key-here")
        print("  3. Enable APIs in config.yaml")
    
    return success


def main():
    """Main test function."""
    print("\n" + "="*60)
    print("SYSTEM CONNECTION TEST")
    print("LLM Energy Analysis - Grant 2026")
    print("="*60)
    
    # Load config
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"\n❌ Failed to load config.yaml: {e}")
        sys.exit(1)
    
    # Run tests
    results = {
        'shelly': test_shelly(config),
        'ollama': test_ollama(config),
        'cloud': test_cloud_apis(config)
    }
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for component, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {component.upper()}: {status}")
    
    all_pass = all(results.values())
    
    if all_pass:
        print("\n✅ All systems operational!")
        print("\nYou can now run benchmarks:")
        print("  python src/run_benchmark.py")
    else:
        print("\n⚠️  Some systems need attention.")
        print("Fix the issues above before running benchmarks.")
    
    print("\n" + "="*60)
    
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
