"""
Grant Report Generator - LLM Energy Analysis

Generates comprehensive grant reports from benchmark results.
Combines data analysis with visualizations for academic publication.
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
import yaml

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from src.analyze_results import BenchmarkAnalyzer
from src.generate_graphs import GraphGenerator


class GrantReportGenerator:
    """Generate comprehensive grant reports from benchmark data."""
    
    def __init__(self, config_path='config.yaml', output_dir='reports'):
        """Initialize report generator.
        
        Args:
            config_path: Path to configuration file
            output_dir: Directory for report output
        """
        self.config = self._load_config(config_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Initialize analyzer
        self.analyzer = BenchmarkAnalyzer()
        
        # Try to load latest results
        if not self.analyzer.load_latest_results():
            raise ValueError("No benchmark results found. Run benchmarks first.")
        
        # Initialize graph generator
        self.graph_generator = GraphGenerator(
            self.analyzer,
            output_dir=self.config['output']['graphs_dir']
        )
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def generate_markdown_report(self) -> str:
        """Generate a comprehensive markdown report.
        
        Returns:
            Path to generated markdown file
        """
        timestamp = datetime.now().strftime(self.config['output']['timestamp_format'])
        output_path = self.output_dir / f"grant_report_{timestamp}.md"
        
        # Generate all graphs first
        print("Generating visualizations...")
        self.graph_generator.generate_all_graphs()
        
        # Analyze results
        print("Analyzing benchmark data...")
        local_stats = self.analyzer.analyze_local_results()
        cloud_stats = self.analyzer.analyze_cloud_results()
        comparison = self.analyzer.compare_local_vs_cloud()
        
        # Build report content
        content = self._build_report_content(local_stats, cloud_stats, comparison)
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"\n✅ Markdown report generated: {output_path}")
        return str(output_path)
    
    def generate_html_report(self) -> str:
        """Generate an HTML version of the report.
        
        Returns:
            Path to generated HTML file
        """
        # First generate markdown
        md_path = self.generate_markdown_report()
        
        # Convert to HTML
        timestamp = datetime.now().strftime(self.config['output']['timestamp_format'])
        html_path = self.output_dir / f"grant_report_{timestamp}.html"
        
        with open(md_path, 'r', encoding='utf-8') as f:
            md_content = f.read()
        
        html_content = self._markdown_to_html(md_content)
        
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ HTML report generated: {html_path}")
        return str(html_path)
    
    def _build_report_content(self, local_stats: Dict, cloud_stats: Dict, comparison: Dict) -> str:
        """Build the full report content."""
        
        content = []
        
        # Title and metadata
        content.append("# LLM Energy Analysis - Grant 2026 Research Report")
        content.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        content.append("\n**Researcher:** Grayson Jackson")
        content.append("\n**Institution:** University of Arkansas at Little Rock")
        content.append("\n**Grant Program:** Signature Experience Grant 2026\n")
        
        content.append("\n---\n")
        
        # Executive Summary
        content.append(self._generate_executive_summary(local_stats, cloud_stats, comparison))
        
        # Research Question
        content.append("\n## Research Question\n")
        content.append("**What is the measurable energy cost of maintaining data sovereignty ")
        content.append("through local LLM inference compared to cloud-based solutions?**\n")
        
        # Methodology Overview
        content.append(self._generate_methodology_section())
        
        # Results - Local Benchmarks
        content.append(self._generate_local_results_section(local_stats))
        
        # Results - Cloud Benchmarks
        content.append(self._generate_cloud_results_section(cloud_stats))
        
        # Comparative Analysis
        content.append(self._generate_comparison_section(comparison))
        
        # Visualizations
        content.append(self._generate_visualizations_section())
        
        # Discussion
        content.append(self._generate_discussion_section(comparison))
        
        # Conclusions
        content.append(self._generate_conclusions_section(comparison))
        
        # Limitations
        content.append(self._generate_limitations_section())
        
        # Future Work
        content.append(self._generate_future_work_section())
        
        # References
        content.append(self._generate_references_section())
        
        return '\n'.join(content)
    
    def _generate_executive_summary(self, local_stats: Dict, cloud_stats: Dict, comparison: Dict) -> str:
        """Generate executive summary section."""
        lines = [
            "\n## Executive Summary\n",
            "This research quantifies the operational energy cost of data sovereignty by measuring ",
            "the energy efficiency of local Large Language Model (LLM) inference versus cloud-based APIs.\n"
        ]
        
        if local_stats and cloud_stats:
            local_avg = local_stats.get('avg_joules_per_token', 0)
            cloud_avg = cloud_stats.get('avg_joules_per_token', 0)
            
            if local_avg > 0 and cloud_avg > 0:
                ratio = local_avg / cloud_avg
                lines.append(f"\n### Key Findings\n")
                lines.append(f"- **Local LLM Energy Efficiency:** {local_avg:.4f} Joules per token (average)\n")
                lines.append(f"- **Cloud API Energy Efficiency:** {cloud_avg:.4f} Joules per token (average)\n")
                lines.append(f"- **Energy Ratio:** Local inference consumes {ratio:.2f}x the energy of cloud APIs\n")
                
                if 'total_cost_usd' in cloud_stats:
                    lines.append(f"- **Cloud Operational Cost:** ${cloud_stats['total_cost_usd']:.4f} for {cloud_stats['total_tokens']:,} tokens\n")
                
                lines.append(f"- **Total Prompts Tested:** {local_stats.get('total_prompts', 0)}\n")
                lines.append(f"- **Models Evaluated:** {local_stats.get('models_tested', 'N/A')}\n")
        
        return ''.join(lines)
    
    def _generate_methodology_section(self) -> str:
        """Generate methodology overview."""
        return """
