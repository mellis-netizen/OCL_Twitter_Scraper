# TGE Swarm Security Groups
# Comprehensive security group configuration following principle of least privilege

# Application Load Balancer Security Group
resource "aws_security_group" "alb" {
  name_prefix = "${local.name_prefix}-alb-"
  vpc_id      = aws_vpc.main.id
  
  # HTTP access from internet
  ingress {
    description = "HTTP from internet"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
  }
  
  # HTTPS access from internet
  ingress {
    description = "HTTPS from internet"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
  }
  
  # All outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Name = "${local.name_prefix}-alb-sg"
    Purpose = "Application Load Balancer"
  }
}

# Swarm Queen Security Group
resource "aws_security_group" "swarm_queen" {
  name_prefix = "${local.name_prefix}-queen-"
  vpc_id      = aws_vpc.main.id
  
  # API port from ALB
  ingress {
    description     = "Queen API from ALB"
    from_port       = local.service_ports.queen_api
    to_port         = local.service_ports.queen_api
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
  
  # Metrics port from monitoring
  ingress {
    description     = "Queen metrics from monitoring"
    from_port       = local.service_ports.queen_metrics
    to_port         = local.service_ports.queen_metrics
    protocol        = "tcp"
    security_groups = [aws_security_group.monitoring.id]
  }
  
  # SSH access from bastion
  ingress {
    description     = "SSH from bastion"
    from_port       = 22
    to_port         = 22
    protocol        = "tcp"
    security_groups = [aws_security_group.bastion.id]
  }
  
  # All outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Name = "${local.name_prefix}-queen-sg"
    Purpose = "Swarm Queen Orchestrator"
  }
}

# Memory Coordinator Security Group
resource "aws_security_group" "memory_coordinator" {
  name_prefix = "${local.name_prefix}-coordinator-"
  vpc_id      = aws_vpc.main.id
  
  # Coordinator API from queen and agents
  ingress {
    description     = "Coordinator API from Queen"
    from_port       = local.service_ports.coordinator
    to_port         = local.service_ports.coordinator
    protocol        = "tcp"
    security_groups = [aws_security_group.swarm_queen.id]
  }
  
  ingress {
    description     = "Coordinator API from Agents"
    from_port       = local.service_ports.coordinator
    to_port         = local.service_ports.coordinator
    protocol        = "tcp"
    security_groups = [aws_security_group.swarm_agents.id]
  }
  
  # SSH access from bastion
  ingress {
    description     = "SSH from bastion"
    from_port       = 22
    to_port         = 22
    protocol        = "tcp"
    security_groups = [aws_security_group.bastion.id]
  }
  
  # All outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Name = "${local.name_prefix}-coordinator-sg"
    Purpose = "Memory Coordinator"
  }
}

# Swarm Agents Security Group
resource "aws_security_group" "swarm_agents" {
  name_prefix = "${local.name_prefix}-agents-"
  vpc_id      = aws_vpc.main.id
  
  # Agent metrics ports from monitoring
  ingress {
    description     = "Agent metrics from monitoring"
    from_port       = 8010
    to_port         = 8020
    protocol        = "tcp"
    security_groups = [aws_security_group.monitoring.id]
  }
  
  # Inter-agent communication
  ingress {
    description = "Inter-agent communication"
    from_port   = 8000
    to_port     = 8999
    protocol    = "tcp"
    self        = true
  }
  
  # SSH access from bastion
  ingress {
    description     = "SSH from bastion"
    from_port       = 22
    to_port         = 22
    protocol        = "tcp"
    security_groups = [aws_security_group.bastion.id]
  }
  
  # All outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Name = "${local.name_prefix}-agents-sg"
    Purpose = "Swarm Agents"
  }
}

# PostgreSQL Database Security Group
resource "aws_security_group" "postgres" {
  name_prefix = "${local.name_prefix}-postgres-"
  vpc_id      = aws_vpc.main.id
  
  # PostgreSQL port from application servers
  ingress {
    description     = "PostgreSQL from Queen"
    from_port       = local.service_ports.postgres
    to_port         = local.service_ports.postgres
    protocol        = "tcp"
    security_groups = [aws_security_group.swarm_queen.id]
  }
  
  ingress {
    description     = "PostgreSQL from Coordinator"
    from_port       = local.service_ports.postgres
    to_port         = local.service_ports.postgres
    protocol        = "tcp"
    security_groups = [aws_security_group.memory_coordinator.id]
  }
  
  ingress {
    description     = "PostgreSQL from Agents"
    from_port       = local.service_ports.postgres
    to_port         = local.service_ports.postgres
    protocol        = "tcp"
    security_groups = [aws_security_group.swarm_agents.id]
  }
  
  ingress {
    description     = "PostgreSQL from Monitoring"
    from_port       = local.service_ports.postgres
    to_port         = local.service_ports.postgres
    protocol        = "tcp"
    security_groups = [aws_security_group.monitoring.id]
  }
  
  tags = {
    Name = "${local.name_prefix}-postgres-sg"
    Purpose = "PostgreSQL Database"
  }
}

