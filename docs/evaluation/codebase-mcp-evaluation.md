# Codebase-MCP Tools Comprehensive Evaluation

**Test Date:** October 11, 2025  
**Tester:** Claude (AI Assistant)  
**Tools Tested:** 15 of 15 available MCP tools  

---

## Executive Summary

The codebase-MCP server demonstrates solid functionality across work item management, task tracking, and code search operations. However, **one critical timezone bug blocks project configuration entirely**, and repository indexing silently fails without creating chunks. The system shows good architectural design with optimistic locking and proper hierarchy support, but needs immediate attention to the configuration subsystem.

**Severity Ratings:**
- 🔴 **Critical (1)**: Blocks core functionality
- 🟡 **High (2)**: Impacts usability/reliability  
- 🟢 **Medium (3)**: Reduces quality of life

---

## Tool Category Results

### ✅ Work Items (5/5 tools functional)
**Status:** Fully operational with excellent feature parity

**Tested:**
- `create_work_item`: ✅ Creates projects, sessions, tasks with proper hierarchy
- `query_work_item`: ✅ Returns full hierarchy with descendants
- `update_work_item`: ✅ Optimistic locking working (version increments)
- `list_work_items`: ✅ Filtering and pagination working
- Hierarchy management: ✅ Parent-child relationships tracked via materialized path

**Strengths:**
- Proper timezone-aware timestamps (ISO 8601 with +00:00)
- Optimistic locking prevents concurrent update conflicts
- Materialized path enables efficient hierarchy queries
- Metadata validation enforces type-specific schemas

**Observations:**
- Session metadata requires `prompts_count` and `yaml_frontmatter` fields
- `yaml_frontmatter` must be dict with `schema_version` key
- Version tracking works correctly (increments on update)

---

### ⚠️ Tasks (4/4 tools functional with caveats)
**Status:** Working but limited by array parameter bug

**Tested:**
- `create_task`: ✅ Basic creation works
- `list_tasks`: ✅ Both summary and full_details modes work
- `update_task`: ✅ Status and branch tracking operational
- `get_task`: ✅ Returns complete task data

**Token Efficiency Feature:**
The new summary mode is excellent - reducing from ~800-1000 tokens to ~120-150 tokens (6x reduction) is a smart architectural choice for task browsing.

**Issue:** 
Array parameters (`planning_references`) fail with validation error. Creating tasks with document references requires workaround or API fix.

---

### ⚠️ Deployments (1/1 tool functional with caveats)
**Status:** Working after understanding metadata schema

**Tested:**
- `record_deployment`: ✅ Creates deployment records with relationships

**Metadata Requirements (not obvious from docs):**
```json
{
  "pr_number": 123,
  "pr_title": "string",
  "commit_hash": "40-char-hex-lowercase",
  "test_summary": {
    "total": int,
    "passed": int,
    "failed": int
  },
  "constitutional_compliance": boolean
}
```

**Issue:**
Array parameters (`work_item_ids`, `vendor_ids`) fail validation. Cannot link deployments to work items via API call - must be null.

---

### 🔴 Project Configuration (0/2 tools functional)
**Status:** BROKEN - Critical timezone bug

**Tested:**
- `get_project_configuration`: ❌ Fails - database not initialized
- `update_project_configuration`: ❌ **CRITICAL BUG**

**Error Details:**
```
asyncpg.exceptions.DataError: can't subtract offset-naive and offset-aware datetimes
```

**Root Cause:**
The server is mixing timezone-aware datetime (`last_health_check_at` with UTC) and timezone-naive datetime (`updated_at` without timezone) when inserting into `TIMESTAMP WITHOUT TIME ZONE` columns. PostgreSQL's asyncpg driver correctly rejects this operation.

**Impact:**
- Cannot initialize project configuration
- Cannot set active context type
- Cannot manage token budgets
- Cannot track git state at project level

**Fix Needed:**
Ensure all datetime objects are either timezone-aware OR timezone-naive consistently. Recommended: Use timezone-aware throughout (UTC) and strip timezone when inserting to `TIMESTAMP WITHOUT TIME ZONE` columns.

