# agents/ec2_agent/doc_search.py


class DocSearch:
    def __init__(self):
        # Intent-specific documentation references
        self.intent_docs = {
            "web_server": {
                "common_issues": [
                    "Security groups allow unrestricted access",
                    "No HTTPS/SSL termination configured",
                    "Instance not in Auto Scaling Group",
                    "No load balancer for high availability",
                    "EBS volumes not encrypted",
                    "No monitoring or logging enabled"
                ],
                "aws_docs": "https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-security-groups.html",
                "best_practices": [
                    "Use Application Load Balancer for SSL termination",
                    "Configure Auto Scaling for high availability",
                    "Restrict security groups to necessary ports only",
                    "Enable CloudWatch monitoring and logging",
                    "Use encrypted EBS volumes",
                    "Implement proper backup strategy"
                ]
            },
            "database_server": {
                "common_issues": [
                    "Database ports exposed to public internet",
                    "No encryption at rest or in transit",
                    "Insufficient backup and recovery strategy",
                    "Using general-purpose instances for database workloads",
                    "No monitoring for database performance metrics",
                    "Direct EC2 instead of managed RDS service"
                ],
                "aws_docs": "https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_BestPractices.html",
                "best_practices": [
                    "Use memory-optimized instances (r5, r6) for databases",
                    "Restrict database access to application security groups only",
                    "Enable encryption at rest and in transit",
                    "Set up automated backups and snapshots",
                    "Consider Amazon RDS for managed database service",
                    "Use Provisioned IOPS for consistent performance",
                    "Monitor CPU, memory, disk I/O, and connections"
                ]
            },
            "application_server": {
                "common_issues": [
                    "Overly permissive security group rules",
                    "No application-level monitoring",
                    "Missing auto-scaling configuration",
                    "Application logs not centralized",
                    "No health checks configured",
                    "Hardcoded configuration and secrets"
                ],
                "aws_docs": "https://docs.aws.amazon.com/elasticloadbalancing/latest/application/introduction.html",
                "best_practices": [
                    "Use specific security group rules for application ports",
                    "Implement health checks for load balancer targets",
                    "Configure auto-scaling based on application metrics",
                    "Use AWS Systems Manager Parameter Store for configuration",
                    "Enable application performance monitoring",
                    "Centralize logging with CloudWatch Logs"
                ]
            },
            "development_testing": {
                "common_issues": [
                    "Dev instances left running 24/7 (cost waste)",
                    "Production-level instance types for dev/test",
                    "No automated start/stop scheduling",
                    "Development and production in same network",
                    "No proper snapshot strategy for testing",
                    "Using On-Demand instead of Spot instances"
                ],
                "aws_docs": "https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/spot-instances.html",
                "best_practices": [
                    "Use AWS Instance Scheduler for automatic start/stop",
                    "Consider Spot Instances for development workloads",
                    "Use smaller, burstable instance types (t3, t4g)",
                    "Separate development and production environments",
                    "Take snapshots before major changes",
                    "Use infrastructure as code for consistency"
                ]
            },
            "batch_processing": {
                "common_issues": [
                    "Using On-Demand instances for batch workloads",
                    "No job queuing and scheduling system",
                    "Insufficient monitoring of batch job performance",
                    "Not using appropriate compute-optimized instances",
                    "Manual scaling instead of auto-scaling",
                    "No retry mechanism for failed jobs"
                ],
                "aws_docs": "https://docs.aws.amazon.com/batch/latest/userguide/what-is-batch.html",
                "best_practices": [
                    "Use AWS Batch for managed batch computing",
                    "Consider Spot Instances for cost-effective batch processing",
                    "Use compute-optimized instances (c5, c6) for CPU-intensive tasks",
                    "Implement proper job queuing and priority management",
                    "Set up CloudWatch metrics for batch job monitoring",
                    "Use containerized workloads for better resource utilization"
                ]
            },
            "high_performance_computing": {
                "common_issues": [
                    "Not using GPU instances for ML/AI workloads",
                    "Insufficient network performance for HPC clusters",
                    "No cluster placement groups for low latency",
                    "Using general storage instead of high-performance options",
                    "Inadequate inter-node communication optimization",
                    "No proper job scheduling for HPC workloads"
                ],
                "aws_docs": "https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/placement-groups.html",
                "best_practices": [
                    "Use GPU instances (p3, p4, g4) for ML/AI workloads",
                    "Configure cluster placement groups for low latency",
                    "Enable enhanced networking (SR-IOV) for better performance",
                    "Use high-performance storage (NVMe SSD, FSx)",
                    "Consider AWS ParallelCluster for HPC workloads",
                    "Optimize for CUDA and MPI applications"
                ]
            },
            "bastion_host": {
                "common_issues": [
                    "SSH access from unrestricted IP ranges (0.0.0.0/0)",
                    "No multi-factor authentication for SSH access",
                    "Single bastion host (no high availability)",
                    "Insufficient SSH session logging and monitoring",
                    "Using password authentication instead of key-based",
                    "No regular security patching and updates"
                ],
                "aws_docs": "https://docs.aws.amazon.com/quickstart/latest/linux-bastion/architecture.html",
                "best_practices": [
                    "Restrict SSH access to specific IP ranges only",
                    "Use AWS Systems Manager Session Manager as alternative",
                    "Deploy bastion hosts in multiple Availability Zones",
                    "Enable detailed SSH logging and audit trails",
                    "Use key-based authentication with regular key rotation",
                    "Keep bastion hosts updated with latest security patches",
                    "Consider AWS Client VPN as modern alternative"
                ]
            },
            "load_balancer": {
                "common_issues": [
                    "Using Classic Load Balancer instead of modern ALB/NLB",
                    "No SSL/TLS termination at load balancer",
                    "Health checks not properly configured",
                    "No cross-zone load balancing enabled",
                    "Missing access logging for troubleshooting",
                    "Not using multiple Availability Zones"
                ],
                "aws_docs": "https://docs.aws.amazon.com/elasticloadbalancing/latest/application/introduction.html",
                "best_practices": [
                    "Use Application Load Balancer for HTTP/HTTPS traffic",
                    "Enable SSL/TLS termination at load balancer level",
                    "Configure proper health checks for target instances",
                    "Enable cross-zone load balancing for better distribution",
                    "Set up access logging for monitoring and troubleshooting",
                    "Deploy across multiple Availability Zones for high availability"
                ]
            },
            "microservices": {
                "common_issues": [
                    "Running microservices on oversized EC2 instances",
                    "No containerization for better resource utilization",
                    "Lack of service discovery and communication",
                    "No centralized logging and monitoring",
                    "Manual deployment instead of CI/CD pipelines",
                    "No proper API gateway for service exposure"
                ],
                "aws_docs": "https://docs.aws.amazon.com/ecs/latest/developerguide/Welcome.html",
                "best_practices": [
                    "Consider Amazon ECS or EKS for container orchestration",
                    "Use smaller instance types or AWS Fargate",
                    "Implement service discovery with AWS Cloud Map",
                    "Set up centralized logging with CloudWatch Logs",
                    "Use API Gateway for external service exposure",
                    "Implement CI/CD pipelines for automated deployment"
                ]
            }
        }
    
    def search(self, issue, intent=None):
        """
        Enhanced doc search with intent context.
        
        Args:
            issue: The detected EC2 issue
            intent: User's detected intent (e.g., "web_server", "database_server")
        """
        if intent and intent in self.intent_docs:
            docs = self.intent_docs[intent]
            
            # Find most relevant issue
            relevant_issue = None
            best_match_score = 0
            
            for common_issue in docs["common_issues"]:
                # Calculate relevance score based on keyword matching
                issue_keywords = set(issue.lower().split())
                common_issue_keywords = set(common_issue.lower().split())
                
                # Find intersection and calculate match score
                matches = len(issue_keywords.intersection(common_issue_keywords))
                match_score = matches / max(len(issue_keywords), len(common_issue_keywords))
                
                if match_score > best_match_score and match_score > 0.2:  # At least 20% match
                    best_match_score = match_score
                    relevant_issue = common_issue
            
            if relevant_issue:
                return {
                    "issue_type": relevant_issue,
                    "intent": intent,
                    "aws_docs": docs["aws_docs"],
                    "best_practices": docs["best_practices"],
                    "suggestion": f"This appears to be a {intent.replace('_', ' ')} issue. {relevant_issue} is a common problem in this scenario.",
                    "match_score": best_match_score
                }
        
        # Enhanced fallback search with EC2-specific categories
        return self._fallback_search(issue)
    
    def _fallback_search(self, issue):
        """Fallback search for issues not covered by intent-specific docs."""
        issue_lower = issue.lower()
        
        # Security-related issues
        security_keywords = ['security group', 'port', 'access', 'ssh', 'firewall', 'encryption']
        if any(keyword in issue_lower for keyword in security_keywords):
            return {
                "category": "security",
                "aws_docs": "https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-security.html",
                "suggestion": "This appears to be a security-related EC2 issue. Check EC2 security best practices."
            }
        
        # Performance-related issues
        performance_keywords = ['cpu', 'memory', 'disk', 'network', 'performance', 'slow', 'bottleneck']
        if any(keyword in issue_lower for keyword in performance_keywords):
            return {
                "category": "performance",
                "aws_docs": "https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/monitoring-system-instance-status-check.html",
                "suggestion": "This appears to be a performance-related EC2 issue. Review instance monitoring and optimization."
            }
        
        # Cost-related issues
        cost_keywords = ['cost', 'expensive', 'billing', 'pricing', 'optimize', 'savings']
        if any(keyword in issue_lower for keyword in cost_keywords):
            return {
                "category": "cost_optimization",
                "aws_docs": "https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-lifecycle.html",
                "suggestion": "This appears to be a cost optimization issue. Consider right-sizing, scheduling, or Reserved Instances."
            }
        
        # Networking issues
        network_keywords = ['vpc', 'subnet', 'route', 'gateway', 'dns', 'connectivity']
        if any(keyword in issue_lower for keyword in network_keywords):
            return {
                "category": "networking",
                "aws_docs": "https://docs.aws.amazon.com/vpc/latest/userguide/what-is-amazon-vpc.html",
                "suggestion": "This appears to be a networking-related issue. Check VPC configuration and routing."
            }
        
        # Storage issues
        storage_keywords = ['ebs', 'volume', 'disk', 'storage', 'snapshot', 'backup']
        if any(keyword in issue_lower for keyword in storage_keywords):
            return {
                "category": "storage",
                "aws_docs": "https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/AmazonEBS.html",
                "suggestion": "This appears to be a storage-related issue. Review EBS volume configuration."
            }
        
        # Generic fallback
        return f"No direct rule found. Refer to AWS EC2 Documentation for: {issue}"
    
    def get_security_checklist(self, intent=None):
        """Get a security checklist based on intent."""
        if intent and intent in self.intent_docs:
            return {
                "intent": intent,
                "checklist": self.intent_docs[intent]["best_practices"],
                "common_pitfalls": self.intent_docs[intent]["common_issues"]
            }
        
        # Generic EC2 security checklist
        return {
            "intent": "general",
            "checklist": [
                "Use least-privilege security groups",
                "Enable EBS encryption for data at rest",
                "Keep instances updated with security patches",
                "Use IAM roles instead of access keys",
                "Enable CloudTrail for API logging",
                "Monitor with CloudWatch",
                "Use private subnets for internal resources",
                "Implement proper backup strategy"
            ],
            "common_pitfalls": [
                "Security groups with 0.0.0.0/0 access",
                "Unencrypted EBS volumes",
                "Missing security patches",
                "Hardcoded credentials in applications",
                "No monitoring or alerting",
                "Public instances without proper security"
            ]
        }
    
    def get_cost_optimization_tips(self, intent=None):
        """Get cost optimization tips based on instance intent."""
        cost_tips = {
            "web_server": [
                "Use Auto Scaling to match demand",
                "Consider Reserved Instances for predictable workloads",
                "Use Application Load Balancer instead of multiple instances",
                "Implement caching to reduce compute needs"
            ],
            "database_server": [
                "Consider Amazon RDS for managed database service",
                "Use Reserved Instances for long-running databases",
                "Right-size instance types based on actual usage",
                "Use Read Replicas instead of larger primary instances"
            ],
            "development_testing": [
                "Use Instance Scheduler to stop instances outside work hours",
                "Consider Spot Instances for fault-tolerant workloads",
                "Use smaller, burstable instance types (t3, t4g)",
                "Take snapshots instead of keeping multiple running instances"
            ],
            "batch_processing": [
                "Use Spot Instances for significant cost savings",
                "Consider AWS Batch for better resource utilization",
                "Use scheduled scaling for predictable batch jobs",
                "Optimize instance types for CPU vs memory requirements"
            ]
        }
        
        return cost_tips.get(intent, [
            "Right-size instances based on actual usage",
            "Use Reserved Instances for predictable workloads",
            "Consider Spot Instances for fault-tolerant applications",
            "Monitor usage with CloudWatch and AWS Cost Explorer"
        ])
    
    def get_remediation_guidance(self, issue_type, intent=None):
        """Get specific remediation guidance for an issue."""
        remediation_guides = {
            "open_security_group": {
                "steps": [
                    "1. Navigate to EC2 > Security Groups",
                    "2. Select the security group with overly permissive rules",
                    "3. Click 'Edit inbound rules'",
                    "4. Replace 0.0.0.0/0 with specific IP ranges or security groups",
                    "5. Remove unnecessary ports and protocols",
                    "6. Test connectivity after changes"
                ],
                "validation": "Verify applications still work with restricted access",
                "automation": "Use AWS Config Rules to detect and alert on overly permissive security groups"
            },
            "unencrypted_ebs": {
                "steps": [
                    "1. Create encrypted snapshot of unencrypted volume",
                    "2. Create new encrypted volume from encrypted snapshot",
                    "3. Stop the instance",
                    "4. Detach original volume and attach encrypted volume",
                    "5. Update device mapping if necessary",
                    "6. Start instance and verify functionality"
                ],
                "validation": "Confirm instance boots and applications work normally",
                "automation": "Enable encryption by default for new EBS volumes"
            },
            "missing_backups": {
                "steps": [
                    "1. Create manual snapshot to establish baseline",
                    "2. Set up automated snapshot lifecycle policy",
                    "3. Use AWS Backup for cross-service backup strategy",
                    "4. Configure retention policies based on requirements",
                    "5. Test restore procedures regularly"
                ],
                "validation": "Test restore process from snapshots",
                "automation": "Use AWS Backup or Data Lifecycle Manager for automated backups"
            },
            "oversized_instance": {
                "steps": [
                    "1. Review CloudWatch metrics for CPU, memory, and network usage",
                    "2. Identify appropriate smaller instance type",
                    "3. Create AMI of current instance",
                    "4. Launch new instance with smaller type from AMI",
                    "5. Test application performance on new instance",
                    "6. Update load balancer targets and DNS if needed",
                    "7. Terminate original instance after validation"
                ],
                "validation": "Monitor performance metrics after instance type change",
                "automation": "Use AWS Compute Optimizer for right-sizing recommendations"
            }
        }
        
        return remediation_guides.get(issue_type, {
            "steps": ["Refer to AWS documentation for specific remediation steps"],
            "validation": "Test changes in non-production environment first",
            "automation": "Consider automating this fix using AWS Config or Lambda"
        })