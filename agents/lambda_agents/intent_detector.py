# agents/lambda_agents/intent_detector.py

import re
import json
from typing import Dict, List, Optional, Tuple
from enum import Enum


class LambdaIntent(Enum):
    """Possible user intents for Lambda functions."""
    API_ENDPOINT = "api_endpoint"
    SCHEDULED_TASK = "scheduled_task"
    EVENT_PROCESSOR = "event_processor"
    DATA_TRANSFORMATION = "data_transformation"
    STREAM_PROCESSOR = "stream_processor"
    NOTIFICATION_HANDLER = "notification_handler"
    ASYNC_TASK = "async_task"
    WEBHOOK_HANDLER = "webhook_handler"
    BATCH_PROCESSING = "batch_processing"
    CRON_JOB = "cron_job"
    UNKNOWN = "unknown"


class IntentDetector:
    """
    Detects user intent for Lambda functions through multiple methods:
    1. Explicit user input
    2. Automatic detection based on function analysis
    3. LLM-powered intent inference
    """
    
    def __init__(self):
        self.api_indicators = [
            'api', 'rest', 'http', 'request', 'response', 'handler', 'endpoint',
            'gateway', 'routes', 'cors', 'method'
        ]
        
        self.scheduled_indicators = [
            'schedule', 'cron', 'timer', 'periodic', 'job', 'batch',
            'eventbridge', 'cloudwatch'
        ]
        
        self.event_processor_indicators = [
            'event', 'process', 'consume', 'trigger', 'listener',
            's3', 'dynamodb', 'sqs', 'sns'
        ]
        
        self.stream_processor_indicators = [
            'stream', 'kinesis', 'dynamodb streams', 'firehose',
            'real-time', 'realtime', 'processing'
        ]
        
        self.notification_indicators = [
            'notification', 'email', 'sms', 'alert', 'message',
            'publish', 'subscribe', 'sns'
        ]
        
        self.data_transformation_indicators = [
            'transform', 'convert', 'normalize', 'parse', 'etl',
            'data', 'format', 'decode', 'encode'
        ]

    def detect_intent(self, 
                     function_name: str, 
                     client, 
                     user_intent: Optional[str] = None,
                     user_description: Optional[str] = None) -> Tuple[LambdaIntent, float, str]:
        """
        Main intent detection method.
        
        Args:
            function_name: Lambda function name
            client: Lambda client for API calls
            user_intent: Explicit user intent if provided
            user_description: User's description of function purpose
            
        Returns:
            Tuple of (Intent, Confidence 0-1, Reasoning)
        """
        
        # 1. Check explicit user intent
        if user_intent:
            try:
                intent = LambdaIntent[user_intent.upper().replace(" ", "_")]
                return intent, 1.0, f"User explicitly specified intent: {user_intent}"
            except KeyError:
                pass
        
        # 2. Analyze function configuration
        try:
            config = client.get_function_configuration(FunctionName=function_name)
        except Exception as e:
            return LambdaIntent.UNKNOWN, 0.0, f"Could not retrieve function config: {str(e)}"
        
        return self._detect_from_config(function_name, config, user_description)
    
    def _detect_from_config(self, 
                           function_name: str, 
                           config: dict,
                           user_description: Optional[str] = None) -> Tuple[LambdaIntent, float, str]:
        """Detect intent from function configuration."""
        
        # Combine all text for analysis
        analysis_text = function_name.lower()
        
        if user_description:
            analysis_text += " " + user_description.lower()
        
        # Check handler path
        handler = config.get('Handler', '').lower()
        analysis_text += " " + handler
        
        # Check environment variables
        env_vars = config.get('Environment', {}).get('Variables', {})
        for key, value in env_vars.items():
            analysis_text += f" {key.lower()} {str(value).lower()}"
        
        # Check description
        if 'Description' in config:
            analysis_text += " " + config['Description'].lower()
        
        # Score each intent
        scores = {}
        
        # API Endpoint
        api_score = sum(1 for ind in self.api_indicators if ind in analysis_text)
        scores[LambdaIntent.API_ENDPOINT] = api_score
        
        # Scheduled Task
        scheduled_score = sum(1 for ind in self.scheduled_indicators if ind in analysis_text)
        scores[LambdaIntent.SCHEDULED_TASK] = scheduled_score
        
        # Event Processor
        event_score = sum(1 for ind in self.event_processor_indicators if ind in analysis_text)
        scores[LambdaIntent.EVENT_PROCESSOR] = event_score
        
        # Stream Processor
        stream_score = sum(1 for ind in self.stream_processor_indicators if ind in analysis_text)
        scores[LambdaIntent.STREAM_PROCESSOR] = stream_score
        
        # Notification Handler
        notify_score = sum(1 for ind in self.notification_indicators if ind in analysis_text)
        scores[LambdaIntent.NOTIFICATION_HANDLER] = notify_score
        
        # Data Transformation
        transform_score = sum(1 for ind in self.data_transformation_indicators if ind in analysis_text)
        scores[LambdaIntent.DATA_TRANSFORMATION] = transform_score
        
        # Async Task - check for async patterns
        async_score = 0
        if 'async' in analysis_text or 'background' in analysis_text:
            async_score = 2
        scores[LambdaIntent.ASYNC_TASK] = async_score
        
        # Webhook Handler
        webhook_score = 0
        if any(ind in analysis_text for ind in ['webhook', 'hook', 'github', 'gitlab', 'bitbucket']):
            webhook_score = 2
        scores[LambdaIntent.WEBHOOK_HANDLER] = webhook_score
        
        # Get best match
        best_intent = max(scores, key=scores.get)
        score = scores[best_intent]
        
        if score == 0:
            return LambdaIntent.UNKNOWN, 0.0, "Could not determine function intent from analysis"
        
        # Normalize confidence (max score is ~10 for most intents)
        confidence = min(score / 10.0, 1.0)
        reasoning = f"Detected intent '{best_intent.value}' based on function configuration analysis"
        
        return best_intent, confidence, reasoning

    def convert_intent_to_checks(self, intent: LambdaIntent) -> List[str]:
        """Convert detected intent to specific security checks."""
        intent_checks = {
            LambdaIntent.API_ENDPOINT: [
                "logging_enabled",
                "environment_variables_encrypted",
                "appropriate_timeout"
            ],
            LambdaIntent.SCHEDULED_TASK: [
                "logging_enabled",
                "environment_variables_encrypted",
                "dead_letter_queue_configured"
            ],
            LambdaIntent.EVENT_PROCESSOR: [
                "logging_enabled",
                "environment_variables_encrypted",
                "error_handling"
            ],
            LambdaIntent.STREAM_PROCESSOR: [
                "logging_enabled",
                "environment_variables_encrypted",
                "batch_size_optimized"
            ],
            LambdaIntent.NOTIFICATION_HANDLER: [
                "logging_enabled",
                "environment_variables_encrypted",
                "appropriate_timeout"
            ],
            LambdaIntent.DATA_TRANSFORMATION: [
                "logging_enabled",
                "environment_variables_encrypted",
                "memory_allocation"
            ],
            LambdaIntent.ASYNC_TASK: [
                "logging_enabled",
                "environment_variables_encrypted",
                "appropriate_timeout"
            ],
            LambdaIntent.WEBHOOK_HANDLER: [
                "logging_enabled",
                "environment_variables_encrypted",
                "request_validation"
            ],
            LambdaIntent.BATCH_PROCESSING: [
                "logging_enabled",
                "environment_variables_encrypted",
                "timeout_for_batch"
            ],
            LambdaIntent.CRON_JOB: [
                "logging_enabled",
                "environment_variables_encrypted",
                "monitoring"
            ]
        }
        
        return intent_checks.get(intent, ["logging_enabled", "environment_variables_encrypted"])
