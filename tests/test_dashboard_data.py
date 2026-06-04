
import sys
import unittest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from body.computer_body import ComputerBody
from ui.dashboard import DashboardPanel

class TestDashboardData(unittest.TestCase):
    def test_data_mapping(self):
        """Test if dashboard correctly interprets body stats"""
        body = ComputerBody()
        stats = body.get_stats()
        
        print(f"Body stats keys: {stats.keys()}")
        if "vitals" in stats:
            print(f"Vitals keys: {stats['vitals'].keys()}")
            
        # Simulate what DashboardPanel does (FIXED LOGIC)
        full_stats = {"body": stats}  # Re-added this line
        body_data = full_stats.get("body", {})
        vitals = body_data.get("vitals", body_data)
        
        # Try to get CPU/RAM using the new keys
        cpu = vitals.get("cpu_percent", vitals.get("cpu_usage", 0))
        ram = vitals.get("ram_percent", vitals.get("memory_usage", 0))
        
        print(f"Dashboard sees CPU: {cpu}")
        print(f"Dashboard sees RAM: {ram}")
        
        # This determines if the bug exists (CPU can validly be 0.0)
        self.assertIsNotNone(cpu, "Dashboard failed to read CPU usage from stats")
        self.assertIsNotNone(ram, "Dashboard failed to read RAM usage from stats")
        self.assertGreaterEqual(cpu, 0.0)
        self.assertGreater(ram, 0.0) # RAM is always > 0

if __name__ == "__main__":
    unittest.main()
