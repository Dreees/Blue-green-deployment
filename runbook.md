# Blue/Green Deployment Runbook

## Alert Types and Response Actions

### 1. Failover Detected Alert

**What it means:**
- Traffic has automatically switched between pools(e.g., blue → green)
- The backup pool became active to maintain availability
- Nginx detected upstream failures in the active pool

**Alert Example:**
```
🚨 Failover Detected! 🚨
Pool switched: blue → green
Release: v1.0.1
Log: <timestamp>
Action: Check health of blue container
```

**Operator Actions:**

1. **Verify the failover status:**
```bash
   curl http://localhost:8080/version
```

2. **Inspect failed container logs:**
```bash
   docker logs app_blue or docker logs app_green
```

3. **Check container health endpoints:**
```bash
   docker ps
   curl http://localhost:8081/healthz  # Blue
   curl http://localhost:8082/healthz  # Green
```
---

### 2. High Error Rate Alert

**What it means:**
- More than ${ERROR_RATE_THRESHOLD}% of requests resulted in 5xx errors
- Calculated over ${WINDOW_SIZE} requests
- Indicates instability in the active pool

**Alert Example:**
```
🚨 High Error Rate Alert! 🚨
Error rate: 5.50% (threshold: 2%)
Window size: 200 requests
Current pool: green
Log: <timestamp> 
Action: Inspect logs and consider switching pools
```

---

## Monitoring Commands
```bash

# View watcher logs
docker logs -f alert_watcher

# Check all containers
docker ps

#View Nginx logs
docker exec nginx tail -f /var/log/nginx/access.log
---

## Testing & Chaos Simulation

### Test Failover
```bash
# 1. Verify baseline
curl http://localhost:8080/version

# 2. TRigger failure in blue pool
curl -X POST http://localhost:8081/chaos/start?mode=error

# 3. Verify failover (should see green)
for i in {1..20}; do curl -s http://localhost:8080/version | grep pool; sleep 0.5; done

# 4. Check Slack for failover alert

# 5. Stop chaos
curl -X POST http://localhost:8081/chaos/stop
```

### Test High Error Rate Alert
```bash
# 1. Start chaos
curl -X POST http://localhost:8081/chaos/start?mode=error

# 2. Generate 200+ requests
for i in {1..240}; do curl -s http://localhost:8080/version > /dev/null; sleep 0.1; done

# 3. Check Slack for error rate alert

# 4. Stop chaos
curl -X POST http://localhost:8081/chaos/stop
```
### Alert Cooldown

- Failover alerts: 300 seconds (5 minutes) cooldown by default
- Error rate alerts: 300 seconds (5 minutes) cooldown by default
- Adjust `ALERT_COOLDOWN_SEC` in `.env` if needed

