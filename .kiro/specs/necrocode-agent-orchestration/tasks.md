# Implementation Plan

- [x] 1. Enhance base Spirit class with workload tracking
  - Update BaseSpirit dataclass to include instance_number, current_tasks, completed_tasks fields
  - Implement assign_task(), complete_task(), and get_workload() methods
  - Update identifier generation to include instance number (e.g., "frontend_spirit_1")
  - _Requirements: 1.4, 3.2, 4.1_

- [x] 2. Implement Issue Router component
  - [x] 2.1 Create IssueRouter class with keyword-based routing logic
    - Define ROUTING_RULES dictionary with keywords for each agent type (frontend, backend, database, qa, devops, architect)
    - Implement route_issue() method that analyzes issue title and description
    - Support both Japanese and English keywords
    - _Requirements: 3.1, 4.1_
  
  - [x] 2.2 Implement load balancing logic
    - Create _get_agent_by_type() method to find available agents
    - Implement _balance_load() method using least-busy strategy
    - Handle case when no agents of requested type are available
    - _Requirements: 3.2, 4.2_
  
  - [x] 2.3 Integrate IssueRouter with Scrum Master Spirit
    - Add route_issue() method to ScrumMasterSpirit
    - Update assign_tasks() to use IssueRouter for automatic assignment
    - Add _get_available_agent() method for load balancing
    - _Requirements: 3.1, 3.3_

- [x] 3. Update Workspace Manager for multiple agent instances
  - [x] 3.1 Enhance branch naming convention
    - Update create_branch() to accept issue_id parameter
    - Implement logic for both instance-based and issue-based branch names
    - Extract instance number from spirit_id for branch naming
    - _Requirements: 4.3, 8.2_
  
  - [x] 3.2 Update commit message formatting
    - Modify commit message format to include instance number
    - Add issue_id reference in commit messages
    - Ensure format follows "spirit-{instance}(scope): spell description [#issue-id]"
    - _Requirements: 4.5_
  
  - [x] 3.3 Implement branch tracking per agent instance
    - Add get_active_branches() method to track branches by spirit_id
    - Store branch-to-agent mapping in WorkspaceManager
    - _Requirements: 8.2_

- [x] 4. Create Issue and AgentInstance data models
  - Define Issue dataclass with id, title, description, labels, priority, assigned_to, status, timestamps
  - Define AgentInstance dataclass with identifier, role, instance_number, skills, workspace, task lists, branches, status
  - Update Task dataclass to include id, agent_instance, issue_id, branch_name fields
  - Update RoleRequest to include count field for multiple agent instances
  - _Requirements: 1.4, 3.2, 4.1_

- [x] 5. Update Necromancer to support multiple agent instances
  - [x] 5.1 Modify summon_team() to create multiple instances per role
    - Parse RoleRequest count field to determine number of instances
    - Generate unique identifiers for each instance (e.g., frontend_spirit_1, frontend_spirit_2)
    - Register all instances with MessageBus
    - _Requirements: 1.4, 8.2_
  
  - [x] 5.2 Integrate IssueRouter into sprint execution
    - Instantiate IssueRouter in Necromancer.__init__()
    - Use IssueRouter for task assignment during execute_sprint()
    - Update task assignment messages to include specific agent_instance
    - _Requirements: 3.1, 4.1_

- [x] 6. Enhance Spirit Protocol message types
  - Add issue_assignment message type for IssueRouter → Agent communication
  - Add workload_query message type for load balancing
  - Add agent_status message type for tracking agent availability
  - Update AgentMessage payload to include issue_id and agent_instance fields
  - _Requirements: 7.1, 7.3_

- [x] 7. Update existing Spirit implementations
  - [x] 7.1 Update ArchitectSpirit with instance tracking
    - Add workload tracking to ArchitectSpirit
    - Update methods to use new BaseSpirit interface
    - _Requirements: 2.5_
  
  - [x] 7.2 Update ScrumMasterSpirit with routing capabilities
    - Integrate IssueRouter into ScrumMasterSpirit
    - Update decompose_job() to create Issue objects
    - Modify assign_tasks() to use automatic routing
    - _Requirements: 3.1, 3.2, 3.3_
  
  - [x] 7.3 Update development Spirits (Frontend, Backend, Database)
    - Add workload tracking to FrontendSpirit, BackendSpirit, DatabaseSpirit
    - Implement task assignment and completion handlers
    - Update branch creation to use new naming convention
    - _Requirements: 4.1, 4.2, 4.3_
  
  - [x] 7.4 Update QA and DevOps Spirits
    - Add workload tracking to QASpirit and DevOpsSpirit
    - Update test failure reporting to include issue_id
    - _Requirements: 5.4, 6.4_

- [x] 8. Create demo script with multiple agent instances
  - Create example job description requiring multiple frontend and backend agents
  - Demonstrate automatic issue routing to different agent instances
  - Show parallel work on different branches by multiple agents of same type
  - Display workload distribution across agent instances
  - _Requirements: 1.1, 1.4, 8.2_

- [x] 9. Add logging and monitoring
  - [x] 9.1 Implement detailed logging for issue routing decisions
    - Log keyword matches and routing rationale
    - Log load balancing decisions
    - _Requirements: 9.1, 9.2_
  
  - [x] 9.2 Add workload monitoring dashboard output
    - Display current workload per agent instance
    - Show active branches per agent
    - Track task completion rates
    - _Requirements: 3.5, 8.5_

- [x] 10. Write integration tests
  - [x] 10.1 Test issue routing with various keywords
    - Test Japanese and English keyword detection
    - Test routing to correct agent types
    - Test fallback to scrum_master for ambiguous issues
    - _Requirements: 3.1_
  
  - [x] 10.2 Test load balancing with multiple agents
    - Create scenario with 2 frontend and 2 backend agents
    - Assign multiple tasks and verify even distribution
    - Test handling of agent unavailability
    - _Requirements: 3.2, 8.2_
  
  - [x] 10.3 Test branch naming with multiple instances
    - Verify unique branch names for multiple agents
    - Test both instance-based and issue-based naming
    - Verify commit message formatting
    - _Requirements: 4.3, 4.5_
  
  - [x] 10.4 Test end-to-end workflow with parallel agents
    - Summon team with multiple instances
    - Route issues automatically
    - Execute sprint with parallel work
    - Verify all agents complete their tasks
    - _Requirements: 1.1, 3.1, 4.1, 8.2_
