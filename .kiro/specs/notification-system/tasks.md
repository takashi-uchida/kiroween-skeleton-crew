# Notification System - Implementation Tasks

- [ ] 1. Set up project structure and core interfaces
  - Create `necrocode/notification_system/` directory structure
  - Define base `NotificationChannel` abstract class with `send()`, `validate_config()`, `health_check()` methods
  - Define `NotificationEvent`, `NotificationConfig`, `ChannelConfig`, `FormattedMessage`, `DeliveryResult` dataclasses in `models.py`
  - Create `exceptions.py` with custom exception classes (`NotificationError`, `ChannelError`, `TemplateError`, `DeliveryError`)
  - Create `__init__.py` with module exports
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [ ] 2. Implement template engine
  - [ ] 2.1 Create `TemplateEngine` class with Jinja2 integration
    - Implement `render(template_name, context)` method for template rendering
    - Implement `register_template()` and `list_templates()` methods
    - Add template caching mechanism
    - Support multiple output formats (Markdown, HTML, JSON)
    - _Requirements: 1.4_
  
  - [ ] 2.2 Create default message templates
    - Create `templates/notifications/slack/` directory with job_completed.json, job_failed.json, pr_created.json templates
    - Create `templates/notifications/email/` directory with HTML templates and base.html
    - Create `templates/notifications/discord/` directory with embed templates
    - Create `templates/notifications/sms/` directory with plain text templates
    - Implement template variable interpolation for event data
    - _Requirements: 1.4_

- [ ] 3. Implement event filtering system
  - [ ] 3.1 Create `EventFilter` class
    - Implement `matches(event, filter_expr)` method for filter evaluation
    - Implement `compile_filter(filter_config)` to parse filter expressions
    - Support filtering by event_type, severity, source, metadata fields
    - Add support for complex logic (AND/OR/NOT operations)
    - _Requirements: 1.3_
  
  - [ ] 3.2 Create `RoutingRule` dataclass and routing logic
    - Implement routing rule evaluation in priority order
    - Add channel selection based on event type and filters
    - Implement global filter application
    - _Requirements: 1.3_

- [ ] 4. Implement Slack channel
  - [ ] 4.1 Create `SlackChannel` class extending `NotificationChannel`
    - Implement `send()` method using Slack Blocks API
    - Add webhook URL validation in `validate_config()`
    - Implement `health_check()` with test message capability
    - Support thread replies for related notifications
    - Handle rate limiting and retries
    - _Requirements: 1.1, 1.4_
  
  - [ ]* 4.2 Write unit tests for SlackChannel
    - Test message formatting with mock webhook
    - Test error handling and retries
    - Test configuration validation
    - _Requirements: 1.1_

- [ ] 5. Implement Email channel
  - [ ] 5.1 Create `EmailChannel` class extending `NotificationChannel`
    - Implement `send()` method with aiosmtplib for async SMTP
    - Support HTML + plain text multipart messages
    - Add SMTP configuration validation (server, port, TLS, credentials)
    - Implement authentication with username/password
    - Support multiple recipients (to, cc, bcc)
    - _Requirements: 1.1, 1.4_
  
  - [ ]* 5.2 Write unit tests for EmailChannel
    - Test email formatting and multipart messages
    - Test SMTP connection and authentication
    - Test error handling for failed deliveries
    - _Requirements: 1.1_

- [ ] 6. Implement Discord channel
  - [ ] 6.1 Create `DiscordChannel` class extending `NotificationChannel`
    - Implement `send()` method using Discord webhook API
    - Format messages as Discord Embeds with color coding by severity
    - Add webhook URL validation
    - Support thumbnail and image attachments
    - Implement rate limiting compliance
    - _Requirements: 1.1, 1.4_
  
  - [ ]* 6.2 Write unit tests for DiscordChannel
    - Test embed formatting with mock webhook
    - Test color coding by severity
    - Test error handling
    - _Requirements: 1.1_

- [ ] 7. Implement Webhook channel
  - [ ] 7.1 Create `WebhookChannel` class extending `NotificationChannel`
    - Implement `send()` method with aiohttp for async HTTP POST
    - Support custom headers and authentication
    - Implement HMAC signature generation for request verification
    - Add configurable retry logic
    - Support JSON payload formatting
    - _Requirements: 1.1, 1.4_
  
  - [ ]* 7.2 Write unit tests for WebhookChannel
    - Test HTTP POST with custom headers
    - Test HMAC signature generation
    - Test retry logic on failures
    - _Requirements: 1.1_

