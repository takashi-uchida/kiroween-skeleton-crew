"""Automate documentation-organization spec via DocumentationSpirit."""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Dict, List

import sys


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from framework.agents.documentation_agent import DocumentationSpirit


STEERING_DIR = ROOT / ".kiro" / "steering"

SOURCE_FILES = {
    "product": "product.md",
    "tech": "tech.md",
    "structure": "structure.md",
    "workflow": "agent-workflow.md",
}


def normalize_text(text: str) -> str:
    replacements = [
        ("Agent", "Spirit"),
        ("agent", "spirit"),
        ("Orchestrator", "Necromancer"),
        ("orchestrator", "necromancer"),
        ("Repository", "Workspace"),
        ("repository", "workspace"),
    ]
    normalized = text
    for old, new in replacements:
        normalized = normalized.replace(old, new)
    return normalized


def parse_markdown_sections(path: Path) -> List[Dict[str, str]]:
    sections: List[Dict[str, str]] = []
    if not path.exists():
        return sections

    current: Dict[str, str] | None = None
    buffer: List[str] = []

    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("#"):
                level = len(line) - len(line.lstrip("#"))
                if level <= 2:
                    if current is not None:
                        current["content"] = "".join(buffer).strip()
                        sections.append(current)
                    title = line.lstrip("#").strip()
                    current = {"level": level, "title": title, "content": ""}
                    buffer = []
                    continue
            buffer.append(line)

    if current is not None:
        current["content"] = "".join(buffer).strip()
        sections.append(current)

    return sections


def section_lookup(sections: List[Dict[str, str]], title: str) -> str:
    for section in sections:
        if section["title"].lower() == title.lower():
            return section["content"].strip()
    return ""


def ensure_backups() -> Dict[str, Path]:
    resolved: Dict[str, Path] = {}
    for key, filename in SOURCE_FILES.items():
        src = STEERING_DIR / filename
        backup = src.with_suffix(src.suffix + ".bak")
        if backup.exists():
            resolved[key] = backup
        elif src.exists():
            backup.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            resolved[key] = backup
        else:
            raise FileNotFoundError(f"Missing source file for {key}: {src}")
    return resolved


def build_overview(product_sections: List[Dict[str, str]]) -> str:
    def grab(title: str) -> str:
        return section_lookup(product_sections, title)

    quick_reference = textwrap.dedent(
        """
        - **Purpose**: Explain NecroCode's value, concepts, and who benefits.
        - **Audience**: Stakeholders, onboarding developers, and spirits needing context.
        - **Read Next**: Technical design → architecture.md, implementation guide → development.md.
        """
    ).strip()

    sections = [
        "# NecroCode Overview",
        "",
        "## Quick Reference",
        quick_reference,
        "",
        "## Product Vision",
        grab("What is NecroCode?"),
        "",
        "## Core Concept",
        grab("Core Concept"),
        "",
        "## Key Features",
        grab("Key Features"),
        "",
        "## How It Works",
        grab("How It Works"),
        "",
        "## Target Users",
        grab("Target Users"),
        "",
        "## Differentiation",
        grab("Differentiation"),
        "",
        "## See Also",
        "- [architecture.md](architecture.md) — Spirit Protocol, components, data models",
        "- [development.md](development.md) — Directory structure, workflows, best practices",
    ]
    return "\n".join(filter(None, sections)).strip() + "\n"


def build_architecture(tech_sections: List[Dict[str, str]]) -> str:
    def grab(title: str) -> str:
        return section_lookup(tech_sections, title)

    quick_reference = textwrap.dedent(
        """
        - **Purpose**: Document how NecroCode works internally.
        - **Audience**: Architects, senior devs, spirits extending the platform.
        - **Cross-Links**: Product framing in overview.md, implementation guide in development.md.
        """
    ).strip()

    sections = [
        "# NecroCode Architecture",
        "",
        "## Quick Reference",
        quick_reference,
        "",
        "## Core Technologies",
        grab("Core Technologies"),
        "",
        "## Architecture Patterns",
        grab("Architecture Patterns"),
        "",
        "## Workspace Isolation",
        grab("Workspace Isolation"),
        "",
        "## Spirit Protocol",
        grab("Communication Protocol"),
        "",
        "## Key Components",
        grab("Key Components"),
        "",
        "## Data Models",
        grab("Data Models"),
        "",
        "## Dependencies",
        grab("Dependencies"),
        "",
        "## Quality Attributes",
        "### Performance",
        grab("Performance Characteristics"),
        "",
        "### Security",
        grab("Security Considerations"),
        "",
        "### Scalability",
        grab("Scalability"),
        "",
        "## See Also",
        "- [overview.md](overview.md) — Product context and use cases",
        "- [development.md](development.md) — Module layout and workflows",
    ]
    return "\n".join(filter(None, sections)).strip() + "\n"


