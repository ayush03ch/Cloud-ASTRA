"""
RAG-based security issue detection using text embeddings
Searches a knowledge base of AWS security documentation for relevant issues
"""

import os
import json
import re
from typing import List, Dict, Tuple
from pathlib import Path
import numpy as np


class RAGSecuritySearch:
    """RAG-based security documentation search using simple TF-IDF similarity"""
    
    def __init__(self, knowledge_base_path: str = None):
        """
        Initialize RAG search with knowledge base
        
        Args:
            knowledge_base_path: Path to knowledge base directory (default: knowledge_base/)
        """
        if knowledge_base_path is None:
            # Default to knowledge_base directory in project root
            project_root = Path(__file__).parent.parent.parent
            knowledge_base_path = project_root / "knowledge_base"
        
        self.knowledge_base_path = Path(knowledge_base_path)
        self.enabled = True
        self.documents = {}
        self.vocabulary = set()
        self.idf = {}
        
        # Load knowledge base
        self._load_knowledge_base()
        print(f"[RAG] Initialized with {len(self.documents)} documents")
    
    def _load_knowledge_base(self):
        """Load all text documents from knowledge base directory"""
        if not self.knowledge_base_path.exists():
            print(f"[RAG] Knowledge base not found at {self.knowledge_base_path}, creating placeholder")
            self.enabled = False
            return
        
        # Load documents by service
        for service_dir in ['s3', 'ec2', 'iam', 'lambda']:
            service_path = self.knowledge_base_path / service_dir
            if service_path.exists():
                self._load_service_documents(service_dir, service_path)
        
        # Build vocabulary and IDF scores
        self._build_vocabulary()
        
        if not self.documents:
            print("[RAG] No documents loaded, RAG disabled")
            self.enabled = False
    
    def _load_service_documents(self, service: str, service_path: Path):
        """Load all .txt files from a service directory"""
        for doc_file in service_path.glob("*.txt"):
            try:
                with open(doc_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Parse document structure
                doc_data = self._parse_document(content)
                doc_id = f"{service}_{doc_file.stem}"
                
                self.documents[doc_id] = {
                    'service': service,
                    'filename': doc_file.name,
                    'content': content,
                    'title': doc_data.get('title', doc_file.stem),
                    'sections': doc_data.get('sections', {}),
                    'keywords': doc_data.get('keywords', [])
                }
                
            except Exception as e:
                print(f"[RAG] Error loading {doc_file}: {e}")
    
    def _parse_document(self, content: str) -> Dict:
        """Parse document into structured sections"""
        result = {
            'sections': {},
            'keywords': []
        }
        
        # Extract title (first line starting with #)
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            result['title'] = title_match.group(1).strip()
        
        # Extract sections
        sections = re.split(r'\n##\s+', content)
        for section in sections[1:]:  # Skip first (before any ##)
            lines = section.split('\n', 1)
            if len(lines) == 2:
                section_title = lines[0].strip()
                section_content = lines[1].strip()
                result['sections'][section_title] = section_content
        
        # Extract keywords (lines starting with Keywords:)
        keywords_match = re.search(r'Keywords:\s*(.+)$', content, re.MULTILINE)
        if keywords_match:
            result['keywords'] = [k.strip() for k in keywords_match.group(1).split(',')]
        
        return result
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization"""
        # Convert to lowercase and extract words
        words = re.findall(r'\b\w+\b', text.lower())
        return words
    
    def _build_vocabulary(self):
        """Build vocabulary and compute IDF scores"""
        # Collect all words
        doc_count = len(self.documents)
        word_doc_count = {}
        
        for doc_id, doc in self.documents.items():
            words = set(self._tokenize(doc['content']))
            self.vocabulary.update(words)
            
            for word in words:
                word_doc_count[word] = word_doc_count.get(word, 0) + 1
        
        # Compute IDF scores
        for word in self.vocabulary:
            df = word_doc_count.get(word, 0)
            self.idf[word] = np.log((doc_count + 1) / (df + 1)) + 1
    
    def _compute_tf_idf(self, text: str) -> Dict[str, float]:
        """Compute TF-IDF vector for text"""
        words = self._tokenize(text)
        tf = {}
        
        # Compute term frequency
        for word in words:
            tf[word] = tf.get(word, 0) + 1
        
        # Normalize by document length
        total_words = len(words)
        if total_words > 0:
            for word in tf:
                tf[word] = tf[word] / total_words
        
        # Compute TF-IDF
        tf_idf = {}
        for word, tf_score in tf.items():
            if word in self.idf:
                tf_idf[word] = tf_score * self.idf[word]
        
        return tf_idf
    
    def _cosine_similarity(self, vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
        """Compute cosine similarity between two TF-IDF vectors"""
        # Get common words
        common_words = set(vec1.keys()) & set(vec2.keys())
        
        if not common_words:
            return 0.0
        
        # Compute dot product
        dot_product = sum(vec1[word] * vec2[word] for word in common_words)
        
        # Compute magnitudes
        mag1 = np.sqrt(sum(v ** 2 for v in vec1.values()))
        mag2 = np.sqrt(sum(v ** 2 for v in vec2.values()))
        
        if mag1 == 0 or mag2 == 0:
            return 0.0
        
        return dot_product / (mag1 * mag2)
    
    def search_security_issues(
        self,
        service: str,
        configuration: Dict,
        intent: str,
        top_k: int = 5
    ) -> List[Dict]:
        """
        Search security knowledge base for potential issues
        
        Args:
            service: AWS service (s3, lambda, ec2, iam)
            configuration: Resource configuration dict
            intent: Detected intent
            top_k: Number of similar documents to return
            
        Returns:
            List of finding dicts with relevant documentation
        """
        if not self.enabled:
            print(f"[RAG] Search skipped - RAG not enabled")
            return []
        
        # Build search query from configuration and intent
        query_parts = [
            f"service: {service}",
            f"intent: {intent}",
            f"configuration: {json.dumps(configuration)}"
        ]
        query = " ".join(query_parts)
        
        # Compute query TF-IDF
        query_vec = self._compute_tf_idf(query)
        
        # Find similar documents
        similarities = []
        for doc_id, doc in self.documents.items():
            # Only search documents for this service
            if doc['service'] != service:
                continue
            
            # Compute document TF-IDF
            doc_vec = self._compute_tf_idf(doc['content'])
            
            # Compute similarity
            similarity = self._cosine_similarity(query_vec, doc_vec)
            
            # Boost if intent matches keywords
            if intent in doc.get('keywords', []):
                similarity *= 1.5
            
            similarities.append((doc_id, similarity, doc))
        
        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Return top-k results
        findings = []
        for doc_id, score, doc in similarities[:top_k]:
            if score > 0.1:  # Minimum relevance threshold
                finding = {
                    'source': 'rag_knowledge_base',
                    'doc_id': doc_id,
                    'title': doc['title'],
                    'relevance_score': float(score),
                    'sections': doc['sections'],
                    'keywords': doc['keywords'],
                    'filename': doc['filename']
                }
                findings.append(finding)
                print(f"[RAG] Found relevant doc: {doc['title']} (score: {score:.3f})")
        
        return findings
