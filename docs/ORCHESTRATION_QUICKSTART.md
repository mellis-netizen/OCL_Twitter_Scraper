# TGE Swarm Orchestration - Quick Start Guide

## Overview

The TGE Swarm Orchestration system combines the main TGE scraper with multi-agent coordination for maximum efficiency. This guide will help you get started quickly.

## Architecture at a Glance

```
Orchestrator → Specialized Agents → Parallel Execution → Shared Results
                     ↓
    News Scrapers + Twitter Monitors + Analyzers + Quality Checks
                     ↓
            Coordinated via Memory & Message Queue
```

## Prerequisites

1. **Python 3.8+**
2. **Redis** (for message queue)
3. **Optional**: Claude-Flow for advanced coordination

```bash
# Check Python version
python3 --version

# Install Redis (macOS)
brew install redis
brew services start redis

# Or use Docker
docker run -d -p 6379:6379 redis:latest

# Optional: Install Claude-Flow
npm install -g claude-flow@alpha
```

## Quick Start (5 Minutes)

### 1. Install Dependencies

```bash
cd /Users/apple/Documents/GitHub/OCL_Twitter_Scraper-1

# Install Python packages
pip3 install -r requirements.txt

# Install additional async dependencies
pip3 install aiofiles pyyaml redis
```

### 2. Create Configuration

```bash
# Copy example configuration
cp config/tge_swarm.yaml.example config/tge_swarm.yaml

# Edit configuration (optional)
# Set Twitter bearer token if using Twitter monitoring
nano config/tge_swarm.yaml
```

**Minimal Configuration** (config/tge_swarm.yaml):
```yaml
cluster_name: tge-swarm
redis_urls:
  - localhost:6379

agents:
  news_scraper:
    count: 2
  keyword_analyzer:
    count: 2
  data_quality:
    count: 1

companies:
  - name: "Example Project"
    tokens: ["EXPL"]
    priority: "HIGH"

keywords:
  - "token generation event"
  - "tge"
  - "airdrop"

news_sources:
  - "https://cointelegraph.com/rss"
```

### 3. Deploy and Run

```bash
# Deploy and start in one command
python3 scripts/deploy_swarm.py deploy-and-start

# Or step-by-step
python3 scripts/deploy_swarm.py deploy
python3 scripts/deploy_swarm.py start
```

### 4. Monitor Status

```bash
# Check system status
python3 scripts/deploy_swarm.py status

# Or use orchestrator directly
python3 src/orchestrator.py --status
```

## What Happens?

1. **Deployment Phase**:
   - Validates environment (Python, Redis)
   - Creates directory structure
   - Initializes message queue
   - Spawns specialized agents

2. **Operation Phase**:
   - Runs scraping cycles every 5 minutes (configurable)
   - News scrapers fetch articles in parallel
   - Twitter monitors search for TGE mentions
   - Keyword analyzers process content
   - Quality agents deduplicate results

3. **Results**:
   - Stored in shared memory (`tge-memory/`)
   - Available via status API
   - Logged to `logs/orchestrator.log`

## File Structure

```
OCL_Twitter_Scraper-1/
├── src/
│   ├── agents/                    # Specialized agent implementations
│   │   ├── base_agent.py         # Base agent class with hooks
│   │   ├── news_scraper_agent.py # News scraping agent
│   │   ├── twitter_monitor_agent.py
│   │   ├── keyword_analyzer_agent.py
│   │   ├── data_quality_agent.py
│   │   └── coordinator_agent.py
│   ├── orchestrator.py           # Main orchestration service
│   ├── message_queue_integration.py
│   ├── memory_coordinator.py
│   └── swarm_config.py
│
├── scripts/
│   └── deploy_swarm.py          # Deployment automation
│
├── config/
│   ├── tge_swarm.yaml           # Your configuration
│   └── tge_swarm.yaml.example   # Example template
│
├── docs/
│   ├── orchestration-architecture.md  # Full architecture docs
│   └── ORCHESTRATION_QUICKSTART.md    # This file
│
├── tge-memory/                  # Shared memory storage
│   ├── shared/                  # Cross-agent data
│   ├── dedup/                   # Deduplication cache
│   ├── agents/                  # Agent state
│   └── metrics/                 # Performance metrics
│
└── logs/                        # Log files
    ├── orchestrator.log
    └── deployment.log
```

## Configuration Guide

### Agent Scaling

Adjust agent counts based on your needs:

```yaml
agents:
  news_scraper:
    count: 4      # More scrapers = more parallel feeds
  twitter_monitor:
    count: 2      # Twitter rate limits apply
  keyword_analyzer:
    count: 4      # More analyzers = faster processing
  data_quality:
    count: 2      # Parallel deduplication
```

### Scraping Interval

```yaml
scraping_interval: 300  # Seconds between cycles (default: 5 min)
```

**Recommendations**:
- Development: 600 (10 minutes)
- Production: 300 (5 minutes)
- High-frequency: 120 (2 minutes)

### Companies and Keywords

