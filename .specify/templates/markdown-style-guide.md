# Markdown Style Guide

This style guide defines the markdown conventions for all documentation in the Codebase MCP Server project. All documentation files must adhere to GitHub-flavored Markdown (GFM) specification.

## Reference

- [GitHub-Flavored Markdown Specification](https://github.github.com/gfm/)
- [CommonMark Specification](https://spec.commonmark.org/)

## Headings

### Hierarchy Rules

- **H1 (`#`)**: Document title only (one per file)
- **H2 (`##`)**: Major sections
- **H3 (`###`)**: Subsections
- **H4 (`####`)**: Sub-subsections (use sparingly)
- **H5+**: Avoid using; restructure content if needed

### Formatting

- Use ATX-style headings (with `#` symbols)
- Add a single space after the `#` symbols
- Use sentence case for headings (capitalize first word only, unless proper nouns)
- Do not end headings with punctuation
- Leave one blank line before and after headings

**Example:**

```markdown
# Document title

This is the introduction paragraph.

## Major section

Content for the major section.

### Subsection

Content for the subsection.
```

## Code Blocks

### Fenced Code Blocks

- Use triple backticks (```) for code blocks
- Always specify the language identifier for syntax highlighting
- Use four-space indentation within code blocks when appropriate
- Leave one blank line before and after code blocks

**Supported language identifiers:**

- `python` - Python code
- `bash` or `sh` - Shell commands
- `json` - JSON data
- `yaml` - YAML configuration
- `sql` - SQL queries
- `markdown` or `md` - Markdown examples
- `text` - Plain text (no highlighting)

**Example:**

```markdown
Configure the database connection:

​```python
from sqlalchemy import create_engine

engine = create_engine("postgresql+asyncpg://localhost/codebase_mcp")
​```

Run the migration:

​```bash
alembic upgrade head
​```
```

### Inline Code

- Use single backticks for inline code references
- Use for: function names, variable names, file paths, command names, short code snippets
- Do not use for emphasis (use italic or bold instead)

**Example:**

```markdown
The `index_repository()` function accepts a `repo_path` parameter. Edit the `.specify/templates/spec-template.md` file.
```

## Tables

### Basic Tables

- Use pipes (`|`) to separate columns
- Include a header row with column names
- Include a separator row with hyphens
- Align columns using colons in the separator row
- Add spaces around cell content for readability

**Alignment:**

- Left-aligned: `:---` or `---`
- Center-aligned: `:---:`
- Right-aligned: `---:`

**Example:**

```markdown
| Column 1      | Column 2      | Column 3      |
|:------------- |:-------------:| -------------:|
| Left-aligned  | Center-aligned| Right-aligned |
| Value 1       | Value 2       | Value 3       |
| Value 4       | Value 5       | Value 6       |
```

### Complex Tables

- Keep tables simple (max 5 columns recommended)
- For complex data, consider using multiple simple tables
- Use line breaks within cells sparingly (use `<br>` if needed)
- Avoid deeply nested content in table cells

**Example:**

```markdown
| Task ID | Description                    | Status    | Owner   |
|:------- |:------------------------------ |:--------- |:------- |
| T001    | Initialize project structure   | Complete  | Alice   |
| T002    | Add contract tests             | In Progress| Bob    |
| T003    | Implement embeddings API       | Pending   | Charlie |
```

## Lists

### Unordered Lists (Bullets)

- Use hyphens (`-`) for bullet points (consistency over asterisks or plus signs)
- Add a space after the hyphen
- Use for non-sequential items
- Leave one blank line before and after the list

**Example:**

```markdown
Core principles:

- Simplicity over features
- Local-first architecture
- Protocol compliance
- Performance guarantees
```

### Ordered Lists (Numbered)

- Use `1.`, `2.`, `3.` for numbered items
- Add a space after the period
- Use for sequential steps or prioritized items
- Numbers should increment sequentially

**Example:**

```markdown
Migration workflow:

1. Backup database
2. Apply migrations
3. Validate migration
4. Monitor logs
```

### Nested Lists

- Indent nested items with 2 spaces
- Maintain consistent indentation for all nested levels
- Limit nesting to 3 levels maximum

**Example:**

```markdown
Project structure:

- `.specify/`
  - `memory/`
    - `constitution.md`
  - `scripts/`
    - `create-new-feature.sh`
    - `check-prerequisites.sh`
  - `templates/`
    - `spec-template.md`
    - `plan-template.md`
```

### Task Lists

- Use `- [ ]` for uncompleted tasks
- Use `- [x]` for completed tasks
- Add a space after the checkbox

**Example:**

```markdown
Implementation progress:

- [x] Initialize project structure
- [x] Add contract tests
- [ ] Implement embeddings API
- [ ] Add integration tests
```

## Links

### Internal Links (Cross-References)

- Use relative paths for links within the repository
- Start with `./` for same directory, `../` for parent directory
- Use descriptive link text (not "click here" or bare URLs)
- Prefer markdown link syntax over bare URLs

**Example:**

```markdown
See the [specification template](./spec-template.md) for details.

Refer to the [constitution](../memory/constitution.md) for principles.

For more information, see the [migrations guide](../../docs/migrations/002-schema-refactoring.md).
```

### External Links

- Use absolute URLs for external references
- Always include `https://` protocol
- Open external links with descriptive text

**Example:**

```markdown
This project follows the [GitHub-Flavored Markdown specification](https://github.github.com/gfm/).

For more details, see the [FastMCP documentation](https://github.com/jlowin/fastmcp).
```

### Reference-Style Links

- Use reference-style links for repeated URLs
- Define references at the bottom of the section or document
- Use descriptive reference labels

**Example:**

```markdown
The [MCP specification][mcp-spec] defines the protocol. For implementation details, see the [Python SDK][mcp-sdk].

[mcp-spec]: https://modelcontextprotocol.io/specification
[mcp-sdk]: https://github.com/anthropics/python-mcp-sdk
```

## Emphasis

### Bold

- Use double asterisks (`**text**`) for bold
- Use for: important terms on first use, critical warnings, section emphasis
- Do not overuse (diminishes effectiveness)

**Example:**

```markdown
**WARNING**: Always backup the database before migrations.

The **Model Context Protocol** (MCP) is a standardized protocol.
```

### Italic

- Use single underscores (`_text_`) for italic
- Use for: introducing new terms, emphasis, citations
- Do not use for code references (use inline code instead)

**Example:**

```markdown
The system uses _semantic search_ to find relevant code.

As noted in _the specification_, performance is critical.
```

### Inline Code

- Use single backticks (`` `text` ``) for code references
- Use for: function names, variable names, file paths, command names
- See the "Inline Code" section above for detailed guidelines

### Strikethrough

- Use double tildes (`~~text~~`) for strikethrough
- Use sparingly for showing corrections or deprecated information

**Example:**

```markdown
~~Use Python 3.9~~ This project requires Python 3.11+.
```

## File Naming

### Convention

- Use lowercase with hyphens for file names
- Format: `lowercase-with-hyphens.md`
- Avoid underscores, spaces, or special characters
- Use descriptive names that reflect content

**Examples:**

```
Good:
- specification-template.md
- database-migration-guide.md
- quickstart.md
- markdown-style-guide.md

Bad:
- SpecificationTemplate.md (camelCase)
- database_migration_guide.md (underscores)
- Quickstart Guide.md (spaces)
- guide.md (too generic)
```

### Directory Structure

- Use lowercase directories with hyphens
- Keep directory depth reasonable (max 4 levels)
- Group related files in subdirectories

**Example:**

```
.specify/
├── memory/
│   └── constitution.md
├── scripts/
│   └── bash/
│       └── create-new-feature.sh
└── templates/
    ├── spec-template.md
    ├── plan-template.md
    └── markdown-style-guide.md
```

## Horizontal Rules

- Use three hyphens (`---`) for horizontal rules
- Leave one blank line before and after the rule
- Use sparingly to separate major sections

**Example:**

```markdown
## Section One

Content for section one.

---

## Section Two

Content for section two.
```

## Blockquotes

- Use `>` for blockquotes
- Add a space after the `>`
- Use for: important notes, quotes from external sources, callouts

**Example:**

```markdown
> **Note**: This operation is irreversible. Always create a backup first.

From the specification:

> The Model Context Protocol enables AI assistants to securely access
> local and remote resources through a standardized interface.
```

## Images

- Use descriptive alt text for all images
- Store images in `docs/images/` or feature-specific directories
- Use relative paths for image references
- Provide context before and after images

**Example:**

```markdown
The architecture follows a client-server model:

![MCP Architecture Diagram](../images/mcp-architecture.png)

The diagram shows the three-tier structure.
```

## Line Length

- Prefer soft wrapping (no hard line breaks in paragraphs)
- Let the editor handle line wrapping for readability
- Use hard breaks only for semantic line breaks (one sentence per line in some contexts)
- Keep code blocks readable (consider 80-100 character width)

## Whitespace

- Use one blank line between paragraphs
- Use one blank line before and after headings
- Use one blank line before and after code blocks
- Use one blank line before and after lists
- Use one blank line before and after tables
- No trailing whitespace at end of lines
- End files with a single newline character

## Special Formatting

### Admonitions (Notes, Warnings)

- Use blockquotes with bold labels for admonitions
- Common types: Note, Warning, Important, Tip

**Example:**

```markdown
> **Note**: Configuration changes require a server restart.

> **Warning**: This operation will delete all data. Backup first.

> **Important**: Python 3.11+ is required for this project.

> **Tip**: Use the `--json` flag for machine-readable output.
```

### Placeholders

- Use `[UPPERCASE_TOKENS]` for template placeholders
- Document all placeholders in template files
- Replace placeholders during document generation

**Example:**

```markdown
# [FEATURE_NAME] Specification

**Feature Owner**: [OWNER_NAME]
**Created**: [CREATION_DATE]

## Overview

[FEATURE_DESCRIPTION]
```

## Documentation Structure

### Standard Document Sections

Most documentation files should follow this structure:

1. **Title** (H1) - Document name
2. **Overview** (H2) - Brief introduction
3. **Main Content** (H2) - Core documentation
4. **Examples** (H2) - Practical examples
5. **References** (H2) - Related documentation, external links

**Example:**

```markdown
# Feature Name

Brief one-line description.

## Overview

Detailed introduction to the feature.

## Installation

Step-by-step installation instructions.

## Usage

How to use the feature with examples.

## Configuration

Configuration options and examples.

## Troubleshooting

Common issues and solutions.

## References

- [Related Documentation](./related.md)
- [External Resource](https://example.com)
```

## Validation

### Markdown Linting

- Use `markdownlint` for automated validation
- Configuration: `.markdownlint.json` in repository root
- Run before committing documentation changes

### Manual Review Checklist

- [ ] All headings follow hierarchy rules
- [ ] Code blocks have language identifiers
- [ ] Tables are properly formatted and aligned
- [ ] Links are valid (no broken references)
- [ ] File names use lowercase-with-hyphens
- [ ] No trailing whitespace
- [ ] File ends with single newline
- [ ] Inline code used for code references
- [ ] Lists are properly formatted and indented
- [ ] One blank line between major elements

## Common Mistakes

### What to Avoid

1. **Mixing heading styles**: Don't use both `# Heading` and underline-style headings
2. **Inconsistent list markers**: Use hyphens consistently for bullets
3. **Missing language identifiers**: Always specify language for code blocks
4. **Bare URLs**: Use descriptive link text instead of raw URLs
5. **Overusing bold/italic**: Reserve for actual emphasis
6. **Inconsistent file naming**: Stick to lowercase-with-hyphens
7. **Hard line breaks in paragraphs**: Let the editor handle wrapping
8. **Trailing whitespace**: Remove all trailing spaces
9. **Multiple blank lines**: Use only one blank line between elements
10. **Undefined placeholders**: Always document what placeholders mean

## Version History

- **v1.0.0** (2025-10-13): Initial style guide creation