# Redis Cache Security Group
resource "aws_security_group" "redis" {
  name_prefix = "${local.name_prefix}-redis-"
  vpc_id      = aws_vpc.main.id
  
  # Redis cluster ports from application servers
  ingress {
    description     = "Redis from Queen"
    from_port       = local.service_ports.redis_start
    to_port         = local.service_ports.redis_end
    protocol        = "tcp"
    security_groups = [aws_security_group.swarm_queen.id]
  }
  
  ingress {
    description     = "Redis from Coordinator"
    from_port       = local.service_ports.redis_start
    to_port         = local.service_ports.redis_end
    protocol        = "tcp"
    security_groups = [aws_security_group.memory_coordinator.id]
  }
  
  ingress {
    description     = "Redis from Agents"
    from_port       = local.service_ports.redis_start
    to_port         = local.service_ports.redis_end
    protocol        = "tcp"
    security_groups = [aws_security_group.swarm_agents.id]
  }
  
  # Redis default port for single instance mode
  ingress {
    description     = "Redis default port"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [
      aws_security_group.swarm_queen.id,
      aws_security_group.memory_coordinator.id,
      aws_security_group.swarm_agents.id
    ]
  }
  
  tags = {
    Name = "${local.name_prefix}-redis-sg"
    Purpose = "Redis Cache Cluster"
  }
}

# Monitoring Security Group (Prometheus, Grafana, etc.)
resource "aws_security_group" "monitoring" {
  name_prefix = "${local.name_prefix}-monitoring-"
  vpc_id      = aws_vpc.main.id
  
  # Prometheus port from ALB and internal
  ingress {
    description     = "Prometheus from ALB"
    from_port       = local.service_ports.prometheus
    to_port         = local.service_ports.prometheus
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
  
  # Grafana port from ALB
  ingress {
    description     = "Grafana from ALB"
    from_port       = local.service_ports.grafana
    to_port         = local.service_ports.grafana
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
  
  # AlertManager port
  ingress {
    description     = "AlertManager from ALB"
    from_port       = local.service_ports.alertmanager
    to_port         = local.service_ports.alertmanager
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
  
  # Jaeger port from ALB
  ingress {
    description     = "Jaeger from ALB"
    from_port       = local.service_ports.jaeger
    to_port         = local.service_ports.jaeger
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
  
  # SSH access from bastion
  ingress {
    description     = "SSH from bastion"
    from_port       = 22
    to_port         = 22
    protocol        = "tcp"
    security_groups = [aws_security_group.bastion.id]
  }
  
  # All outbound traffic for scraping metrics
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Name = "${local.name_prefix}-monitoring-sg"
    Purpose = "Monitoring Stack"
  }
}

# Consul Service Discovery Security Group
resource "aws_security_group" "consul" {
  name_prefix = "${local.name_prefix}-consul-"
  vpc_id      = aws_vpc.main.id
  
  # Consul HTTP API
  ingress {
    description     = "Consul HTTP API"
    from_port       = local.service_ports.consul
    to_port         = local.service_ports.consul
    protocol        = "tcp"
    security_groups = [
      aws_security_group.swarm_queen.id,
      aws_security_group.memory_coordinator.id,
      aws_security_group.swarm_agents.id,
      aws_security_group.monitoring.id
    ]
  }
  
  # Consul DNS
  ingress {
    description = "Consul DNS"
    from_port   = 8600
    to_port     = 8600
    protocol    = "udp"
    cidr_blocks = [var.vpc_cidr]
  }
  
  # Consul Gossip (TCP)
  ingress {
    description = "Consul Gossip TCP"
    from_port   = 8301
    to_port     = 8301
    protocol    = "tcp"
    self        = true
  }
  
  # Consul Gossip (UDP)
  ingress {
    description = "Consul Gossip UDP"
    from_port   = 8301
    to_port     = 8301
    protocol    = "udp"
    self        = true
  }
  
  # SSH access from bastion
  ingress {
    description     = "SSH from bastion"
    from_port       = 22
    to_port         = 22
    protocol        = "tcp"
    security_groups = [aws_security_group.bastion.id]
  }
  
  # All outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Name = "${local.name_prefix}-consul-sg"
    Purpose = "Consul Service Discovery"
  }
}

# Bastion Host Security Group
resource "aws_security_group" "bastion" {
  name_prefix = "${local.name_prefix}-bastion-"
  vpc_id      = aws_vpc.main.id
  
  # SSH access from allowed CIDR blocks
  ingress {
    description = "SSH from allowed IPs"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
  }
  
  # All outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Name = "${local.name_prefix}-bastion-sg"
    Purpose = "Bastion Host"
  }
}

# Security Group for backup instances
resource "aws_security_group" "backup" {
  name_prefix = "${local.name_prefix}-backup-"
  vpc_id      = aws_vpc.main.id
  
  # SSH access from bastion
  ingress {
    description     = "SSH from bastion"
    from_port       = 22
    to_port         = 22
    protocol        = "tcp"
    security_groups = [aws_security_group.bastion.id]
  }
  
  # All outbound traffic for backup operations
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Name = "${local.name_prefix}-backup-sg"
    Purpose = "Backup Services"
  }
}