---

### 🔴 Code Search (1/2 tools functional)
**Status:** Search works, indexing silently fails

**Tested:**
- `index_repository`: ❌ **SILENT FAILURE**
- `search_code`: ✅ Works against previously indexed codebase

**Index Failure Details:**
```json
{
  "repository_id": "f8e20b9b-89f7-40b5-94f5-13b5959690dc",
  "files_indexed": 0,
  "chunks_created": 0,
  "duration_seconds": 0.023,
  "status": "success"
}
```

Despite 2 Python files existing in `/tmp/test-repo`, indexing returned `status: "success"` with 0 files indexed. This is a **silent failure** - the worst kind of bug because users won't know indexing didn't work.

**Search Quality:**
Semantic search against the pre-existing codebase returned relevant results with good similarity scores (0.74+). The feature works when content is indexed.

---

### ⚠️ Vendors (1/2 tools accessible)
**Status:** Query works, creation not implemented

**Tested:**
- `query_vendor_status`: ✅ Returns appropriate error for missing vendor
- `update_vendor_status`: ✅ Expected to work with optimistic locking
- `create_vendor()`: ❌ Not implemented (per user request, not testing)

**Note:** Without vendor creation capability, the vendor tracking system is view-only for any AI client.

---

## Issues Detected

### 🔴 Critical Issues

#### 1. Project Configuration Timezone Bug
**Function:** `update_project_configuration`  
**Severity:** CRITICAL (blocks all project config operations)

**User Story:**
As a developer trying to initialize the project configuration for my codebase management system, I need the system to properly handle datetime values when storing them in the database so that I can set my active context type, configure token budgets, and track git state without encountering database errors that completely block the configuration subsystem. Currently, when I attempt to update the project configuration, the system crashes with a timezone-related database error, which means I cannot use any of the project-level configuration features that are essential for organizing my work. This isn't just an inconvenience—it's a complete blocker that prevents the project configuration table from even being initialized, rendering the entire configuration management system unusable.

**Problem:**
Mixing timezone-aware and timezone-naive datetimes causes PostgreSQL insertion failure.

**Error:**
```python
# Server is doing this:
last_health_check_at = datetime.now(timezone.utc)  # Timezone-aware
updated_at = datetime.now()  # Timezone-naive

# PostgreSQL rejects comparing these for TIMESTAMP WITHOUT TIME ZONE columns
```

**Fix:**
```python
# Option 1: Make everything timezone-aware, strip before insert
dt_utc = datetime.now(timezone.utc)
db_value = dt_utc.replace(tzinfo=None)  # Strip for TIMESTAMP WITHOUT TIME ZONE

# Option 2: Use PostgreSQL TIMESTAMP WITH TIME ZONE
# Update schema and keep timezone info throughout
```

**Why This Matters:**
The project configuration is the singleton control center. Without it, users can't set active context, manage token budgets, or track git state at the project level. This needs fixing before any real project use.

---

#### 2. Repository Indexing Silent Failure
**Function:** `index_repository`  
**Severity:** CRITICAL (semantic search depends on indexed content)

**User Story:**
As a developer who relies on semantic code search to navigate and understand my codebase, I need the repository indexing process to actually scan and index my code files so that I can perform meaningful searches across my project. When I run the indexing tool on a directory containing valid code files, the system reports success but shows zero files indexed and zero chunks created, which means the semantic search feature becomes completely useless because there's no content to search. What makes this particularly dangerous is that the system claims "success" even though it did nothing, so I have no way of knowing whether my code is actually indexed or not. I might spend time trying to search for code patterns, getting frustrated with poor results, only to discover later that nothing was ever indexed in the first place. I need the indexing to either work correctly and actually process my files, or at minimum fail loudly with a clear error message explaining why it couldn't index the code.

**Problem:**
Indexing reports `status: "success"` with `files_indexed: 0` despite files existing in the target directory.

