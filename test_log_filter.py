import time
def search_log_for_chat(logfile, wait_time=20):
    start = time.time()
    seen = set()
    print("Watching log for chat events...")
    while time.time() - start < wait_time:
        with open(logfile, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()[-300:] # read last 300
            for line in lines:
                if 'CHAT' in line or 'web_server' in line.lower() or 'error' in line.lower() or 'traceback' in line.lower():
                    if line not in seen:
                        print(line.strip())
                        seen.add(line)
        time.sleep(1)

if __name__ == "__main__":
    search_log_for_chat("d:/NEXUS/data/logs/nexus_all.log")