Add companies you want to monitor:

```yaml
companies:
  - name: "Starknet"
    aliases: ["StarkWare", "STRK"]
    tokens: ["STRK"]
    priority: "HIGH"

  - name: "zkSync"
    aliases: ["Matter Labs", "ZK"]
    tokens: ["ZK"]
    priority: "HIGH"
```

Customize keywords:

```yaml
keywords:
  - "token generation event"
  - "tge is live"
  - "airdrop"
  - "token launch"
  # Add more specific keywords
```

## Advanced Features

### Claude-Flow Integration

Enable advanced coordination with Claude-Flow hooks:

```bash
# Install Claude-Flow
npm install -g claude-flow@alpha

# Initialize swarm
npx claude-flow@alpha swarm init --topology mesh

# Hooks are automatically used when available
```

Benefits:
- Session management
- Memory persistence
- Neural pattern learning
- Automated coordination

### Custom Agents

Create your own specialized agent:

```python
# src/agents/my_custom_agent.py
from src.agents.base_agent import BaseAgent

class MyCustomAgent(BaseAgent):
    async def _do_initialize(self):
        self.logger.info("Custom agent initialized")

    async def _execute_task_impl(self, task):
        # Your custom logic
        return {'result': 'success'}

    async def _do_shutdown(self):
        self.logger.info("Custom agent shutdown")
```

Register in orchestrator:

```python
# src/orchestrator.py
from src.agents.my_custom_agent import MyCustomAgent

# In _initialize_agents()
agent = MyCustomAgent(agent_id='custom-1', config={})
await agent.initialize()
self.agents['custom-1'] = agent
```

### Monitoring and Metrics

**View Real-Time Status**:
```bash
watch -n 5 'python3 src/orchestrator.py --status'
```

**Check Logs**:
```bash
tail -f logs/orchestrator.log
```

**Memory Statistics**:
```python
from src.memory_coordinator import TGEMemoryCoordinator

coordinator = TGEMemoryCoordinator('./tge-memory')
await coordinator.initialize()
stats = await coordinator.get_stats()
print(stats)
```

## Troubleshooting

### Redis Not Running

```bash
# Check Redis
redis-cli ping
# Should return: PONG

# Start Redis
redis-server

# Or with Docker
docker run -d -p 6379:6379 redis:latest
```

### Import Errors

```bash
# Ensure all dependencies installed
pip3 install -r requirements.txt
pip3 install aiofiles pyyaml redis asyncio
```

### No Agents Initialized

Check configuration:
```bash
cat config/tge_swarm.yaml | grep -A 10 "agents:"
```

Ensure agent counts > 0:
```yaml
agents:
  news_scraper:
    count: 2  # Must be > 0
```

### High Memory Usage

Reduce agent counts or enable cleanup:

```python
# In orchestrator or via cron
await memory_coordinator.cleanup_old_entries(max_age_days=3)
```

## Performance Tips

1. **Optimize Agent Counts**:
   - More agents = more parallelism
   - But also more memory usage
   - Balance based on your server capacity

2. **Tune Scraping Interval**:
   - Longer intervals = less load
   - But slower TGE detection
   - 5 minutes is a good balance

3. **Enable Caching**:
   - Shared memory reduces duplicate work
   - Deduplication prevents reprocessing
   - Rate limit sharing prevents API overuse

4. **Monitor Performance**:
   - Check logs for bottlenecks
   - View memory statistics
   - Adjust configuration accordingly

## Integration with Existing System

The orchestration system works alongside your existing TGE monitor:

```python
# Use orchestrator for parallel scraping
from src.orchestrator import TGESwarmOrchestrator

orchestrator = TGESwarmOrchestrator('config/tge_swarm.yaml')
await orchestrator.initialize()

# Run one cycle
await orchestrator.orchestrate_scraping_cycle()

# Get results from shared memory
latest_data = await orchestrator.memory_coordinator.retrieve_shared_data('latest_cycle')
```

Or run as a separate service:

```bash
# Terminal 1: Run orchestrator
python3 scripts/deploy_swarm.py start

# Terminal 2: Your existing system continues
python3 src/main_optimized_db.py
```

## Next Steps

1. **Read Full Documentation**: `docs/orchestration-architecture.md`
2. **Customize Configuration**: `config/tge_swarm.yaml`
3. **Explore Agents**: `src/agents/`
4. **Set Up Monitoring**: Grafana + Prometheus (coming soon)
5. **Deploy to Production**: Docker + Kubernetes (future)

## Getting Help

- **Documentation**: `docs/orchestration-architecture.md`
- **Configuration Examples**: `config/tge_swarm.yaml.example`
- **Issues**: Check logs in `logs/`
- **Status**: `python3 scripts/deploy_swarm.py status`

## What's Next?

- **Phase 2**: Multi-node deployment support
- **Phase 3**: Neural pattern learning
- **Phase 4**: Production monitoring dashboards

---

**Version**: 1.0
**Last Updated**: 2025-10-11

Happy swarm orchestrating! 🚀