## Methodology

### Hardware Configuration
- **GPU:** NVIDIA RTX 5060 Ti (16GB VRAM)
- **CPU:** AMD Ryzen 9 5900XT
- **Power Monitoring:** Shelly Smart Plug (hardware-level measurement)
- **Polling Interval:** 1-second power readings

### Software Stack
- **Local Inference:** Ollama with LLaMA 3 and Mistral models
- **Cloud APIs:** OpenAI (GPT-3.5, GPT-4), Anthropic (Claude 3)
- **Configuration:** Temperature 0.7, consistent across all tests

### Experimental Protocol
1. **Baseline Measurement:** 60-second idle power measurement
2. **Thermal Stabilization:** 3 warm-up queries per model
3. **Controlled Testing:** Standardized prompts with 30-second cooling periods
4. **Repetition:** 3 runs per prompt for statistical validity
5. **Data Collection:** Continuous power monitoring at 1Hz

### Test Prompts
Standardized prompts across 5 categories:
- Code Generation
- Text Summarization
- Question Answering
- Creative Writing
- Technical Documentation

For detailed methodology, see `docs/methodology.md`.
"""
    
    def _generate_local_results_section(self, stats: Dict) -> str:
        """Generate local benchmark results section."""
        lines = ["\n## Local LLM Benchmark Results\n"]
        
        if not stats:
            lines.append("No local benchmark data available.\n")
            return ''.join(lines)
        
        lines.append("### Energy Efficiency Metrics\n")
        lines.append(f"- **Average Energy per Token:** {stats.get('avg_joules_per_token', 0):.4f} Joules\n")
        lines.append(f"- **Median Energy per Token:** {stats.get('median_joules_per_token', 0):.4f} Joules\n")
        lines.append(f"- **Standard Deviation:** {stats.get('std_joules_per_token', 0):.4f} Joules\n")
        
        lines.append("\n### Performance Metrics\n")
        lines.append(f"- **Average Generation Time:** {stats.get('avg_generation_time', 0):.2f} seconds\n")
        lines.append(f"- **Average Tokens per Second:** {stats.get('avg_tokens_per_sec', 0):.2f}\n")
        lines.append(f"- **Average Power Draw:** {stats.get('avg_power_w', 0):.2f} Watts\n")
        
        lines.append("\n### Data Collection\n")
        lines.append(f"- **Total Prompts:** {stats.get('total_prompts', 0)}\n")
        lines.append(f"- **Total Tokens Generated:** {stats.get('total_tokens', 0):,}\n")
        lines.append(f"- **Total Energy Consumed:** {stats.get('total_energy_joules', 0):,.2f} Joules\n")
        
        return ''.join(lines)
    
    def _generate_cloud_results_section(self, stats: Dict) -> str:
        """Generate cloud benchmark results section."""
        lines = ["\n## Cloud API Benchmark Results\n"]
        
        if not stats:
            lines.append("No cloud benchmark data available.\n")
            return ''.join(lines)
        
        lines.append("### Energy Efficiency Metrics\n")
        lines.append(f"- **Average Energy per Token:** {stats.get('avg_joules_per_token', 0):.4f} Joules\n")
        lines.append(f"- **Median Energy per Token:** {stats.get('median_joules_per_token', 0):.4f} Joules\n")
        lines.append(f"- **Standard Deviation:** {stats.get('std_joules_per_token', 0):.4f} Joules\n")
        
        lines.append("\n### Performance Metrics\n")
        lines.append(f"- **Average Response Time:** {stats.get('avg_response_time', 0):.2f} seconds\n")
        
        lines.append("\n### Cost Analysis\n")
        lines.append(f"- **Total Cost:** ${stats.get('total_cost_usd', 0):.4f}\n")
        lines.append(f"- **Average Cost per Token:** ${stats.get('avg_cost_per_token', 0):.6f}\n")
        lines.append(f"- **Cost per 1M Tokens:** ${stats.get('avg_cost_per_token', 0) * 1_000_000:.2f}\n")
        
        lines.append("\n### Data Collection\n")
        lines.append(f"- **Total Prompts:** {stats.get('total_prompts', 0)}\n")
        lines.append(f"- **Total Tokens Generated:** {stats.get('total_tokens', 0):,}\n")
        lines.append(f"- **Total Estimated Energy:** {stats.get('total_energy_joules', 0):,.2f} Joules\n")
        
        lines.append("\n*Note: Cloud energy values are estimates based on provider sustainability reports.*\n")
        
        return ''.join(lines)
    
    def _generate_comparison_section(self, comparison: Dict) -> str:
        """Generate comparative analysis section."""
        lines = ["\n## Local vs Cloud Comparison\n"]
        
        if not comparison:
            lines.append("Comparative analysis not available.\n")
            return ''.join(lines)
        
        lines.append("### Energy Efficiency\n")
        
        local_j = comparison.get('local_joules_per_token', 0)
        cloud_j = comparison.get('cloud_joules_per_token', 0)
        
        if local_j > 0 and cloud_j > 0:
            ratio = local_j / cloud_j
            lines.append(f"- **Local:** {local_j:.4f} J/token\n")
            lines.append(f"- **Cloud:** {cloud_j:.4f} J/token\n")
            lines.append(f"- **Ratio:** {ratio:.2f}x (local vs cloud)\n")
            
            if ratio > 1:
                lines.append(f"\nLocal inference consumes **{ratio:.2f}x more energy** per token than cloud APIs.\n")
            else:
                lines.append(f"\nLocal inference is **{1/ratio:.2f}x more efficient** than cloud APIs.\n")
        
        lines.append("\n### Performance\n")
        local_time = comparison.get('local_avg_time', 0)
        cloud_time = comparison.get('cloud_avg_time', 0)
        
        if local_time > 0 and cloud_time > 0:
            lines.append(f"- **Local Generation Time:** {local_time:.2f} seconds\n")
            lines.append(f"- **Cloud Response Time:** {cloud_time:.2f} seconds\n")
        
        return ''.join(lines)
    
    def _generate_visualizations_section(self) -> str:
        """Generate visualizations section with graph references."""
        graphs_dir = Path(self.config['output']['graphs_dir'])
        
        return f"""
