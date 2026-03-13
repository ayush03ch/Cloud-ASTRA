# supervisor/dispatcher.py
from agents.s3_agent.s3_agent import S3Agent
from agents.ec2_agent.ec2_agent import EC2Agent
from agents.iam_agent.iam_agent import IAMAgent
from agents.lambda_agents.lambda_agent import LambdaAgent
from agents.route53_agent.route53_agent import Route53Agent
from agents.apigateway_agent.apigateway_agent import APIGatewayAgent
from agents.cloudfront_agent.cloudfront_agent import CloudFrontAgent
from agents.vpc_agent.vpc_agent import VPCAgent
import logging

logger = logging.getLogger(__name__)

class Dispatcher:
    """
    Sends tasks to appropriate service agents.
    Supports S3, EC2, IAM, and future services.
    """

    def __init__(self, creds):
        self.creds = creds

    def dispatch(self, user_intent_input=None, service=None, ec2_filters=None, ec2_checks=None, iam_scope=None, iam_checks=None, lambda_function_name=None, lambda_checks=None, route53_scope=None, route53_checks=None, apigw_scope=None, apigw_checks=None, cloudfront_scope=None, cloudfront_checks=None, vpc_scope=None, vpc_checks=None):
        """
        Dispatch scan to appropriate service(s).
        
        Args:
            user_intent_input: User's explicit intent for resources
            service: Specific service to scan ('s3', 'ec2', 'iam', 'lambda', 'route53', 'apigateway', 'cloudfront', 'vpc', or None for all)
            ec2_filters: Dict with instance_ids and tags filters for EC2
            ec2_checks: Dict with check flags for EC2 (security_groups, ebs_encryption, etc.)
            iam_scope: Scope for IAM scan ('account', 'users', 'roles', 'policies')
            iam_checks: Dict with check flags for IAM (access_key_rotation, mfa_enforcement, etc.)
            lambda_function_name: Specific Lambda function name to scan (or None for all)
            lambda_checks: Dict with check flags for Lambda
            route53_scope: Scope for Route53 scan ('all', 'public', 'private', or specific zone ID)
            route53_checks: Dict with check flags for Route53 (dnssec, query_logging, etc.)
            apigw_scope: Specific REST API id/name or 'all'
            apigw_checks: Dict with check flags for API Gateway
            cloudfront_scope: Scope for CloudFront scan ('all', or specific distribution ID)
            cloudfront_checks: Dict with check flags for CloudFront
            vpc_scope: Scope for VPC scan ('all', or specific VPC ID)
            vpc_checks: Dict with check flags for VPC
        """
        results = {}
        
        # Determine which services to scan
        services_to_scan = []
        if service:
            services_to_scan = [service]
        else:
            services_to_scan = ['s3', 'ec2']  # Default: scan both
        
        # S3 Agent
        if 's3' in services_to_scan:
            try:
                s3_agent = S3Agent(creds=self.creds)
                results["s3"] = s3_agent.scan(user_intent_input=user_intent_input)
                logger.info(f"S3 scan completed successfully with {len(results['s3'])} findings")
            except Exception as e:
                logger.error(f"S3 scan failed: {e}", exc_info=True)
                results["s3"] = []
        
        # EC2 Agent
        if 'ec2' in services_to_scan:
            try:
                ec2_agent = EC2Agent(creds=self.creds)
                
                # Prepare scope for EC2 (instance IDs or tags filter)
                scope = "all"
                if ec2_filters:
                    if ec2_filters.get('instance_ids'):
                        scope = ec2_filters['instance_ids']
                    elif ec2_filters.get('tags'):
                        # For tag-based filtering, we'll use "all" and filter in EC2Agent later
                        scope = "all"
                
                results["ec2"] = ec2_agent.scan(
                    user_intent_input=user_intent_input,
                    scope=scope
                )
                logger.info("EC2 scan completed successfully")
            except Exception as e:
                logger.error(f"EC2 scan failed: {e}")
                results["ec2"] = []
        
        # IAM Agent
        if 'iam' in services_to_scan:
            try:
                iam_agent = IAMAgent(creds=self.creds)
                
                # Prepare scope for IAM
                scope = iam_scope or "account"
                
                results["iam"] = iam_agent.scan(
                    user_intent_input=user_intent_input,
                    scope=scope
                )
                logger.info("IAM scan completed successfully")
            except Exception as e:
                logger.error(f"IAM scan failed: {e}")
                results["iam"] = []
        
        # Lambda Agent
        if 'lambda' in services_to_scan:
            try:
                lambda_agent = LambdaAgent(creds=self.creds)
                
                # Prepare scope for Lambda (specific function or all)
                scope = lambda_function_name if lambda_function_name else "all"
                
                results["lambda"] = lambda_agent.scan(
                    user_intent_input=user_intent_input,
                    scope=scope
                )
                logger.info("Lambda scan completed successfully")
            except Exception as e:
                logger.error(f"Lambda scan failed: {e}")
                results["lambda"] = []
        
        # Route53 Agent
        if 'route53' in services_to_scan:
            try:
                route53_agent = Route53Agent(creds=self.creds)
                
                # Prepare scope for Route53 (all, public, private, or specific zone)
                scope = route53_scope or "all"
                
                results["route53"] = route53_agent.scan(
                    user_intent_input=user_intent_input,
                    scope=scope
                )
                logger.info("Route53 scan completed successfully")
            except Exception as e:
                logger.error(f"Route53 scan failed: {e}")
                results["route53"] = []
        
        # API Gateway Agent
        if 'apigateway' in services_to_scan:
            try:
                apigw_agent = APIGatewayAgent(creds=self.creds)
                scope = apigw_scope or "all"
                results["apigateway"] = apigw_agent.scan(
                    user_intent_input=user_intent_input,
                    scope=scope
                )
                logger.info("API Gateway scan completed successfully")
            except Exception as e:
                logger.error(f"API Gateway scan failed: {e}")
                results["apigateway"] = []

        # CloudFront Agent
        if 'cloudfront' in services_to_scan:
            try:
                cloudfront_agent = CloudFrontAgent(creds=self.creds)
                scope = cloudfront_scope or "all"
                results["cloudfront"] = cloudfront_agent.scan(
                    user_intent_input=user_intent_input,
                    scope=scope
                )
                logger.info("CloudFront scan completed successfully")
            except Exception as e:
                logger.error(f"CloudFront scan failed: {e}")
                results["cloudfront"] = []

        # VPC Agent
        if 'vpc' in services_to_scan:
            try:
                vpc_agent = VPCAgent(creds=self.creds)
                scope = vpc_scope or "all"
                results["vpc"] = vpc_agent.scan(
                    user_intent_input=user_intent_input,
                    scope=scope
                )
                logger.info("VPC scan completed successfully")
            except Exception as e:
                logger.error(f"VPC scan failed: {e}")
                results["vpc"] = []

        return {"findings": results}