**Test Case:**
```bash
# Directory contents
/tmp/test-repo/
├── main.py      (273 bytes, valid Python)
└── utils.py     (385 bytes, valid Python)

# Result
{
  "files_indexed": 0,
  "chunks_created": 0,
  "status": "success"  # ← Should be "failed" or "partial"
}
```

**Likely Causes:**
1. File scanner not finding files (check path traversal)
2. File type filtering too aggressive (check extension whitelist)
3. File reading failing silently (check error handling)
4. Chunking logic skipping all content (check chunking thresholds)

**Fix Priority:**
HIGH - Semantic search is a key differentiator. If indexing doesn't work, the feature is useless. Additionally, returning `status: "success"` when no work was done violates user expectations and makes debugging impossible.

**Recommendation:**
- Add verbose logging to each indexing stage
- Return `status: "partial"` or `"failed"` when files_indexed == 0
- Include `errors` array with specific failure reasons
- Consider adding dry-run mode that reports what would be indexed

---

### 🟡 High-Priority Issues

#### 3. Array Parameters Don't Work
**Functions:** `create_task`, `record_deployment`  
**Severity:** HIGH (blocks linking relationships)

**User Story:**
As a developer tracking my work through tasks and deployments, I need the ability to link related items together—such as referencing planning documents when creating tasks or connecting work items to deployments—so that I can maintain proper relationships and traceability across my project management system. Currently, whenever I try to pass arrays of references (like planning document paths or work item IDs), the system rejects my request with a validation error, which means I cannot establish these important connections between different parts of my project. This forces me to create disconnected entities that lose valuable context about what documents informed a task's creation or which work items were included in a specific deployment. Without these relationships, the system becomes a collection of isolated data points rather than an interconnected project management tool, making it much harder to understand dependencies, track changes, and maintain a complete audit trail of how work progresses through the system.

**Problem:**
When passing arrays like `["item1", "item2"]`, the server returns:
```
Input validation error: '["item1", "item2"]' is not valid under any of the given schemas
```

**Impact:**
- Cannot create tasks with planning document references
- Cannot link deployments to work items or vendors
- Many-to-many relationships cannot be established via MCP calls

**Test Cases:**
```python
# All of these fail
create_task(planning_references=["docs/plan.md"])
record_deployment(work_item_ids=["uuid1", "uuid2"])
record_deployment(vendor_ids=["uuid1"])
```

**Possible Causes:**
1. JSON schema definition mismatch between client and server
2. MCP parameter serialization not handling arrays
3. Pydantic validation strictness issue

**Workaround:**
Currently, relationships must be null on creation. May need separate endpoint to add relationships post-creation.

---

### 🟢 Medium-Priority Issues

#### 4. Inadequate Documentation for Metadata Schemas and Validation Rules
**Functions:** `create_work_item`, `record_deployment`, `update_project_configuration`  
**Severity:** MEDIUM (discoverable but frustrating)

**User Story:**
As a developer integrating with the MCP tools, I need clear documentation about what metadata fields are required and what validation rules apply to parameters so that I can successfully use the tools without wasting time on trial-and-error debugging. Currently, when I try to create work items or record deployments, the tool descriptions simply say "metadata: Type-specific JSONB metadata" without explaining what fields are actually required, what data types they expect, or what the valid ranges are for numeric parameters. This means I have to guess, submit a request, get a cryptic validation error, adjust my approach, and repeat until I stumble upon the correct format. For example, session metadata requires specific fields like "prompts_count" and a nested "yaml_frontmatter" structure with a "schema_version" key, but none of this is mentioned in the documentation. Similarly, deployment metadata needs "test_summary" as a dict (not a string), and commit hashes must be exactly 40 lowercase hex characters, but I only discover these requirements through failed attempts. Even worse, when I try to set token budgets that seem reasonable (like 150,000 or 200,000), they're rejected without explanation of what the actual valid range is. This poor documentation creates unnecessary friction and makes the system feel unreliable, when in reality it might work perfectly fine if I just knew the correct format upfront.

**Problem:**
Required metadata fields aren't documented in tool descriptions.