## Visualizations

The following graphs provide visual analysis of the benchmark results:

1. **Energy Comparison** - `{graphs_dir}/energy_comparison.png`
   - Direct comparison of energy efficiency between local and cloud inference

2. **Energy by Model** - `{graphs_dir}/energy_by_model.png`
   - Detailed breakdown of energy consumption for each model tested

3. **Cost Analysis** - `{graphs_dir}/cost_analysis.png`
   - Cloud API costs and energy-cost relationship

4. **Performance Comparison** - `{graphs_dir}/performance_comparison.png`
   - Response time and throughput metrics

5. **Energy by Category** - `{graphs_dir}/energy_by_category.png`
   - Energy consumption across different prompt types

6. **Privacy-Energy Tradeoff** - `{graphs_dir}/tradeoff_analysis.png`
   - Analysis of the energy cost of data sovereignty

All graphs are saved in publication-quality format (300 DPI) in the `{graphs_dir}/` directory.
"""
    
    def _generate_discussion_section(self, comparison: Dict) -> str:
        """Generate discussion section."""
        return """
## Discussion

### Energy Cost of Data Sovereignty

This research demonstrates a measurable energy premium for maintaining data sovereignty through 
local LLM inference. The results quantify the operational trade-off between strict data privacy 
and energy efficiency.

### Factors Contributing to Energy Differences

1. **Infrastructure Efficiency**: Cloud data centers benefit from:
   - Economies of scale
   - Optimized cooling systems (low PUE)
   - Specialized inference hardware
   - Load balancing across geographic regions

