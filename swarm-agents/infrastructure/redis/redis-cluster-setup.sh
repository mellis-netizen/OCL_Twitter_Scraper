#!/bin/bash
# Redis Cluster Setup Script for TGE Swarm
# Configures a 3-master Redis cluster with pub/sub and persistence

set -e

REDIS_PASSWORD=${REDIS_PASSWORD:-redis_secure_pass}
CLUSTER_NODES="redis-master-1:7001 redis-master-2:7002 redis-master-3:7003"

echo "🔧 Setting up Redis Cluster for TGE Swarm..."

# Wait for all Redis nodes to be ready
echo "⏳ Waiting for Redis nodes to be ready..."
for node in $CLUSTER_NODES; do
    host=$(echo $node | cut -d: -f1)
    port=$(echo $node | cut -d: -f2)
    
    echo "Checking $host:$port..."
    while ! redis-cli -h $host -p $port -a $REDIS_PASSWORD ping > /dev/null 2>&1; do
        echo "Waiting for $host:$port to be ready..."
        sleep 2
    done
    echo "✅ $host:$port is ready"
done

# Create Redis cluster
echo "🚀 Creating Redis cluster..."
redis-cli --cluster create \
    redis-master-1:7001 \
    redis-master-2:7002 \
    redis-master-3:7003 \
    --cluster-replicas 0 \
    --cluster-yes \
    -a $REDIS_PASSWORD

# Verify cluster status
echo "📊 Verifying cluster status..."
redis-cli -h redis-master-1 -p 7001 -a $REDIS_PASSWORD cluster nodes

# Configure pub/sub channels for swarm communication
echo "📡 Setting up pub/sub channels..."

# Agent communication channels
redis-cli -h redis-master-1 -p 7001 -a $REDIS_PASSWORD << EOF
CONFIG SET notify-keyspace-events Ex
SET swarm:channels:agent-communication "ready"
SET swarm:channels:queen-commands "ready"
SET swarm:channels:memory-sync "ready"
SET swarm:channels:health-checks "ready"
SET swarm:channels:deployment-events "ready"
EOF

# Memory coordination channels
redis-cli -h redis-master-2 -p 7002 -a $REDIS_PASSWORD << EOF
SET swarm:memory:shared-insights "ready"
SET swarm:memory:cross-pollination "ready"
SET swarm:memory:synthesis-queue "ready"
SET swarm:memory:priority-alerts "ready"
EOF

# Performance monitoring channels
redis-cli -h redis-master-3 -p 7003 -a $REDIS_PASSWORD << EOF
SET swarm:metrics:performance "ready"
SET swarm:metrics:health "ready"
SET swarm:metrics:resource-usage "ready"
SET swarm:metrics:alerts "ready"
EOF

echo "✅ Redis cluster setup complete!"

# Test cluster operations
echo "🧪 Testing cluster operations..."

# Test basic operations across nodes
redis-cli -h redis-master-1 -p 7001 -a $REDIS_PASSWORD SET test:key1 "value1"
redis-cli -h redis-master-2 -p 7002 -a $REDIS_PASSWORD SET test:key2 "value2"
redis-cli -h redis-master-3 -p 7003 -a $REDIS_PASSWORD SET test:key3 "value3"

# Test retrieval
value1=$(redis-cli -h redis-master-1 -p 7001 -a $REDIS_PASSWORD GET test:key1)
value2=$(redis-cli -h redis-master-2 -p 7002 -a $REDIS_PASSWORD GET test:key2)
value3=$(redis-cli -h redis-master-3 -p 7003 -a $REDIS_PASSWORD GET test:key3)

if [[ "$value1" == "value1" && "$value2" == "value2" && "$value3" == "value3" ]]; then
    echo "✅ Cluster operations test passed"
else
    echo "❌ Cluster operations test failed"
    exit 1
fi

# Test pub/sub
echo "🔔 Testing pub/sub functionality..."
(redis-cli -h redis-master-1 -p 7001 -a $REDIS_PASSWORD SUBSCRIBE swarm:test:channel > /tmp/pubsub_test.log 2>&1 &)
sleep 2
redis-cli -h redis-master-2 -p 7002 -a $REDIS_PASSWORD PUBLISH swarm:test:channel "test message"
sleep 2

if grep -q "test message" /tmp/pubsub_test.log; then
    echo "✅ Pub/sub test passed"
else
    echo "❌ Pub/sub test failed"
fi

# Cleanup test keys
redis-cli -h redis-master-1 -p 7001 -a $REDIS_PASSWORD DEL test:key1 test:key2 test:key3
pkill -f "redis-cli.*SUBSCRIBE" || true
rm -f /tmp/pubsub_test.log

echo "🎉 Redis cluster is ready for TGE Swarm operations!"

# Print cluster information
echo ""
echo "📋 Cluster Information:"
echo "============================"
echo "Cluster Nodes: $CLUSTER_NODES"
echo "Password: [PROTECTED]"
echo "Pub/Sub Channels:"
echo "  - swarm:channels:agent-communication"
echo "  - swarm:channels:queen-commands"
echo "  - swarm:channels:memory-sync"
echo "  - swarm:channels:health-checks"
echo "  - swarm:channels:deployment-events"
echo "  - swarm:memory:* (memory coordination)"
echo "  - swarm:metrics:* (performance monitoring)"
echo ""
echo "Health Check Commands:"
echo "  redis-cli -h redis-master-1 -p 7001 -a \$REDIS_PASSWORD cluster info"
echo "  redis-cli -h redis-master-1 -p 7001 -a \$REDIS_PASSWORD cluster nodes"
echo "============================"