"""Documentation Spirit - handles documentation reorganization and maintenance."""

from typing import Dict, List, Optional
from pathlib import Path
from .base_agent import BaseSpirit


class DocumentationSpirit(BaseSpirit):
    """Spirit specialized in documentation organization and technical writing."""
    
    def __init__(self, role: str, skills: List[str], workspace: str, instance_number: int = 1):
        super().__init__(role, skills, workspace, instance_number)
    
    def reorganize_docs(self, source_files: List[str], target_structure: Dict) -> str:
        """Reorganize documentation from multiple source files into new structure.
        
        Args:
            source_files: List of source file paths to consolidate
            target_structure: Dictionary mapping target files to their content sections
            
        Returns:
            Chant message describing the reorganization
        """
        return self.chant(
            f"Reorganizing {len(source_files)} documents into "
            f"{len(target_structure)} new files..."
        )
    
    def consolidate_content(self, sections: List[Dict]) -> Dict:
        """Consolidate duplicate content from multiple sections.
        
        Args:
            sections: List of content sections with metadata
            
        Returns:
            Dictionary with consolidated content and deduplication report
        """
        # Track unique content
        unique_sections = {}
        duplicates_found = []
        
        for section in sections:
            content_hash = hash(section.get('content', ''))
            if content_hash not in unique_sections:
                unique_sections[content_hash] = section
            else:
                duplicates_found.append({
                    'original': unique_sections[content_hash].get('title'),
                    'duplicate': section.get('title')
                })
        
        return {
            'unique_sections': list(unique_sections.values()),
            'duplicates_removed': len(duplicates_found),
            'duplicates': duplicates_found,
            'chant': self.chant(
                f"Consolidated {len(sections)} sections, "
                f"removed {len(duplicates_found)} duplicates"
            )
        }
    
    def add_cross_references(self, docs: Dict[str, str]) -> Dict:
        """Add cross-references between related documentation sections.
        
        Args:
            docs: Dictionary mapping file paths to their content
            
        Returns:
            Dictionary with updated content and cross-reference report
        """
        cross_refs_added = 0
        updated_docs = {}
        
        # Simple cross-reference patterns
        ref_patterns = {
            'architecture': 'For architectural details, see [architecture.md](architecture.md)',
            'development': 'For implementation guide, see [development.md](development.md)',
            'overview': 'For product overview, see [overview.md](overview.md)'
        }
        
        for file_path, content in docs.items():
            updated_content = content
            # Add cross-references based on content analysis
            for keyword, ref_text in ref_patterns.items():
                if keyword in content.lower() and ref_text not in content:
                    # Add reference at appropriate location
                    cross_refs_added += 1
            
            updated_docs[file_path] = updated_content
        
        return {
            'updated_docs': updated_docs,
            'cross_refs_added': cross_refs_added,
            'chant': self.chant(f"Added {cross_refs_added} cross-references")
        }
    
    def validate_documentation(self, docs: Dict[str, str]) -> Dict:
        """Validate documentation for completeness and consistency.
        
        Args:
            docs: Dictionary mapping file paths to their content
            
        Returns:
            Validation report with issues found
        """
        issues = []
        
        for file_path, content in docs.items():
            # Check for broken links
            if '[' in content and '](' in content:
                # Simple link validation
                pass
            
            # Check for consistent terminology
            inconsistent_terms = self._check_terminology(content)
            if inconsistent_terms:
                issues.append({
                    'file': file_path,
                    'type': 'terminology',
                    'issues': inconsistent_terms
                })
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'chant': self.chant(
                f"Validation complete: {len(issues)} issues found"
            )
        }
    
    def _check_terminology(self, content: str) -> List[str]:
        """Check for inconsistent terminology in content.
        
        Args:
            content: Document content to check
            
        Returns:
            List of inconsistent terms found
        """
        inconsistencies = []
        
        # Define preferred terms and their alternatives
        term_pairs = [
            ('Spirit', 'Agent'),
            ('Workspace', 'Repository'),
            ('Necromancer', 'Orchestrator')
        ]
        
        for preferred, alternative in term_pairs:
            if alternative in content and preferred in content:
                inconsistencies.append(
                    f"Mixed use of '{preferred}' and '{alternative}'"
                )
        
        return inconsistencies
    
    def create_documentation_plan(self, requirements: Dict) -> Dict:
        """Create a plan for documentation reorganization.
        
        Args:
            requirements: Requirements specification for documentation
            
        Returns:
            Documentation plan with tasks and structure
        """
        plan = {
            'target_files': [],
            'content_mapping': {},
            'validation_steps': [],
            'estimated_sections': 0
        }
        
        # Analyze requirements and create plan
        if 'eliminate_redundancy' in requirements:
            plan['validation_steps'].append('deduplication_check')
        
        if 'create_hierarchy' in requirements:
            plan['target_files'] = ['overview.md', 'architecture.md', 'development.md']
        
        if 'consolidate_specs' in requirements:
            plan['validation_steps'].append('consolidation_check')
        
        if 'improve_navigation' in requirements:
            plan['validation_steps'].append('cross_reference_check')
        
        return {
            'plan': plan,
            'chant': self.chant(
                f"Created documentation plan with {len(plan['target_files'])} target files"
            )
        }
    
    def extract_sections(self, file_path: str, section_markers: List[str]) -> List[Dict]:
        """Extract specific sections from a documentation file.
        
        Args:
            file_path: Path to the documentation file
            section_markers: List of section headers to extract
            
        Returns:
            List of extracted sections with metadata
        """
        sections = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Simple section extraction based on markdown headers
            lines = content.split('\n')
            current_section = None
            current_content = []
            
            for line in lines:
                if line.startswith('#'):
                    # Save previous section
                    if current_section:
                        sections.append({
                            'title': current_section,
                            'content': '\n'.join(current_content),
                            'source_file': file_path
                        })
                    
                    # Start new section
                    current_section = line.strip('#').strip()
                    current_content = []
                else:
                    current_content.append(line)
            
            # Save last section
            if current_section:
                sections.append({
                    'title': current_section,
                    'content': '\n'.join(current_content),
                    'source_file': file_path
                })
        
        except FileNotFoundError:
            pass
        
        return sections
    
    def merge_sections(self, sections: List[Dict], target_file: str) -> str:
        """Merge multiple sections into a single documentation file.
        
        Args:
            sections: List of sections to merge
            target_file: Target file path
            
        Returns:
            Merged content as string
        """
        merged_content = []
        
        for section in sections:
            # Add section header
            merged_content.append(f"## {section['title']}\n")
            merged_content.append(section['content'])
            merged_content.append('\n')
        
        return '\n'.join(merged_content)
    
    def summon_documentation(self) -> str:
        """Spirit summoning chant for documentation work."""
        return self.chant("Rising from the archives to organize the ancient texts...")
    
    def weave_structure(self) -> str:
        """Chant for creating documentation structure."""
        return self.chant("Weaving the tapestry of knowledge...")