- [ ] 8. Implement SMS channel (optional)
  - [ ] 8.1 Create `SMSChannel` class extending `NotificationChannel`
    - Implement `send()` method with Twilio integration
    - Add Twilio credentials validation (account_sid, auth_token)
    - Implement character limit handling and truncation
    - Add cost tracking for SMS deliveries
    - Support multiple recipient phone numbers
    - _Requirements: 1.1, 1.4_
  
  - [ ]* 8.2 Write unit tests for SMSChannel
    - Test Twilio API integration with mock client
    - Test character limit handling
    - Test error handling for failed SMS
    - _Requirements: 1.1_

- [ ] 9. Implement ChannelRegistry
  - Create `ChannelRegistry` class for managing notification channels
  - Implement `register_channel()` and `get_channel()` methods
  - Add channel discovery and listing functionality
  - Implement dynamic enable/disable of channels
  - Add channel health monitoring
  - _Requirements: 1.1, 1.3_

- [ ] 10. Implement NotificationManager
  - [ ] 10.1 Create core NotificationManager class
    - Implement `notify(event)` method as main entry point
    - Add event routing logic using RoutingRule evaluation
    - Implement channel selection based on event type and filters
    - Coordinate message formatting via TemplateEngine
    - Implement async delivery to multiple channels
    - Add delivery result aggregation
    - _Requirements: 1.2, 1.3, 1.4_
  
  - [ ] 10.2 Add retry and error handling
    - Implement exponential backoff retry logic with RetryPolicy
    - Add circuit breaker pattern for unreliable channels
    - Implement failed delivery queue for manual review
    - Add fallback channel routing on primary failure
    - Log all delivery attempts and results
    - _Requirements: 1.2, 1.3_
  
  - [ ] 10.3 Add rate limiting
    - Implement per-channel rate limiting with token bucket algorithm
    - Add rate limit configuration (max_requests, window_seconds, burst_size)
    - Track rate limit usage per channel
    - Queue messages when rate limit exceeded
    - _Requirements: 1.3_

- [ ] 11. Implement configuration management
  - [ ] 11.1 Create `ConfigLoader` class
    - Implement YAML configuration file loading from `config/notifications.yaml`
    - Support workspace-specific overrides from `.kiro/notifications.yaml`
    - Load sensitive credentials from environment variables
    - Validate configuration schema
    - _Requirements: 1.3_
  
  - [ ] 11.2 Add dynamic configuration updates
    - Implement `reload_config()` method for runtime updates
    - Add `enable_channel()` and `disable_channel()` methods
    - Implement `update_routing_rules()` for dynamic rule changes
    - Emit configuration change events
    - _Requirements: 1.3_

- [ ] 12. Integrate with Task Registry
  - Modify `necrocode/task_registry/task_registry.py` to emit notification events
  - Add event emission in `update_task_state()` for COMPLETED and FAILED states
  - Add event emission in `create_taskset()` for job started
  - Include task_id, spec_id, and relevant metadata in events
  - _Requirements: 1.2_

- [ ] 13. Integrate with Dispatcher
  - Modify `necrocode/dispatcher/dispatcher_core.py` to emit notification events
  - Add event emission in `dispatch_task()` for job started
  - Add event emission in task completion/failure handlers
  - Include job_id, task_count, and execution metadata in events
  - _Requirements: 1.2_

- [ ] 14. Integrate with Review PR Service
  - Modify `necrocode/review_pr_service/pr_service.py` to emit notification events
  - Add event emission in `create_pull_request()` for PR created
  - Add event emission for PR merged and PR closed events
  - Include pr_url, pr_number, and PR metadata in events
  - Add links to PR in notification events
  - _Requirements: 1.2_

- [ ] 15. Create example usage scripts
  - [ ] 15.1 Create `examples/notification_basic_usage.py`
    - Demonstrate basic notification sending to Slack
    - Show configuration loading
    - Demonstrate event creation and delivery
    - _Requirements: 1.1, 1.2, 1.4_
  
  - [ ] 15.2 Create `examples/notification_multi_channel.py`
    - Demonstrate sending to multiple channels simultaneously
    - Show routing rule configuration
    - Demonstrate filter usage
    - _Requirements: 1.1, 1.3_
  
  - [ ] 15.3 Create `examples/notification_custom_template.py`
    - Demonstrate custom template registration
    - Show template rendering with custom data
    - Demonstrate template overrides per channel
    - _Requirements: 1.4_

- [ ] 16. Create comprehensive documentation
  - Create `necrocode/notification_system/README.md` with overview and usage guide
  - Document all configuration options with examples
  - Document event types and their metadata
  - Document template variables and formatting
  - Add troubleshooting section for common issues
  - Document integration points with other NecroCode components
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [ ]* 17. Write integration tests
  - Create `tests/test_notification_integration.py` for end-to-end flows
  - Test multi-channel delivery with real event data
  - Test configuration loading and validation
  - Test error recovery and retry mechanisms
  - Test rate limiting behavior
  - Test circuit breaker functionality
  - _Requirements: 1.1, 1.2, 1.3_
