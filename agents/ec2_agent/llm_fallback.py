# agents/ec2_agent/llm_fallback.py


class LLMFallback:
    def suggest_fix(self, issue, intent=None, instance_id=None):
        """
        Enhanced LLM fallback with intent context for EC2 instances.
        
        Args:
            issue: The detected EC2 issue
            intent: User's detected intent (e.g., "web_server", "database_server")
            instance_id: EC2 instance ID for context
        """
        # Intent-aware fix suggestions
        if intent == "web_server":
            return {
                "service": "ec2",
                "issue": f"Web server issue: {issue}",
                "fix": {
                    "action": "manual_review",
                    "params": {},
                    "suggestion": "Configure security groups for HTTP/HTTPS only, set up Auto Scaling and Load Balancer, enable SSL/TLS"
                },
                "auto_safe": False,
                "intent_context": f"Instance '{instance_id}' appears to be for web server hosting",
                "recommended_actions": [
                    "Restrict security groups to ports 80, 443, and SSH from specific IPs",
                    "Set up Application Load Balancer with SSL termination",
                    "Configure Auto Scaling Group for high availability",
                    "Enable CloudWatch monitoring for web server metrics",
                    "Implement proper backup strategy with EBS snapshots"
                ]
            }
        
        elif intent == "database_server":
            return {
                "service": "ec2", 
                "issue": f"Database server issue: {issue}",
                "fix": {
                    "action": "manual_review",
                    "params": {},
                    "suggestion": "Restrict database access to application servers only, enable encryption, set up backups"
                },
                "auto_safe": False,
                "intent_context": f"Instance '{instance_id}' appears to be for database hosting",
                "recommended_actions": [
                    "Restrict security groups to database ports from application servers only",
                    "Enable EBS encryption for data at rest",
                    "Set up automated EBS snapshots and cross-region backups",
                    "Use memory-optimized instances (r5, r6) for better performance",
                    "Consider migrating to Amazon RDS for managed database service",
                    "Monitor CPU, memory, disk I/O, and database connections"
                ]
            }
        
        elif intent == "application_server":
            return {
                "service": "ec2",
                "issue": f"Application server issue: {issue}",
                "fix": {
                    "action": "manual_review",
                    "params": {},
                    "suggestion": "Configure application-specific security groups, set up health checks, implement auto-scaling"
                },
                "auto_safe": False,
                "intent_context": f"Instance '{instance_id}' is for application hosting",
                "recommended_actions": [
                    "Use specific security group rules for application ports",
                    "Configure health checks for load balancer integration",
                    "Set up auto-scaling based on application metrics",
                    "Use AWS Systems Manager Parameter Store for configuration",
                    "Implement centralized logging with CloudWatch Logs",
                    "Monitor application performance and response times"
                ]
            }
        
        elif intent == "development_testing":
            return {
                "service": "ec2",
                "issue": f"Development/testing issue: {issue}",
                "fix": {
                    "action": "manual_review",
                    "params": {},
                    "suggestion": "Implement cost optimization with instance scheduling, use appropriate instance types, separate from production"
                },
                "auto_safe": False,
                "intent_context": f"Instance '{instance_id}' is for development/testing purposes",
                "recommended_actions": [
                    "Set up AWS Instance Scheduler for automatic start/stop",
                    "Consider using Spot Instances for cost savings",
                    "Use smaller, burstable instance types (t3, t4g) for dev workloads",
                    "Separate development and production environments",
                    "Take snapshots before major changes or testing",
                    "Use infrastructure as code for consistent environments"
                ]
            }
        
        elif intent == "batch_processing":
            return {
                "service": "ec2",
                "issue": f"Batch processing issue: {issue}",
                "fix": {
                    "action": "manual_review",
                    "params": {},
                    "suggestion": "Use AWS Batch or compute-optimized instances, implement job queuing, consider Spot instances"
                },
                "auto_safe": False,
                "intent_context": f"Instance '{instance_id}' is for batch processing workloads",
                "recommended_actions": [
                    "Consider AWS Batch for managed batch computing",
                    "Use Spot Instances for cost-effective batch processing",
                    "Use compute-optimized instances (c5, c6) for CPU-intensive tasks",
                    "Implement proper job queuing and priority management",
                    "Set up CloudWatch metrics for batch job monitoring",
                    "Use containerized workloads for better resource utilization"
                ]
            }
        
        elif intent == "high_performance_computing":
            return {
                "service": "ec2",
                "issue": f"HPC issue: {issue}",
                "fix": {
                    "action": "manual_review",
                    "params": {},
                    "suggestion": "Use GPU instances for ML/AI, configure cluster placement groups, optimize networking"
                },
                "auto_safe": False,
                "intent_context": f"Instance '{instance_id}' is for high-performance computing",
                "recommended_actions": [
                    "Use GPU instances (p3, p4, g4) for ML/AI workloads",
                    "Configure cluster placement groups for low latency",
                    "Enable enhanced networking (SR-IOV) for better performance",
                    "Use high-performance storage (NVMe SSD, Amazon FSx)",
                    "Consider AWS ParallelCluster for HPC workloads",
                    "Optimize for CUDA and MPI applications"
                ]
            }
        
        elif intent == "bastion_host":
            return {
                "service": "ec2",
                "issue": f"Bastion host issue: {issue}",
                "fix": {
                    "action": "manual_review",
                    "params": {},
                    "suggestion": "Restrict SSH access, implement MFA, consider Session Manager alternative"
                },
                "auto_safe": False,
                "intent_context": f"Instance '{instance_id}' is configured as a bastion host",
                "recommended_actions": [
                    "Restrict SSH access to specific IP ranges only",
                    "Consider AWS Systems Manager Session Manager as alternative",
                    "Deploy bastion hosts in multiple Availability Zones",
                    "Enable detailed SSH logging and audit trails",
                    "Use key-based authentication with regular key rotation",
                    "Keep bastion hosts updated with latest security patches"
                ]
            }
        
        elif intent == "load_balancer":
            return {
                "service": "ec2",
                "issue": f"Load balancer issue: {issue}",
                "fix": {
                    "action": "manual_review",
                    "params": {},
                    "suggestion": "Consider using managed ALB/NLB instead of EC2-based load balancer, configure health checks"
                },
                "auto_safe": False,
                "intent_context": f"Instance '{instance_id}' appears to be used for load balancing",
                "recommended_actions": [
                    "Consider using Application Load Balancer (ALB) instead",
                    "Use Network Load Balancer (NLB) for TCP/UDP traffic",
                    "Configure proper health checks for backend instances",
                    "Enable SSL/TLS termination at load balancer level",
                    "Set up cross-zone load balancing",
                    "Enable access logging for monitoring and troubleshooting"
                ]
            }
        
        elif intent == "microservices":
            return {
                "service": "ec2",
                "issue": f"Microservices issue: {issue}",
                "fix": {
                    "action": "manual_review",
                    "params": {},
                    "suggestion": "Consider containerization with ECS/EKS, implement service discovery, use API Gateway"
                },
                "auto_safe": False,
                "intent_context": f"Instance '{instance_id}' is part of microservices architecture",
                "recommended_actions": [
                    "Consider Amazon ECS or EKS for container orchestration",
                    "Use smaller instance types or AWS Fargate for containers",
                    "Implement service discovery with AWS Cloud Map",
                    "Set up centralized logging with CloudWatch Logs",
                    "Use API Gateway for external service exposure",
                    "Implement CI/CD pipelines for automated deployment"
                ]
            }
        
        elif intent == "data_processing":
            return {
                "service": "ec2",
                "issue": f"Data processing issue: {issue}",
                "fix": {
                    "action": "manual_review",
                    "params": {},
                    "suggestion": "Use appropriate instance types for data processing, consider managed services like EMR"
                },
                "auto_safe": False,
                "intent_context": f"Instance '{instance_id}' is for data processing workloads",
                "recommended_actions": [
                    "Consider Amazon EMR for big data processing",
                    "Use memory-optimized instances for in-memory processing",
                    "Use high-performance storage for data-intensive workloads",
                    "Consider Spot Instances for fault-tolerant processing",
                    "Implement data partitioning and parallel processing",
                    "Set up monitoring for data processing metrics"
                ]
            }
        
        else:
            # Fallback for unknown intent
            return {
                "service": "ec2",
                "issue": issue,
                "fix": {
                    "action": "manual_review",
                    "params": {},
                    "suggestion": "Manual review required - intent unclear. Follow EC2 security best practices."
                },
                "auto_safe": False,
                "intent_context": f"Instance '{instance_id}' intent is unclear",
                "recommended_actions": [
                    "Review EC2 best practices documentation",
                    "Analyze instance usage patterns and purpose",
                    "Consult with instance owner about intended use case",
                    "Apply general security and cost optimization practices"
                ]
            }
    
    def get_quick_fixes(self, intent=None):
        """Get quick fix suggestions based on intent."""
        quick_fixes = {
            "web_server": [
                "Add HTTPS listener to load balancer",
                "Restrict security group to ports 80, 443 only",
                "Enable Auto Scaling for high availability"
            ],
            "database_server": [
                "Restrict database security group to application servers only",
                "Enable EBS encryption on database volumes",
                "Set up automated EBS snapshots"
            ],
            "development_testing": [
                "Set up Instance Scheduler for cost savings",
                "Use Spot Instances for non-critical dev workloads",
                "Downsize to burstable instance types (t3, t4g)"
            ],
            "application_server": [
                "Configure application health checks",
                "Set up CloudWatch monitoring for application metrics",
                "Use Systems Manager Parameter Store for configuration"
            ],
            "bastion_host": [
                "Restrict SSH to specific IP ranges",
                "Enable CloudTrail logging for SSH sessions",
                "Consider Session Manager as SSH alternative"
            ]
        }
        
        return quick_fixes.get(intent, [
            "Review security groups for least privilege access",
            "Enable EBS encryption for data protection",
            "Set up CloudWatch monitoring and alerting"
        ])
    
    def get_cost_optimization_recommendations(self, intent=None):
        """Get cost optimization recommendations based on intent."""
        cost_recommendations = {
            "web_server": {
                "immediate": "Use Auto Scaling to match demand",
                "short_term": "Consider Reserved Instances for predictable workloads",
                "long_term": "Implement CDN and caching to reduce compute needs"
            },
            "database_server": {
                "immediate": "Right-size instance based on actual usage",
                "short_term": "Consider RDS for managed database benefits",
                "long_term": "Use Reserved Instances for long-running databases"
            },
            "development_testing": {
                "immediate": "Stop instances outside work hours",
                "short_term": "Use Spot Instances for fault-tolerant workloads",
                "long_term": "Implement infrastructure as code for efficient resource use"
            },
            "batch_processing": {
                "immediate": "Use Spot Instances for batch jobs",
                "short_term": "Consider AWS Batch for better resource management",
                "long_term": "Optimize job scheduling and resource allocation"
            }
        }
        
        return cost_recommendations.get(intent, {
            "immediate": "Review instance utilization and right-size",
            "short_term": "Consider Reserved Instances for predictable workloads", 
            "long_term": "Implement automated cost monitoring and optimization"
        })
    
    def get_security_recommendations(self, issue_type):
        """Get security recommendations for specific issue types."""
        recommendations = {
            "open_security_group": {
                "immediate": "Restrict security group rules to specific IP ranges",
                "short_term": "Implement security group rule auditing",
                "long_term": "Use AWS Config Rules for automated compliance checking"
            },
            "unencrypted_storage": {
                "immediate": "Enable encryption for new EBS volumes",
                "short_term": "Encrypt existing volumes using snapshots",
                "long_term": "Enable encryption by default for all EBS volumes"
            },
            "missing_patches": {
                "immediate": "Apply critical security patches manually",
                "short_term": "Use Systems Manager Patch Manager",
                "long_term": "Implement automated patching with maintenance windows"
            },
            "no_monitoring": {
                "immediate": "Enable basic CloudWatch monitoring",
                "short_term": "Set up custom metrics and alarms",
                "long_term": "Implement comprehensive monitoring with third-party tools"
            }
        }
        
        return recommendations.get(issue_type, {
            "immediate": "Apply security best practices immediately",
            "short_term": "Implement security monitoring and alerting",
            "long_term": "Automate security compliance and remediation"
        })