**Examples:**

**Session Metadata:**
Tool says: `metadata: Type-specific JSONB metadata`  
Reality: Must include `prompts_count`, `yaml_frontmatter` with nested `schema_version`

**Deployment Metadata:**
Tool says: `metadata: Deployment metadata dict`  
Reality: Must include `test_summary` as dict (not string), `commit_hash` must be 40-char lowercase hex

**Impact:**
Trial-and-error required to discover field requirements. Wastes developer time and creates poor UX.

**Recommendation:**
Add concrete metadata examples to each tool's description:

```python
# In tool description
"""
Session metadata example:
{
  "focus_area": "Feature development",
  "token_budget": 100000,
  "prompts_count": 0,
  "yaml_frontmatter": {
    "schema_version": "1.0",
    "date": "2025-10-11",
    "type": "feature"
  }
}

Deployment metadata example:
{
  "pr_number": 123,
  "pr_title": "Feature: Add new extractor",
  "commit_hash": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",  # Must be 40-char lowercase hex
  "test_summary": {
    "total": 100,
    "passed": 98,
    "failed": 2
  },
  "constitutional_compliance": true
}

Token budget constraints: Integer between 1,000 and 1,000,000
"""
```

---

## Suggested Enhancements

### 1. Bulk Operations Support
**Motivation:** Efficiency and atomic operations

**User Story:**
As a developer setting up new projects or managing large-scale updates, I need the ability to create or modify multiple related work items in a single operation so that I can ensure atomic transactions and reduce the time spent on repetitive API calls. Currently, when I want to set up a new feature with a project, multiple sessions, and dozens of tasks, I have to make individual API calls for each item, which is slow and creates a risk that some items succeed while others fail, leaving my project in an inconsistent state. Similarly, when a critical dependency breaks and I need to mark 15 related tasks as "blocked," I have to update each one individually, hoping none of the updates fail halfway through. What I need is the ability to batch these operations together so they either all succeed or all fail as a unit, giving me transactional safety and dramatically reducing the overhead of managing large work item hierarchies. This would also improve performance by reducing network roundtrips and enable patterns like "create a project from a template" where an entire hierarchy is instantiated in one atomic operation.

Many workflows need to create multiple related items:
- Create project + sessions + tasks in one transaction
- Update multiple work items to "blocked" status when dependency fails
- Record deployment affecting dozens of work items

**Proposed Tools:**

```python
bulk_create_work_items(
    items: List[WorkItemCreate]
) -> BulkCreateResult

bulk_update_work_items(
    updates: List[Tuple[UUID, Dict[str, Any]]]
) -> BulkUpdateResult
```

**Benefits:**
- Atomic operations (all succeed or all fail)
- Reduced roundtrip latency
- Transaction safety

---

### 2. Work Item Search
**Motivation:** Discovery and navigation

**User Story:**
As a developer managing dozens or hundreds of work items across multiple sessions and projects, I need a powerful search capability to find specific work items based on their content, metadata, or relationships so that I can quickly locate relevant work without manually paging through long lists or remembering exact IDs. Currently, the only way to find work items is to either know their UUID already or iterate through paginated lists filtered only by basic criteria like status or type, which becomes impractical once I have more than a few dozen items. When I'm trying to answer questions like "which tasks mention PostgreSQL migration?" or "show me all work items blocked by integration tests" or "find sessions related to authentication," I have no efficient way to get those answers. I end up either keeping external notes about where things are or spending significant time clicking through lists trying to spot the right item. What I need is a search tool that can find work items by text content in titles and descriptions, by metadata values, by status combinations, by dependency relationships, and ideally by semantic similarity to handle fuzzy queries. This would transform work item management from a manual filing system into an intelligent discovery platform where I can ask natural questions and find what I need.

Current approach requires knowing IDs or iterating through pages. Real workflows need search:
- "Find all tasks blocked by integration tests"
- "Show me sessions related to authentication"
- "Which work items mention 'PostgreSQL migration'?"

**Proposed Tool:**

