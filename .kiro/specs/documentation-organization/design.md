# Design Document: Documentation Organization

## Overview

This design reorganizes the NecroCode steering documentation from four overlapping files into a streamlined three-document structure. The new structure eliminates redundancy, improves discoverability, and separates concerns by audience and purpose.

### Current State
- `product.md`: Product overview, features, how it works
- `tech.md`: Technical stack, architecture patterns, data models, file structure
- `structure.md`: Directory layout, module organization, naming conventions
- `agent-workflow.md`: Agent roles, communication protocol, parallel execution

### Target State
- `overview.md`: Product vision, core concepts, key features (for understanding what NecroCode is)
- `architecture.md`: System design, technical stack, components, protocols (for understanding how it works)
- `development.md`: Code structure, conventions, workflows, best practices (for implementing features)

## Architecture

### Documentation Structure

```
.kiro/steering/
├── overview.md          # What is NecroCode? (Product & Concepts)
├── architecture.md      # How does it work? (System Design)
└── development.md       # How to build it? (Implementation Guide)
```

### Content Distribution

#### overview.md (Product & Concepts)
**Purpose**: Help users and stakeholders understand what NecroCode is and why it exists

**Content**:
- Product vision and value proposition
- Core concepts (Necromancer, Spirits, Workspaces)
- Key features and capabilities
- Target users and use cases
- High-level workflow example
- Differentiation from alternatives

**Audience**: Product managers, new developers, stakeholders, AI agents needing context

#### architecture.md (System Design)
**Purpose**: Help developers understand the technical architecture and design decisions

**Content**:
- System architecture overview
- Technical stack and dependencies
- Core components and their responsibilities
- Communication protocols (Spirit Protocol, Message Bus)
- Data models and interfaces
- Architecture patterns (orchestrator, worker, event-driven)
- Workspace isolation strategy
- Performance and scalability characteristics

**Audience**: Architects, senior developers, AI agents implementing features

#### development.md (Implementation Guide)
**Purpose**: Help developers write code that follows project conventions

**Content**:
- Directory structure and organization
- Module organization and import patterns
- Naming conventions (files, classes, functions, branches)
- Agent roles and responsibilities
- Workflow processes (summoning, execution, completion)
- Code examples and usage patterns
- Extension points for new features
- Best practices and guidelines

**Audience**: Active developers, AI agents writing code

## Components and Interfaces

### Document Templates

Each document follows a consistent structure:

```markdown
# [Document Title]

## Quick Reference
[Key information at a glance]

## [Main Sections]
[Detailed content organized by topic]

## See Also
[Cross-references to related documents]
```

### Cross-Reference Pattern

Documents reference each other using consistent patterns:

```markdown
For implementation details, see [architecture.md](architecture.md#component-name)
For code structure, see [development.md](development.md#module-organization)
For product context, see [overview.md](overview.md#core-concepts)
```

## Data Models

### Content Mapping

#### From product.md → overview.md
- What is NecroCode? → Overview section
- Core Concept → Core Concepts section
- Key Features → Key Features section
- How It Works → Workflow Example section
- Target Users → Target Users section
- Differentiation → Differentiation section
- Technology Stack → MOVE to architecture.md

#### From tech.md → architecture.md
- Core Technologies → Technical Stack section
- Architecture Patterns → Architecture Patterns section
- Communication Protocol → Spirit Protocol section
- Key Components → Core Components section
- Data Models → Data Models section
- Dependencies → Dependencies section
- Performance Characteristics → Performance section
- Security Considerations → Security section
- Scalability → Scalability section
- File Structure → MOVE to development.md

#### From structure.md → development.md
- Directory Layout → Directory Structure section
- Key Directories Explained → Directory Guide section
- Module Organization → Module Organization section
- Import Paths → Import Conventions section
- Configuration Files → Configuration section
- Naming Conventions → Naming Conventions section
- Extension Points → Extension Points section
- Best Practices → Best Practices section

#### From agent-workflow.md → development.md
- Complete Workflow → Agent Workflow section
- Agent Roles & Responsibilities → Agent Roles section
- Communication Protocol → CONSOLIDATE with architecture.md
- Parallel Execution → Parallel Execution section
- Workspace Isolation → CONSOLIDATE with architecture.md
- Error Handling → Error Handling section
- Monitoring & Observability → Monitoring section
- Best Practices → MERGE with existing Best Practices
- Example: Complete Flow → Usage Examples section

### Deduplication Strategy

1. **Spirit Protocol**: Define once in architecture.md, reference from development.md
2. **Branch Naming**: Define once in development.md, reference from architecture.md
3. **Workspace Isolation**: Define architecture in architecture.md, implementation in development.md
4. **Data Models**: Define once in architecture.md, usage examples in development.md
5. **Best Practices**: Consolidate all into development.md

## Error Handling

### Migration Validation

After reorganization:
1. Verify all content from original files is preserved
2. Check that no duplicate definitions exist
3. Validate all cross-references resolve correctly
4. Ensure consistent terminology throughout

### Rollback Strategy

Keep original files as `.bak` until validation complete:
- `product.md.bak`
- `tech.md.bak`
- `structure.md.bak`
- `agent-workflow.md.bak`

## Testing Strategy

### Content Verification

1. **Completeness Check**: Ensure all sections from original files are mapped to new structure
2. **Duplication Check**: Search for duplicate content across new files
3. **Cross-Reference Check**: Verify all internal links work correctly
4. **Terminology Check**: Ensure consistent use of terms (Spirit vs Agent, Workspace vs Repository)

### Validation Criteria

- [ ] All original content preserved or intentionally removed
- [ ] No duplicate sections across documents
- [ ] All cross-references valid
- [ ] Consistent terminology throughout
- [ ] Each document serves its intended audience
- [ ] Navigation between documents is clear

## Implementation Notes

### Content Consolidation Rules

1. **When content appears in multiple files**: Keep in most appropriate location, add cross-reference in others
2. **When content spans multiple concerns**: Split into architecture (what/why) and development (how)
3. **When examples exist**: Keep in development.md with references from architecture.md
4. **When definitions exist**: Keep in architecture.md with usage in development.md

### Writing Style

- **overview.md**: Conversational, accessible, focuses on benefits and concepts
- **architecture.md**: Technical but explanatory, focuses on design decisions
- **development.md**: Prescriptive and practical, focuses on implementation

## See Also

- Original files: `product.md`, `tech.md`, `structure.md`, `agent-workflow.md`
- Related specs: `.kiro/specs/necrocode-agent-orchestration/`
