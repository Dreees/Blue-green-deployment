#!/usr/bin/env python3
import os
import re
import time
import json
import requests
from collections import deque
from datetime import datetime

SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL')
ERROR_RATE_THRESHOLD = float(os.getenv('ERROR_RATE_THRESHOLD', '2'))
WINDOW_SIZE = int(os.getenv('WINDOW_SIZE', '200'))
ALERT_COOLDOWN_SEC = int(os.getenv('ALERT_COOLDOWN_SEC', '300'))

LOG_FILE = '/var/log/nginx/access.log'

# State tracking
last_pool = None
request_window = deque(maxlen=WINDOW_SIZE)
last_failover_alert = None
last_error_rate_alert = None
processed_lines = 0

# Regex to parse custom log format - more flexible
LOG_PATTERN = re.compile(
    r'pool=(?P<pool>\w+)\s+'
    r'release=(?P<release>[\w\.\-]+)\s+'
    r'upstream_status=(?P<upstream_status>\d+)'
)

def send_slack_alert(message, alert_type):
    """Send alert to Slack with cooldown"""
    global last_failover_alert, last_error_rate_alert
    
    if not SLACK_WEBHOOK_URL:
        print(f"[ALERT - NO WEBHOOK] {message}")
        return
    
    now = datetime.now()
    
    # Check cooldown
    if alert_type == 'failover' and last_failover_alert:
        elapsed = (now - last_failover_alert).total_seconds()
        if elapsed < ALERT_COOLDOWN_SEC:
            print(f"[COOLDOWN] Skipping failover alert (last sent {elapsed:.0f}s ago)")
            return
    elif alert_type == 'error_rate' and last_error_rate_alert:
        elapsed = (now - last_error_rate_alert).total_seconds()
        if elapsed < ALERT_COOLDOWN_SEC:
            print(f"[COOLDOWN] Skipping error rate alert (last sent {elapsed:.0f}s ago)")
            return
    
    payload = {
        "text": message,
        "username": "DevOps Monitor",
        "icon_emoji": ":warning:"
    }
    
    try:
        print(f"[SLACK] Sending alert to Slack...")
        response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=5)
        if response.status_code == 200:
            print(f"[SLACK] ✓ Alert sent successfully!")
            print(f"[SLACK] Message: {message}")
            if alert_type == 'failover':
                last_failover_alert = now
            elif alert_type == 'error_rate':
                last_error_rate_alert = now
        else:
            print(f"[SLACK ERROR] Status {response.status_code}: {response.text}")
    except Exception as e:
        print(f"[SLACK ERROR] Failed to send: {e}")

def calculate_error_rate():
    """Calculate 5xx error rate over the window"""
    if len(request_window) == 0:
        return 0.0
    
    error_count = sum(1 for status in request_window if status >= 500)
    return (error_count / len(request_window)) * 100

def process_log_line(line):
    """Parse and process a single log line"""
    global last_pool, processed_lines
    
    processed_lines += 1
    
    match = LOG_PATTERN.search(line)
    if not match:
        if processed_lines <= 5:  # Only show first few parse failures
            print(f"[PARSE FAILED] Line: {line[:100]}")
        return
    
    pool = match.group('pool')
    release = match.group('release')
    upstream_status = int(match.group('upstream_status'))
    
    print(f"[PARSED #{processed_lines}] Pool: {pool}, Status: {upstream_status}, Release: {release}")
    
    # Track request in window
    request_window.append(upstream_status)
    
    # Detect failover
    if last_pool is not None and last_pool != pool:
        print(f"[FAILOVER DETECTED!] {last_pool} → {pool}")
        message = (
            f"🚨 *Failover Detected!* 🚨\n"
            f"Pool switched: `{last_pool}` → `{pool}`\n"
            f"Release: `{release}`\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Action: Check health of `{last_pool}` container"
        )
        send_slack_alert(message, 'failover')
    
    # Set the pool for next comparison
    if last_pool is None:
        print(f"[INITIAL POOL] Set to: {pool}")
    last_pool = pool
    
    # Check error rate
    if len(request_window) >= WINDOW_SIZE:
        error_rate = calculate_error_rate()
        print(f"[ERROR RATE] {error_rate:.2f}% over last {len(request_window)} requests")
        
        if error_rate > ERROR_RATE_THRESHOLD:
            print(f"[ERROR RATE ALERT!] {error_rate:.2f}% exceeds threshold {ERROR_RATE_THRESHOLD}%")
            message = (
                f"🚨 *High Error Rate Alert!* 🚨\n"
                f"Error rate: `{error_rate:.2f}%` (threshold: {ERROR_RATE_THRESHOLD}%)\n"
                f"Window size: {WINDOW_SIZE} requests\n"
                f"Current pool: `{pool}`\n"
                f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Action: Inspect logs and consider switching pools"
            )
            send_slack_alert(message, 'error_rate')
    else:
        print(f"[WINDOW] {len(request_window)}/{WINDOW_SIZE} requests collected")

def tail_log_file():
    """Tail the Nginx log file without seeking"""
    print(f"[WATCHER] ========================================")
    print(f"[WATCHER] Starting Blue/Green Log Watcher")
    print(f"[WATCHER] ========================================")
    print(f"[WATCHER] Monitoring: {LOG_FILE}")
    print(f"[WATCHER] Error threshold: {ERROR_RATE_THRESHOLD}%")
    print(f"[WATCHER] Window size: {WINDOW_SIZE} requests")
    print(f"[WATCHER] Alert cooldown: {ALERT_COOLDOWN_SEC}s")
    print(f"[WATCHER] Slack configured: {'YES' if SLACK_WEBHOOK_URL else 'NO'}")
    
    if SLACK_WEBHOOK_URL:
        print(f"[WATCHER] Webhook: {SLACK_WEBHOOK_URL[:50]}...")
    
    print(f"[WATCHER] ========================================\n")
    
    
    while not os.path.exists(LOG_FILE):
        print(f"[WATCHER] Waiting for {LOG_FILE}...")
        time.sleep(2)
    
    print(f"[WATCHER]  Log file found!")
    print(f"[WATCHER] Starting to monitor new log entries...\n")
    

    import subprocess
    
    proc = subprocess.Popen(
        ['tail', '-F', '-n', '0', LOG_FILE], 
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        bufsize=1  # Line buffered
    )
    
    print(f"[WATCHER] ✓ Tail process started (PID: {proc.pid})")
    print(f"[WATCHER] Waiting for new log entries...\n")
    
    try:
        while True:
            line = proc.stdout.readline()
            if line:
                process_log_line(line.strip())
            else:
                # Check if process is still alive
                if proc.poll() is not None:
                    print(f"[WATCHER ERROR] Tail process died!")
                    break
                time.sleep(0.1)
    except KeyboardInterrupt:
        print(f"\n[WATCHER] Shutting down gracefully...")
        proc.kill()
    except Exception as e:
        print(f"[WATCHER ERROR] {e}")
        proc.kill()

if __name__ == '__main__':
    tail_log_file()