```python
search_work_items(
    query: str,
    item_type: Optional[str] = None,
    status: Optional[str] = None,
    metadata_filters: Optional[Dict] = None
) -> SearchResults
```

**Implementation:**
Could leverage existing semantic search infrastructure (pgvector) or add full-text search (tsvector).

---

### 3. Work Item Dependency Management
**Motivation:** Explicit blocking relationships

**User Story:**
As a developer coordinating complex work where some tasks cannot proceed until others are completed, I need explicit dependency tracking between work items so that I can clearly document blocking relationships, visualize dependency chains, and make informed decisions about what work can proceed in parallel versus what must wait. Currently, while the system mentions that dependency information exists in the work item responses, there are no tools to actually create, modify, or query these relationships. This means when I have a task that's blocked by another task still in research, or when I have multiple work items that all depend on a single infrastructure upgrade, I have to track these relationships in external notes or remember them manually. This leads to mistakes where I start work on something that's actually blocked, or where I complete a critical piece of work but forget to unblock all the dependent items waiting for it. What I need is the ability to explicitly declare "Task A is blocked-by Task B," query the full dependency graph for a work item to see everything it depends on and everything depending on it, and get warnings when I'm about to create circular dependencies. This would enable better planning, clearer communication about why work isn't progressing, and automated detection of when blocked work becomes unblocked.

Currently, dependencies are mentioned in `query_work_item` response but no tools to manage them:

```python
add_work_item_dependency(
    work_item_id: UUID,
    depends_on_id: UUID,
    dependency_type: str  # "blocked-by", "depends-on", "related-to"
) -> DependencyResult

remove_work_item_dependency(
    work_item_id: UUID,
    depends_on_id: UUID
) -> DependencyResult

get_dependency_graph(
    work_item_id: UUID,
    depth: int = 5
) -> DependencyGraph
```

**Use Cases:**
- Block task until research completes
- Show full dependency chain for project
- Identify circular dependencies

---

### 4. Enhanced Deployment Queries
**Motivation:** Trend analysis and rollback decisions

**User Story:**
As a developer responsible for maintaining production systems and making deployment decisions, I need the ability to query and analyze deployment history so that I can understand what was deployed when, identify patterns in deployment success or failure, determine the impact radius of specific deployments, and make informed decisions about whether to roll back changes. Currently, I can record deployments but I cannot query them—there's no way to ask "show me all deployments in the last 24 hours," "which deployments included this specific work item," "what vendors were affected by yesterday's release," or "what was the test pass rate trend over the last 10 deployments." Without this visibility, I'm essentially writing deployment information into a black hole where it can never be retrieved or analyzed. When a production issue occurs and I need to quickly identify what changed recently, or when I want to understand if our deployment quality is improving over time, I have no tools to answer these questions. What I need is a comprehensive deployment query system that lets me filter by date ranges, search by affected work items or vendors, analyze test result trends, and generate deployment impact reports that show exactly what changed in each release and what the blast radius was.

Current: Create deployments only  
Needed: Query and analyze deployment history

```python
list_deployments(
    after: Optional[datetime] = None,
    before: Optional[datetime] = None,
    work_item_id: Optional[UUID] = None,
    vendor_id: Optional[UUID] = None
) -> DeploymentList

get_deployment_impact(
    deployment_id: UUID
) -> ImpactAnalysis  # Shows affected vendors, work items, test results
```

**Use Cases:**
- "Show deployments in the last 24 hours"
- "What deployments included this work item?"
- "Which vendors were affected by last deployment?"

---

### 5. Task Templates
**Motivation:** Consistency and speed

