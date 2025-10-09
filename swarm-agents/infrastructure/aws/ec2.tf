# TGE Swarm EC2 Instance Configuration
# Production-ready EC2 instances with auto-scaling and proper resource allocation

# Launch Template for Swarm Queen
resource "aws_launch_template" "swarm_queen" {
  name_prefix   = "${local.name_prefix}-queen-"
  image_id      = data.aws_ami.amazon_linux.id
  instance_type = var.instance_types.queen
  key_name      = var.key_pair_name
  
  vpc_security_group_ids = [aws_security_group.swarm_queen.id]
  
  # IAM Instance Profile
  iam_instance_profile {
    name = aws_iam_instance_profile.swarm_queen.name
  }
  
  # EBS Optimization
  ebs_optimized = true
  
  # Block Device Mappings
  block_device_mappings {
    device_name = "/dev/xvda"
    ebs {
      volume_type           = "gp3"
      volume_size           = 20
      iops                  = 3000
      throughput            = 125
      encrypted             = true
      delete_on_termination = true
    }
  }
  
  # Additional EBS volume for application data
  block_device_mappings {
    device_name = "/dev/sdf"
    ebs {
      volume_type           = "gp3"
      volume_size           = 100
      iops                  = 3000
      throughput            = 125
      encrypted             = true
      delete_on_termination = false
    }
  }
  
  # User Data Script
  user_data = base64encode(templatefile("${path.module}/user-data/swarm-queen.sh", {
    environment = var.environment
    postgres_endpoint = aws_rds_cluster.postgres.endpoint
    redis_endpoint = aws_elasticache_replication_group.redis.configuration_endpoint_address
    consul_endpoint = aws_instance.consul.private_ip
  }))
  
  # Monitoring
  monitoring {
    enabled = var.cloudwatch_config.detailed_monitoring
  }
  
  # Metadata Options (IMDSv2 enforcement)
  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
    http_put_response_hop_limit = 1
  }
  
  tags = {
    Name = "${local.name_prefix}-queen-template"
    Service = "Swarm-Queen"
  }
  
  tag_specifications {
    resource_type = "instance"
    tags = {
      Name = "${local.name_prefix}-queen"
      Service = "Swarm-Queen"
      Environment = var.environment
    }
  }
}

# Launch Template for Memory Coordinator
resource "aws_launch_template" "memory_coordinator" {
  name_prefix   = "${local.name_prefix}-coordinator-"
  image_id      = data.aws_ami.amazon_linux.id
  instance_type = var.instance_types.coordinator
  key_name      = var.key_pair_name
  
  vpc_security_group_ids = [aws_security_group.memory_coordinator.id]
  
  iam_instance_profile {
    name = aws_iam_instance_profile.memory_coordinator.name
  }
  
  ebs_optimized = true
  
  block_device_mappings {
    device_name = "/dev/xvda"
    ebs {
      volume_type           = "gp3"
      volume_size           = 20
      iops                  = 3000
      throughput            = 125
      encrypted             = true
      delete_on_termination = true
    }
  }
  
  # EBS volume for memory coordination data
  block_device_mappings {
    device_name = "/dev/sdf"
    ebs {
      volume_type           = "gp3"
      volume_size           = 50
      iops                  = 3000
      throughput            = 125
      encrypted             = true
      delete_on_termination = false
    }
  }
  
  user_data = base64encode(templatefile("${path.module}/user-data/memory-coordinator.sh", {
    environment = var.environment
    postgres_endpoint = aws_rds_cluster.postgres.endpoint
    redis_endpoint = aws_elasticache_replication_group.redis.configuration_endpoint_address
    queen_endpoint = aws_lb.main.dns_name
  }))
  
  monitoring {
    enabled = var.cloudwatch_config.detailed_monitoring
  }
  
  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
    http_put_response_hop_limit = 1
  }
  
  tags = {
    Name = "${local.name_prefix}-coordinator-template"
    Service = "Memory-Coordinator"
  }
  
  tag_specifications {
    resource_type = "instance"
    tags = {
      Name = "${local.name_prefix}-coordinator"
      Service = "Memory-Coordinator"
      Environment = var.environment
    }
  }
}

