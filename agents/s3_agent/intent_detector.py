# agents/s3_agent/intent_detector.py

import re
import json
from typing import Dict, List, Optional, Tuple
from enum import Enum

class S3Intent(Enum):
    """Possible user intents for S3 buckets."""
    WEBSITE_HOSTING = "website_hosting"
    DATA_STORAGE = "data_storage" 
    DATA_ARCHIVAL = "data_archival"
    BACKUP_STORAGE = "backup_storage"
    LOG_STORAGE = "log_storage"
    CDN_ORIGIN = "cdn_origin"
    DATA_LAKE = "data_lake"
    UNKNOWN = "unknown"

class IntentDetector:
    """
    Detects user intent for S3 buckets through multiple methods:
    1. Explicit user input
    2. Automatic detection based on bucket analysis
    3. LLM-powered intent inference
    """
    
    def __init__(self):
        self.website_indicators = [
            'index.html', 'index.htm', 'main.html', 'home.html',
            'error.html', '404.html', 'robots.txt', 'sitemap.xml'
        ]
        
        self.archival_indicators = [
            'archive', 'backup', 'old', 'historical', 'retention'
        ]
        
        self.log_indicators = [
            'log', 'logs', 'audit', 'access', 'cloudtrail', 'vpc-flow'
        ]
        
        self.data_lake_indicators = [
            'datalake', 'data-lake', 'analytics', 'etl', 'raw-data', 'processed'
        ]

    def detect_intent(self, 
                     bucket_name: str, 
                     client, 
                     user_intent: Optional[str] = None,
                     user_description: Optional[str] = None) -> Tuple[S3Intent, float, str]:
        """
        Main intent detection method.
        
        Args:
            bucket_name: S3 bucket name
            client: S3 client for API calls
            user_intent: Explicit user intent if provided
            user_description: User's description of bucket purpose
            
        Returns:
            Tuple of (Intent, Confidence 0-1, Reasoning)
        """
        print(f" Detecting intent for bucket: {bucket_name}")
        
        # DEBUG: Show what user intent was received
        print(f" DEBUG: user_intent parameter = {user_intent}")
        
        # Priority 1: Explicit user intent
        if user_intent:
            intent = self._parse_user_intent(user_intent)
            print(f" DEBUG: Parsed user intent: {intent} (from '{user_intent}')")
            if intent != S3Intent.UNKNOWN:
                print(f" User specified intent: {intent.value}")
                return intent, 1.0, "Explicitly specified by user"
        
        # Priority 2: User description analysis
        if user_description:
            intent, confidence, reasoning = self._analyze_user_description(user_description)
            if confidence > 0.7:
                print(f" Intent from description: {intent.value} (confidence: {confidence})")
                return intent, confidence, reasoning
        
        # Priority 3: Automatic detection
        auto_intent, auto_confidence, auto_reasoning = self._auto_detect_intent(bucket_name, client)
        print(f" Auto-detected intent: {auto_intent.value} (confidence: {auto_confidence})")
        
        return auto_intent, auto_confidence, auto_reasoning

    def _parse_user_intent(self, user_intent: str) -> S3Intent:
        """Parse explicit user intent input."""
        intent_mapping = {
            'website': S3Intent.WEBSITE_HOSTING,
            'website hosting': S3Intent.WEBSITE_HOSTING,
            'static website': S3Intent.WEBSITE_HOSTING,
            'hosting': S3Intent.WEBSITE_HOSTING,
            'storage': S3Intent.DATA_STORAGE,
            'data storage': S3Intent.DATA_STORAGE,
            'archive': S3Intent.DATA_ARCHIVAL,
            'archival': S3Intent.DATA_ARCHIVAL,
            'backup': S3Intent.BACKUP_STORAGE,
            'logs': S3Intent.LOG_STORAGE,
            'logging': S3Intent.LOG_STORAGE,
            'cdn': S3Intent.CDN_ORIGIN,
            'data lake': S3Intent.DATA_LAKE,
            'analytics': S3Intent.DATA_LAKE
        }
        
        user_intent_lower = user_intent.lower().strip()
        return intent_mapping.get(user_intent_lower, S3Intent.UNKNOWN)

    def _analyze_user_description(self, description: str) -> Tuple[S3Intent, float, str]:
        """Analyze user's text description to infer intent."""
        description_lower = description.lower()
        
        # Website hosting keywords
        website_keywords = ['website', 'web', 'html', 'hosting', 'frontend', 'static site', 'blog']
        if any(keyword in description_lower for keyword in website_keywords):
            return S3Intent.WEBSITE_HOSTING, 0.9, f"Description contains website keywords: {website_keywords}"
        
        # Data storage keywords  
        storage_keywords = ['store', 'storage', 'data', 'files', 'documents', 'uploads']
        if any(keyword in description_lower for keyword in storage_keywords):
            return S3Intent.DATA_STORAGE, 0.8, f"Description contains storage keywords"
        
        # Archive keywords
        archive_keywords = ['archive', 'old', 'backup', 'retention', 'compliance']
        if any(keyword in description_lower for keyword in archive_keywords):
            return S3Intent.DATA_ARCHIVAL, 0.8, f"Description contains archival keywords"
        
        # Log keywords
        log_keywords = ['log', 'audit', 'monitoring', 'tracking']
        if any(keyword in description_lower for keyword in log_keywords):
            return S3Intent.LOG_STORAGE, 0.8, f"Description contains logging keywords"
        
        return S3Intent.UNKNOWN, 0.3, "No clear intent indicators in description"

    def _auto_detect_intent(self, bucket_name: str, client) -> Tuple[S3Intent, float, str]:
        """Automatically detect intent based on bucket analysis."""
        evidence = []
        confidence_scores = {}
        
        # 1. Analyze bucket name
        name_intent, name_confidence, name_reason = self._analyze_bucket_name(bucket_name)
        if name_confidence > 0.5:
            evidence.append(name_reason)
            confidence_scores[name_intent] = name_confidence
        
        # 2. Check website configuration
        website_intent, website_confidence, website_reason = self._check_website_config(client, bucket_name)
        if website_confidence > 0.5:
            evidence.append(website_reason)
            confidence_scores[website_intent] = confidence_scores.get(website_intent, 0) + website_confidence
        
        # 3. Analyze bucket contents
        content_intent, content_confidence, content_reason = self._analyze_bucket_contents(client, bucket_name)
        if content_confidence > 0.5:
            evidence.append(content_reason)
            confidence_scores[content_intent] = confidence_scores.get(content_intent, 0) + content_confidence
        
        # 4. Check storage class patterns
        storage_intent, storage_confidence, storage_reason = self._analyze_storage_classes(client, bucket_name)
        if storage_confidence > 0.5:
            evidence.append(storage_reason)
            confidence_scores[storage_intent] = confidence_scores.get(storage_intent, 0) + storage_confidence
        
        # Determine best intent
        if confidence_scores:
            best_intent = max(confidence_scores.items(), key=lambda x: x[1])
            intent, total_confidence = best_intent
            # Normalize confidence (max 1.0)
            normalized_confidence = min(total_confidence / 2.0, 1.0)
            reasoning = "; ".join(evidence)
            return intent, normalized_confidence, reasoning
        
        # If no clear intent indicators found, default to DATA_STORAGE
        # This is safer for beginners than UNKNOWN
        return S3Intent.DATA_STORAGE, 0.3, "No clear intent indicators found, defaulting to data storage for security"

    def _analyze_bucket_name(self, bucket_name: str) -> Tuple[S3Intent, float, str]:
        """Analyze bucket name for intent clues."""
        name_lower = bucket_name.lower()
        
        # Website hosting patterns
        if any(indicator in name_lower for indicator in ['website', 'www', 'site', 'web', 'frontend']):
            return S3Intent.WEBSITE_HOSTING, 0.7, f"Bucket name suggests website: '{bucket_name}'"
        
        # Archival patterns
        if any(indicator in name_lower for indicator in self.archival_indicators):
            return S3Intent.DATA_ARCHIVAL, 0.6, f"Bucket name suggests archival: '{bucket_name}'"
        
        # Log patterns
        if any(indicator in name_lower for indicator in self.log_indicators):
            return S3Intent.LOG_STORAGE, 0.6, f"Bucket name suggests logging: '{bucket_name}'"
        
        # Data lake patterns
        if any(indicator in name_lower for indicator in self.data_lake_indicators):
            return S3Intent.DATA_LAKE, 0.6, f"Bucket name suggests data lake: '{bucket_name}'"
        
        return S3Intent.UNKNOWN, 0.0, "No intent indicators in bucket name"

    def _check_website_config(self, client, bucket_name: str) -> Tuple[S3Intent, float, str]:
        """Check if bucket has website hosting configuration."""
        try:
            response = client.get_bucket_website(Bucket=bucket_name)
            index_doc = response.get('IndexDocument', {}).get('Suffix', '')
            return S3Intent.WEBSITE_HOSTING, 0.9, f"Website hosting enabled with index: {index_doc}"
        except Exception as e:
            if hasattr(e, 'response') and e.response.get('Error', {}).get('Code') == 'NoSuchWebsiteConfiguration':
                return S3Intent.UNKNOWN, 0.0, "No website configuration"
            return S3Intent.UNKNOWN, 0.0, f"Error checking website config: {e}"

    def _analyze_bucket_contents(self, client, bucket_name: str) -> Tuple[S3Intent, float, str]:
        """Analyze bucket contents to infer intent."""
        try:
            response = client.list_objects_v2(Bucket=bucket_name, MaxKeys=100)
            objects = response.get('Contents', [])
            
            if not objects:
                return S3Intent.UNKNOWN, 0.0, "Empty bucket"
            
            file_types = {}
            total_files = len(objects)
            
            # Analyze file extensions
            for obj in objects:
                key = obj['Key'].lower()
                if '.' in key:
                    ext = key.split('.')[-1]
                    file_types[ext] = file_types.get(ext, 0) + 1
                
                # Check for specific website files
                if any(indicator in key for indicator in self.website_indicators):
                    return S3Intent.WEBSITE_HOSTING, 0.8, f"Found website files: {key}"
            
            # Analyze file type distribution
            web_extensions = ['html', 'htm', 'css', 'js', 'png', 'jpg', 'jpeg', 'gif', 'svg', 'ico']
            web_files = sum(file_types.get(ext, 0) for ext in web_extensions)
            
            if web_files > total_files * 0.5:  # More than 50% web files
                return S3Intent.WEBSITE_HOSTING, 0.7, f"High percentage of web files: {web_files}/{total_files}"
            
            # Check for log file patterns
            log_extensions = ['log', 'txt', 'gz']
            log_files = sum(file_types.get(ext, 0) for ext in log_extensions)
            if log_files > total_files * 0.7:
                return S3Intent.LOG_STORAGE, 0.6, f"High percentage of log files: {log_files}/{total_files}"
            
            # Default to data storage for mixed content
            return S3Intent.DATA_STORAGE, 0.5, f"Mixed file types suggest general storage: {list(file_types.keys())[:5]}"
            
        except Exception as e:
            # If we can't analyze contents (empty bucket, permission issues, etc.)
            # Default to DATA_STORAGE intent for safety
            return S3Intent.DATA_STORAGE, 0.4, f"Unable to analyze contents, defaulting to data storage: {e}"

    def _analyze_storage_classes(self, client, bucket_name: str) -> Tuple[S3Intent, float, str]:
        """Analyze storage classes used in bucket."""
        try:
            response = client.list_objects_v2(Bucket=bucket_name, MaxKeys=100)
            objects = response.get('Contents', [])
            
            if not objects:
                return S3Intent.UNKNOWN, 0.0, "No objects to analyze"
            
            storage_classes = {}
            for obj in objects:
                storage_class = obj.get('StorageClass', 'STANDARD')
                storage_classes[storage_class] = storage_classes.get(storage_class, 0) + 1
            
            total_objects = len(objects)
            
            # High percentage of GLACIER or DEEP_ARCHIVE suggests archival
            archival_classes = ['GLACIER', 'DEEP_ARCHIVE']
            archival_count = sum(storage_classes.get(cls, 0) for cls in archival_classes)
            if archival_count > total_objects * 0.5:
                return S3Intent.DATA_ARCHIVAL, 0.7, f"High percentage of archival storage classes: {archival_count}/{total_objects}"
            
            # Mostly STANDARD suggests active use (website or regular storage)
            standard_count = storage_classes.get('STANDARD', 0)
            if standard_count > total_objects * 0.8:
                return S3Intent.DATA_STORAGE, 0.4, f"Mostly STANDARD storage class: {standard_count}/{total_objects}"
            
            return S3Intent.UNKNOWN, 0.2, f"Mixed storage classes: {storage_classes}"
            
        except Exception as e:
            return S3Intent.UNKNOWN, 0.0, f"Error analyzing storage classes: {e}"

    def get_intent_recommendations(self, intent: S3Intent, bucket_name: str) -> Dict:
        """Get recommendations based on detected intent."""
        recommendations = {
            S3Intent.WEBSITE_HOSTING: {
                "security": {
                    "public_access": "Enable public read access for objects",
                    "public_access_block": "Disable BlockPublicPolicy for website hosting",
                    "bucket_policy": "Add GetObject policy for /* resources"
                },
                "configuration": {
                    "website_hosting": "Ensure index.html and error.html are configured",
                    "storage_class": "Use STANDARD for active website files"
                },
                "cost_optimization": {
                    "storage_class": "Consider STANDARD_IA for infrequently accessed assets",
                    "cloudfront": "Add CloudFront CDN for better performance and cost"
                }
            },
            S3Intent.DATA_STORAGE: {
                "security": {
                    "public_access": "Block all public access",
                    "encryption": "Enable default encryption",
                    "versioning": "Enable versioning for data protection"
                },
                "configuration": {
                    "lifecycle": "Set up lifecycle rules based on access patterns",
                    "storage_class": "Use appropriate storage class for access frequency"
                },
                "cost_optimization": {
                    "storage_class": "Move to IA or Glacier for infrequent access",
                    "lifecycle": "Automate transitions to cheaper storage classes"
                }
            },
            S3Intent.DATA_ARCHIVAL: {
                "security": {
                    "public_access": "Block all public access",
                    "encryption": "Enable encryption at rest",
                    "mfa_delete": "Enable MFA delete for protection"
                },
                "configuration": {
                    "storage_class": "Use GLACIER or DEEP_ARCHIVE",
                    "lifecycle": "Set up automatic transition to archival classes"
                },
                "cost_optimization": {
                    "storage_class": "Use DEEP_ARCHIVE for long-term retention",
                    "lifecycle": "Automate deletion after retention period"
                }
            }
            # Add more intent-specific recommendations...
        }
        
        return recommendations.get(intent, {})