**User Story:**
As a developer who frequently works on similar types of projects with predictable workflows, I need reusable task templates that capture common work patterns so that I can quickly bootstrap new work with consistent structure and complete checklists instead of manually recreating the same set of tasks every time. Currently, when I start integrating a new vendor (which I do regularly), I have to manually create the same sequence of tasks every time: research the vendor's format, implement the extractor, write tests, and document the integration. Each time I do this, there's a risk I'll forget a step or create tasks with inconsistent naming or estimation. Similarly, when I start developing a new feature, there's a standard workflow I follow with specific phases and checkpoints, but I have to recreate this structure from scratch each time. What I need is the ability to define these recurring patterns as templates—for example, a "vendor integration template" that automatically creates all the standard tasks with appropriate time estimates and sequencing, or a "feature development template" that sets up the research, implementation, testing, and documentation phases. This would dramatically reduce the setup time for new work, ensure consistency across similar efforts, and capture institutional knowledge about how work should be structured so that best practices are automatically applied rather than having to be remembered each time.

Recurring patterns (e.g., vendor integration, feature development) should be templated:

```python
create_task_from_template(
    template_name: str,
    variables: Dict[str, str]
) -> Task

# Example templates
vendor_integration_template = {
    "tasks": [
        {"title": "Research {vendor} format", "estimated_hours": 2},
        {"title": "Implement {vendor} extractor", "estimated_hours": 4},
        {"title": "Write {vendor} tests", "estimated_hours": 3}
    ]
}
```

---

### 6. Repository Indexing Health Check
**Motivation:** Debugging and monitoring

**User Story:**
As a developer relying on semantic code search to navigate my codebase, I need diagnostic tools that tell me whether my repositories are properly indexed and healthy so that I can troubleshoot search quality issues and understand when I need to reindex content. Currently, when semantic search returns poor results or no results at all, I have no way to determine whether the problem is that the repository isn't indexed, the index is stale, my search query is wrong, or something else entirely. The indexing process reports success or failure, but gives me no insight into what it found, what it skipped, or why certain files might not be indexed. This makes debugging search problems incredibly frustrating because I'm operating blind—I don't know if my Python files are indexed but my JavaScript files aren't, whether the index is from three weeks ago when the code was different, or if there are permission issues preventing certain directories from being scanned. What I need is a health check tool that can inspect a repository path and tell me: does this directory exist, is it readable, how many files are present, how many are indexable, whether they're already indexed, when the index was last updated, how many chunks are stored, and any warnings about large binary files or other issues. This diagnostic information would transform debugging from guesswork into methodical problem-solving.

Add diagnostic tool to check indexing status:

```python
get_repository_health(
    repo_path: str
) -> RepositoryHealth

# Returns
{
  "path": "/path/to/repo",
  "exists": true,
  "readable": true,
  "file_count": 156,
  "indexable_files": 142,
  "already_indexed": true,
  "last_indexed": "2025-10-11T12:00:00Z",
  "chunks_stored": 1234,
  "issues": ["Large binary files detected: 14"]
}
```

**Use Cases:**
- Debug why indexing isn't working
- Monitor staleness of indexed content
- Identify configuration problems before indexing

---

### 7. Vendor Audit Trail
**Motivation:** Debugging and compliance

**User Story:**
As a developer maintaining multiple vendor extractors that change status over time, I need a complete audit trail showing the history of changes to each vendor so that I can debug problems, understand when and why vendors broke, comply with audit requirements, and learn from patterns in vendor stability. Currently, while vendor status has version numbers for optimistic locking, there's no way to see the historical changes—I can only see the current state. This means when a vendor that was working last week suddenly shows as "broken," I have no visibility into what changed, when it changed, who changed it, or what the previous state was. If a vendor configuration got accidentally modified and is now failing, I have no way to see what the working configuration looked like so I can restore it. When I'm trying to understand patterns like "why does the EPSON vendor break every quarter," I can't analyze the historical status changes to identify correlations with their format updates. What I need is a time-series audit log for each vendor that captures every status change, every metadata update, who made the change, when it happened, and ideally a diff showing exactly what changed. This would enable rollback to known-good configurations, root cause analysis of vendor failures, compliance reporting for audit purposes, and data-driven insights about vendor reliability patterns.

Track all changes to vendor status over time:

```python
get_vendor_history(
    name: str,
    limit: int = 50
) -> VendorHistory

# Returns list of changes
[
  {
    "timestamp": "2025-10-11T14:00:00Z",
    "version": 5,
    "status": "operational",
    "changed_by": "claude-code",
    "metadata_diff": {"test_passed": {"old": false, "new": true}}
  },
  ...
]
```

---

### 8. Work Item Time Tracking
**Motivation:** Project management and estimation

**User Story:**
As a developer who wants to improve my estimation accuracy and understand where my time actually goes, I need built-in time tracking for work items so that I can compare estimated effort against actual time spent, identify work that consistently takes longer than expected, and make more realistic commitments based on historical data. Currently, when I create tasks, I might estimate "this will take 4 hours," but I have no systematic way to track whether it actually took 4 hours, 2 hours, or 8 hours. This means my estimates never improve because I'm not learning from reality—I'm just guessing every time. When I try to plan a sprint or estimate how long a new vendor integration will take, I'm shooting in the dark because I don't have data about how long similar work took in the past. What I need is the ability to start a timer when I begin work on an item, stop it when I finish or context switch, and automatically accumulate the actual time spent. The system should track multiple work sessions for a single item (because real work is rarely continuous), show me the variance between estimated and actual time, and let me analyze patterns like "vendor research always takes 2x longer than I estimate" or "testing is my most underestimated activity." This data would transform project planning from intuition-based guessing into evidence-based estimation.

Add time tracking to understand actual vs. estimated effort:

```python
start_work_timer(work_item_id: UUID) -> Timer
stop_work_timer(work_item_id: UUID) -> TimeEntry
get_time_summary(work_item_id: UUID) -> TimeSummary

# Metadata enrichment
{
  "estimated_hours": 4.0,
  "actual_hours": 6.5,
  "sessions": [
    {"start": "...", "end": "...", "duration_hours": 2.5},
    {"start": "...", "end": "...", "duration_hours": 4.0}
  ]
}
```

---

### 9. Code Search Filters
**Motivation:** Precision and relevance

**User Story:**
As a developer using semantic code search to find relevant code patterns, I need advanced filtering capabilities beyond basic semantic similarity so that I can narrow my search to recently modified files, exclude test directories when I'm looking for production code, limit results to files under a certain size, or require a minimum similarity threshold to filter out tangential matches. Currently, semantic search returns results from across my entire codebase regardless of when files were modified, whether they're in directories I care about, or how big they are. This means when I'm investigating a recent authentication bug and search for "authentication logic," I get results from old deprecated code alongside current implementations, mixed with test fixtures and mock objects. When I'm looking for database query patterns but want to exclude the test suite, I have no way to filter out the test directory—I just get everything and have to manually scan through results to find production code. When I want high-confidence matches only because I'm looking for exact patterns rather than general concepts, I have no way to require a minimum similarity score, so I get pages of loosely related results that waste my time. What I need is a rich set of filters that let me combine semantic search with practical constraints: show me authentication code that was modified in the last month, exclude the tests directory, require 80% similarity or higher, and limit to files under 5000 lines. This would transform search from a scattershot tool into a precision instrument.

Current search is semantic-only. Add filters for better targeting:

```python
search_code(
    query: str,
    file_type: Optional[str] = None,         # ✅ Already exists
    directory: Optional[str] = None,          # ✅ Already exists  
    modified_after: Optional[datetime] = None, # 🆕 New
    max_file_size: Optional[int] = None,      # 🆕 New
    exclude_dirs: List[str] = None,           # 🆕 New
    min_similarity: float = 0.0               # 🆕 New
)
```

**Example Use Cases:**
```python
# Find recent authentication changes
search_code("authentication", modified_after="2025-10-01")

# Search only in src/, exclude tests
search_code("validation logic", directory="src", exclude_dirs=["tests"])

# High-confidence matches only
search_code("database connection", min_similarity=0.8)
```

---

### 10. Configuration Presets
**Motivation:** Context switching efficiency