# Launch Template for Swarm Agents
resource "aws_launch_template" "swarm_agents" {
  name_prefix   = "${local.name_prefix}-agents-"
  image_id      = data.aws_ami.amazon_linux.id
  instance_type = var.instance_types.agent
  key_name      = var.key_pair_name
  
  vpc_security_group_ids = [aws_security_group.swarm_agents.id]
  
  iam_instance_profile {
    name = aws_iam_instance_profile.swarm_agents.name
  }
  
  ebs_optimized = true
  
  block_device_mappings {
    device_name = "/dev/xvda"
    ebs {
      volume_type           = "gp3"
      volume_size           = 20
      iops                  = 3000
      throughput            = 125
      encrypted             = true
      delete_on_termination = true
    }
  }
  
  user_data = base64encode(templatefile("${path.module}/user-data/swarm-agents.sh", {
    environment = var.environment
    postgres_endpoint = aws_rds_cluster.postgres.endpoint
    redis_endpoint = aws_elasticache_replication_group.redis.configuration_endpoint_address
    queen_endpoint = aws_lb.main.dns_name
    coordinator_endpoint = aws_instance.memory_coordinator.private_ip
  }))
  
  monitoring {
    enabled = var.cloudwatch_config.detailed_monitoring
  }
  
  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
    http_put_response_hop_limit = 1
  }
  
  tags = {
    Name = "${local.name_prefix}-agents-template"
    Service = "Swarm-Agents"
  }
  
  tag_specifications {
    resource_type = "instance"
    tags = {
      Name = "${local.name_prefix}-agent"
      Service = "Swarm-Agents"
      Environment = var.environment
    }
  }
}

# Launch Template for Monitoring Stack
resource "aws_launch_template" "monitoring" {
  name_prefix   = "${local.name_prefix}-monitoring-"
  image_id      = data.aws_ami.amazon_linux.id
  instance_type = var.instance_types.monitoring
  key_name      = var.key_pair_name
  
  vpc_security_group_ids = [aws_security_group.monitoring.id]
  
  iam_instance_profile {
    name = aws_iam_instance_profile.monitoring.name
  }
  
  ebs_optimized = true
  
  block_device_mappings {
    device_name = "/dev/xvda"
    ebs {
      volume_type           = "gp3"
      volume_size           = 20
      iops                  = 3000
      throughput            = 125
      encrypted             = true
      delete_on_termination = true
    }
  }
  
  # Large EBS volume for monitoring data
  block_device_mappings {
    device_name = "/dev/sdf"
    ebs {
      volume_type           = "gp3"
      volume_size           = 200
      iops                  = 3000
      throughput            = 125
      encrypted             = true
      delete_on_termination = false
    }
  }
  
  user_data = base64encode(templatefile("${path.module}/user-data/monitoring.sh", {
    environment = var.environment
  }))
  
  monitoring {
    enabled = var.cloudwatch_config.detailed_monitoring
  }
  
  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
    http_put_response_hop_limit = 1
  }
  
  tags = {
    Name = "${local.name_prefix}-monitoring-template"
    Service = "Monitoring"
  }
  
  tag_specifications {
    resource_type = "instance"
    tags = {
      Name = "${local.name_prefix}-monitoring"
      Service = "Monitoring"
      Environment = var.environment
    }
  }
}

