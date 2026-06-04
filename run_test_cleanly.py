import subprocess
try:
    result = subprocess.run(['python', 'test_web_chat.py'], capture_output=True, text=True, encoding='utf-8', errors='ignore')
    print("STDOUT:")
    print(result.stdout)
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
except Exception as e:
    print(f"Error: {e}")