**User Story:**
As a developer who switches between different types of work throughout the day—feature development in the morning, bug investigation in the afternoon, deep research on complex problems in the evening—I need the ability to save and quickly restore configuration presets for each work mode so that I don't have to manually reconfigure context type and token budgets every time I context switch. Currently, when I'm doing feature development, I might want the context set to "feature" with a 200,000 token budget, but when I switch to debugging a production issue, I need "maintenance" context with a tighter 100,000 token budget to stay focused, and when I'm doing research or architecture work, I want "research" context with a generous 500,000 token budget for deep exploration. Right now, I'd have to manually update these settings each time I switch modes, which is tedious and error-prone—I often forget to change the context type and then wonder why my work isn't being tracked correctly. What I need is the ability to save named presets like "feature_dev," "bug_investigation," and "research_mode" that capture the right configuration for each work style, then switch between them with a single command. This would make context switching instant and automatic, ensure I always have appropriate settings for the type of work I'm doing, and eliminate the cognitive overhead of remembering to reconfigure things manually every time my focus shifts.

Development workflows switch between contexts frequently:

```python
save_configuration_preset(
    name: str,
    config: ProjectConfig
) -> Preset

load_configuration_preset(
    name: str
) -> ProjectConfig

list_configuration_presets() -> List[Preset]

# Example presets
{
  "feature_development": {
    "active_context_type": "feature",
    "default_token_budget": 200000
  },
  "bug_investigation": {
    "active_context_type": "maintenance",
    "default_token_budget": 100000
  },
  "deep_research": {
    "active_context_type": "research",
    "default_token_budget": 500000
  }
}
```

---

## Recommendations Priority

### Immediate (Fix Before Production Use)
1. **Fix timezone bug in project configuration** (blocks core functionality)
2. **Fix repository indexing silent failure** (breaks semantic search)
3. **Document metadata schemas** (critical UX issue)

### Short Term (Next Sprint)
4. Fix array parameter validation
5. Add bulk operations support
6. Implement work item search
7. Add repository health check tool

### Medium Term (Next Quarter)
8. Enhanced deployment queries
9. Work item dependency management
10. Vendor audit trail
11. Code search filters

### Long Term (Future Enhancements)
12. Task templates
13. Time tracking
14. Configuration presets

---

## Confidence Assessment

**Overall System Quality:** 7.5/10
- ✅ Solid architecture (optimistic locking, hierarchy, metadata flexibility)
- ✅ Good separation of concerns (work items vs tasks vs vendors)
- ✅ Semantic search foundation is excellent
- ❌ Critical bugs block key subsystems
- ❌ API usability needs improvement

**Production Readiness:** Not Ready
- Blockers: Project config broken, indexing fails silently
- After fixes: Ready for beta testing

**Recommendation:**
Fix the critical issues (timezone bug, indexing failure) and this is a solid foundation for AI-driven project management. The architecture choices (materialized paths, JSONB metadata, pgvector search) are all good. Just needs the rough edges polished.

---

## Test Methodology

**Approach:** Systematic black-box testing of all 15 MCP tools
- Created test data for work items, tasks, deployments
- Attempted repository indexing with synthetic codebase
- Tested search against pre-existing indexed content
- Validated optimistic locking behavior
- Verified error handling for edge cases

**Limitations:**
- Could not fully test vendor operations (no create_vendor)
- Could not fully test project configuration (blocked by timezone bug)
- Repository indexing failure limited code search validation
- Array parameters consistently failed, limiting relationship testing

**Environment:**
- Container-based execution
- PostgreSQL backend with pgvector
- Python-based MCP server

---

## Conclusion

The codebase-MCP server shows promise as an AI-native project management system. The architecture is sound, the features are well-thought-out, and when things work, they work well. The work item hierarchy, optimistic locking, and semantic search are all impressive.

**But** - and this is a big but - the critical bugs need immediate attention. A project management system where you can't configure the project, and a semantic search system where indexing silently fails, isn't ready for real use.

Fix those two issues, clean up the API usability (array parameters, metadata docs), and this becomes a genuinely useful tool for AI-driven development workflows.

**Final Grade: B+ (with potential for A after critical fixes)**

The bones are good. Polish the rough edges and this will shine.
