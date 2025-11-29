# Cost Tracker - Implementation Plan

- [ ] 1. Set up project structure and core data models
  - Create directory structure: `necrocode/cost_tracker/`
  - Define all data models in `models.py`: UsageRecord, ModelPricing, Budget, BudgetStatus, CostSummary, UsageTrend
  - Create exception classes in `exceptions.py`
  - Create `__init__.py` with proper exports
  - _Requirements: 1.1, 1.2_

- [ ] 2. Implement Cost Calculator
  - [ ] 2.1 Create CostCalculator class with default pricing
    - Implement `calculate_cost()` method for token-to-cost conversion
    - Add DEFAULT_PRICING dictionary with current model prices
    - Implement `add_model_pricing()` for custom models
    - _Requirements: 1.2_
  
  - [ ] 2.2 Write unit tests for cost calculations
    - Test cost calculation accuracy for each model
    - Test custom pricing addition
    - Test error handling for unknown models
    - _Requirements: 1.2_

- [ ] 3. Implement Usage Store
  - [ ] 3.1 Create UsageStore class with JSONL persistence
    - Implement `save_record()` with date-based file organization
    - Implement `get_records_by_job()` for job-level queries
    - Implement `get_records_by_period()` for time-range queries
    - Add helper methods for serialization/deserialization
    - _Requirements: 1.1_
  
  - [ ] 3.2 Write unit tests for storage operations
    - Test JSONL read/write operations
    - Test date-based file organization
    - Test query methods with various filters
    - Test concurrent access scenarios
    - _Requirements: 1.1_

- [ ] 4. Implement Usage Collector
  - [ ] 4.1 Create UsageCollector class
    - Implement `record_usage()` method
    - Integrate with CostCalculator for cost computation
    - Integrate with UsageStore for persistence
    - Add support for optional metadata (agent_instance, operation)
    - _Requirements: 1.1, 1.2_
  
  - [ ] 4.2 Write unit tests for usage collection
    - Test usage recording flow
    - Test integration with calculator and store
    - Test metadata handling
    - _Requirements: 1.1, 1.2_

- [ ] 5. Implement Budget Manager
  - [ ] 5.1 Create BudgetManager class
    - Implement `set_budget()` for budget configuration
    - Implement `check_budget()` for status checking
    - Implement `can_proceed()` for execution gating
    - Add `_get_period_range()` helper for date calculations
    - Implement alert callback mechanism
    - _Requirements: 1.3_
  
  - [ ] 5.2 Write unit tests for budget management
    - Test budget setting and retrieval
    - Test budget status calculations
    - Test alert triggering at threshold
    - Test hard limit enforcement
    - Test period range calculations
    - _Requirements: 1.3_

- [ ] 6. Implement Report Generator
  - [ ] 6.1 Create ReportGenerator class
    - Implement `generate_summary()` for cost aggregation
    - Implement `generate_trend()` for daily trends
    - Implement `forecast_monthly_cost()` for predictions
    - Add aggregation by model, job, and agent
    - _Requirements: 1.4_
  
  - [ ] 6.2 Write unit tests for report generation
    - Test summary generation with various data sets
    - Test trend calculation accuracy
    - Test forecast algorithm
    - Test aggregation logic
    - _Requirements: 1.4_

- [ ] 7. Implement Cost Tracker Service
  - [ ] 7.1 Create CostTracker main class
    - Initialize all components (calculator, store, collector, budget_manager, report_generator)
    - Implement `record_llm_usage()` as main entry point
    - Implement `get_job_cost()` for job-level queries
    - Implement `get_summary()` with default date handling
    - Add configuration loading from YAML
    - _Requirements: 1.1, 1.2, 1.3, 1.4_
  
  - [ ] 7.2 Write integration tests for Cost Tracker
    - Test end-to-end usage recording and retrieval
    - Test budget enforcement in realistic scenarios
    - Test report generation with real data
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [ ] 8. Integrate with Agent Runner
  - [ ] 8.1 Modify LLM client for cost tracking
    - Update `necrocode/agent_runner/llm_client.py` to accept CostTracker instance
    - Add cost tracking hooks after each LLM API call
    - Pass job_id and task_id context to cost tracker
    - Handle cases where cost tracker is not configured
    - _Requirements: 1.1, 1.2_
  
  - [ ] 8.2 Update Agent Runner configuration
    - Add cost_tracker initialization in RunnerOrchestrator
    - Update agent runner config to include cost tracker settings
    - _Requirements: 1.1, 1.2_
  
  - [ ] 8.3 Write integration tests for Agent Runner
    - Test LLM usage recording during task execution
    - Test cost accumulation across multiple tasks
    - _Requirements: 1.1, 1.2_

- [ ] 9. Implement CLI interface
  - [ ] 9.1 Create CLI commands in necrocode_cli.py
    - Implement `necrocode cost summary` command
    - Implement `necrocode cost by-job <job-id>` command
    - Implement `necrocode cost budget` subcommands (status, set)
    - Implement `necrocode cost report` with format options
    - Implement `necrocode cost forecast` command
    - Add date range parsing and formatting
    - _Requirements: 1.4_
  
  - [ ] 9.2 Write CLI tests
    - Test each CLI command with various arguments
    - Test output formatting (JSON, CSV, table)
    - Test error handling for invalid inputs
    - _Requirements: 1.4_

- [ ] 10. Create configuration and examples
  - [ ] 10.1 Create configuration file template
    - Create `config/cost-tracker.yaml` with default settings
    - Document all configuration options
    - Add environment variable substitution support
    - _Requirements: 1.2, 1.3_
  
  - [ ] 10.2 Create usage examples
    - Create `examples/cost_tracker_basic_usage.py`
    - Create `examples/cost_tracker_budget_management.py`
    - Create `examples/cost_tracker_reporting.py`
    - _Requirements: 1.1, 1.2, 1.3, 1.4_
  
  - [ ] 10.3 Create README documentation
    - Create `necrocode/cost_tracker/README.md` with overview
    - Document API usage and configuration
    - Add CLI command reference
    - Include integration examples
    - _Requirements: 1.1, 1.2, 1.3, 1.4_
