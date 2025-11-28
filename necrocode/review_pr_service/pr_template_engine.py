"""
PR Template Engine for Review & PR Service.

Generates PR descriptions using Jinja2 templates with task and artifact data.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
from jinja2 import Environment, FileSystemLoader, Template, TemplateNotFound
import logging

from necrocode.review_pr_service.config import PRServiceConfig, TemplateConfig
from necrocode.review_pr_service.exceptions import PRServiceError
from necrocode.task_registry.models import Task, Artifact, ArtifactType


logger = logging.getLogger(__name__)


class PRTemplateEngine:
    """
    PR Template Engine for generating PR descriptions.
    
    Uses Jinja2 to render Markdown templates with task and artifact data.
    Supports custom templates and various formatting options.
    """
    
    # Default PR template
    DEFAULT_TEMPLATE = """## Task: {{task_id}} - {{title}}

### Description
{{description}}

{% if acceptance_criteria %}
### Acceptance Criteria
{% for criterion in acceptance_criteria %}
- [ ] {{criterion}}
{% endfor %}
{% endif %}

{% if test_results %}
### Test Results
{{test_results}}
{% endif %}

{% if artifact_links %}
### Artifacts
{{artifact_links}}
{% endif %}

{% if execution_logs %}
### Execution Logs
{{execution_logs}}
{% endif %}

{% if custom_sections %}
{% for section_title, section_content in custom_sections.items() %}
### {{section_title}}
{{section_content}}
{% endfor %}
{% endif %}

