# Ultra-Low-Cost EC2 Configuration
# Spot instances with interruption handling

# Launch template for spot instances
resource "aws_launch_template" "main" {
  name_prefix   = "${local.name_prefix}-main"
  image_id      = data.aws_ami.amazon_linux.id
  instance_type = local.instance_types.all_in_one
  key_name      = var.key_name

  vpc_security_group_ids = [aws_security_group.main.id]

  # Use GP3 for better price/performance
  block_device_mappings {
    device_name = "/dev/xvda"
    ebs {
      volume_size = var.storage_size
      volume_type = "gp3"
      throughput  = 125  # Minimum for gp3
      iops        = 3000 # Minimum for gp3
      encrypted   = true
      delete_on_termination = true
    }
  }

  # IAM instance profile
  iam_instance_profile {
    name = aws_iam_instance_profile.main.name
  }

  # User data for initial setup
  user_data = base64encode(templatefile("${path.module}/../scripts/user-data-main.sh", {
    region = var.aws_region
    auto_shutdown_enabled = var.auto_shutdown_enabled
    auto_shutdown_schedule = var.auto_shutdown_schedule
    auto_startup_schedule = var.auto_startup_schedule
  }))

  # Monitoring (disabled to save costs)
  monitoring {
    enabled = var.enable_detailed_monitoring
  }

  # Spot instance configuration
  instance_market_options {
    market_type = "spot"
    spot_options {
      max_price                      = local.spot_price
      spot_instance_type             = "persistent"
      instance_interruption_behavior = var.spot_instance_interruption_behavior
    }
  }

  tag_specifications {
    resource_type = "instance"
    tags = {
      Name = "${local.name_prefix}-main"
      Type = "Primary"
      Cost = "Optimized"
    }
  }

  tags = {
    Name = "${local.name_prefix}-launch-template"
  }
}

# Auto Scaling Group for automatic recovery
resource "aws_autoscaling_group" "main" {
  name                = "${local.name_prefix}-asg"
  vpc_zone_identifier = [aws_subnet.public.id]
  target_group_arns   = [aws_lb_target_group.main.arn]
  health_check_type   = "ELB"
  health_check_grace_period = 300

  min_size         = 1
  max_size         = 1
  desired_capacity = 1

  launch_template {
    id      = aws_launch_template.main.id
    version = "$Latest"
  }

  # Instance refresh for updates
  instance_refresh {
    strategy = "Rolling"
    preferences {
      min_healthy_percentage = 0  # Allow complete replacement
    }
  }

  tag {
    key                 = "Name"
    value               = "${local.name_prefix}-asg"
    propagate_at_launch = false
  }

  tag {
    key                 = "Environment"
    value               = var.environment
    propagate_at_launch = true
  }
}

# Backup instance (t3.nano for minimal cost)
resource "aws_instance" "backup" {
  ami           = data.aws_ami.amazon_linux.id
  instance_type = local.instance_types.backup
  key_name      = var.key_name
  subnet_id     = aws_subnet.public.id
  
  vpc_security_group_ids = [aws_security_group.backup.id]
  iam_instance_profile   = aws_iam_instance_profile.backup.name

  # Minimal storage
  root_block_device {
    volume_size = 8  # Minimum size
    volume_type = "gp3"
    encrypted   = true
    delete_on_termination = true
  }

  user_data = base64encode(templatefile("${path.module}/../scripts/user-data-backup.sh", {
    region = var.aws_region
  }))

  # Disable detailed monitoring
  monitoring = var.enable_detailed_monitoring

  tags = {
    Name = "${local.name_prefix}-backup"
    Type = "Backup"
    Cost = "Optimized"
  }
}

# Elastic IP for the main instance (optional, costs $3.65/month)
resource "aws_eip" "main" {
  count  = var.environment == "production" ? 1 : 0
  domain = "vpc"

  tags = {
    Name = "${local.name_prefix}-main-eip"
  }
}

# Associate EIP with the main instance
resource "aws_eip_association" "main" {
  count       = var.environment == "production" ? 1 : 0
  instance_id = aws_autoscaling_group.main.instances[0].instance_id
  allocation_id = aws_eip.main[0].id
}