2. **Model Optimization**: Cloud providers may use:
   - Optimized model architectures
   - Quantization techniques
   - Inference acceleration hardware
   - Batch processing efficiencies

3. **System Overhead**: Local measurements include:
   - Total system power (CPU, RAM, storage)
   - Cooling requirements
   - Idle baseline consumption
   - Single-user inefficiencies

### Implications for Privacy-Sensitive Applications

Organizations handling sensitive data face a quantifiable energy cost for maintaining data 
sovereignty. This information can inform:

- Infrastructure planning decisions
- Carbon footprint calculations
- Cost-benefit analysis of privacy measures
- Policy decisions regarding data handling

### Environmental Considerations

While local inference may consume more energy per token, the total environmental impact depends on:
- Energy source (renewable vs fossil fuels)
- Data center PUE
- Network transmission energy
- Hardware lifecycle and manufacturing impact
"""
    
    def _generate_conclusions_section(self, comparison: Dict) -> str:
        """Generate conclusions section."""
        lines = ["\n## Conclusions\n"]
        
        local_j = comparison.get('local_joules_per_token', 0)
        cloud_j = comparison.get('cloud_joules_per_token', 0)
        
        if local_j > 0 and cloud_j > 0:
            ratio = local_j / cloud_j
            
            lines.append(f"1. **Measurable Energy Premium**: Local LLM inference consumes approximately "
                        f"{ratio:.2f}x the energy per token compared to cloud APIs.\n\n")
            
            lines.append("2. **Data Sovereignty Cost**: Organizations prioritizing data privacy face a "
                        "quantifiable operational energy cost.\n\n")
            
            lines.append("3. **Infrastructure Efficiency**: Cloud data centers demonstrate superior energy "
                        "efficiency due to scale, optimization, and specialized hardware.\n\n")
            
            lines.append("4. **Decision Framework**: This research provides empirical data for evaluating "
                        "privacy-energy trade-offs in AI deployment strategies.\n\n")
            
            lines.append("5. **Sustainability Impact**: Understanding these metrics is crucial for "
                        "organizations committed to both data privacy and environmental sustainability.\n")
        else:
            lines.append("Analysis demonstrates the importance of measuring energy consumption in "
                        "AI inference workloads for informed decision-making.\n")
        
        return ''.join(lines)
    
    def _generate_limitations_section(self) -> str:
        """Generate limitations section."""
        return """
## Limitations

1. **Token Counting**: Local model token counts are approximations (no native tokenizer access)
2. **Cloud Energy Estimates**: Based on provider-reported averages, not direct measurements
3. **System Overhead**: Local measurements include total system power, not isolated GPU
4. **Model Variability**: Results specific to tested models and configurations
5. **Network Latency**: Cloud metrics include network overhead
6. **Sample Size**: Limited to available hardware and API access
7. **Temporal Factors**: Power grid carbon intensity varies by time and location

## Future Work

1. **Extended Model Testing**: Evaluate additional models and parameter sizes
2. **Hardware Comparison**: Test different GPU configurations and power profiles
3. **Optimization Study**: Measure impact of quantization and optimization techniques
4. **Carbon Intensity**: Incorporate time-of-use energy sourcing data
5. **Cost-Benefit Analysis**: Extend to include hardware amortization and TCO
6. **Real-World Workloads**: Test with production-scale usage patterns
"""
    
    def _generate_future_work_section(self) -> str:
        """Generate future work section."""
        return """
## Recommendations

### For Researchers
- Use this methodology as a framework for energy studies
- Extend measurements to additional models and hardware
- Investigate optimization techniques and their energy impact

### For Organizations
- Consider both privacy and energy costs in deployment decisions
- Evaluate renewable energy sourcing for local infrastructure
- Monitor and optimize inference workloads
- Calculate total cost of ownership including energy

### For Policymakers
- Develop guidelines for energy-efficient AI deployment
- Incentivize renewable energy use in data centers
- Support research into efficient privacy-preserving technologies
"""
    
    def _generate_references_section(self) -> str:
        """Generate references section."""
        return """
## References

1. OpenAI. (2024). *Sustainability and Energy Efficiency Reports*. OpenAI.
2. Anthropic. (2024). *Environmental Impact Documentation*. Anthropic.
3. IEEE. (2023). *Standards for Power Measurement in Computing Systems*.
4. SPEC. (2024). *Power and Performance Benchmarks*.
5. Strubell, E., et al. (2019). *Energy and Policy Considerations for Deep Learning in NLP*. ACL.
6. Patterson, D., et al. (2021). *Carbon Emissions and Large Neural Network Training*. arXiv.