# Auto Scaling Group for Swarm Agents
resource "aws_autoscaling_group" "swarm_agents" {
  name = "${local.name_prefix}-agents-asg"
  
  vpc_zone_identifier = aws_subnet.private[*].id
  target_group_arns   = [aws_lb_target_group.agents.arn]
  health_check_type   = var.swarm_agent_config.health_check_type
  health_check_grace_period = var.swarm_agent_config.health_check_grace_period
  
  min_size         = var.swarm_agent_config.min_size
  max_size         = var.swarm_agent_config.max_size
  desired_capacity = var.swarm_agent_config.desired_capacity
  
  launch_template {
    id      = aws_launch_template.swarm_agents.id
    version = "$Latest"
  }
  
  # Instance refresh configuration
  instance_refresh {
    strategy = "Rolling"
    preferences {
      min_healthy_percentage = 50
      instance_warmup       = 300
    }
  }
  
  # Scaling policies
  enabled_metrics = [
    "GroupMinSize",
    "GroupMaxSize",
    "GroupDesiredCapacity",
    "GroupInServiceInstances",
    "GroupTotalInstances"
  ]
  
  tags = [
    {
      key                 = "Name"
      value               = "${local.name_prefix}-agent"
      propagate_at_launch = true
    },
    {
      key                 = "Service"
      value               = "Swarm-Agents"
      propagate_at_launch = true
    },
    {
      key                 = "Environment"
      value               = var.environment
      propagate_at_launch = true
    }
  ]
  
  lifecycle {
    create_before_destroy = true
  }
}

# Auto Scaling Policies for Agents
resource "aws_autoscaling_policy" "agents_scale_up" {
  name                   = "${local.name_prefix}-agents-scale-up"
  scaling_adjustment     = 2
  adjustment_type        = "ChangeInCapacity"
  cooldown              = 300
  autoscaling_group_name = aws_autoscaling_group.swarm_agents.name
}

resource "aws_autoscaling_policy" "agents_scale_down" {
  name                   = "${local.name_prefix}-agents-scale-down"
  scaling_adjustment     = -1
  adjustment_type        = "ChangeInCapacity"
  cooldown              = 300
  autoscaling_group_name = aws_autoscaling_group.swarm_agents.name
}

# CloudWatch Alarms for Auto Scaling
resource "aws_cloudwatch_metric_alarm" "agents_cpu_high" {
  alarm_name          = "${local.name_prefix}-agents-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = "300"
  statistic           = "Average"
  threshold           = "75"
  alarm_description   = "This metric monitors agents cpu utilization"
  alarm_actions       = [aws_autoscaling_policy.agents_scale_up.arn]
  
  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.swarm_agents.name
  }
}

resource "aws_cloudwatch_metric_alarm" "agents_cpu_low" {
  alarm_name          = "${local.name_prefix}-agents-cpu-low"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = "300"
  statistic           = "Average"
  threshold           = "25"
  alarm_description   = "This metric monitors agents cpu utilization"
  alarm_actions       = [aws_autoscaling_policy.agents_scale_down.arn]
  
  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.swarm_agents.name
  }
}

