"""
Visualization Module

Generates publication-quality graphs and charts from benchmark results
for research reports and presentations.
"""

import os
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import logging

from analyze_results import BenchmarkAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set style for publication-quality figures
sns.set_style("whitegrid")
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['font.size'] = 10
plt.rcParams['axes.labelsize'] = 11
plt.rcParams['axes.titlesize'] = 12
plt.rcParams['xtick.labelsize'] = 9
plt.rcParams['ytick.labelsize'] = 9


class GraphGenerator:
    """
    Generate visualizations from benchmark data.
    """
    
    def __init__(self, analyzer: BenchmarkAnalyzer, output_dir='data/graphs'):
        """
        Initialize graph generator.
        
        Args:
            analyzer: BenchmarkAnalyzer instance with loaded data
            output_dir: Directory to save generated graphs
        """
        self.analyzer = analyzer
        self.output_dir = output_dir
        Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    def plot_energy_comparison(self):
        """Plot energy consumption comparison between local and cloud."""
        local_analysis = self.analyzer.analyze_local_results()
        cloud_analysis = self.analyzer.analyze_cloud_results()
        
        if not local_analysis or not cloud_analysis:
            logger.warning("Insufficient data for energy comparison plot")
            return
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Prepare data
        labels = ['Local LLM', 'Cloud API']
        energy_values = [
            local_analysis['avg_joules_per_token'],
            cloud_analysis['avg_joules_per_token']
        ]
        colors = ['#2E86AB', '#A23B72']
        
        # Create bar chart
        bars = ax.bar(labels, energy_values, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.4f} J',
                   ha='center', va='bottom', fontweight='bold')
        
        ax.set_ylabel('Joules per Token', fontweight='bold')
        ax.set_title('Energy Efficiency: Local vs Cloud LLM Inference', fontweight='bold', pad=20)
        ax.set_ylim(0, max(energy_values) * 1.2)
        
        plt.tight_layout()
        filepath = os.path.join(self.output_dir, 'energy_comparison.png')
        plt.savefig(filepath, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Saved: {filepath}")
    
    def plot_energy_by_model(self):
        """Plot energy consumption by model for both local and cloud."""
        local_analysis = self.analyzer.analyze_local_results()
        cloud_analysis = self.analyzer.analyze_cloud_results()
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        # Local models
        if local_analysis and 'by_model' in local_analysis:
            models = list(local_analysis['by_model'].keys())
            energy = [local_analysis['by_model'][m]['avg_joules_per_token'] for m in models]
            
            ax1.barh(models, energy, color='#2E86AB', alpha=0.8, edgecolor='black')
            ax1.set_xlabel('Joules per Token', fontweight='bold')
            ax1.set_title('Local Models - Energy Efficiency', fontweight='bold')
            ax1.invert_yaxis()
            
            for i, v in enumerate(energy):
                ax1.text(v, i, f' {v:.4f}', va='center', fontweight='bold')
        
        # Cloud models
        if cloud_analysis and 'by_model' in cloud_analysis:
            models = list(cloud_analysis['by_model'].keys())
            energy = [cloud_analysis['by_model'][m]['avg_joules_per_token'] for m in models]
            
            ax2.barh(models, energy, color='#A23B72', alpha=0.8, edgecolor='black')
            ax2.set_xlabel('Joules per Token', fontweight='bold')
            ax2.set_title('Cloud Models - Energy Efficiency', fontweight='bold')
            ax2.invert_yaxis()
            
            for i, v in enumerate(energy):
                ax2.text(v, i, f' {v:.4f}', va='center', fontweight='bold')
        
        plt.tight_layout()
        filepath = os.path.join(self.output_dir, 'energy_by_model.png')
        plt.savefig(filepath, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Saved: {filepath}")
    
    def plot_cost_analysis(self):
        """Plot cost analysis for cloud APIs."""
        cloud_analysis = self.analyzer.analyze_cloud_results()
        
        if not cloud_analysis or 'by_provider' not in cloud_analysis:
            logger.warning("Insufficient data for cost analysis plot")
            return
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        # Cost by provider
        providers = list(cloud_analysis['by_provider'].keys())
        costs = [cloud_analysis['by_provider'][p]['total_cost_usd'] for p in providers]
        
        ax1.bar(providers, costs, color='#F18F01', alpha=0.8, edgecolor='black', linewidth=1.5)
        ax1.set_ylabel('Total Cost (USD)', fontweight='bold')
        ax1.set_title('Cloud API Cost by Provider', fontweight='bold')
        
        for i, v in enumerate(costs):
            ax1.text(i, v, f'${v:.4f}', ha='center', va='bottom', fontweight='bold')
        
        # Cost per token by model
        if 'by_model' in cloud_analysis:
            models = list(cloud_analysis['by_model'].keys())
            cost_per_query = [cloud_analysis['by_model'][m]['avg_cost_per_query'] for m in models]
            
            ax2.barh(models, cost_per_query, color='#C73E1D', alpha=0.8, edgecolor='black')
            ax2.set_xlabel('Average Cost per Query (USD)', fontweight='bold')
            ax2.set_title('Cloud Model Cost Comparison', fontweight='bold')
            ax2.invert_yaxis()
            
            for i, v in enumerate(cost_per_query):
                ax2.text(v, i, f' ${v:.4f}', va='center', fontweight='bold')
        
        plt.tight_layout()
        filepath = os.path.join(self.output_dir, 'cost_analysis.png')
        plt.savefig(filepath, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Saved: {filepath}")
    
    def plot_performance_comparison(self):
        """Plot performance metrics comparison."""
        local_analysis = self.analyzer.analyze_local_results()
        cloud_analysis = self.analyzer.analyze_cloud_results()
        
        if not local_analysis or not cloud_analysis:
            logger.warning("Insufficient data for performance comparison")
            return
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        labels = ['Local LLM', 'Cloud API']
        times = [
            local_analysis.get('avg_generation_time_sec', 0),
            cloud_analysis.get('avg_response_time_sec', 0)
        ]
        colors = ['#2E86AB', '#A23B72']
        
        bars = ax.bar(labels, times, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)
        
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.2f}s',
                   ha='center', va='bottom', fontweight='bold')
        
        ax.set_ylabel('Average Response Time (seconds)', fontweight='bold')
        ax.set_title('Response Time Comparison', fontweight='bold', pad=20)
        ax.set_ylim(0, max(times) * 1.2)
        
        plt.tight_layout()
        filepath = os.path.join(self.output_dir, 'performance_comparison.png')
        plt.savefig(filepath, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Saved: {filepath}")
    
    def plot_energy_by_category(self):
        """Plot energy consumption by prompt category."""
        local_analysis = self.analyzer.analyze_local_results()
        
        if not local_analysis or 'by_category' not in local_analysis:
            logger.warning("Insufficient data for category analysis")
            return
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        categories = list(local_analysis['by_category'].keys())
        energy = [local_analysis['by_category'][c]['avg_joules_per_token'] for c in categories]
        
        # Sort by energy
        sorted_data = sorted(zip(categories, energy), key=lambda x: x[1], reverse=True)
        categories, energy = zip(*sorted_data)
        
        bars = ax.barh(categories, energy, color='#06A77D', alpha=0.8, edgecolor='black')
        ax.set_xlabel('Joules per Token', fontweight='bold')
        ax.set_title('Energy Consumption by Task Category (Local)', fontweight='bold')
        ax.invert_yaxis()
        
        for i, v in enumerate(energy):
            ax.text(v, i, f' {v:.4f}', va='center', fontweight='bold')
        
        plt.tight_layout()
        filepath = os.path.join(self.output_dir, 'energy_by_category.png')
        plt.savefig(filepath, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Saved: {filepath}")
    
    def plot_power_timeline(self):
        """Plot power consumption over time from baseline data."""
        if self.analyzer.baseline_data is None:
            logger.warning("No baseline data available for power timeline")
            return
        
        df = self.analyzer.baseline_data
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        ax.plot(df['elapsed_sec'], df['power_w'], color='#2E86AB', linewidth=2, alpha=0.7)
        ax.fill_between(df['elapsed_sec'], df['power_w'], alpha=0.3, color='#2E86AB')
        
        # Add mean line
        mean_power = df['power_w'].mean()
        ax.axhline(mean_power, color='red', linestyle='--', linewidth=2, label=f'Mean: {mean_power:.2f} W')
        
        ax.set_xlabel('Time (seconds)', fontweight='bold')
        ax.set_ylabel('Power Consumption (Watts)', fontweight='bold')
        ax.set_title('System Power Consumption - Baseline Measurement', fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        filepath = os.path.join(self.output_dir, 'power_timeline.png')
        plt.savefig(filepath, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Saved: {filepath}")
    
    def plot_tradeoff_analysis(self):
        """Plot the privacy-energy tradeoff."""
        comparison = self.analyzer.compare_local_vs_cloud()
        
        if not comparison or 'comparison' not in comparison:
            logger.warning("Insufficient data for tradeoff analysis")
            return
        
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Data points
        local_energy = comparison['local']['avg_joules_per_token']
        cloud_energy = comparison['cloud']['avg_joules_per_token']
        cloud_cost = comparison['cloud']['cost_per_1k_tokens']
        
        # Plot points
        ax.scatter([1], [local_energy], s=500, c='#2E86AB', alpha=0.8, 
                  edgecolors='black', linewidth=2, label='Local (Full Privacy)', zorder=3)
        ax.scatter([0], [cloud_energy], s=500, c='#A23B72', alpha=0.8,
                  edgecolors='black', linewidth=2, label='Cloud (Data Shared)', zorder=3)
        
        # Connect with arrow
        ax.annotate('', xy=(0, cloud_energy), xytext=(1, local_energy),
                   arrowprops=dict(arrowstyle='->', lw=2, color='gray', alpha=0.5))
        
        # Add labels
        ax.text(1, local_energy, f'\n{local_energy:.4f} J/token\n$0 per query',
               ha='center', va='bottom', fontweight='bold', fontsize=10)
        ax.text(0, cloud_energy, f'\n{cloud_energy:.4f} J/token\n${cloud_cost:.4f} per 1K tokens',
               ha='center', va='bottom', fontweight='bold', fontsize=10)
        
        ax.set_xlim(-0.2, 1.2)
        ax.set_ylim(0, max(local_energy, cloud_energy) * 1.3)
        ax.set_xlabel('Data Privacy Level', fontweight='bold', fontsize=12)
        ax.set_ylabel('Energy per Token (Joules)', fontweight='bold', fontsize=12)
        ax.set_xticks([0, 1])
        ax.set_xticklabels(['Cloud\n(Shared)', 'Local\n(Private)'], fontsize=11)
        ax.set_title('Privacy vs Energy Tradeoff Analysis', fontweight='bold', fontsize=14, pad=20)
        ax.legend(loc='upper right', fontsize=10)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        filepath = os.path.join(self.output_dir, 'privacy_energy_tradeoff.png')
        plt.savefig(filepath, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Saved: {filepath}")
    
    def generate_all_graphs(self):
        """Generate all visualization graphs."""
        logger.info("Generating all graphs...")
        
        self.plot_energy_comparison()
        self.plot_energy_by_model()
        self.plot_cost_analysis()
        self.plot_performance_comparison()
        self.plot_energy_by_category()
        self.plot_power_timeline()
        self.plot_tradeoff_analysis()
        
        logger.info(f"All graphs saved to: {self.output_dir}")


def main():
    """Main function to generate graphs."""
    print("\n" + "=" * 80)
    print("LLM ENERGY ANALYSIS - GRAPH GENERATION")
    print("=" * 80)
    
    # Load and analyze data
    analyzer = BenchmarkAnalyzer()
    
    print("\n📂 Loading benchmark results...")
    if not analyzer.load_latest_results():
        print("❌ No benchmark results found!")
        print("Run benchmarks first: python src/run_benchmark.py")
        return
    
    print("✅ Results loaded")
    
    # Generate graphs
    print("\n📊 Generating visualizations...")
    generator = GraphGenerator(analyzer)
    generator.generate_all_graphs()
    
    print(f"\n✅ All graphs generated!")
    print(f"\nGraphs saved to: {generator.output_dir}")
    print("\nGenerated files:")
    print("  - energy_comparison.png")
    print("  - energy_by_model.png")
    print("  - cost_analysis.png")
    print("  - performance_comparison.png")
    print("  - energy_by_category.png")
    print("  - power_timeline.png")
    print("  - privacy_energy_tradeoff.png")
    
    print("\nThese graphs are publication-ready (300 DPI) and suitable for your grant report.")


if __name__ == "__main__":
    main()
