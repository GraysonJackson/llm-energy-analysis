"""
Power Monitor Module - Shelly Smart Plug Integration

This module provides real-time power monitoring capabilities using the Shelly Smart Plug.
It connects via REST API to measure wattage and calculate energy consumption.
"""

import requests
import time
import logging
import math
import os
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime
from dotenv import dotenv_values

logger = logging.getLogger(__name__)


class PowerMonitor:
    """
    Interface to Shelly Smart Plug for power monitoring.
    
    Provides methods to:
    - Read current power consumption
    - Start/stop measurement sessions
    - Calculate total energy used
    - Export measurement data
    """

    @classmethod
    def from_config(cls, settings):
        env_path = Path(__file__).resolve().parent.parent / '.env'
        host = (os.getenv('SHELLY_IP') or dotenv_values(env_path).get('SHELLY_IP')
                or settings.get('ip_address') or '').strip()
        if not host:
            raise ValueError('Set SHELLY_IP in the repository .env file')
        return cls(host, settings.get('polling_interval', 1.0), settings.get('timeout', 5))
    
    def __init__(self, ip_address: str, polling_interval: float = 1.0, timeout: int = 5):
        """
        Initialize the power monitor.
        
        Args:
            ip_address: IP address of the Shelly Smart Plug
            polling_interval: Seconds between power readings (default: 1.0)
            timeout: HTTP request timeout in seconds (default: 5)
        """
        self.ip_address = ip_address
        self.polling_interval = polling_interval
        self.timeout = timeout
        self.base_url = f"http://{ip_address}"
        self._power_endpoint = None
        
        # Measurement state
        self.is_monitoring = False
        self.measurements: List[Dict] = []
        self.session_start_time: Optional[float] = None
        
        logger.info(f"PowerMonitor initialized for {ip_address}")
    
    def test_connection(self) -> bool:
        """
        Test connection to the Shelly plug.
        
        Returns:
            True if connection successful, False otherwise
        """
        return self.get_current_power() is not None
    
    def get_current_power(self) -> Optional[float]:
        """
        Get the current power consumption in watts.
        
        Returns:
            Power in watts, or None if reading failed
        """
        endpoints = (self._power_endpoint,) if self._power_endpoint else (
            '/rpc/Switch.GetStatus?id=0', '/status')
        failures = []
        for endpoint in endpoints:
            try:
                response = requests.get(self.base_url + endpoint, timeout=self.timeout,
                                        allow_redirects=False)
                if response.status_code != 200:
                    failures.append(f'{endpoint}: HTTP {response.status_code}')
                    if response.status_code in (401, 403):
                        break
                    continue
                data = response.json()
                power = data['apower'] if 'apower' in data else data['meters'][0]['power']
                if isinstance(power, bool):
                    raise ValueError('Expected a wattage')
                watts = float(power)
                if not math.isfinite(watts) or watts < 0:
                    raise ValueError('Expected finite, nonnegative watts')
            except (requests.RequestException, KeyError, IndexError, TypeError, ValueError) as exc:
                failures.append(f'{endpoint}: {type(exc).__name__}')
                continue
            self._power_endpoint = endpoint
            return watts
        logger.error('Shelly power reading unavailable (%s)', '; '.join(failures))
        return None
    
    def start_monitoring(self):
        """Start a monitoring session."""
        if self.is_monitoring:
            logger.warning("Monitoring already in progress")
            return
        
        self.measurements = []
        self.session_start_time = time.time()
        self.is_monitoring = True
        logger.info("Monitoring session started")
    
    def record_measurement(self) -> Optional[Dict]:
        """
        Record a single power measurement.
        
        Returns:
            Dict with timestamp and power, or None if reading failed
        """
        if not self.is_monitoring:
            logger.warning("Not currently monitoring. Call start_monitoring() first.")
            return None
        
        power = self.get_current_power()
        if power is None:
            return None
        
        measurement = {
            'timestamp': datetime.now().isoformat(),
            'elapsed_sec': time.time() - self.session_start_time,
            'power_w': power
        }
        
        self.measurements.append(measurement)
        return measurement
    
    def stop_monitoring(self) -> Dict:
        """
        Stop the monitoring session and return summary statistics.
        
        Returns:
            Dict containing session statistics
        """
        if not self.is_monitoring:
            logger.warning("No monitoring session to stop")
            return {}
        
        self.is_monitoring = False
        duration = time.time() - self.session_start_time
        
        if not self.measurements:
            logger.warning("No measurements recorded")
            return {'duration_sec': duration, 'measurement_count': 0}
        
        # Calculate statistics
        powers = [m['power_w'] for m in self.measurements]
        avg_power = sum(powers) / len(powers)
        min_power = min(powers)
        max_power = max(powers)
        
        # Energy = Power × Time
        # Trapezoidal integration for more accurate energy calculation
        energy_joules = 0.0
        for i in range(len(self.measurements) - 1):
            dt = self.measurements[i+1]['elapsed_sec'] - self.measurements[i]['elapsed_sec']
            avg_p = (self.measurements[i]['power_w'] + self.measurements[i+1]['power_w']) / 2
            energy_joules += avg_p * dt
        
        energy_wh = energy_joules / 3600  # Convert to watt-hours
        
        stats = {
            'duration_sec': duration,
            'measurement_count': len(self.measurements),
            'avg_power_w': avg_power,
            'min_power_w': min_power,
            'max_power_w': max_power,
            'energy_joules': energy_joules,
            'energy_wh': energy_wh
        }
        
        logger.info(f"Monitoring session complete: {stats}")
        return stats
    
    def get_measurements(self) -> List[Dict]:
        """
        Get all measurements from the current/last session.
        
        Returns:
            List of measurement dictionaries
        """
        return self.measurements.copy()
    
    def measure_baseline(self, duration: int = 60) -> Dict:
        """
        Measure baseline idle power for a specified duration.
        
        Args:
            duration: Measurement duration in seconds
            
        Returns:
            Dict with baseline statistics
        """
        logger.info(f"Measuring baseline power for {duration} seconds...")
        
        self.start_monitoring()
        
        try:
            end_time = time.time() + duration
            while time.time() < end_time:
                self.record_measurement()
                remaining = end_time - time.time()
                
                if remaining > 0:
                    time.sleep(min(self.polling_interval, remaining))
        
        except KeyboardInterrupt:
            logger.warning("Baseline measurement interrupted")
        
        finally:
            stats = self.stop_monitoring()
        
        return stats
    
    def monitor_during_task(self, task_func, *args, **kwargs):
        """
        Monitor power consumption during execution of a task function.
        
        Args:
            task_func: Function to execute while monitoring
            *args, **kwargs: Arguments to pass to task_func
            
        Returns:
            Tuple of (task_result, power_stats)
        """
        self.start_monitoring()
        
        # Start monitoring thread
        import threading
        stop_event = threading.Event()
        
        def monitor_loop():
            while not stop_event.is_set():
                self.record_measurement()
                time.sleep(self.polling_interval)
        
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
        
        try:
            # Execute the task
            result = task_func(*args, **kwargs)
        
        finally:
            # Stop monitoring
            stop_event.set()
            monitor_thread.join(timeout=5)
            stats = self.stop_monitoring()
        
        return result, stats
    
    def export_to_csv(self, filepath: str):
        """
        Export measurements to CSV file.
        
        Args:
            filepath: Path to output CSV file
        """
        import csv
        
        if not self.measurements:
            logger.warning("No measurements to export")
            return
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['timestamp', 'elapsed_sec', 'power_w'])
            writer.writeheader()
            writer.writerows(self.measurements)
        
        logger.info(f"Exported {len(self.measurements)} measurements to {filepath}")


