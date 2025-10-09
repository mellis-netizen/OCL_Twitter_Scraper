# TGE Swarm Application Load Balancer Configuration
# High availability load balancing with SSL termination and health checks

# Application Load Balancer
resource "aws_lb" "main" {
  name               = "${local.name_prefix}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id
  
  enable_deletion_protection       = var.alb_config.enable_deletion_protection
  idle_timeout                    = var.alb_config.idle_timeout
  enable_http2                    = var.alb_config.enable_http2
  enable_cross_zone_load_balancing = var.alb_config.enable_cross_zone_load_balancing
  
  # Access logs
  access_logs {
    bucket  = aws_s3_bucket.alb_logs.bucket
    prefix  = "alb-access-logs"
    enabled = true
  }
  
  tags = {
    Name = "${local.name_prefix}-alb"
    Environment = var.environment
  }
}

# S3 Bucket for ALB Access Logs
resource "aws_s3_bucket" "alb_logs" {
  bucket        = "${local.name_prefix}-alb-logs-${random_string.bucket_suffix.result}"
  force_destroy = true
  
  tags = {
    Name = "${local.name_prefix}-alb-logs"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "alb_logs" {
  bucket = aws_s3_bucket.alb_logs.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "alb_logs" {
  bucket = aws_s3_bucket.alb_logs.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "alb_logs" {
  bucket = aws_s3_bucket.alb_logs.id
  
  rule {
    id     = "log_expiration"
    status = "Enabled"
    
    expiration {
      days = 90
    }
    
    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

# ALB Target Groups
# Swarm Queen Target Group
resource "aws_lb_target_group" "queen" {
  name     = "${local.name_prefix}-queen-tg"
  port     = local.service_ports.queen_api
  protocol = "HTTP"
  vpc_id   = aws_vpc.main.id
  
  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 10
    interval            = 30
    path                = "/health"
    matcher             = "200"
    protocol            = "HTTP"
    port                = "traffic-port"
  }
  
  tags = {
    Name = "${local.name_prefix}-queen-tg"
    Service = "Swarm-Queen"
  }
}

# Swarm Agents Target Group
resource "aws_lb_target_group" "agents" {
  name     = "${local.name_prefix}-agents-tg"
  port     = 8000
  protocol = "HTTP"
  vpc_id   = aws_vpc.main.id
  
  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 10
    interval            = 30
    path                = "/health"
    matcher             = "200"
    protocol            = "HTTP"
    port                = "traffic-port"
  }
  
  tags = {
    Name = "${local.name_prefix}-agents-tg"
    Service = "Swarm-Agents"
  }
}

# Monitoring Target Group (Grafana)
resource "aws_lb_target_group" "monitoring" {
  name     = "${local.name_prefix}-monitoring-tg"
  port     = local.service_ports.grafana
  protocol = "HTTP"
  vpc_id   = aws_vpc.main.id
  
  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 10
    interval            = 30
    path                = "/api/health"
    matcher             = "200"
    protocol            = "HTTP"
    port                = "traffic-port"
  }
  
  tags = {
    Name = "${local.name_prefix}-monitoring-tg"
    Service = "Monitoring"
  }
}

# Prometheus Target Group
resource "aws_lb_target_group" "prometheus" {
  name     = "${local.name_prefix}-prometheus-tg"
  port     = local.service_ports.prometheus
  protocol = "HTTP"
  vpc_id   = aws_vpc.main.id
  
  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 10
    interval            = 30
    path                = "/-/healthy"
    matcher             = "200"
    protocol            = "HTTP"
    port                = "traffic-port"
  }
  
  tags = {
    Name = "${local.name_prefix}-prometheus-tg"
    Service = "Prometheus"
  }
}

# Target Group Attachments
resource "aws_lb_target_group_attachment" "queen" {
  target_group_arn = aws_lb_target_group.queen.arn
  target_id        = aws_instance.swarm_queen.id
  port             = local.service_ports.queen_api
}

resource "aws_lb_target_group_attachment" "monitoring" {
  target_group_arn = aws_lb_target_group.monitoring.arn
  target_id        = aws_instance.monitoring.id
  port             = local.service_ports.grafana
}

resource "aws_lb_target_group_attachment" "prometheus" {
  target_group_arn = aws_lb_target_group.prometheus.arn
  target_id        = aws_instance.monitoring.id
  port             = local.service_ports.prometheus
}

# HTTP Listener (redirects to HTTPS)
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"
  
  default_action {
    type = "redirect"
    
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

# HTTPS Listener
resource "aws_lb_listener" "https" {
  count = var.certificate_arn != "" ? 1 : 0
  
  load_balancer_arn = aws_lb.main.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS-1-2-2017-01"
  certificate_arn   = var.certificate_arn
  
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.queen.arn
  }
}

# HTTP Listener (when no SSL certificate)
resource "aws_lb_listener" "http_main" {
  count = var.certificate_arn == "" ? 1 : 0
  
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"
  
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.queen.arn
  }
}

# Listener Rules for path-based routing
# Grafana Dashboard
resource "aws_lb_listener_rule" "grafana" {
  count = var.certificate_arn != "" ? 1 : 0
  
  listener_arn = aws_lb_listener.https[0].arn
  priority     = 100
  
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.monitoring.arn
  }
  
  condition {
    path_pattern {
      values = ["/grafana", "/grafana/*"]
    }
  }
}