# Single instances for core services (with high availability via standby)
resource "aws_instance" "swarm_queen" {
  ami           = data.aws_ami.amazon_linux.id
  instance_type = var.instance_types.queen
  key_name      = var.key_pair_name
  subnet_id     = aws_subnet.private[0].id
  
  vpc_security_group_ids = [aws_security_group.swarm_queen.id]
  iam_instance_profile   = aws_iam_instance_profile.swarm_queen.name
  
  ebs_optimized = true
  monitoring    = var.cloudwatch_config.detailed_monitoring
  
  # EBS volumes
  root_block_device {
    volume_type           = "gp3"
    volume_size           = 20
    iops                  = 3000
    throughput            = 125
    encrypted             = true
    delete_on_termination = true
  }
  
  user_data = base64encode(templatefile("${path.module}/user-data/swarm-queen.sh", {
    environment = var.environment
    postgres_endpoint = aws_rds_cluster.postgres.endpoint
    redis_endpoint = aws_elasticache_replication_group.redis.configuration_endpoint_address
    consul_endpoint = aws_instance.consul.private_ip
  }))
  
  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
    http_put_response_hop_limit = 1
  }
  
  tags = {
    Name = "${local.name_prefix}-queen-primary"
    Service = "Swarm-Queen"
    Environment = var.environment
    Role = "Primary"
  }
  
  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_instance" "memory_coordinator" {
  ami           = data.aws_ami.amazon_linux.id
  instance_type = var.instance_types.coordinator
  key_name      = var.key_pair_name
  subnet_id     = aws_subnet.private[1].id
  
  vpc_security_group_ids = [aws_security_group.memory_coordinator.id]
  iam_instance_profile   = aws_iam_instance_profile.memory_coordinator.name
  
  ebs_optimized = true
  monitoring    = var.cloudwatch_config.detailed_monitoring
  
  root_block_device {
    volume_type           = "gp3"
    volume_size           = 20
    iops                  = 3000
    throughput            = 125
    encrypted             = true
    delete_on_termination = true
  }
  
  user_data = base64encode(templatefile("${path.module}/user-data/memory-coordinator.sh", {
    environment = var.environment
    postgres_endpoint = aws_rds_cluster.postgres.endpoint
    redis_endpoint = aws_elasticache_replication_group.redis.configuration_endpoint_address
    queen_endpoint = aws_instance.swarm_queen.private_ip
  }))
  
  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
    http_put_response_hop_limit = 1
  }
  
  tags = {
    Name = "${local.name_prefix}-coordinator"
    Service = "Memory-Coordinator"
    Environment = var.environment
  }
  
  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_instance" "monitoring" {
  ami           = data.aws_ami.amazon_linux.id
  instance_type = var.instance_types.monitoring
  key_name      = var.key_pair_name
  subnet_id     = aws_subnet.private[2].id
  
  vpc_security_group_ids = [aws_security_group.monitoring.id]
  iam_instance_profile   = aws_iam_instance_profile.monitoring.name
  
  ebs_optimized = true
  monitoring    = var.cloudwatch_config.detailed_monitoring
  
  root_block_device {
    volume_type           = "gp3"
    volume_size           = 20
    iops                  = 3000
    throughput            = 125
    encrypted             = true
    delete_on_termination = true
  }
  
  user_data = base64encode(templatefile("${path.module}/user-data/monitoring.sh", {
    environment = var.environment
  }))
  
  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
    http_put_response_hop_limit = 1
  }
  
  tags = {
    Name = "${local.name_prefix}-monitoring"
    Service = "Monitoring"
    Environment = var.environment
  }
  
  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_instance" "consul" {
  ami           = data.aws_ami.amazon_linux.id
  instance_type = "t3.small"
  key_name      = var.key_pair_name
  subnet_id     = aws_subnet.private[0].id
  
  vpc_security_group_ids = [aws_security_group.consul.id]
  iam_instance_profile   = aws_iam_instance_profile.consul.name
  
  ebs_optimized = true
  monitoring    = var.cloudwatch_config.detailed_monitoring
  
  root_block_device {
    volume_type           = "gp3"
    volume_size           = 20
    iops                  = 3000
    throughput            = 125
    encrypted             = true
    delete_on_termination = true
  }
  
  user_data = base64encode(templatefile("${path.module}/user-data/consul.sh", {
    environment = var.environment
  }))
  
  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
    http_put_response_hop_limit = 1
  }
  
  tags = {
    Name = "${local.name_prefix}-consul"
    Service = "Consul"
    Environment = var.environment
  }
  
  lifecycle {
    create_before_destroy = true
  }
}

# Bastion Host for secure access
resource "aws_instance" "bastion" {
  ami           = data.aws_ami.amazon_linux.id
  instance_type = "t3.micro"
  key_name      = var.key_pair_name
  subnet_id     = aws_subnet.public[0].id
  
  vpc_security_group_ids = [aws_security_group.bastion.id]
  iam_instance_profile   = aws_iam_instance_profile.bastion.name
  
  monitoring = var.cloudwatch_config.detailed_monitoring
  
  root_block_device {
    volume_type           = "gp3"
    volume_size           = 10
    encrypted             = true
    delete_on_termination = true
  }
  
  user_data = base64encode(templatefile("${path.module}/user-data/bastion.sh", {
    environment = var.environment
  }))
  
  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
    http_put_response_hop_limit = 1
  }
  
  tags = {
    Name = "${local.name_prefix}-bastion"
    Service = "Bastion"
    Environment = var.environment
  }
}