def main():
    """Test the power monitor functionality."""
    import sys
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Load configuration
    try:
        import yaml
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        monitor = PowerMonitor.from_config(config['shelly'])
    
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        sys.exit(1)
    
    # Test connection
    print("\nTesting connection to the configured Shelly plug...")
    if not monitor.test_connection():
        print("❌ Connection failed!")
        print("\nTroubleshooting:")
        print("1. Check that SHELLY_IP in .env is correct")
        print("2. Ensure the Shelly plug is on the same network")
        print("3. Check the Shelly status API for your model")
        sys.exit(1)
    
    print("✅ Connection successful!")
    
    # Get current power
    print("\nReading current power consumption...")
    power = monitor.get_current_power()
    if power is not None:
        print(f"Current power: {power:.2f} W")
    
    # Measure baseline
    print("\nMeasuring baseline for 10 seconds...")
    baseline = monitor.measure_baseline(duration=10)
    if not baseline.get('measurement_count'):
        sys.exit('No Shelly power samples were received during baseline measurement')
    print(f"\nBaseline Statistics:")
    print(f"  Average Power: {baseline['avg_power_w']:.2f} W")
    print(f"  Min Power: {baseline['min_power_w']:.2f} W")
    print(f"  Max Power: {baseline['max_power_w']:.2f} W")
    print(f"  Total Energy: {baseline['energy_wh']:.4f} Wh ({baseline['energy_joules']:.2f} J)")
    
    print("\n✅ Power monitor test complete!")


if __name__ == "__main__":
    main()