## Acknowledgments

- **Institution**: University of Arkansas at Little Rock
- **Grant Program**: Signature Experience Grant 2026
- **Tools**: Ollama, Python ecosystem, Shelly Smart Plug
- **Open Source Community**: Contributors to all software dependencies

---

*Report generated automatically from benchmark data. For questions or additional analysis, 
contact the researcher.*
"""
    
    def _markdown_to_html(self, markdown_content: str) -> str:
        """Convert markdown to HTML with basic styling."""
        
        html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LLM Energy Analysis - Grant 2026 Report</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
            border-bottom: 2px solid #ecf0f1;
            padding-bottom: 5px;
        }}
        h3 {{
            color: #7f8c8d;
            margin-top: 20px;
        }}
        code {{
            background-color: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }}
        pre {{
            background-color: #f4f4f4;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
        }}
        ul, ol {{
            margin-left: 20px;
        }}
        strong {{
            color: #2c3e50;
        }}
        hr {{
            border: none;
            border-top: 2px solid #ecf0f1;
            margin: 30px 0;
        }}
        .metadata {{
            color: #7f8c8d;
            font-style: italic;
        }}
    </style>
</head>
<body>
{content}
</body>
</html>"""
        
        # Basic markdown to HTML conversion
        html_content = markdown_content
        
        # Headers
        html_content = html_content.replace('\n# ', '\n<h1>').replace('\n## ', '\n<h2>').replace('\n### ', '\n<h3>')
        html_content = html_content.replace('</h1>', '</h1>\n').replace('</h2>', '</h2>\n').replace('</h3>', '</h3>\n')
        
        # Bold
        import re
        html_content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html_content)
        
        # Paragraphs
        html_content = html_content.replace('\n\n', '</p><p>')
        html_content = '<p>' + html_content + '</p>'
        
        # Lists (basic)
        html_content = html_content.replace('<p>- ', '<ul><li>').replace('\n- ', '</li><li>')
        html_content = re.sub(r'</li><li>([^<]+?)</p>', r'</li><li>\1</li></ul>', html_content)
        
        # Horizontal rules
        html_content = html_content.replace('<p>---</p>', '<hr>')
        
        return html_template.format(content=html_content)
    
    def print_summary(self):
        """Print a summary of available data."""
        print("\n" + "="*60)
        print("GRANT REPORT GENERATOR - DATA SUMMARY")
        print("="*60)
        
        if self.analyzer.local_df is not None:
            print(f"\n📊 Local Benchmark Data:")
            print(f"   - Records: {len(self.analyzer.local_df)}")
            print(f"   - Models: {self.analyzer.local_df['model'].nunique()}")
            print(f"   - Prompts: {self.analyzer.local_df['prompt_id'].nunique()}")
        
        if self.analyzer.cloud_df is not None:
            print(f"\n☁️  Cloud Benchmark Data:")
            print(f"   - Records: {len(self.analyzer.cloud_df)}")
            print(f"   - Providers: {self.analyzer.cloud_df['provider'].nunique()}")
            print(f"   - Models: {self.analyzer.cloud_df['model'].nunique()}")
        
        print("\n" + "="*60 + "\n")


def main():
    """Main entry point for report generation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate grant reports from benchmark data")
    parser.add_argument('--format', choices=['markdown', 'html', 'both'], default='both',
                       help='Output format (default: both)')
    parser.add_argument('--config', default='config.yaml',
                       help='Path to configuration file')
    parser.add_argument('--output-dir', default='reports',
                       help='Output directory for reports')
    
    args = parser.parse_args()
    
    try:
        # Create generator
        generator = GrantReportGenerator(
            config_path=args.config,
            output_dir=args.output_dir
        )
        
        # Show data summary
        generator.print_summary()
        
        # Generate reports
        print("Generating grant report...\n")
        
        if args.format in ['markdown', 'both']:
            md_path = generator.generate_markdown_report()
            print(f"✅ Markdown report: {md_path}")
        
        if args.format in ['html', 'both']:
            html_path = generator.generate_html_report()
            print(f"✅ HTML report: {html_path}")
        
        print("\n🎉 Report generation complete!")
        
    except ValueError as e:
        print(f"\n❌ Error: {e}")
        print("\nPlease run benchmarks first:")
        print("  python src/run_benchmark.py")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
