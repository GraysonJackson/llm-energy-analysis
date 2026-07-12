"""
Cloud API Benchmark Module

This module handles benchmarking of cloud-based LLM APIs (OpenAI, Anthropic).
Tracks token usage, costs, and estimates energy consumption based on provider data.
"""

import time
import logging
import os
from typing import Dict, List, Optional
from datetime import datetime
from dotenv import load_dotenv

# Import API clients
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class CloudBenchmark:
    """
    Benchmark suite for cloud-based LLM APIs.
    
    Features:
    - OpenAI and Anthropic API support
    - Token usage and cost tracking
    - Energy attribution based on provider reports
    - Response time measurement
    """
    
    def __init__(self, config: Dict):
        """
        Initialize cloud benchmark with configuration.
        
        Args:
            config: Configuration dict with API settings and energy attribution
        """
        self.config = config
        
        # Initialize API clients
        self.openai_client = None
        self.anthropic_client = None
        
        if OpenAI and config.get('cloud', {}).get('openai', {}).get('enabled', False):
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                self.openai_client = OpenAI(api_key=api_key)
                logger.info("OpenAI client initialized")
            else:
                logger.warning("OpenAI enabled but no API key found")
        
        if Anthropic and config.get('cloud', {}).get('anthropic', {}).get('enabled', False):
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if api_key:
                self.anthropic_client = Anthropic(api_key=api_key)
                logger.info("Anthropic client initialized")
            else:
                logger.warning("Anthropic enabled but no API key found")
    
    def test_connections(self) -> Dict[str, bool]:
        """
        Test connections to all enabled cloud APIs.
        
        Returns:
            Dict mapping provider name to connection status
        """
        status = {}
        
        # Test OpenAI
        if self.openai_client:
            try:
                # Simple API test
                response = self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": "Hi"}],
                    max_tokens=5
                )
                status['openai'] = True
                logger.info("OpenAI connection successful")
            except Exception as e:
                status['openai'] = False
                logger.error(f"OpenAI connection failed: {e}")
        
        # Test Anthropic
        if self.anthropic_client:
            try:
                response = self.anthropic_client.messages.create(
                    model="claude-3-sonnet-20240229",
                    max_tokens=5,
                    messages=[{"role": "user", "content": "Hi"}]
                )
                status['anthropic'] = True
                logger.info("Anthropic connection successful")
            except Exception as e:
                status['anthropic'] = False
                logger.error(f"Anthropic connection failed: {e}")
        
        return status
    
    def generate_openai(self, 
                       model: str, 
                       prompt: str, 
                       max_tokens: int = 1000,
                       temperature: float = 0.7) -> Dict:
        """
        Generate response using OpenAI API.
        
        Args:
            model: Model name (e.g., 'gpt-4', 'gpt-3.5-turbo')
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            
        Returns:
            Dict with response and metadata
        """
        if not self.openai_client:
            return {
                'success': False,
                'error': 'OpenAI client not initialized'
            }
        
        logger.info(f"Generating with OpenAI {model}...")
        start_time = time.time()
        
        try:
            response = self.openai_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            end_time = time.time()
            
            # Extract data
            content = response.choices[0].message.content
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            total_tokens = response.usage.total_tokens
            
            # Calculate cost (approximate rates as of 2024)
            cost_per_1k = self._get_openai_cost(model)
            cost_usd = (total_tokens / 1000) * cost_per_1k
            
            # Get energy attribution
            energy_per_token = self._get_energy_per_token('openai', model)
            estimated_energy = total_tokens * energy_per_token
            
            result = {
                'provider': 'openai',
                'model': model,
                'prompt': prompt,
                'response': content,
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'total_tokens': total_tokens,
                'response_time_sec': end_time - start_time,
                'cost_usd': cost_usd,
                'estimated_energy_joules': estimated_energy,
                'joules_per_token': energy_per_token,
                'timestamp': datetime.now().isoformat(),
                'success': True
            }
            
            logger.info(f"Generated {total_tokens} tokens in {result['response_time_sec']:.2f}s (${cost_usd:.4f})")
            return result
        
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            return {
                'provider': 'openai',
                'model': model,
                'prompt': prompt,
                'error': str(e),
                'success': False,
                'timestamp': datetime.now().isoformat()
            }
    
    def generate_anthropic(self, 
                          model: str, 
                          prompt: str, 
                          max_tokens: int = 1000,
                          temperature: float = 0.7) -> Dict:
        """
        Generate response using Anthropic API.
        
        Args:
            model: Model name (e.g., 'claude-3-opus-20240229')
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            
        Returns:
            Dict with response and metadata
        """
        if not self.anthropic_client:
            return {
                'success': False,
                'error': 'Anthropic client not initialized'
            }
        
        logger.info(f"Generating with Anthropic {model}...")
        start_time = time.time()
        
        try:
            response = self.anthropic_client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}]
            )
            
            end_time = time.time()
            
            # Extract data
            content = response.content[0].text
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            total_tokens = input_tokens + output_tokens
            
            # Calculate cost
            cost_per_1k = self._get_anthropic_cost(model)
            cost_usd = (total_tokens / 1000) * cost_per_1k
            
            # Get energy attribution
            energy_per_token = self._get_energy_per_token('anthropic', model)
            estimated_energy = total_tokens * energy_per_token
            
            result = {
                'provider': 'anthropic',
                'model': model,
                'prompt': prompt,
                'response': content,
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'total_tokens': total_tokens,
                'response_time_sec': end_time - start_time,
                'cost_usd': cost_usd,
                'estimated_energy_joules': estimated_energy,
                'joules_per_token': energy_per_token,
                'timestamp': datetime.now().isoformat(),
                'success': True
            }
            
            logger.info(f"Generated {total_tokens} tokens in {result['response_time_sec']:.2f}s (${cost_usd:.4f})")
            return result
        
        except Exception as e:
            logger.error(f"Anthropic generation failed: {e}")
            return {
                'provider': 'anthropic',
                'model': model,
                'prompt': prompt,
                'error': str(e),
                'success': False,
                'timestamp': datetime.now().isoformat()
            }
    
    def benchmark_prompt(self, 
                        provider: str,
                        model: str,
                        prompt_data: Dict) -> Dict:
        """
        Benchmark a single prompt with a cloud provider.
        
        Args:
            provider: 'openai' or 'anthropic'
            model: Model name
            prompt_data: Dict with 'id', 'category', 'prompt' keys
            
        Returns:
            Dict with benchmark results
        """
        prompt_id = prompt_data.get('id', 'unknown')
        category = prompt_data.get('category', 'unknown')
        prompt = prompt_data.get('prompt', '')
        
        logger.info(f"Benchmarking prompt {prompt_id} ({category}) with {provider}/{model}")
        
        # Get max_tokens from config
        max_tokens = self.config.get('cloud', {}).get(provider, {}).get('max_tokens', 1000)
        temperature = self.config.get('cloud', {}).get(provider, {}).get('temperature', 0.7)
        
        # Generate based on provider
        if provider == 'openai':
            result = self.generate_openai(model, prompt, max_tokens, temperature)
        elif provider == 'anthropic':
            result = self.generate_anthropic(model, prompt, max_tokens, temperature)
        else:
            return {
                'success': False,
                'error': f'Unknown provider: {provider}'
            }
        
        # Add prompt metadata
        result['prompt_id'] = prompt_id
        result['prompt_category'] = category
        
        return result
    
    def benchmark_providers(self,
                           prompts: List[Dict],
                           repetitions: int = 1) -> List[Dict]:
        """
        Benchmark multiple prompts across all enabled cloud providers.
        
        Args:
            prompts: List of prompt dicts
            repetitions: Number of times to repeat each prompt
            
        Returns:
            List of benchmark results
        """
        results = []
        
        # Get enabled providers and models
        providers_models = []
        
        if self.openai_client:
            openai_models = self.config.get('cloud', {}).get('openai', {}).get('models', [])
            for model in openai_models:
                providers_models.append(('openai', model))
        
        if self.anthropic_client:
            anthropic_models = self.config.get('cloud', {}).get('anthropic', {}).get('models', [])
            for model in anthropic_models:
                providers_models.append(('anthropic', model))
        
        logger.info(f"Benchmarking {len(prompts)} prompts across {len(providers_models)} provider/model combinations")
        
        for rep in range(repetitions):
            logger.info(f"Repetition {rep+1}/{repetitions}")
            
            for provider, model in providers_models:
                logger.info(f"Testing {provider}/{model}")
                
                for prompt_data in prompts:
                    result = self.benchmark_prompt(provider, model, prompt_data)
                    result['repetition'] = rep + 1
                    results.append(result)
                    
                    # Small delay between API calls to respect rate limits
                    time.sleep(1)
        
        logger.info(f"Cloud benchmark complete. {len(results)} results collected.")
        return results
    
    def _get_openai_cost(self, model: str) -> float:
        """Get approximate cost per 1K tokens for OpenAI model."""
        costs = {
            'gpt-4': 0.03,
            'gpt-3.5-turbo': 0.002,
        }
        return costs.get(model, 0.01)
    
    def _get_anthropic_cost(self, model: str) -> float:
        """Get approximate cost per 1K tokens for Anthropic model."""
        costs = {
            'claude-3-opus-20240229': 0.015,
            'claude-3-sonnet-20240229': 0.003,
        }
        return costs.get(model, 0.01)
    
    def _get_energy_per_token(self, provider: str, model: str) -> float:
        """
        Get energy per token from config (based on provider sustainability reports).
        
        Returns:
            Joules per token
        """
        attribution = self.config.get('energy_attribution', {}).get(provider, {})
        joules_per_token = attribution.get('joules_per_token', {}).get(model, 3.0)
        pue = attribution.get('pue', 1.2)
        
        # Apply PUE (data center overhead)
        return joules_per_token * pue
    
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
        
        fieldnames = [
            'timestamp', 'provider', 'model', 'prompt_id', 'prompt_category', 'repetition',
            'input_tokens', 'output_tokens', 'total_tokens',
            'response_time_sec', 'cost_usd',
            'estimated_energy_joules', 'joules_per_token',
            'success'
        ]
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(results)
        
        logger.info(f"Exported {len(results)} results to {filepath}")


def main():
    """Test cloud benchmark functionality."""
    import sys
    import yaml
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Load config
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        sys.exit(1)
    
    # Create benchmark
    benchmark = CloudBenchmark(config)
    
    # Test connections
    print("\nTesting cloud API connections...")
    status = benchmark.test_connections()
    
    for provider, connected in status.items():
        if connected:
            print(f"✅ {provider}: Connected")
        else:
            print(f"❌ {provider}: Connection failed")
    
    if not any(status.values()):
        print("\n⚠️  No cloud APIs connected!")
        print("Make sure you have API keys in your .env file:")
        print("  - OPENAI_API_KEY")
        print("  - ANTHROPIC_API_KEY")
        sys.exit(0)
    
    # Test generation
    if status.get('openai'):
        print("\nTesting OpenAI generation...")
        result = benchmark.generate_openai(
            model="gpt-3.5-turbo",
            prompt="Write a haiku about clouds.",
            max_tokens=100
        )
        
        if result.get('success'):
            print(f"✅ Response: {result['response']}")
            print(f"   Tokens: {result['total_tokens']}, Cost: ${result['cost_usd']:.4f}")
    
    print("\n✅ Cloud benchmark test complete!")


if __name__ == "__main__":
    main()
