"""
Local LLM Benchmark Module - Ollama Integration

This module handles benchmarking of locally-hosted LLMs through Ollama.
Measures token generation, timing, and integrates with power monitoring.
"""

import ollama
import time
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class LocalLLMBenchmark:
    """
    Benchmark suite for local LLM inference via Ollama.
    
    Features:
    - Token counting and timing
    - Multiple model support
    - Power consumption integration
    - Standardized prompt execution
    """
    
    def __init__(self, host: str = "http://localhost:11434", 
                 temperature: float = 0.7, 
                 top_p: float = 0.9,
                 timeout: int = 300):
        """
        Initialize the local LLM benchmark.
        
        Args:
            host: Ollama server URL
            temperature: Sampling temperature (0-1)
            top_p: Top-p sampling parameter
            timeout: Maximum generation time in seconds
        """
        self.host = host
        self.temperature = temperature
        self.top_p = top_p
        self.timeout = timeout
        
        # Set Ollama host
        ollama.Client(host=host)
        
        logger.info(f"LocalLLMBenchmark initialized with host: {host}")
    
    def test_connection(self) -> bool:
        """
        Test connection to Ollama server.
        
        Returns:
            True if Ollama is available, False otherwise
        """
        try:
            models = ollama.list()
            logger.info(f"Ollama connection successful. Available models: {len(models['models'])}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            return False
    
    def list_models(self) -> List[str]:
        """
        List all available models in Ollama.
        
        Returns:
            List of model names
        """
        try:
            response = ollama.list()
            models = [model['name'] for model in response['models']]
            return models
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []
    
    def count_tokens(self, text: str, model: str) -> int:
        """
        Count tokens in text for a specific model.
        
        Args:
            text: Text to tokenize
            model: Model name for tokenization
            
        Returns:
            Number of tokens
        """
        # Rough estimation: ~4 characters per token for English text
        # For more accurate counting, we'd need model-specific tokenizers
        # This is a simplified approximation
        return len(text) // 4
    
    def generate(self, 
                 model: str, 
                 prompt: str, 
                 max_tokens: int = 1000) -> Dict:
        """
        Generate a response from the local LLM.
        
        Args:
            model: Model name (e.g., 'llama3', 'mistral')
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            
        Returns:
            Dict containing response and metadata
        """
        logger.info(f"Generating with model {model}...")
        
        start_time = time.time()
        
        try:
            # Generate response with streaming to track tokens
            full_response = ""
            token_count = 0
            first_token_time = None
            
            stream = ollama.generate(
                model=model,
                prompt=prompt,
                options={
                    'temperature': self.temperature,
                    'top_p': self.top_p,
                    'num_predict': max_tokens
                },
                stream=True
            )
            
            for chunk in stream:
                if 'response' in chunk:
                    if first_token_time is None:
                        first_token_time = time.time()
                    
                    full_response += chunk['response']
                    token_count += 1
                
                # Check timeout
                if time.time() - start_time > self.timeout:
                    logger.warning(f"Generation timeout after {self.timeout}s")
                    break
            
            end_time = time.time()
            
            # Calculate metrics
            generation_time = end_time - start_time
            time_to_first_token = first_token_time - start_time if first_token_time else 0
            
            # Estimate input/output tokens
            input_tokens = self.count_tokens(prompt, model)
            output_tokens = self.count_tokens(full_response, model)
            total_tokens = input_tokens + output_tokens
            
            tokens_per_sec = output_tokens / generation_time if generation_time > 0 else 0
            
            result = {
                'model': model,
                'prompt': prompt,
                'response': full_response,
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'total_tokens': total_tokens,
                'generation_time_sec': generation_time,
                'time_to_first_token_sec': time_to_first_token,
                'tokens_per_sec': tokens_per_sec,
                'timestamp': datetime.now().isoformat(),
                'success': True
            }
            
            logger.info(f"Generated {output_tokens} tokens in {generation_time:.2f}s ({tokens_per_sec:.2f} tok/s)")
            return result
        
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return {
                'model': model,
                'prompt': prompt,
                'error': str(e),
                'success': False,
                'timestamp': datetime.now().isoformat()
            }
    
    def benchmark_prompt(self, 
                        model: str, 
                        prompt_data: Dict,
                        power_monitor=None) -> Dict:
        """
        Benchmark a single prompt with power monitoring.
        
        Args:
            model: Model name
            prompt_data: Dict with 'id', 'category', 'prompt' keys
            power_monitor: Optional PowerMonitor instance
            
        Returns:
            Dict with benchmark results including power data
        """
        prompt_id = prompt_data.get('id', 'unknown')
        category = prompt_data.get('category', 'unknown')
        prompt = prompt_data.get('prompt', '')
        
        logger.info(f"Benchmarking prompt {prompt_id} ({category}) with {model}")
        
        # Start power monitoring if available
        if power_monitor:
            power_monitor.start_monitoring()
            power_start = power_monitor.get_current_power()
        else:
            power_start = None
        
        # Generate response
        result = self.generate(model, prompt)
        
        # Stop power monitoring
        if power_monitor:
            power_stats = power_monitor.stop_monitoring()
            power_end = power_monitor.get_current_power()
            
            result['power_start_w'] = power_start
            result['power_end_w'] = power_end
            result['power_avg_w'] = power_stats.get('avg_power_w', 0)
            result['energy_joules'] = power_stats.get('energy_joules', 0)
            
            # Calculate joules per token
            if result.get('total_tokens', 0) > 0:
                result['joules_per_token'] = result['energy_joules'] / result['total_tokens']
            else:
                result['joules_per_token'] = 0
        
        # Add prompt metadata
        result['prompt_id'] = prompt_id
        result['prompt_category'] = category
        
        return result
    
    def run_warmup(self, model: str, count: int = 3):
        """
        Run warmup queries to stabilize model loading and temperature.
        
        Args:
            model: Model name
            count: Number of warmup queries
        """
        logger.info(f"Running {count} warmup queries for {model}...")
        
        warmup_prompt = "Say 'ready' and nothing else."
        
        for i in range(count):
            logger.info(f"Warmup {i+1}/{count}")
            result = self.generate(model, warmup_prompt, max_tokens=10)
            
            if not result.get('success'):
                logger.warning(f"Warmup {i+1} failed")
            
            # Small delay between warmups
            time.sleep(2)
        
        logger.info("Warmup complete")
    
    def benchmark_model(self, 
                       model: str, 
                       prompts: List[Dict],
                       power_monitor=None,
                       cooling_period: int = 30,
                       repetitions: int = 1) -> List[Dict]:
        """
        Benchmark a model with multiple prompts.
        
        Args:
            model: Model name
            prompts: List of prompt dicts
            power_monitor: Optional PowerMonitor instance
            cooling_period: Seconds to wait between tests
            repetitions: Number of times to repeat each prompt
            
        Returns:
            List of benchmark results
        """
        logger.info(f"Benchmarking {model} with {len(prompts)} prompts (x{repetitions} repetitions)")
        
        results = []
        
        for rep in range(repetitions):
            logger.info(f"Repetition {rep+1}/{repetitions}")
            
            for i, prompt_data in enumerate(prompts):
                logger.info(f"Prompt {i+1}/{len(prompts)}")
                
                # Run benchmark
                result = self.benchmark_prompt(model, prompt_data, power_monitor)
                result['repetition'] = rep + 1
                results.append(result)
                
                # Cooling period (except after last prompt)
                if i < len(prompts) - 1 or rep < repetitions - 1:
                    logger.info(f"Cooling for {cooling_period}s...")
                    time.sleep(cooling_period)
        
        logger.info(f"Benchmark complete. {len(results)} results collected.")
        return results
    
    def export_to_csv(self, results: List[Dict], filepath: str):
        """
        Export benchmark results to CSV.
        
        Args:
            results: List of benchmark result dicts
            filepath: Output CSV file path
        """
        import csv
        
        if not results:
            logger.warning("No results to export")
            return
        
        # Define CSV columns
        fieldnames = [
            'timestamp', 'model', 'prompt_id', 'prompt_category', 'repetition',
            'input_tokens', 'output_tokens', 'total_tokens',
            'generation_time_sec', 'time_to_first_token_sec', 'tokens_per_sec',
            'power_start_w', 'power_end_w', 'power_avg_w',
            'energy_joules', 'joules_per_token',
            'success'
        ]
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(results)
        
        logger.info(f"Exported {len(results)} results to {filepath}")


def main():
    """Test the local LLM benchmark functionality."""
    import sys
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create benchmark
    benchmark = LocalLLMBenchmark()
    
    # Test connection
    print("\nTesting Ollama connection...")
    if not benchmark.test_connection():
        print("❌ Failed to connect to Ollama!")
        print("\nTroubleshooting:")
        print("1. Make sure Ollama is installed: https://ollama.ai")
        print("2. Check that Ollama is running: ollama list")
        print("3. Verify the default port (11434) is accessible")
        sys.exit(1)
    
    print("✅ Connected to Ollama!")
    
    # List models
    models = benchmark.list_models()
    print(f"\nAvailable models: {', '.join(models) if models else 'None'}")
    
    if not models:
        print("\n⚠️  No models found!")
        print("Pull a model with: ollama pull llama3")
        sys.exit(0)
    
    # Test generation with first available model
    test_model = models[0]
    print(f"\nTesting generation with {test_model}...")
    
    test_prompt = "Write a haiku about computers."
    result = benchmark.generate(test_model, test_prompt, max_tokens=100)
    
    if result.get('success'):
        print(f"\n✅ Generation successful!")
        print(f"Response: {result['response']}")
        print(f"\nMetrics:")
        print(f"  Tokens: {result['total_tokens']} ({result['input_tokens']} in, {result['output_tokens']} out)")
        print(f"  Time: {result['generation_time_sec']:.2f}s")
        print(f"  Speed: {result['tokens_per_sec']:.2f} tokens/sec")
    else:
        print(f"❌ Generation failed: {result.get('error')}")
    
    print("\n✅ Local LLM benchmark test complete!")


if __name__ == "__main__":
    main()