---
*This PR was automatically created by NecroCode Review & PR Service*
"""
    
    def __init__(self, config: PRServiceConfig):
        """
        Initialize PR Template Engine.
        
        Args:
            config: PR Service configuration
        """
        self.config = config
        self.template_config = config.template
        self.jinja_env: Optional[Environment] = None
        self._setup_jinja_environment()
    
    def _setup_jinja_environment(self) -> None:
        """Setup Jinja2 environment with template loaders."""
        template_path = self.template_config.template_path
        
        if template_path and Path(template_path).parent.exists():
            # Use file system loader if template directory exists
            template_dir = str(Path(template_path).parent)
            self.jinja_env = Environment(
                loader=FileSystemLoader(template_dir),
                trim_blocks=True,
                lstrip_blocks=True,
                keep_trailing_newline=True
            )
            logger.info(f"Initialized Jinja2 environment with template directory: {template_dir}")
        else:
            # Use default template
            self.jinja_env = None
            logger.info("Using default inline template")
    
    def _load_template(self) -> Template:
        """
        Load PR template from file or use default.
        
        Returns:
            Jinja2 Template object
            
        Raises:
            PRServiceError: If template file cannot be loaded
        """
        template_path = self.template_config.template_path
        
        if self.jinja_env and template_path:
            try:
                template_name = Path(template_path).name
                template = self.jinja_env.get_template(template_name)
                logger.debug(f"Loaded template from file: {template_path}")
                return template
            except TemplateNotFound:
                logger.warning(
                    f"Template file not found: {template_path}, using default template"
                )
        
        # Use default template
        if not self.jinja_env:
            self.jinja_env = Environment(
                trim_blocks=True,
                lstrip_blocks=True,
                keep_trailing_newline=True
            )
        
        template = self.jinja_env.from_string(self.DEFAULT_TEMPLATE)
        logger.debug("Using default inline template")
        return template

    def generate(
        self,
        task: Task,
        artifacts: Optional[List[Artifact]] = None,
        acceptance_criteria: Optional[List[str]] = None,
        custom_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate PR description from task and artifacts.
        
        Args:
            task: Task object containing task information
            artifacts: List of artifacts (optional, uses task.artifacts if not provided)
            acceptance_criteria: List of acceptance criteria (optional)
            custom_data: Additional custom data for template (optional)
            
        Returns:
            Generated PR description as Markdown string
            
        Raises:
            PRServiceError: If template rendering fails
        """
        try:
            template = self._load_template()
            
            # Use task artifacts if not provided
            if artifacts is None:
                artifacts = task.artifacts
            
            # Build template context
            context = {
                "task_id": task.id,
                "title": task.title,
                "description": task.description,
                "acceptance_criteria": acceptance_criteria or [],
                "test_results": None,
                "artifact_links": None,
                "execution_logs": None,
                "custom_sections": self.template_config.custom_sections.copy()
            }
            
            # Add test results if enabled
            if self.template_config.include_test_results:
                context["test_results"] = self._format_test_results(artifacts)
            
            # Add artifact links if enabled
            if self.template_config.include_artifact_links:
                context["artifact_links"] = self._format_artifact_links(artifacts)
            
            # Add execution logs if enabled
            if self.template_config.include_execution_logs:
                context["execution_logs"] = self._format_execution_logs(artifacts)
            
            # Merge custom data
            if custom_data:
                context.update(custom_data)
            
            # Render template
            description = template.render(**context)
            logger.info(f"Generated PR description for task {task.id}")
            return description
            
        except Exception as e:
            logger.error(f"Failed to generate PR description: {e}")
            raise PRServiceError(f"Template rendering failed: {e}") from e

    def _format_test_results(self, artifacts: List[Artifact]) -> Optional[str]:
        """
        Format test results from artifacts into a summary.
        
        Args:
            artifacts: List of artifacts
            
        Returns:
            Formatted test results summary or None if no test artifacts
        """
        if not artifacts:
            return None
        
        # Find test result artifacts
        test_artifacts = [
            artifact for artifact in artifacts
            if artifact.type == ArtifactType.TEST_RESULT
        ]
        
        if not test_artifacts:
            return None
        
        # Build test results summary
        lines = []
        
        for artifact in test_artifacts:
            metadata = artifact.metadata
            
            # Extract test statistics from metadata
            total = metadata.get("total_tests", 0)
            passed = metadata.get("passed", 0)
            failed = metadata.get("failed", 0)
            skipped = metadata.get("skipped", 0)
            duration = metadata.get("duration", 0)
            
            if total > 0:
                pass_rate = (passed / total) * 100 if total > 0 else 0
                
                lines.append(f"**Test Summary:**")
                lines.append(f"- Total: {total}")
                lines.append(f"- Passed: {passed} ✅")
                
                if failed > 0:
                    lines.append(f"- Failed: {failed} ❌")
                
                if skipped > 0:
                    lines.append(f"- Skipped: {skipped} ⏭️")
                
                lines.append(f"- Pass Rate: {pass_rate:.1f}%")
                
                if duration > 0:
                    lines.append(f"- Duration: {duration:.2f}s")
                
                # Add link to full results
                lines.append(f"\n[View Full Test Results]({artifact.uri})")
            else:
                # No test statistics, just link to artifact
                lines.append(f"[Test Results]({artifact.uri})")
        
        return "\n".join(lines) if lines else None

    def _format_artifact_links(self, artifacts: List[Artifact]) -> Optional[str]:
        """
        Format artifact links into a list.
        
        Args:
            artifacts: List of artifacts
            
        Returns:
            Formatted artifact links or None if no artifacts
        """
        if not artifacts:
            return None
        
        lines = []
        
        # Group artifacts by type
        artifacts_by_type: Dict[ArtifactType, List[Artifact]] = {}
        for artifact in artifacts:
            if artifact.type not in artifacts_by_type:
                artifacts_by_type[artifact.type] = []
            artifacts_by_type[artifact.type].append(artifact)
        
        # Format each type
        type_labels = {
            ArtifactType.DIFF: "Code Changes",
            ArtifactType.LOG: "Execution Logs",
            ArtifactType.TEST_RESULT: "Test Results"
        }
        
        for artifact_type, type_artifacts in sorted(
            artifacts_by_type.items(),
            key=lambda x: x[0].value
        ):
            label = type_labels.get(artifact_type, artifact_type.value.title())
            
            if len(type_artifacts) == 1:
                artifact = type_artifacts[0]
                size_info = ""
                if artifact.size_bytes:
                    size_kb = artifact.size_bytes / 1024
                    if size_kb < 1024:
                        size_info = f" ({size_kb:.1f} KB)"
                    else:
                        size_mb = size_kb / 1024
                        size_info = f" ({size_mb:.1f} MB)"
                
                lines.append(f"- [{label}]({artifact.uri}){size_info}")
            else:
                # Multiple artifacts of same type
                lines.append(f"- **{label}:**")
                for i, artifact in enumerate(type_artifacts, 1):
                    size_info = ""
                    if artifact.size_bytes:
                        size_kb = artifact.size_bytes / 1024
                        size_info = f" ({size_kb:.1f} KB)"
                    
                    # Use metadata name if available
                    name = artifact.metadata.get("name", f"{label} {i}")
                    lines.append(f"  - [{name}]({artifact.uri}){size_info}")
        
        return "\n".join(lines) if lines else None
    
    def _format_execution_logs(self, artifacts: List[Artifact]) -> Optional[str]:
        """
        Format execution logs from artifacts.
        
        Args:
            artifacts: List of artifacts
            
        Returns:
            Formatted execution logs or None if no log artifacts
        """
        if not artifacts:
            return None
        
        # Find log artifacts
        log_artifacts = [
            artifact for artifact in artifacts
            if artifact.type == ArtifactType.LOG
        ]
        
        if not log_artifacts:
            return None
        
        lines = []
        
        for artifact in log_artifacts:
            metadata = artifact.metadata
            log_name = metadata.get("name", "Execution Log")
            
            # Add execution time if available
            if "execution_time" in metadata:
                duration = metadata["execution_time"]
                lines.append(f"**{log_name}** (Duration: {duration:.2f}s)")
            else:
                lines.append(f"**{log_name}**")
            
            lines.append(f"[View Log]({artifact.uri})")
            
            # Add error summary if available
            if metadata.get("has_errors"):
                error_count = metadata.get("error_count", 0)
                lines.append(f"⚠️ Contains {error_count} error(s)")
            
            lines.append("")  # Empty line between logs
        
        return "\n".join(lines).strip() if lines else None

    def load_custom_template(self, template_path: str) -> None:
        """
        Load a custom template from the specified path.
        
        Args:
            template_path: Path to custom template file
            
        Raises:
            PRServiceError: If template file cannot be loaded
        """
        template_file = Path(template_path)
        
        if not template_file.exists():
            raise PRServiceError(f"Custom template file not found: {template_path}")
        
        if not template_file.is_file():
            raise PRServiceError(f"Custom template path is not a file: {template_path}")
        
        # Update configuration
        self.template_config.template_path = str(template_file)
        
        # Reinitialize Jinja environment
        self._setup_jinja_environment()
        
        logger.info(f"Loaded custom template: {template_path}")
    
    def set_custom_section(self, title: str, content: str) -> None:
        """
        Add or update a custom section in the template.
        
        Args:
            title: Section title
            content: Section content
        """
        self.template_config.custom_sections[title] = content
        logger.debug(f"Added custom section: {title}")
    
    def remove_custom_section(self, title: str) -> None:
        """
        Remove a custom section from the template.
        
        Args:
            title: Section title to remove
        """
        if title in self.template_config.custom_sections:
            del self.template_config.custom_sections[title]
            logger.debug(f"Removed custom section: {title}")
    
    def clear_custom_sections(self) -> None:
        """Clear all custom sections."""
        self.template_config.custom_sections.clear()
        logger.debug("Cleared all custom sections")
    
    def generate_comment(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        template_path: Optional[str] = None
    ) -> str:
        """
        Generate a PR comment using a template.
        
        Args:
            message: Main comment message
            details: Additional details to include
            template_path: Optional custom comment template path
            
        Returns:
            Generated comment text
        """
        # Default comment template
        default_comment_template = """{{message}}

{% if details %}
{% for key, value in details.items() %}
**{{key}}:** {{value}}
{% endfor %}
{% endif %}

---
*Posted by NecroCode Review & PR Service*
"""
        
        try:
            # Load custom comment template if provided
            if template_path and Path(template_path).exists():
                with open(template_path, "r") as f:
                    template_str = f.read()
                template = self.jinja_env.from_string(template_str)
            elif self.template_config.comment_template_path:
                comment_path = Path(self.template_config.comment_template_path)
                if comment_path.exists():
                    with open(comment_path, "r") as f:
                        template_str = f.read()
                    template = self.jinja_env.from_string(template_str)
                else:
                    template = self.jinja_env.from_string(default_comment_template)
            else:
                template = self.jinja_env.from_string(default_comment_template)
            
            # Render comment
            context = {
                "message": message,
                "details": details or {}
            }
            
            comment = template.render(**context)
            logger.debug("Generated PR comment")
            return comment
            
        except Exception as e:
            logger.error(f"Failed to generate comment: {e}")
            # Fallback to simple message
            return message
    
    def validate_template(self, template_path: Optional[str] = None) -> List[str]:
        """
        Validate a template for syntax errors.
        
        Args:
            template_path: Path to template file (uses configured path if not provided)
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        try:
            if template_path:
                template_file = Path(template_path)
                if not template_file.exists():
                    errors.append(f"Template file not found: {template_path}")
                    return errors
                
                with open(template_file, "r") as f:
                    template_str = f.read()
            else:
                # Validate current template
                template = self._load_template()
                return errors  # If we got here, template is valid
            
            # Try to parse template
            if self.jinja_env:
                self.jinja_env.from_string(template_str)
            else:
                env = Environment()
                env.from_string(template_str)
            
        except Exception as e:
            errors.append(f"Template syntax error: {e}")
        
        return errors
