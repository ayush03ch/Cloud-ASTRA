"""
LLM-based solution generator that creates step-by-step remediation guidance
Uses findings and RAG documents to generate comprehensive solutions with LLM
"""

import os
import json
import logging
import google.generativeai as genai
from typing import List, Dict, Optional

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class SolutionGenerator:
    """Generate step-by-step solutions for security findings using LLM"""
    
    def __init__(self):
        """Initialize the solution generator with Gemini API"""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error("[SolutionGen] GEMINI_API_KEY environment variable not set")
            raise ValueError("GEMINI_API_KEY environment variable not set")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        logger.info("[SolutionGen] ✅ Initialized solution generator with gemini-2.5-flash")
    
    def generate_solutions(
        self,
        findings: List[Dict],
        rag_documents: Optional[List[Dict]] = None,
        service: str = "aws",
        context: Optional[str] = None
    ) -> List[Dict]:
        """
        Generate step-by-step solutions for findings using LLM and RAG context.
        
        Args:
            findings: List of security findings with issue descriptions
            rag_documents: Optional list of relevant RAG documents for context
            service: AWS service (s3, ec2, iam, lambda)
            context: Optional additional context
            
        Returns:
            List of findings enriched with solutions and implementation steps
        """
        if not findings:
            logger.debug("[SolutionGen] No findings to generate solutions for")
            return []
        
        logger.info(f"[SolutionGen] Starting solution generation for {len(findings)} findings (service: {service})")
        enriched_findings = []
        
        for idx, finding in enumerate(findings, 1):
            try:
                logger.debug(f"[SolutionGen] [{idx}/{len(findings)}] Processing finding: {finding.get('issue', 'unknown')}")
                
                solution = self._generate_solution_for_finding(
                    finding=finding,
                    rag_documents=rag_documents,
                    service=service,
                    context=context
                )
                
                # Merge solution into finding
                enriched_finding = {
                    **finding,
                    'solution': solution.get('solution_steps', []),
                    'implementation_guide': solution.get('implementation_guide', ''),
                    'time_estimate': solution.get('time_estimate', 'Unknown'),
                    'difficulty_level': solution.get('difficulty_level', 'medium'),
                    'automation_possible': solution.get('automation_possible', False),
                    'prerequisites': solution.get('prerequisites', []),
                    'verification_steps': solution.get('verification_steps', [])
                }
                
                logger.debug(f"[SolutionGen] [{idx}/{len(findings)}] ✅ Generated solution with {len(solution.get('solution_steps', []))} steps")
                enriched_findings.append(enriched_finding)
                
            except Exception as e:
                logger.error(f"[SolutionGen] [{idx}/{len(findings)}] ❌ Failed to generate solution for {finding.get('issue', 'unknown')}: {e}")
                # Add empty solution structure if generation fails
                enriched_findings.append({
                    **finding,
                    'solution': [],
                    'implementation_guide': 'Manual review required',
                    'time_estimate': 'Unknown',
                    'difficulty_level': 'unknown',
                    'automation_possible': False,
                    'prerequisites': [],
                    'verification_steps': []
                })
        
        logger.info(f"[SolutionGen] ✅ Completed solution generation - enriched {len(enriched_findings)}/{len(findings)} findings")
        return enriched_findings
    
    def _generate_solution_for_finding(
        self,
        finding: Dict,
        rag_documents: Optional[List[Dict]],
        service: str,
        context: Optional[str]
    ) -> Dict:
        """Generate a solution for a single finding"""
        
        logger.debug(f"[SolutionGen] Building prompt for: {finding.get('issue', 'unknown')}")
        
        # Build prompt with RAG context
        prompt = self._build_solution_prompt(
            finding=finding,
            rag_documents=rag_documents,
            service=service,
            context=context
        )
        
        try:
            logger.debug(f"[SolutionGen] 📞 Calling Gemini API for: {finding.get('issue', 'unknown')}")
            
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.2,
                    response_mime_type="application/json"
                )
            )
            
            response_text = response.text.strip()
            logger.debug(f"[SolutionGen] ✅ Received Gemini response ({len(response_text)} chars)")
            
            result = json.loads(response_text)
            logger.debug(f"[SolutionGen] ✅ Parsed JSON with {len(result.get('solution_steps', []))} steps")
            
            return {
                'solution_steps': result.get('solution_steps', []),
                'implementation_guide': result.get('implementation_guide', ''),
                'time_estimate': result.get('time_estimate', 'Unknown'),
                'difficulty_level': result.get('difficulty_level', 'medium'),
                'automation_possible': result.get('automation_possible', False),
                'prerequisites': result.get('prerequisites', []),
                'verification_steps': result.get('verification_steps', []),
                'warnings': result.get('warnings', [])
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"[SolutionGen] ❌ Failed to parse LLM response as JSON: {e}")
            return self._get_default_solution()
        except Exception as e:
            logger.error(f"[SolutionGen] ❌ Error generating solution: {e}")
            return self._get_default_solution()
    
    def _build_solution_prompt(
        self,
        finding: Dict,
        rag_documents: Optional[List[Dict]],
        service: str,
        context: Optional[str]
    ) -> str:
        """Build the prompt for solution generation"""
        
        logger.debug(f"[SolutionGen] Building solution prompt for {service}://{finding.get('resource', 'unknown')}")
        
        # Format finding information
        issue = finding.get('issue', 'Security issue detected')
        resource = finding.get('resource', 'Resource')
        description = finding.get('description', finding.get('details', ''))
        severity = finding.get('severity', 'medium')
        
        # Format RAG document references
        rag_context = ""
        if rag_documents and len(rag_documents) > 0:
            logger.debug(f"[SolutionGen] Including {len(rag_documents[:3])} RAG documents in prompt")
            rag_context = "\n**Relevant Security Best Practices Documentation:**\n"
            for i, doc in enumerate(rag_documents[:3], 1):  # Use top 3 documents
                rag_context += f"\n{i}. {doc.get('title', 'Document')}\n"
                if doc.get('sections'):
                    for section_name, section_content in list(doc.get('sections', {}).items())[:2]:
                        rag_context += f"   - {section_name}: {section_content[:200]}...\n"
        
        prompt = f"""You are an AWS security expert and cloud architect. 
Generate a comprehensive, step-by-step solution guide for the following security issue.

**Issue Details:**
- Service: {service.upper()}
- Resource: {resource}
- Issue: {issue}
- Severity: {severity}
- Description: {description}

{rag_context}

**Additional Context:**
{context if context else "None"}

**Task:**
Create a detailed remediation plan that includes:
1. Clear understanding of the issue and why it matters
2. Numbered step-by-step solution steps (be specific with AWS console clicks, CLI commands, or code changes)
3. Time estimate for implementation
4. Difficulty level (easy/medium/hard)
5. Whether automation is possible
6. Prerequisites before implementing
7. Verification steps to confirm the fix worked
8. Any warnings or side effects to consider

**Output Format (JSON only):**
{{
  "solution_steps": [
    {{
      "step_number": 1,
      "title": "Step title",
      "description": "Detailed description of what to do",
      "action": "Console|CLI|Code|Configuration",
      "details": "Specific instructions or commands",
      "screenshot_hint": "Where to find this in AWS console (optional)"
    }}
  ],
  "implementation_guide": "Paragraph explaining the overall approach",
  "time_estimate": "5-10 minutes",
  "difficulty_level": "easy|medium|hard",
  "automation_possible": true/false,
  "prerequisites": [
    "IAM permissions needed",
    "AWS CLI installed (if applicable)"
  ],
  "verification_steps": [
    "How to verify the fix is working"
  ],
  "warnings": [
    "Any potential side effects or things to be careful about"
  ]
}}

**Important:** 
- Return ONLY valid JSON, no markdown code blocks
- Make steps actionable and specific
- Include AWS console paths or CLI commands where applicable
- Consider both manual and automated approaches
- Be practical and realistic about effort required"""
        
        return prompt
    
    def _get_default_solution(self) -> Dict:
        """Return a default solution structure when generation fails"""
        return {
            'solution_steps': [
                {
                    'step_number': 1,
                    'title': 'Manual Review Required',
                    'description': 'This issue requires manual review by an AWS security expert',
                    'action': 'Manual',
                    'details': 'Please contact your security team for assistance'
                }
            ],
            'implementation_guide': 'Please consult with your AWS security team',
            'time_estimate': 'Unknown',
            'difficulty_level': 'unknown',
            'automation_possible': False,
            'prerequisites': ['AWS security team consultation'],
            'verification_steps': ['Manual verification required'],
            'warnings': ['This issue may require specialized expertise']
        }
