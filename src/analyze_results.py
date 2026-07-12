"""
Data Analysis Module

Analyzes benchmark results and generates statistical summaries comparing
local LLM inference with cloud APIs in terms of energy efficiency and cost.
"""

import os
import glob
import pandas as pd
import numpy as np
from pathlib import Path
import logging
from typing import Dict, List, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BenchmarkAnalyzer:
    """
    Analyzer for benchmark results.
    
    Provides statistical analysis and comparison between local and cloud inference.
    """
    
    def __init__(self, results_dir='data/results'):
        """
        Initialize the analyzer.
        
        Args:
            results_dir: Directory containing CSV result files
        """
        self.results_dir = results_dir
        self.local_data = None
        self.cloud_data = None
        self.baseline_data = None
    
    def load_latest_results(self) -> bool:
        """
        Load the most recent benchmark results.
        
        Returns:
            True if data loaded successfully, False otherwise
        """
        try:
            # Find latest local benchmark file
            local_files = glob.glob(os.path.join(self.results_dir, 'local_benchmark_*.csv'))
            if local_files:
                latest_local = max(local_files, key=os.path.getctime)
                self.local_data = pd.read_csv(latest_local)
                logger.info(f"Loaded local results: {latest_local} ({len(self.local_data)} rows)")
            
            # Find latest cloud benchmark file
            cloud_files = glob.glob(os.path.join(self.results_dir, 'cloud_benchmark_*.csv'))
            if cloud_files:
                latest_cloud = max(cloud_files, key=os.path.getctime)
                self.cloud_data = pd.read_csv(latest_cloud)
                logger.info(f"Loaded cloud results: {latest_cloud} ({len(self.cloud_data)} rows)")
            
            # Find latest baseline file
            baseline_files = glob.glob(os.path.join(self.results_dir, 'baseline_*.csv'))
            if baseline_files:
                latest_baseline = max(baseline_files, key=os.path.getctime)
                self.baseline_data = pd.read_csv(latest_baseline)
                logger.info(f"Loaded baseline: {latest_baseline} ({len(self.baseline_data)} rows)")
            
            return (self.local_data is not None) or (self.cloud_data is not None)
        
        except Exception as e:
            logger.error(f"Failed to load results: {e}")
            return False
    
    def analyze_local_results(self) -> Dict:
        """
        Analyze local LLM benchmark results.
        
        Returns:
            Dict with statistical analysis
        """
        if self.local_data is None or len(self.local_data) == 0:
            return {}
        
        # Filter successful results
        df = self.local_data[self.local_data['success'] == True].copy()
        
        if len(df) == 0:
            return {}
        
        analysis = {
            'total_tests': len(df),
            'models': df['model'].unique().tolist(),
            'categories': df['prompt_category'].unique().tolist(),
            
            # Token statistics
            'total_tokens': int(df['total_tokens'].sum()),
            'avg_tokens_per_query': float(df['total_tokens'].mean()),
            'input_tokens': int(df['input_tokens'].sum()),
            'output_tokens': int(df['output_tokens'].sum()),
            
            # Performance statistics
            'avg_generation_time_sec': float(df['generation_time_sec'].mean()),
            'median_generation_time_sec': float(df['generation_time_sec'].median()),
            'avg_tokens_per_sec': float(df['tokens_per_sec'].mean()),
            
            # Energy statistics
            'total_energy_joules': float(df['energy_joules'].sum()),
            'total_energy_wh': float(df['energy_joules'].sum() / 3600),
            'avg_power_w': float(df['power_avg_w'].mean()),
            'avg_joules_per_token': float(df['joules_per_token'].mean()),
            'median_joules_per_token': float(df['joules_per_token'].median()),
            'std_joules_per_token': float(df['joules_per_token'].std()),
        }
        
        # Per-model statistics
        analysis['by_model'] = {}
        for model in analysis['models']:
            model_df = df[df['model'] == model]
            analysis['by_model'][model] = {
                'tests': len(model_df),
                'avg_joules_per_token': float(model_df['joules_per_token'].mean()),
                'avg_tokens_per_sec': float(model_df['tokens_per_sec'].mean()),
                'total_energy_wh': float(model_df['energy_joules'].sum() / 3600),
            }
        
        # Per-category statistics
        analysis['by_category'] = {}
        for category in analysis['categories']:
            cat_df = df[df['prompt_category'] == category]
            analysis['by_category'][category] = {
                'tests': len(cat_df),
                'avg_joules_per_token': float(cat_df['joules_per_token'].mean()),
                'avg_generation_time_sec': float(cat_df['generation_time_sec'].mean()),
            }
        
        return analysis
    
    def analyze_cloud_results(self) -> Dict:
        """
        Analyze cloud API benchmark results.
        
        Returns:
            Dict with statistical analysis
        """
        if self.cloud_data is None or len(self.cloud_data) == 0:
            return {}
        
        # Filter successful results
        df = self.cloud_data[self.cloud_data['success'] == True].copy()
        
        if len(df) == 0:
            return {}
        
        analysis = {
            'total_tests': len(df),
            'providers': df['provider'].unique().tolist(),
            'models': df['model'].unique().tolist(),
            'categories': df['prompt_category'].unique().tolist(),
            
            # Token statistics
            'total_tokens': int(df['total_tokens'].sum()),
            'avg_tokens_per_query': float(df['total_tokens'].mean()),
            'input_tokens': int(df['input_tokens'].sum()),
            'output_tokens': int(df['output_tokens'].sum()),
            
            # Performance statistics
            'avg_response_time_sec': float(df['response_time_sec'].mean()),
            'median_response_time_sec': float(df['response_time_sec'].median()),
            
            # Cost statistics
            'total_cost_usd': float(df['cost_usd'].sum()),
            'avg_cost_per_query': float(df['cost_usd'].mean()),
            'cost_per_1k_tokens': float((df['cost_usd'].sum() / df['total_tokens'].sum()) * 1000),
            
            # Energy statistics (estimated)
            'total_estimated_energy_joules': float(df['estimated_energy_joules'].sum()),
            'total_estimated_energy_wh': float(df['estimated_energy_joules'].sum() / 3600),
            'avg_joules_per_token': float(df['joules_per_token'].mean()),
            'median_joules_per_token': float(df['joules_per_token'].median()),
        }
        
        # Per-provider statistics
        analysis['by_provider'] = {}
        for provider in analysis['providers']:
            prov_df = df[df['provider'] == provider]
            analysis['by_provider'][provider] = {
                'tests': len(prov_df),
                'total_cost_usd': float(prov_df['cost_usd'].sum()),
                'avg_joules_per_token': float(prov_df['joules_per_token'].mean()),
                'avg_response_time_sec': float(prov_df['response_time_sec'].mean()),
            }
        
        # Per-model statistics
        analysis['by_model'] = {}
        for model in analysis['models']:
            model_df = df[df['model'] == model]
            analysis['by_model'][model] = {
                'tests': len(model_df),
                'avg_joules_per_token': float(model_df['joules_per_token'].mean()),
                'avg_cost_per_query': float(model_df['cost_usd'].mean()),
                'total_cost_usd': float(model_df['cost_usd'].sum()),
            }
        
        return analysis
    
    def compare_local_vs_cloud(self) -> Dict:
        """
        Compare local and cloud inference metrics.
        
        Returns:
            Dict with comparative analysis
        """
        local_analysis = self.analyze_local_results()
        cloud_analysis = self.analyze_cloud_results()
        
        if not local_analysis or not cloud_analysis:
            return {}
        
        comparison = {
            'local': local_analysis,
            'cloud': cloud_analysis,
            'comparison': {}
        }
        
        # Energy comparison
        local_j_per_token = local_analysis['avg_joules_per_token']
        cloud_j_per_token = cloud_analysis['avg_joules_per_token']
        
        comparison['comparison']['energy'] = {
            'local_joules_per_token': local_j_per_token,
            'cloud_joules_per_token': cloud_j_per_token,
            'local_higher_by_factor': local_j_per_token / cloud_j_per_token if cloud_j_per_token > 0 else 0,
            'local_higher_by_percent': ((local_j_per_token - cloud_j_per_token) / cloud_j_per_token * 100) if cloud_j_per_token > 0 else 0,
        }
        
        # Cost analysis (local has no per-query cost, but has capital cost)
        comparison['comparison']['cost'] = {
            'cloud_cost_per_1k_tokens': cloud_analysis['cost_per_1k_tokens'],
            'cloud_total_cost_usd': cloud_analysis['total_cost_usd'],
        }
        
        # Performance comparison
        if 'avg_generation_time_sec' in local_analysis and 'avg_response_time_sec' in cloud_analysis:
            local_time = local_analysis['avg_generation_time_sec']
            cloud_time = cloud_analysis['avg_response_time_sec']
            
            comparison['comparison']['performance'] = {
                'local_avg_time_sec': local_time,
                'cloud_avg_time_sec': cloud_time,
                'local_faster': local_time < cloud_time,
                'time_difference_sec': abs(local_time - cloud_time),
            }
        
        return comparison
    
    def print_summary(self):
        """Print a human-readable summary of the analysis."""
        print("\n" + "=" * 80)
        print("BENCHMARK ANALYSIS SUMMARY")
        print("=" * 80)
        
        # Local results
        local_analysis = self.analyze_local_results()
        if local_analysis:
            print("\n📍 LOCAL LLM INFERENCE")
            print("-" * 80)
            print(f"Total Tests: {local_analysis['total_tests']}")
            print(f"Models: {', '.join(local_analysis['models'])}")
            print(f"\nTokens:")
            print(f"  Total: {local_analysis['total_tokens']:,}")
            print(f"  Average per query: {local_analysis['avg_tokens_per_query']:.1f}")
            print(f"\nPerformance:")
            print(f"  Avg generation time: {local_analysis['avg_generation_time_sec']:.2f} sec")
            print(f"  Avg speed: {local_analysis['avg_tokens_per_sec']:.2f} tokens/sec")
            print(f"\nEnergy:")
            print(f"  Total energy: {local_analysis['total_energy_wh']:.4f} Wh ({local_analysis['total_energy_joules']:.2f} J)")
            print(f"  Avg power: {local_analysis['avg_power_w']:.2f} W")
            print(f"  Joules/token: {local_analysis['avg_joules_per_token']:.4f} (±{local_analysis['std_joules_per_token']:.4f})")
            
            print(f"\nBy Model:")
            for model, stats in local_analysis['by_model'].items():
                print(f"  {model}:")
                print(f"    Tests: {stats['tests']}, J/token: {stats['avg_joules_per_token']:.4f}, Speed: {stats['avg_tokens_per_sec']:.2f} tok/s")
        
        # Cloud results
        cloud_analysis = self.analyze_cloud_results()
        if cloud_analysis:
            print("\n\n☁️  CLOUD API INFERENCE")
            print("-" * 80)
            print(f"Total Tests: {cloud_analysis['total_tests']}")
            print(f"Providers: {', '.join(cloud_analysis['providers'])}")
            print(f"Models: {', '.join(cloud_analysis['models'])}")
            print(f"\nTokens:")
            print(f"  Total: {cloud_analysis['total_tokens']:,}")
            print(f"  Average per query: {cloud_analysis['avg_tokens_per_query']:.1f}")
            print(f"\nPerformance:")
            print(f"  Avg response time: {cloud_analysis['avg_response_time_sec']:.2f} sec")
            print(f"\nCost:")
            print(f"  Total cost: ${cloud_analysis['total_cost_usd']:.4f}")
            print(f"  Avg per query: ${cloud_analysis['avg_cost_per_query']:.4f}")
            print(f"  Per 1K tokens: ${cloud_analysis['cost_per_1k_tokens']:.4f}")
            print(f"\nEstimated Energy (from provider data):")
            print(f"  Total: {cloud_analysis['total_estimated_energy_wh']:.4f} Wh ({cloud_analysis['total_estimated_energy_joules']:.2f} J)")
            print(f"  Joules/token: {cloud_analysis['avg_joules_per_token']:.4f}")
            
            print(f"\nBy Provider:")
            for provider, stats in cloud_analysis['by_provider'].items():
                print(f"  {provider}:")
                print(f"    Tests: {stats['tests']}, Cost: ${stats['total_cost_usd']:.4f}, J/token: {stats['avg_joules_per_token']:.4f}")
        
        # Comparison
        if local_analysis and cloud_analysis:
            print("\n\n⚖️  LOCAL vs CLOUD COMPARISON")
            print("-" * 80)
            
            comparison = self.compare_local_vs_cloud()['comparison']
            
            energy = comparison['energy']
            print(f"\nEnergy Efficiency:")
            print(f"  Local:  {energy['local_joules_per_token']:.4f} J/token")
            print(f"  Cloud:  {energy['cloud_joules_per_token']:.4f} J/token")
            
            if energy['local_higher_by_percent'] > 0:
                print(f"  → Local uses {energy['local_higher_by_percent']:.1f}% MORE energy per token")
            else:
                print(f"  → Local uses {abs(energy['local_higher_by_percent']):.1f}% LESS energy per token")
            
            print(f"\nCost Analysis:")
            print(f"  Cloud cost per 1K tokens: ${comparison['cost']['cloud_cost_per_1k_tokens']:.4f}")
            print(f"  Cloud total cost: ${comparison['cost']['cloud_total_cost_usd']:.4f}")
            print(f"  Local operational cost: $0 (capital investment only)")
            
            if 'performance' in comparison:
                perf = comparison['performance']
                print(f"\nPerformance:")
                print(f"  Local avg time:  {perf['local_avg_time_sec']:.2f} sec")
                print(f"  Cloud avg time:  {perf['cloud_avg_time_sec']:.2f} sec")
                faster = "Local" if perf['local_faster'] else "Cloud"
                print(f"  → {faster} is faster by {perf['time_difference_sec']:.2f} sec")
        
        print("\n" + "=" * 80)


def main():
    """Main analysis function."""
    print("\n" + "=" * 80)
    print("LLM ENERGY ANALYSIS - DATA ANALYSIS")
    print("=" * 80)
    
    analyzer = BenchmarkAnalyzer()
    
    print("\n📂 Loading benchmark results...")
    if not analyzer.load_latest_results():
        print("❌ No benchmark results found!")
        print("Run benchmarks first: python src/run_benchmark.py")
        return
    
    print("✅ Results loaded\n")
    
    # Print summary
    analyzer.print_summary()
    
    print("\n✅ Analysis complete!")
    print("\nNext step: Generate visualizations with 'python src/generate_graphs.py'")


if __name__ == "__main__":
    main()
