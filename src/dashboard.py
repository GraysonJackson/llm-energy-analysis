"""
Real-Time Monitoring Dashboard - LLM Energy Analysis

Flask-based web dashboard for monitoring benchmark progress in real-time.
Displays live power consumption, token generation metrics, and visualizations.
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import json
import threading
import time

from flask import Flask, render_template_string, jsonify, request
from flask_cors import CORS
import pandas as pd
import yaml

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from power_monitor import PowerMonitor


app = Flask(__name__)
CORS(app)

# Global state
monitor_state = {
    'active': False,
    'current_benchmark': None,
    'power_readings': [],
    'benchmark_history': [],
    'start_time': None
}

config = {}


def load_config(config_path='config.yaml'):
    """Load configuration from YAML file."""
    global config
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config


def load_latest_results():
    """Load the most recent benchmark results."""
    results_dir = Path(config['output']['results_dir'])
    
    if not results_dir.exists():
        return None, None
    
    # Find latest local and cloud results
    local_files = sorted(results_dir.glob('local_benchmark_*.csv'), reverse=True)
    cloud_files = sorted(results_dir.glob('cloud_benchmark_*.csv'), reverse=True)
    
    local_df = None
    cloud_df = None
    
    if local_files:
        local_df = pd.read_csv(local_files[0])
    
    if cloud_files:
        cloud_df = pd.read_csv(cloud_files[0])
    
    return local_df, cloud_df


# HTML Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LLM Energy Analysis Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        header {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        
        h1 {
            color: #667eea;
            margin-bottom: 10px;
        }
        
        .status-bar {
            display: flex;
            gap: 20px;
            margin-top: 15px;
        }
        
        .status-item {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .status-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #dc3545;
        }
        
        .status-indicator.active {
            background: #28a745;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        .card h2 {
            color: #667eea;
            margin-bottom: 15px;
            font-size: 1.2rem;
        }
        
        .metric {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #eee;
        }
        
        .metric:last-child {
            border-bottom: none;
        }
        
        .metric-label {
            color: #666;
        }
        
        .metric-value {
            font-weight: bold;
            color: #333;
        }
        
        .metric-value.highlight {
            color: #667eea;
            font-size: 1.5rem;
        }
        
        .chart-container {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            height: 400px;
        }
        
        .chart-wrapper {
            position: relative;
            height: 320px;
        }
        
        .recent-benchmarks {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
        }
        
        th, td {
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }
        
        th {
            background: #f8f9fa;
            color: #667eea;
            font-weight: 600;
        }
        
        .footer {
            text-align: center;
            color: white;
            margin-top: 20px;
            padding: 20px;
        }
        
        .refresh-info {
            color: #666;
            font-size: 0.9rem;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🔋 LLM Energy Analysis Dashboard</h1>
            <p>Real-time monitoring of local and cloud LLM benchmarks</p>
            <div class="status-bar">
                <div class="status-item">
                    <div class="status-indicator" id="statusIndicator"></div>
                    <span id="statusText">Idle</span>
                </div>
                <div class="status-item">
                    <span id="currentBenchmark">No active benchmark</span>
                </div>
                <div class="status-item">
                    <span id="uptime">Uptime: 0s</span>
                </div>
            </div>
            <div class="refresh-info">Auto-refresh: {{ refresh_interval }}s</div>
        </header>
        
        <div class="dashboard-grid">
            <div class="card">
                <h2>⚡ Current Power</h2>
                <div class="metric">
                    <span class="metric-label">Power Draw</span>
                    <span class="metric-value highlight" id="currentPower">-- W</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Average (30s)</span>
                    <span class="metric-value" id="avgPower">-- W</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Peak Power</span>
                    <span class="metric-value" id="peakPower">-- W</span>
                </div>
            </div>
            
            <div class="card">
                <h2>📊 Session Statistics</h2>
                <div class="metric">
                    <span class="metric-label">Total Tokens</span>
                    <span class="metric-value" id="totalTokens">0</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Total Energy</span>
                    <span class="metric-value" id="totalEnergy">0 J</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Avg J/Token</span>
                    <span class="metric-value" id="avgJoulesPerToken">--</span>
                </div>
            </div>
            
            <div class="card">
                <h2>🎯 Performance</h2>
                <div class="metric">
                    <span class="metric-label">Tokens/Second</span>
                    <span class="metric-value" id="tokensPerSec">--</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Tests Completed</span>
                    <span class="metric-value" id="testsCompleted">0</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Active Model</span>
                    <span class="metric-value" id="activeModel">--</span>
                </div>
            </div>
        </div>
        
        <div class="chart-container">
            <h2>Power Consumption Timeline</h2>
            <div class="chart-wrapper">
                <canvas id="powerChart"></canvas>
            </div>
        </div>
        
        <div class="recent-benchmarks">
            <h2>Recent Benchmark Results</h2>
            <table id="resultsTable">
                <thead>
                    <tr>
                        <th>Timestamp</th>
                        <th>Model</th>
                        <th>Tokens</th>
                        <th>Energy (J)</th>
                        <th>J/Token</th>
                        <th>Time (s)</th>
                    </tr>
                </thead>
                <tbody id="resultsBody">
                    <tr>
                        <td colspan="6" style="text-align: center; color: #999;">No results yet</td>
                    </tr>
                </tbody>
            </table>
        </div>
        
        <div class="footer">
            <p>Grant 2026 - LLM Energy Analysis</p>
            <p>University of Arkansas at Little Rock</p>
        </div>
    </div>
    
    <script>
        // Chart setup
        const ctx = document.getElementById('powerChart').getContext('2d');
        const powerChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Power (W)',
                    data: [],
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Watts'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Time'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    }
                }
            }
        });
        
        // Update functions
        function updateDashboard() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    // Update status
                    const indicator = document.getElementById('statusIndicator');
                    const statusText = document.getElementById('statusText');
                    if (data.active) {
                        indicator.classList.add('active');
                        statusText.textContent = 'Active';
                    } else {
                        indicator.classList.remove('active');
                        statusText.textContent = 'Idle';
                    }
                    
                    // Update metrics
                    document.getElementById('currentPower').textContent = 
                        data.current_power ? data.current_power.toFixed(2) + ' W' : '-- W';
                    document.getElementById('avgPower').textContent = 
                        data.avg_power ? data.avg_power.toFixed(2) + ' W' : '-- W';
                    document.getElementById('peakPower').textContent = 
                        data.peak_power ? data.peak_power.toFixed(2) + ' W' : '-- W';
                    
                    document.getElementById('currentBenchmark').textContent = 
                        data.current_benchmark || 'No active benchmark';
                    document.getElementById('uptime').textContent = 
                        'Uptime: ' + data.uptime + 's';
                    
                    // Update chart
                    if (data.power_history && data.power_history.length > 0) {
                        const maxPoints = 60;
                        const history = data.power_history.slice(-maxPoints);
                        
                        powerChart.data.labels = history.map((_, i) => i);
                        powerChart.data.datasets[0].data = history;
                        powerChart.update('none');
                    }
                })
                .catch(error => console.error('Error fetching status:', error));
            
            // Update results
            fetch('/api/results')
                .then(response => response.json())
                .then(data => {
                    if (data.stats) {
                        document.getElementById('totalTokens').textContent = 
                            data.stats.total_tokens.toLocaleString();
                        document.getElementById('totalEnergy').textContent = 
                            data.stats.total_energy.toFixed(2) + ' J';
                        document.getElementById('avgJoulesPerToken').textContent = 
                            data.stats.avg_joules_per_token.toFixed(4);
                        document.getElementById('tokensPerSec').textContent = 
                            data.stats.avg_tokens_per_sec.toFixed(2);
                        document.getElementById('testsCompleted').textContent = 
                            data.stats.total_tests;
                        document.getElementById('activeModel').textContent = 
                            data.stats.latest_model || '--';
                    }
                    
                    if (data.recent && data.recent.length > 0) {
                        const tbody = document.getElementById('resultsBody');
                        tbody.innerHTML = data.recent.map(row => `
                            <tr>
                                <td>${row.timestamp}</td>
                                <td>${row.model}</td>
                                <td>${row.tokens}</td>
                                <td>${row.energy}</td>
                                <td>${row.j_per_token}</td>
                                <td>${row.time}</td>
                            </tr>
                        `).join('');
                    }
                })
                .catch(error => console.error('Error fetching results:', error));
        }
        
        // Initial update and set interval
        updateDashboard();
        setInterval(updateDashboard, {{ refresh_interval * 1000 }});
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    """Serve the main dashboard page."""
    refresh_interval = config.get('dashboard', {}).get('auto_refresh_interval', 5)
    return render_template_string(HTML_TEMPLATE, refresh_interval=refresh_interval)


@app.route('/api/status')
def api_status():
    """Get current monitoring status and power readings."""
    global monitor_state
    
    # Calculate uptime
    uptime = 0
    if monitor_state['start_time']:
        uptime = int(time.time() - monitor_state['start_time'])
    
    # Get current power if available
    current_power = None
    avg_power = None
    peak_power = None
    
    if monitor_state['power_readings']:
        current_power = monitor_state['power_readings'][-1]
        recent = monitor_state['power_readings'][-30:]  # Last 30 readings
        avg_power = sum(recent) / len(recent)
        peak_power = max(monitor_state['power_readings'])
    
    return jsonify({
        'active': monitor_state['active'],
        'current_benchmark': monitor_state['current_benchmark'],
        'current_power': current_power,
        'avg_power': avg_power,
        'peak_power': peak_power,
        'power_history': monitor_state['power_readings'][-60:],  # Last 60 points
        'uptime': uptime
    })


@app.route('/api/results')
def api_results():
    """Get benchmark results and statistics."""
    local_df, cloud_df = load_latest_results()
    
    stats = {
        'total_tokens': 0,
        'total_energy': 0,
        'avg_joules_per_token': 0,
        'avg_tokens_per_sec': 0,
        'total_tests': 0,
        'latest_model': None
    }
    
    recent = []
    
    if local_df is not None and len(local_df) > 0:
        stats['total_tokens'] = int(local_df['total_tokens'].sum())
        stats['total_energy'] = float(local_df['energy_joules'].sum())
        stats['avg_joules_per_token'] = float(local_df['joules_per_token'].mean())
        stats['avg_tokens_per_sec'] = float(local_df['tokens_per_sec'].mean())
        stats['total_tests'] = len(local_df)
        stats['latest_model'] = local_df.iloc[-1]['model']
        
        # Get recent results (last 10)
        recent_df = local_df.tail(10).sort_values('timestamp', ascending=False)
        recent = [
            {
                'timestamp': row['timestamp'],
                'model': row['model'],
                'tokens': int(row['total_tokens']),
                'energy': f"{row['energy_joules']:.2f}",
                'j_per_token': f"{row['joules_per_token']:.4f}",
                'time': f"{row['generation_time_sec']:.2f}"
            }
            for _, row in recent_df.iterrows()
        ]
    
    return jsonify({
        'stats': stats,
        'recent': recent
    })


@app.route('/api/power/start', methods=['POST'])
def api_power_start():
    """Start power monitoring."""
    global monitor_state
    
    monitor_state['active'] = True
    monitor_state['start_time'] = time.time()
    monitor_state['current_benchmark'] = request.json.get('benchmark', 'Manual')
    
    return jsonify({'success': True, 'message': 'Monitoring started'})


@app.route('/api/power/stop', methods=['POST'])
def api_power_stop():
    """Stop power monitoring."""
    global monitor_state
    
    monitor_state['active'] = False
    monitor_state['current_benchmark'] = None
    
    return jsonify({'success': True, 'message': 'Monitoring stopped'})


@app.route('/api/power/reading', methods=['POST'])
def api_power_reading():
    """Add a power reading."""
    global monitor_state
    
    data = request.json
    power = data.get('power')
    
    if power is not None:
        monitor_state['power_readings'].append(power)
        
        # Keep only last 300 readings (5 minutes at 1Hz)
        if len(monitor_state['power_readings']) > 300:
            monitor_state['power_readings'] = monitor_state['power_readings'][-300:]
    
    return jsonify({'success': True})


def run_dashboard(host=None, port=None, debug=False):
    """Run the dashboard server.
    
    Args:
        host: Host address (default from config)
        port: Port number (default from config)
        debug: Enable debug mode
    """
    global config
    config = load_config()
    
    if host is None:
        host = config.get('dashboard', {}).get('host', 'localhost')
    if port is None:
        port = config.get('dashboard', {}).get('port', 5000)
    
    monitor_state['start_time'] = time.time()
    
    print("\n" + "="*60)
    print("LLM ENERGY ANALYSIS DASHBOARD")
    print("="*60)
    print(f"\n🌐 Dashboard running at: http://{host}:{port}")
    print(f"📊 Auto-refresh: {config.get('dashboard', {}).get('auto_refresh_interval', 5)}s")
    print("\nPress Ctrl+C to stop\n")
    print("="*60 + "\n")
    
    app.run(host=host, port=port, debug=debug)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run LLM Energy Analysis Dashboard")
    parser.add_argument('--host', default=None, help='Host address')
    parser.add_argument('--port', type=int, default=None, help='Port number')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--config', default='config.yaml', help='Config file path')
    
    args = parser.parse_args()
    
    try:
        run_dashboard(host=args.host, port=args.port, debug=args.debug)
    except KeyboardInterrupt:
        print("\n\n✅ Dashboard stopped")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
