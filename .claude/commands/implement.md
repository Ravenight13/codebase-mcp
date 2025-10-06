---
description: Execute the implementation plan by processing and executing all tasks defined in tasks.md
---

The user input can be provided directly by the agent or as a command argument - you **MUST** consider it before proceeding with the prompt (if not empty).

User input:

$ARGUMENTS

1. Run `.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` from repo root and parse FEATURE_DIR and AVAILABLE_DOCS list. All paths must be absolute.

2. Load and analyze the implementation context:
   - **REQUIRED**: Read tasks.md for the complete task list and execution plan
   - **REQUIRED**: Read plan.md for tech stack, architecture, and file structure
   - **IF EXISTS**: Read data-model.md for entities and relationships
   - **IF EXISTS**: Read contracts/ for API specifications and test requirements
   - **IF EXISTS**: Read research.md for technical decisions and constraints
   - **IF EXISTS**: Read quickstart.md for integration scenarios

3. Parse tasks.md structure and extract:
   - **Task phases**: Setup, Tests, Core, Integration, Polish
   - **Task dependencies**: Sequential vs parallel execution rules
   - **Task details**: ID, description, file paths, parallel markers [P]
   - **Execution flow**: Order and dependency requirements

4. Execute implementation following the task plan with subagent orchestration:
   - **Phase-by-phase execution**: Complete each phase before moving to the next
   - **Orchestration approach**: Delegate code-writing tasks to specialized subagents using Task tool
   - **Sequential tasks**: Launch one subagent, wait for completion, validate, mark [X], proceed
   - **Parallel tasks [P]**: Launch multiple subagents concurrently with Task tool in single message
   - **Subagent context**: Provide each subagent with task ID, description, file paths, spec, plan, relevant contracts
   - **Follow TDD approach**: Execute test tasks before their corresponding implementation tasks
   - **File-based coordination**: Tasks affecting the same files must run sequentially
   - **Validation checkpoints**: Verify each phase completion before proceeding

5. Implementation execution rules:
   - **Setup first**: Initialize project structure, dependencies, configuration
   - **Tests before code**: Write tests for contracts, entities, and integration scenarios (delegated to subagents)
   - **Core development**: Implement models, services, CLI commands, endpoints (delegated to subagents)
   - **Integration work**: Database connections, middleware, logging, external services (delegated to subagents)
   - **Polish and validation**: Unit tests, performance optimization, documentation
   - **Orchestrator role**: Coordinate subagents, resolve conflicts, validate results, mark tasks complete

6. Subagent orchestration and progress tracking:
   - Identify parallel task groups from `[P]` markers in tasks.md
   - Launch parallel subagents in single message using multiple Task tool calls
   - Monitor subagent completion and collect results
   - Validate subagent output against acceptance criteria before marking [X]
   - Resolve integration conflicts when parallel tasks complete
   - **IMPORTANT**: Only mark tasks as [X] after validation passes
   - Halt execution if any non-parallel task fails
   - For parallel tasks [P], continue with successful tasks, report failed ones
   - Provide clear error messages with context for debugging
   - Suggest next steps if implementation cannot proceed

7. Completion validation:
   - Verify all required tasks are completed
   - Check that implemented features match the original specification
   - Validate that tests pass and coverage meets requirements
   - Confirm the implementation follows the technical plan
   - Report final status with summary of completed work

Note: This command assumes a complete task breakdown exists in tasks.md. If tasks are incomplete or missing, suggest running `/tasks` first to regenerate the task list.
