# Feature Specification: Create Vendor MCP Function

**Feature Branch**: `005-create-vendor`
**Created**: 2025-10-11
**Status**: Draft
**Input**: User description: "As an AI development assistant working with the commission processing system, I need a create_vendor() MCP function so that I can properly initialize vendor tracking records in the database when scaffolding new vendor extractors. Currently, when scripts/new_vendor.sh creates the code skeleton for a new vendor (extractor files, tests, fixtures), there's no programmatic way to simultaneously register that vendor in the database with its initial operational status ("broken" until implementation complete), format support flags (all false initially), and metadata (scaffolder version, creation timestamp). Without this function, there's a manual step or implicit dependency on the first update_vendor_status() call to auto-create the record, which creates ambiguity about vendor lifecycle, breaks the atomic "create vendor" workflow, and prevents the AI from providing accurate vendor status queries immediately after scaffolding. A create_vendor(name, initial_metadata) function would complete the vendor management contract and enable fully automated vendor onboarding with proper database initialization from the start."

## Execution Flow (main)
```
1. Parse user description from Input
   → If empty: ERROR "No feature description provided"
2. Extract key concepts from description
   → Identify: actors, actions, data, constraints
3. For each unclear aspect:
   → Mark with [NEEDS CLARIFICATION: specific question]
4. Fill User Scenarios & Testing section
   → If no clear user flow: ERROR "Cannot determine user scenarios"
5. Generate Functional Requirements
   → Each requirement must be testable
   → Mark ambiguous requirements
6. Identify Key Entities (if data involved)
7. Run Review Checklist
   → If any [NEEDS CLARIFICATION]: WARN "Spec has uncertainties"
   → If implementation details found: ERROR "Remove tech details"
8. Return: SUCCESS (spec ready for planning)
```

---

## ⚡ Quick Guidelines
- ✅ Focus on WHAT users need and WHY
- ❌ Avoid HOW to implement (no tech stack, APIs, code structure)
- 👥 Written for business stakeholders, not developers

### Section Requirements
- **Mandatory sections**: Must be completed for every feature
- **Optional sections**: Include only when relevant to the feature
- When a section doesn't apply, remove it entirely (don't leave as "N/A")

### For AI Generation
When creating this spec from a user prompt:
1. **Mark all ambiguities**: Use [NEEDS CLARIFICATION: specific question] for any assumption you'd need to make
2. **Don't guess**: If the prompt doesn't specify something (e.g., "login system" without auth method), mark it
3. **Think like a tester**: Every vague requirement should fail the "testable and unambiguous" checklist item
4. **Common underspecified areas**:
   - User types and permissions
   - Data retention/deletion policies
   - Performance targets and scale
   - Error handling behaviors
   - Integration requirements
   - Security/compliance needs

---

## Clarifications

### Session 2025-10-11
- Q: What validation rules should apply to vendor names? → A: 1-100 characters, alphanumeric + spaces/hyphens/underscores, case-insensitive uniqueness
- Q: How should the system handle concurrent creation attempts for the same vendor name? → A: Database UNIQUE constraint on name column (let database reject duplicates with error)
- Q: What schema/validation rules should apply to the initial_metadata parameter? → A: Flexible schema: validate known fields (scaffolder_version, created_at) if present, allow additional custom fields
- Q: What is the target latency for the create_vendor() function? → A: <100ms p95 latency (consistent with existing MCP functions)
- Q: What audit requirements and retention policies apply to vendor creation metadata? → A: No special audit requirements beyond standard database record keeping

---

## User Scenarios & Testing

### Primary User Story
An AI development assistant is scaffolding a new vendor extractor using the scripts/new_vendor.sh script. The script creates all necessary code files (extractor, tests, fixtures) for the vendor but needs a programmatic way to simultaneously initialize the vendor's database record with proper initial state. The AI assistant calls the create_vendor() MCP function with the vendor name and initial metadata (scaffolder version, creation timestamp) to register the vendor with "broken" operational status and all format support flags set to false. This completes the atomic vendor onboarding workflow, allowing immediate status queries and eliminating manual database initialization steps.

### Acceptance Scenarios
1. **Given** the scripts/new_vendor.sh script has created code skeleton for vendor "NewCorp", **When** the AI assistant calls create_vendor(name="NewCorp", initial_metadata={"scaffolder_version": "1.0", "created_at": "2025-10-11T10:00:00Z"}), **Then** a vendor record is created in the database with status "broken", all format support flags false, and the provided metadata stored.