resource "aws_lb_listener_rule" "grafana_http" {
  count = var.certificate_arn == "" ? 1 : 0
  
  listener_arn = aws_lb_listener.http_main[0].arn
  priority     = 100
  
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.monitoring.arn
  }
  
  condition {
    path_pattern {
      values = ["/grafana", "/grafana/*"]
    }
  }
}

# Prometheus Metrics
resource "aws_lb_listener_rule" "prometheus" {
  count = var.certificate_arn != "" ? 1 : 0
  
  listener_arn = aws_lb_listener.https[0].arn
  priority     = 200
  
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.prometheus.arn
  }
  
  condition {
    path_pattern {
      values = ["/prometheus", "/prometheus/*"]
    }
  }
}

resource "aws_lb_listener_rule" "prometheus_http" {
  count = var.certificate_arn == "" ? 1 : 0
  
  listener_arn = aws_lb_listener.http_main[0].arn
  priority     = 200
  
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.prometheus.arn
  }
  
  condition {
    path_pattern {
      values = ["/prometheus", "/prometheus/*"]
    }
  }
}

# API routing to agents
resource "aws_lb_listener_rule" "agents_api" {
  count = var.certificate_arn != "" ? 1 : 0
  
  listener_arn = aws_lb_listener.https[0].arn
  priority     = 300
  
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.agents.arn
  }
  
  condition {
    path_pattern {
      values = ["/api/agents", "/api/agents/*"]
    }
  }
}

resource "aws_lb_listener_rule" "agents_api_http" {
  count = var.certificate_arn == "" ? 1 : 0
  
  listener_arn = aws_lb_listener.http_main[0].arn
  priority     = 300
  
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.agents.arn
  }
  
  condition {
    path_pattern {
      values = ["/api/agents", "/api/agents/*"]
    }
  }
}

# Network Load Balancer for internal traffic (optional)
resource "aws_lb" "internal" {
  name               = "${local.name_prefix}-nlb-internal"
  internal           = true
  load_balancer_type = "network"
  subnets            = aws_subnet.private[*].id
  
  enable_deletion_protection       = false
  enable_cross_zone_load_balancing = true
  
  tags = {
    Name = "${local.name_prefix}-nlb-internal"
    Environment = var.environment
    Purpose = "Internal Load Balancing"
  }
}

# NLB Target Group for internal Queen API
resource "aws_lb_target_group" "queen_internal" {
  name     = "${local.name_prefix}-queen-internal-tg"
  port     = local.service_ports.queen_api
  protocol = "TCP"
  vpc_id   = aws_vpc.main.id
  
  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 10
    interval            = 30
    protocol            = "TCP"
    port                = "traffic-port"
  }
  
  tags = {
    Name = "${local.name_prefix}-queen-internal-tg"
    Service = "Swarm-Queen-Internal"
  }
}

# NLB Target Group for Memory Coordinator
resource "aws_lb_target_group" "coordinator_internal" {
  name     = "${local.name_prefix}-coordinator-internal-tg"
  port     = local.service_ports.coordinator
  protocol = "TCP"
  vpc_id   = aws_vpc.main.id
  
  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 10
    interval            = 30
    protocol            = "TCP"
    port                = "traffic-port"
  }
  
  tags = {
    Name = "${local.name_prefix}-coordinator-internal-tg"
    Service = "Memory-Coordinator-Internal"
  }
}

# NLB Listeners
resource "aws_lb_listener" "queen_internal" {
  load_balancer_arn = aws_lb.internal.arn
  port              = local.service_ports.queen_api
  protocol          = "TCP"
  
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.queen_internal.arn
  }
}

resource "aws_lb_listener" "coordinator_internal" {
  load_balancer_arn = aws_lb.internal.arn
  port              = local.service_ports.coordinator
  protocol          = "TCP"
  
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.coordinator_internal.arn
  }
}

# Internal Target Group Attachments
resource "aws_lb_target_group_attachment" "queen_internal" {
  target_group_arn = aws_lb_target_group.queen_internal.arn
  target_id        = aws_instance.swarm_queen.id
  port             = local.service_ports.queen_api
}

resource "aws_lb_target_group_attachment" "coordinator_internal" {
  target_group_arn = aws_lb_target_group.coordinator_internal.arn
  target_id        = aws_instance.memory_coordinator.id
  port             = local.service_ports.coordinator
}

# Random string for unique bucket naming
resource "random_string" "bucket_suffix" {
  length  = 8
  special = false
  upper   = false
}