"""
Power Monitor Module - Shelly Smart Plug Integration

This module provides real-time power monitoring capabilities using the Shelly Smart Plug.
It connects via REST API to measure wattage and calculate energy consumption.
"""

import requests
import time
import logging
from typing import Optional, Dict, List
from datetime import datetime

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
        try:
            response = requests.get(
                f"{self.base_url}/status",
                timeout=self.timeout
            )
            response.raise_for_status()
            logger.info("Shelly plug connection successful")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to Shelly plug: {e}")
            return False
    
    def get_current_power(self) -> Optional[float]:
        """
        Get the current power consumption in watts.
        
        Returns:
            Power in watts, or None if reading failed
        """
        try:
            response = requests.get(
                f"{self.base_url}/status",
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            
            # Shelly plug returns power in watts under 'meters' array
            # Different Shelly models may have different response structures
            if 'meters' in data and len(data['meters']) > 0:
                power = data['meters'][0]['power']
            elif 'apower' in data:  # Some models use 'apower' (active power)
                power = data['apower']
            else:
                logger.error(f"Unexpected response format: {data}")
                return None
            
            return float(power)
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to read power: {e}")
            return None
        except (KeyError, IndexError, ValueError) as e:
            logger.error(f"Failed to parse power data: {e}")
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
        
        ip_address = config['shelly']['ip_address']
        polling_interval = config['shelly']['polling_interval']
        timeout = config['shelly']['timeout']
    
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        logger.info("Using default IP address 192.168.1.100")
        ip_address = "192.168.1.100"
        polling_interval = 1.0
        timeout = 5
    
    # Create monitor
    monitor = PowerMonitor(ip_address, polling_interval, timeout)
    
    # Test connection
    print(f"\nTesting connection to Shelly plug at {ip_address}...")
    if not monitor.test_connection():
        print("❌ Connection failed!")
        print("\nTroubleshooting:")
        print("1. Check that the IP address in config.yaml is correct")
        print("2. Ensure the Shelly plug is on the same network")
        print("3. Try accessing http://{ip_address}/status in your browser")
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
    print(f"\nBaseline Statistics:")
    print(f"  Average Power: {baseline['avg_power_w']:.2f} W")
    print(f"  Min Power: {baseline['min_power_w']:.2f} W")
    print(f"  Max Power: {baseline['max_power_w']:.2f} W")
    print(f"  Total Energy: {baseline['energy_wh']:.4f} Wh ({baseline['energy_joules']:.2f} J)")
    
    print("\n✅ Power monitor test complete!")


if __name__ == "__main__":
    main()
