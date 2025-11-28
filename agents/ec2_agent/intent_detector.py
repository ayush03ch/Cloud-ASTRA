# agents/ec2_agent/intent_detector.py

import re
import json
from typing import Dict, List, Optional, Tuple
from enum import Enum


class EC2Intent(Enum):
    """Possible user intents for EC2 instances."""
    WEB_SERVER = "web_server"
    DATABASE_SERVER = "database_server"
    APPLICATION_SERVER = "application_server"
    DEVELOPMENT_TESTING = "development_testing"
    BATCH_PROCESSING = "batch_processing"
    HIGH_PERFORMANCE_COMPUTING = "high_performance_computing"
    BASTION_HOST = "bastion_host"
    LOAD_BALANCER = "load_balancer"
    MICROSERVICES = "microservices"
    DATA_PROCESSING = "data_processing"
    BACKUP_DISASTER_RECOVERY = "backup_disaster_recovery"
    UNKNOWN = "unknown"


class EC2IntentDetector:
    """
    Detects user intent for EC2 instances through multiple methods:
    1. Explicit user input
    2. Automatic detection based on instance analysis
    3. LLM-powered intent inference
    """
    
    def __init__(self):
        self.web_server_indicators = [
            'web', 'http', 'https', 'nginx', 'apache', 'frontend', 'www', 'site'
        ]
        
        self.database_indicators = [
            'db', 'database', 'mysql', 'postgres', 'oracle', 'mongodb', 'redis',
            'sql', 'nosql', 'rds', 'aurora'
        ]
        
        self.app_server_indicators = [
            'app', 'application', 'api', 'backend', 'service', 'microservice',
            'java', 'spring', 'node', 'python', 'django', 'flask'
        ]
        
        self.dev_test_indicators = [
            'dev', 'development', 'test', 'testing', 'staging', 'qa', 'sandbox',
            'experiment', 'trial', 'demo'
        ]
        
        self.batch_indicators = [
            'batch', 'worker', 'job', 'queue', 'cron', 'scheduled', 'etl',
            'processing', 'compute'
        ]
        
        self.hpc_indicators = [
            'hpc', 'cluster', 'compute', 'gpu', 'ml', 'ai', 'training',
            'scientific', 'research', 'parallel'
        ]
        
        self.bastion_indicators = [
            'bastion', 'jumpbox', 'jump', 'gateway', 'proxy', 'ssh', 'vpn'
        ]

    def detect_intent(self, 
                     instance_id: str,
                     client, 
                     user_intent: Optional[str] = None,
                     user_description: Optional[str] = None) -> Tuple[EC2Intent, float, str]:
        """
        Main intent detection method.
        
        Args:
            instance_id: EC2 instance ID
            client: EC2 client for API calls
            user_intent: Explicit user intent if provided
            user_description: User's description of instance purpose
            
        Returns:
            Tuple of (Intent, Confidence 0-1, Reasoning)
        """
        print(f"🔍 Detecting intent for EC2 instance: {instance_id}")
        
        # DEBUG: Show what user intent was received
        print(f"DEBUG: user_intent parameter = {user_intent}")
        
        # Priority 1: Explicit user intent
        if user_intent:
            intent = self._parse_user_intent(user_intent)
            print(f"DEBUG: Parsed user intent: {intent} (from '{user_intent}')")
            if intent != EC2Intent.UNKNOWN:
                print(f"✅ User specified intent: {intent.value}")
                return intent, 1.0, "Explicitly specified by user"
        
        # Priority 2: User description analysis
        if user_description:
            intent, confidence, reasoning = self._analyze_user_description(user_description)
            if confidence > 0.7:
                print(f"📝 Intent from description: {intent.value} (confidence: {confidence})")
                return intent, confidence, reasoning
        
        # Priority 3: Automatic detection
        auto_intent, auto_confidence, auto_reasoning = self._auto_detect_intent(instance_id, client)
        print(f"🤖 Auto-detected intent: {auto_intent.value} (confidence: {auto_confidence})")
        
        return auto_intent, auto_confidence, auto_reasoning

    def _parse_user_intent(self, user_intent: str) -> EC2Intent:
        """Parse explicit user intent input."""
        intent_mapping = {
            'web': EC2Intent.WEB_SERVER,
            'web server': EC2Intent.WEB_SERVER,
            'website': EC2Intent.WEB_SERVER,
            'frontend': EC2Intent.WEB_SERVER,
            'database': EC2Intent.DATABASE_SERVER,
            'db': EC2Intent.DATABASE_SERVER,
            'database server': EC2Intent.DATABASE_SERVER,
            'application': EC2Intent.APPLICATION_SERVER,
            'app server': EC2Intent.APPLICATION_SERVER,
            'backend': EC2Intent.APPLICATION_SERVER,
            'api': EC2Intent.APPLICATION_SERVER,
            'development': EC2Intent.DEVELOPMENT_TESTING,
            'dev': EC2Intent.DEVELOPMENT_TESTING,
            'testing': EC2Intent.DEVELOPMENT_TESTING,
            'staging': EC2Intent.DEVELOPMENT_TESTING,
            'batch': EC2Intent.BATCH_PROCESSING,
            'worker': EC2Intent.BATCH_PROCESSING,
            'processing': EC2Intent.BATCH_PROCESSING,
            'hpc': EC2Intent.HIGH_PERFORMANCE_COMPUTING,
            'cluster': EC2Intent.HIGH_PERFORMANCE_COMPUTING,
            'gpu': EC2Intent.HIGH_PERFORMANCE_COMPUTING,
            'bastion': EC2Intent.BASTION_HOST,
            'jump box': EC2Intent.BASTION_HOST,
            'gateway': EC2Intent.BASTION_HOST,
            'load balancer': EC2Intent.LOAD_BALANCER,
            'microservice': EC2Intent.MICROSERVICES,
            'data processing': EC2Intent.DATA_PROCESSING,
            'backup': EC2Intent.BACKUP_DISASTER_RECOVERY
        }
        
        user_intent_lower = user_intent.lower().strip()
        return intent_mapping.get(user_intent_lower, EC2Intent.UNKNOWN)

    def _analyze_user_description(self, description: str) -> Tuple[EC2Intent, float, str]:
        """Analyze user's text description to infer intent."""
        description_lower = description.lower()
        
        # Web server keywords
        web_keywords = ['web', 'website', 'http', 'html', 'frontend', 'nginx', 'apache']
        if any(keyword in description_lower for keyword in web_keywords):
            return EC2Intent.WEB_SERVER, 0.9, f"Description contains web server keywords"
        
        # Database keywords
        db_keywords = ['database', 'mysql', 'postgres', 'mongo', 'redis', 'sql']
        if any(keyword in description_lower for keyword in db_keywords):
            return EC2Intent.DATABASE_SERVER, 0.9, f"Description contains database keywords"
        
        # Application server keywords
        app_keywords = ['application', 'api', 'backend', 'service', 'microservice']
        if any(keyword in description_lower for keyword in app_keywords):
            return EC2Intent.APPLICATION_SERVER, 0.8, f"Description contains application keywords"
        
        # Development keywords
        dev_keywords = ['development', 'testing', 'dev', 'qa', 'staging', 'sandbox']
        if any(keyword in description_lower for keyword in dev_keywords):
            return EC2Intent.DEVELOPMENT_TESTING, 0.8, f"Description contains development keywords"
        
        # Batch processing keywords
        batch_keywords = ['batch', 'worker', 'job', 'queue', 'processing', 'etl']
        if any(keyword in description_lower for keyword in batch_keywords):
            return EC2Intent.BATCH_PROCESSING, 0.8, f"Description contains batch processing keywords"
        
        # HPC keywords
        hpc_keywords = ['hpc', 'cluster', 'gpu', 'ml', 'ai', 'training', 'compute']
        if any(keyword in description_lower for keyword in hpc_keywords):
            return EC2Intent.HIGH_PERFORMANCE_COMPUTING, 0.8, f"Description contains HPC keywords"
        
        return EC2Intent.UNKNOWN, 0.3, "No clear intent indicators in description"

    def _auto_detect_intent(self, instance_id: str, client) -> Tuple[EC2Intent, float, str]:
        """Automatically detect intent based on instance analysis."""
        evidence = []
        confidence_scores = {}
        
        try:
            # Get instance details
            response = client.describe_instances(InstanceIds=[instance_id])
            if not response['Reservations']:
                return EC2Intent.UNKNOWN, 0.0, "Instance not found"
            
            instance = response['Reservations'][0]['Instances'][0]
            
            # 1. Analyze instance name/tags
            name_intent, name_confidence, name_reason = self._analyze_instance_tags(instance)
            if name_confidence > 0.5:
                evidence.append(name_reason)
                confidence_scores[name_intent] = name_confidence
            
            # 2. Analyze instance type
            type_intent, type_confidence, type_reason = self._analyze_instance_type(instance)
            if type_confidence > 0.5:
                evidence.append(type_reason)
                confidence_scores[type_intent] = confidence_scores.get(type_intent, 0) + type_confidence
            
            # 3. Analyze security groups
            sg_intent, sg_confidence, sg_reason = self._analyze_security_groups(client, instance)
            if sg_confidence > 0.5:
                evidence.append(sg_reason)
                confidence_scores[sg_intent] = confidence_scores.get(sg_intent, 0) + sg_confidence
            
            # 4. Analyze instance placement and networking
            network_intent, network_confidence, network_reason = self._analyze_network_config(instance)
            if network_confidence > 0.5:
                evidence.append(network_reason)
                confidence_scores[network_intent] = confidence_scores.get(network_intent, 0) + network_confidence
            
            # 5. Analyze EBS volumes
            storage_intent, storage_confidence, storage_reason = self._analyze_storage_config(client, instance)
            if storage_confidence > 0.5:
                evidence.append(storage_reason)
                confidence_scores[storage_intent] = confidence_scores.get(storage_intent, 0) + storage_confidence
            
            # Determine best intent
            if confidence_scores:
                best_intent = max(confidence_scores.items(), key=lambda x: x[1])
                intent, total_confidence = best_intent
                # Normalize confidence (max 1.0)
                normalized_confidence = min(total_confidence / 2.5, 1.0)
                reasoning = "; ".join(evidence)
                return intent, normalized_confidence, reasoning
            
            # Default based on instance characteristics
            if instance.get('State', {}).get('Name') == 'stopped':
                return EC2Intent.DEVELOPMENT_TESTING, 0.4, "Stopped instance suggests development/testing use"
            
            return EC2Intent.APPLICATION_SERVER, 0.3, "No clear intent indicators found, defaulting to application server"
            
        except Exception as e:
            return EC2Intent.UNKNOWN, 0.0, f"Error analyzing instance: {e}"

    def _analyze_instance_tags(self, instance) -> Tuple[EC2Intent, float, str]:
        """Analyze instance tags for intent clues."""
        tags = {tag['Key'].lower(): tag['Value'].lower() for tag in instance.get('Tags', [])}
        
        # Check Name tag
        name = tags.get('name', '')
        if name:
            # Web server patterns
            if any(indicator in name for indicator in self.web_server_indicators):
                return EC2Intent.WEB_SERVER, 0.8, f"Instance name suggests web server: '{name}'"
            
            # Database patterns
            if any(indicator in name for indicator in self.database_indicators):
                return EC2Intent.DATABASE_SERVER, 0.8, f"Instance name suggests database: '{name}'"
            
            # Application server patterns
            if any(indicator in name for indicator in self.app_server_indicators):
                return EC2Intent.APPLICATION_SERVER, 0.7, f"Instance name suggests application server: '{name}'"
            
            # Development patterns
            if any(indicator in name for indicator in self.dev_test_indicators):
                return EC2Intent.DEVELOPMENT_TESTING, 0.7, f"Instance name suggests development: '{name}'"
            
            # Bastion patterns
            if any(indicator in name for indicator in self.bastion_indicators):
                return EC2Intent.BASTION_HOST, 0.9, f"Instance name suggests bastion host: '{name}'"
        
        # Check Environment tag
        env = tags.get('environment', tags.get('env', ''))
        if env in ['dev', 'development', 'test', 'testing', 'staging']:
            return EC2Intent.DEVELOPMENT_TESTING, 0.6, f"Environment tag suggests development: '{env}'"
        
        # Check Role/Purpose tags
        role = tags.get('role', tags.get('purpose', tags.get('function', '')))
        if role:
            role_intent = self._parse_user_intent(role)
            if role_intent != EC2Intent.UNKNOWN:
                return role_intent, 0.7, f"Role tag indicates: '{role}'"
        
        return EC2Intent.UNKNOWN, 0.0, "No intent indicators in tags"

    def _analyze_instance_type(self, instance) -> Tuple[EC2Intent, float, str]:
        """Analyze instance type for intent clues."""
        instance_type = instance.get('InstanceType', '')
        
        # GPU instances suggest HPC/ML workloads
        if any(gpu_type in instance_type for gpu_type in ['p3', 'p4', 'g3', 'g4']):
            return EC2Intent.HIGH_PERFORMANCE_COMPUTING, 0.7, f"GPU instance type suggests HPC/ML: {instance_type}"
        
        # Memory-optimized instances often used for databases
        if any(mem_type in instance_type for mem_type in ['r5', 'r6', 'x1', 'z1']):
            return EC2Intent.DATABASE_SERVER, 0.5, f"Memory-optimized instance suggests database: {instance_type}"
        
        # Compute-optimized for batch processing
        if any(compute_type in instance_type for compute_type in ['c5', 'c6']):
            return EC2Intent.BATCH_PROCESSING, 0.4, f"Compute-optimized instance suggests batch processing: {instance_type}"
        
        # Burstable instances often used for development
        if any(burst_type in instance_type for burst_type in ['t2', 't3', 't4']):
            return EC2Intent.DEVELOPMENT_TESTING, 0.3, f"Burstable instance suggests development: {instance_type}"
        
        return EC2Intent.UNKNOWN, 0.0, "Instance type provides no clear intent indicators"

    def _analyze_security_groups(self, client, instance) -> Tuple[EC2Intent, float, str]:
        """Analyze security groups for intent clues."""
        try:
            sg_ids = [sg['GroupId'] for sg in instance.get('SecurityGroups', [])]
            if not sg_ids:
                return EC2Intent.UNKNOWN, 0.0, "No security groups attached"
            
            response = client.describe_security_groups(GroupIds=sg_ids)
            security_groups = response['SecurityGroups']
            
            open_ports = set()
            for sg in security_groups:
                for rule in sg.get('IpPermissions', []):
                    if rule.get('FromPort'):
                        open_ports.add(rule['FromPort'])
            
            # Web server ports
            web_ports = {80, 443, 8080, 8443}
            if web_ports.intersection(open_ports):
                return EC2Intent.WEB_SERVER, 0.8, f"Web server ports open: {web_ports.intersection(open_ports)}"
            
            # Database ports
            db_ports = {3306, 5432, 1521, 27017, 6379}
            if db_ports.intersection(open_ports):
                return EC2Intent.DATABASE_SERVER, 0.8, f"Database ports open: {db_ports.intersection(open_ports)}"
            
            # SSH only (bastion pattern)
            if open_ports == {22}:
                return EC2Intent.BASTION_HOST, 0.7, "Only SSH port 22 open, suggests bastion host"
            
            # High port ranges (application servers)
            high_ports = {port for port in open_ports if port > 8000}
            if high_ports:
                return EC2Intent.APPLICATION_SERVER, 0.5, f"High ports open suggest application server: {high_ports}"
            
            return EC2Intent.UNKNOWN, 0.2, f"Open ports: {open_ports}"
            
        except Exception as e:
            return EC2Intent.UNKNOWN, 0.0, f"Error analyzing security groups: {e}"

    def _analyze_network_config(self, instance) -> Tuple[EC2Intent, float, str]:
        """Analyze network configuration for intent clues."""
        # Public IP suggests public-facing services
        public_ip = instance.get('PublicIpAddress')
        if public_ip:
            return EC2Intent.WEB_SERVER, 0.4, "Public IP suggests public-facing service"
        
        # Private subnet only suggests internal services
        if not public_ip and instance.get('PrivateIpAddress'):
            return EC2Intent.APPLICATION_SERVER, 0.3, "Private IP only suggests internal service"
        
        return EC2Intent.UNKNOWN, 0.0, "Network configuration provides no clear indicators"

    def _analyze_storage_config(self, client, instance) -> Tuple[EC2Intent, float, str]:
        """Analyze EBS volumes for intent clues."""
        try:
            # Get EBS volumes
            volumes = []
            for bdm in instance.get('BlockDeviceMappings', []):
                if 'Ebs' in bdm:
                    volumes.append(bdm['Ebs']['VolumeId'])
            
            if not volumes:
                return EC2Intent.UNKNOWN, 0.0, "No EBS volumes attached"
            
            response = client.describe_volumes(VolumeIds=volumes)
            total_size = sum(vol['Size'] for vol in response['Volumes'])
            
            # Large storage suggests database or data processing
            if total_size > 500:  # > 500 GB
                return EC2Intent.DATABASE_SERVER, 0.5, f"Large storage ({total_size}GB) suggests database use"
            elif total_size > 100:  # > 100 GB
                return EC2Intent.DATA_PROCESSING, 0.4, f"Moderate storage ({total_size}GB) suggests data processing"
            
            return EC2Intent.UNKNOWN, 0.1, f"Storage size: {total_size}GB"
            
        except Exception as e:
            return EC2Intent.UNKNOWN, 0.0, f"Error analyzing storage: {e}"

    def get_intent_recommendations(self, intent: EC2Intent, instance_id: str) -> Dict:
        """Get recommendations based on detected intent."""
        recommendations = {
            EC2Intent.WEB_SERVER: {
                "security": {
                    "security_groups": "Allow HTTP (80) and HTTPS (443) only from 0.0.0.0/0",
                    "ssh_access": "Restrict SSH (22) to specific IP ranges",
                    "ssl_termination": "Use ALB or CloudFront for SSL termination"
                },
                "configuration": {
                    "auto_scaling": "Set up Auto Scaling for high availability",
                    "load_balancer": "Use Application Load Balancer for distribution",
                    "instance_type": "Use compute-optimized instances (c5, c6)"
                },
                "monitoring": {
                    "cloudwatch": "Monitor CPU, network, and response time",
                    "logging": "Enable access logs and error logs"
                }
            },
            EC2Intent.DATABASE_SERVER: {
                "security": {
                    "security_groups": "Restrict database ports to application servers only",
                    "encryption": "Enable EBS encryption for data at rest",
                    "backup": "Set up automated EBS snapshots"
                },
                "configuration": {
                    "instance_type": "Use memory-optimized instances (r5, r6)",
                    "storage": "Use Provisioned IOPS SSD for consistent performance",
                    "multi_az": "Consider RDS for managed database service"
                },
                "monitoring": {
                    "cloudwatch": "Monitor CPU, memory, disk I/O, and connections",
                    "backup_monitoring": "Monitor backup completion and retention"
                }
            },
            EC2Intent.DEVELOPMENT_TESTING: {
                "security": {
                    "security_groups": "Use restrictive security groups for dev environments",
                    "temporary_access": "Use temporary access credentials",
                    "isolation": "Keep separate from production networks"
                },
                "cost_optimization": {
                    "instance_scheduling": "Use Instance Scheduler to stop/start automatically",
                    "spot_instances": "Consider Spot Instances for cost savings",
                    "right_sizing": "Use smaller instance types for dev/test"
                },
                "configuration": {
                    "snapshots": "Take snapshots before major changes",
                    "automation": "Use infrastructure as code for consistency"
                }
            },
            EC2Intent.BASTION_HOST: {
                "security": {
                    "security_groups": "Allow SSH (22) only from authorized IP ranges",
                    "key_management": "Use separate SSH keys and rotate regularly",
                    "logging": "Enable detailed SSH logging and monitoring"
                },
                "configuration": {
                    "high_availability": "Deploy bastion hosts in multiple AZs",
                    "hardening": "Apply security hardening best practices",
                    "updates": "Keep OS and software up to date"
                },
                "alternatives": {
                    "session_manager": "Consider AWS Systems Manager Session Manager",
                    "vpn": "Evaluate AWS Client VPN as alternative"
                }
            },
            EC2Intent.HIGH_PERFORMANCE_COMPUTING: {
                "performance": {
                    "instance_type": "Use GPU instances (p3, p4) for ML workloads",
                    "placement_groups": "Use cluster placement groups for low latency",
                    "enhanced_networking": "Enable enhanced networking (SR-IOV)"
                },
                "storage": {
                    "high_iops": "Use NVMe SSD instances for high I/O",
                    "fsx": "Consider Amazon FSx for high-performance file systems",
                    "efs": "Use EFS for shared storage across instances"
                },
                "cost_optimization": {
                    "spot_instances": "Use Spot Instances for fault-tolerant workloads",
                    "reserved_instances": "Purchase Reserved Instances for predictable workloads"
                }
            }
        }
        
        return recommendations.get(intent, {})