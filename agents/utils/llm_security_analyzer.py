"""
LLM-based security analysis using Google Gemini API
This is Tier 3 of the detection pipeline (fallback when rules and RAG don't find issues)
"""

import os
import json
import google.generativeai as genai
from typing import List, Dict, Optional


class LLMSecurityAnalyzer:
    """LLM-based security analysis using Google Gemini API"""
    
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        
        genai.configure(api_key=api_key)
        # Use stable model with free tier: 15 RPM, 1M requests/day, 1.5M tokens/day
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        print(f"[LLM] Gemini API initialized successfully with gemini-1.5-flash")
    
    def analyze_security_issues(
        self,
        service: str,
        resource_name: str,
        configuration: Dict,
        intent: str,
        user_context: str = ""
    ) -> List[Dict]:
        """
        Use Gemini to detect security issues
        
        Args:
            service: AWS service (s3, lambda, ec2, iam)
            resource_name: Name of the resource
            configuration: Full resource configuration dict
            intent: Detected intent (website, data-storage, etc)
            user_context: Optional user query for context
            
        Returns:
            List of finding dicts with issue, severity, fix_instructions
        """
        prompt = self._build_security_prompt(
            service, resource_name, configuration, intent, user_context
        )
        
        try:
            print(f"[LLM] Analyzing {service}://{resource_name} with Gemini...")
            
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.3,
                    response_mime_type="application/json"
                )
            )
            
            # Extract JSON from response
            response_text = response.text.strip()
            
            # Parse JSON response
            result = json.loads(response_text)
            
            # Convert to standard finding format
            findings = []
            for issue in result.get('findings', []):
                # Only include if relevant to detected intent
                if issue.get('applies_to_intent', True):
                    findings.append({
                        'resource': f"{service}://{resource_name}",
                        'issue': issue['issue'],
                        'severity': issue.get('severity', 'medium'),
                        'description': issue.get('description', ''),
                        'fix_instructions': [issue.get('recommended_fix', 'Manual review required')],
                        'can_auto_fix': False,
                        'auto_safe': False,
                        'detection_method': 'llm',
                        'confidence': issue.get('confidence', 'medium')
                    })
            
            print(f"[LLM] Found {len(findings)} issues for {resource_name}")
            return findings
            
        except json.JSONDecodeError as e:
            print(f"[LLM] Failed to parse LLM response as JSON: {e}")
            print(f"[LLM] Raw response: {response_text[:200]}...")
            return []
        except Exception as e:
            print(f"[LLM] Security analysis failed: {e}")
            return []
    
    def _build_security_prompt(
        self,
        service: str,
        resource_name: str,
        configuration: Dict,
        intent: str,
        user_context: str
    ) -> str:
        """Build the prompt for Gemini API"""
        
        # Sanitize configuration for JSON serialization
        config_str = json.dumps(configuration, indent=2, default=str)
        
        prompt = f"""You are an AWS security expert analyzing cloud resources for vulnerabilities.

**Task:** Analyze this {service.upper()} resource for security issues.

**Resource Details:**
- Service: {service}
- Resource Name: {resource_name}
- Detected Intent/Purpose: {intent}
- User Context: {user_context if user_context else "None"}

**Configuration:**
```json
{config_str}
```

**Instructions:**
1. Identify security issues considering the resource's intended purpose ({intent})
2. Skip issues that are acceptable for this intent (e.g., public access is OK for websites)
3. Focus on: encryption, access controls, logging, compliance, misconfigurations
4. For each issue provide: name, severity, description, fix, confidence level
5. If the configuration looks secure for the given intent, return an empty findings array

**Output Format (JSON only, no markdown):**
{{
  "findings": [
    {{
      "issue": "Brief issue name",
      "severity": "critical|high|medium|low",
      "description": "Detailed explanation",
      "recommended_fix": "Step-by-step fix instructions",
      "applies_to_intent": true,
      "confidence": "high|medium|low"
    }}
  ]
}}

**Important:** Return ONLY valid JSON. No markdown code blocks, no explanations outside JSON.
"""
        return prompt