2. **Given** no vendor record exists for "AcmeInc" in the database, **When** the AI assistant calls create_vendor(name="AcmeInc", initial_metadata={"scaffolder_version": "1.0"}), **Then** the vendor record is created with default initial state and the function returns success with the vendor details.

3. **Given** a vendor record for "ExistingVendor" already exists in the database, **When** the AI assistant calls create_vendor(name="ExistingVendor", initial_metadata={}), **Then** the function returns an error indicating the vendor already exists and does not modify the existing record.

4. **Given** the create_vendor() function has successfully created a vendor "TechCo", **When** the AI assistant immediately queries vendor status for "TechCo", **Then** the query returns the initialized record with "broken" status and initial metadata.

### Edge Cases
- What happens when create_vendor() is called with an empty vendor name?
- What happens when create_vendor() is called with vendor name that violates naming constraints (>100 characters, invalid characters, etc.)?
- What happens when create_vendor() is called with vendor name that differs only in case from an existing vendor (e.g., "NewCorp" vs "newcorp")?
- What happens when the database connection fails during vendor creation?
- What happens when initial_metadata contains invalid data types for known fields (e.g., scaffolder_version as integer instead of string, or created_at in non-ISO format)?
- What happens when multiple AI assistants try to create the same vendor simultaneously? (Database UNIQUE constraint will cause one to succeed and others to receive duplicate error)

## Requirements

### Functional Requirements
- **FR-001**: System MUST provide a create_vendor() MCP function that can be called programmatically by AI assistants
- **FR-002**: System MUST initialize new vendor records with operational status set to "broken" by default
- **FR-003**: System MUST initialize new vendor records with all format support flags set to false by default
- **FR-004**: System MUST accept vendor name as a required parameter
- **FR-005**: System MUST accept initial metadata as an optional parameter
- **FR-006**: System MUST store provided metadata in the vendor record using flexible schema that validates known fields (scaffolder_version as string, created_at as ISO timestamp) when present and allows additional custom fields
- **FR-007**: System MUST prevent duplicate vendor creation by rejecting attempts to create vendors with names that already exist
- **FR-008**: System MUST return success confirmation with vendor details after successful creation
- **FR-009**: System MUST return clear error messages when vendor creation fails (duplicate name, validation errors, database errors)
- **FR-010**: System MUST make newly created vendor records immediately queryable via existing query_vendor_status() function
- **FR-011**: System MUST integrate with scripts/new_vendor.sh workflow to enable atomic vendor onboarding
- **FR-012**: System MUST validate vendor name is 1-100 characters, contains only alphanumeric characters plus spaces/hyphens/underscores, and enforces case-insensitive uniqueness
- **FR-013**: System MUST handle concurrent creation attempts for the same vendor name safely using database UNIQUE constraint on the name column, returning appropriate error when duplicate detected
- **FR-014**: System MUST persist vendor creation metadata using standard database record keeping (created_by, created_at, updated_at fields)
- **FR-015**: System MUST complete vendor creation within <100ms p95 latency (consistent with existing MCP function performance targets)

### Key Entities
- **Vendor Record**: Represents a commission data vendor in the system with attributes including unique name, operational status (initially "broken"), format support flags (initially all false), metadata (scaffolder version, timestamps), version tracking, and audit fields (created_by, created_at, updated_at).
- **Initial Metadata**: Configuration data provided during vendor creation with flexible schema. Known fields include scaffolder_version (string) and created_at (ISO timestamp), with validation applied when present. Additional custom fields are allowed and stored without validation.

---

## Review & Acceptance Checklist
*GATE: Automated checks run during main() execution*

### Content Quality
- [X] No implementation details (languages, frameworks, APIs)
- [X] Focused on user value and business needs
- [X] Written for non-technical stakeholders
- [X] All mandatory sections completed

### Requirement Completeness
- [X] No [NEEDS CLARIFICATION] markers remain
- [X] Requirements are testable and unambiguous
- [X] Success criteria are measurable
- [X] Scope is clearly bounded
- [X] Dependencies and assumptions identified

---

## Execution Status
*Updated by main() during processing*

- [X] User description parsed
- [X] Key concepts extracted
- [X] Ambiguities marked
- [X] User scenarios defined
- [X] Requirements generated
- [X] Entities identified
- [X] Review checklist passed

---
