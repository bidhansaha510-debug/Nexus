"""Test the Computer Body system."""

import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from utils.logger import print_startup_banner
from body import computer_body

def test():
    print_startup_banner()
    print("\n" + "="*60)
    print("  COMPUTER BODY TEST")
    print("="*60)
    
    computer_body.start()
    time.sleep(1)
    
    # System info
    print("\n[1] System Identity:")
    print(f"    {computer_body.get_system_description()}")
    
    # Vitals
    print("\n[2] Vital Signs:")
    print(f"    {computer_body.get_vitals_description()}")
    
    # Detailed vitals
    v = computer_body.get_vitals()
    print(f"\n[3] Vitals Detail:")
    print(f"    CPU: {v.cpu_percent:.1f}% (cores: {v.cpu_per_core})")
    print(f"    RAM: {v.ram_percent:.1f}% ({v.ram_available_gb:.1f} GB free)")
    print(f"    Disk: {v.disk_percent:.1f}% ({v.disk_free_gb:.1f} GB free)")
    print(f"    Processes: {v.process_count}")
    print(f"    Health: {v.health_score:.0%}")
    
    # List home directory
    print(f"\n[4] Home Directory Contents (first 10):")
    items = computer_body.list_directory(str(Path.home()))[:10]
    for item in items:
        icon = "📁" if item.get("is_dir") else "📄"
        size = item.get("size_human", "")
        print(f"    {icon} {item['name']:30s} {size}")
    
    # Top processes
    print(f"\n[5] Top Processes by CPU:")
    procs = computer_body.get_running_processes(sort_by="cpu", limit=8)
    for p in procs:
        print(f"    PID {p['pid']:6d} | {p['name']:25s} | CPU: {p['cpu_percent']:5.1f}% | RAM: {p['memory_percent']:5.1f}%")
    
    # File operations test
    print(f"\n[6] File Operations Test:")
    test_path = str(DATA_DIR / "body_test.txt")
    
    computer_body.write_file(test_path, "Hello from NEXUS body!\nI can control files.", reason="Test")
    print(f"    Written: {test_path}")
    
    content = computer_body.read_file(test_path)
    print(f"    Read back: {content}")
    
    computer_body.append_file(test_path, "\nAppended line.", reason="Test append")
    content = computer_body.read_file(test_path)
    print(f"    After append: {content}")
    
    computer_body.delete_file(test_path, reason="Test cleanup")
    print(f"    Deleted test file")
    
    # Command execution
    print(f"\n[7] Command Execution:")
    if computer_body._is_windows:
        success, stdout, _ = computer_body.execute_command("echo Hello from NEXUS", reason="Test echo")
    else:
        success, stdout, _ = computer_body.execute_command("echo 'Hello from NEXUS'", reason="Test echo")
    print(f"    Result: {stdout.strip()}")
    
    # Network info
    print(f"\n[8] Network Info:")
    net = computer_body.get_network_info()
    print(f"    Hostname: {net['hostname']}")
    for iface, details in net.get("interfaces", {}).items():
        print(f"    {iface}: {details.get('ip', '?')}")
    print(f"    Active connections: {net.get('connections', '?')}")
    
    # Search files
    print(f"\n[9] Python files in NEXUS directory:")
    py_files = computer_body.search_files(str(Path(__file__).parent), "*.py", recursive=False)
    for f in py_files[:8]:
        print(f"    📄 {Path(f).name}")
    
    # Action log
    print(f"\n[10] Recent Actions:")
    for action in computer_body.get_action_log(5):
        status = "✅" if action["success"] else "❌"
        auto = " [AUTO]" if action["autonomous"] else ""
        print(f"    {status} [{action['action_type']}] {action['description'][:60]}{auto}")
    
    # Stats
    print(f"\n[11] Stats:")
    stats = computer_body.get_stats()
    print(f"    Actions logged: {stats['actions_logged']}")
    print(f"    Autonomous actions: {stats['autonomous_actions']}")
    
    computer_body.stop()
    print("\n✅ Computer Body test complete!")

if __name__ == "__main__":
    from config import DATA_DIR
    test()