def build_development(structure_sections: List[Dict[str, str]], workflow_sections: List[Dict[str, str]]) -> str:
    def grab_structure(title: str) -> str:
        return section_lookup(structure_sections, title)

    def grab_workflow(title: str) -> str:
        return section_lookup(workflow_sections, title)

    quick_reference = textwrap.dedent(
        """
        - **Purpose**: Guide spirits through implementation details.
        - **Audience**: Contributors executing tasks, DocumentationSpirit, Dev/QA spirits.
        - **Cross-Links**: Product overview → overview.md, system design → architecture.md.
        """
    ).strip()

    directory_block = "\n\n".join(
        filter(
            None,
            [
                grab_structure("Directory Layout"),
                grab_structure("Key Directories Explained"),
                grab_structure("Module Organization"),
                grab_structure("Import Paths"),
                grab_structure("Configuration Files"),
                grab_structure("Naming Conventions"),
            ],
        )
    )

    workflow_block = "\n\n".join(
        filter(
            None,
            [
                grab_workflow("Overview"),
                grab_workflow("Complete Workflow"),
                grab_workflow("Agent Roles & Responsibilities"),
                grab_workflow("Communication Protocol"),
                grab_workflow("Parallel Execution"),
                grab_workflow("Workspace Isolation"),
                grab_workflow("Error Handling"),
                grab_workflow("Monitoring & Observability"),
                grab_workflow("Best Practices"),
                grab_workflow("Example: Complete Flow"),
            ],
        )
    )

    extension_section = "\n\n".join(
        filter(None, [grab_structure("Extension Points"), grab_structure("Best Practices")])
    )

    sections = [
        "# NecroCode Development Guide",
        "",
        "## Quick Reference",
        quick_reference,
        "",
        "## Directory Structure & Conventions",
        directory_block,
        "",
        "## Extension Points & Best Practices",
        extension_section,
        "",
        "## Agent Collaboration Workflow",
        workflow_block,
        "",
        "## See Also",
        "- [overview.md](overview.md) — Vision and target users",
        "- [architecture.md](architecture.md) — Protocols, components, data models",
    ]
    return "\n".join(filter(None, sections)).strip() + "\n"


def main() -> None:
    resolved_sources = ensure_backups()
    doc_spirit = DocumentationSpirit(
        role="documentation",
        skills=["technical_writing", "content_organization"],
        workspace=str(ROOT),
        instance_number=1,
    )

    requirements = {
        "eliminate_redundancy": True,
        "create_hierarchy": True,
        "consolidate_specs": True,
        "improve_navigation": True,
    }

    doc_spirit.assign_task("DOC-PLAN")
    plan = doc_spirit.create_documentation_plan(requirements)
    doc_spirit.complete_task("DOC-PLAN")

    sections_by_source = {}
    for key, path in resolved_sources.items():
        doc_spirit.assign_task(f"DOC-EXTRACT-{key.upper()}")
        sections = doc_spirit.extract_sections(str(path), [])
        sections_by_source[key] = sections
        doc_spirit.complete_task(f"DOC-EXTRACT-{key.upper()}")

    all_sections = [section for sections in sections_by_source.values() for section in sections]
    consolidation = doc_spirit.consolidate_content(all_sections)

    product_sections = parse_markdown_sections(resolved_sources["product"])
    tech_sections = parse_markdown_sections(resolved_sources["tech"])
    structure_sections = parse_markdown_sections(resolved_sources["structure"])
    workflow_sections = parse_markdown_sections(resolved_sources["workflow"])

    overview_content = build_overview(product_sections)
    architecture_content = build_architecture(tech_sections)
    development_content = build_development(structure_sections, workflow_sections)

    outputs = {
        STEERING_DIR / "overview.md": overview_content,
        STEERING_DIR / "architecture.md": architecture_content,
        STEERING_DIR / "development.md": development_content,
    }


    for path, content in outputs.items():
        doc_spirit.assign_task(f"DOC-WRITE-{path.stem.upper()}")
        path.write_text(normalize_text(content), encoding="utf-8")
        doc_spirit.complete_task(f"DOC-WRITE-{path.stem.upper()}")

    docs_for_validation = {
        str(path): path.read_text(encoding="utf-8") for path in outputs.keys()
    }
    validation = doc_spirit.validate_documentation(docs_for_validation)
    if not validation["valid"]:
        raise SystemExit(f"Validation issues found: {validation['issues']}")

    print(plan["chant"])
    print(consolidation["chant"])
    print(validation["chant"])


if __name__ == "__main__":
    main()
