# Notification System - Design Document

## Overview

The Notification System provides a flexible, multi-channel notification framework for NecroCode events. It enables real-time alerts for job lifecycle events, task completions, PR activities, and error conditions across multiple communication platforms (Slack, Email, Discord, Webhook, SMS).

**Design Philosophy**: The system follows a publisher-subscriber pattern with pluggable channel adapters, template-based message formatting, and event filtering capabilities. It integrates seamlessly with existing NecroCode components (Task Registry, Dispatcher, Review PR Service) to capture and broadcast relevant events.

## Architecture

### High-Level Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    NecroCode Components                      │
│  (Task Registry, Dispatcher, Agent Runner, PR Service)      │
└────────────────────┬────────────────────────────────────────┘
                     │ Events
                     ▼
         ┌───────────────────────┐
         │  NotificationManager  │
         │  - Event routing      │
         │  - Filter evaluation  │
         │  - Channel selection  │
         └───────────┬───────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌─────────────────┐
│ ChannelRegistry │    │ TemplateEngine  │
│ - Channel mgmt  │    │ - Format msgs   │
│ - Config load   │    │ - Interpolation │
└────────┬────────┘    └─────────────────┘
         │
    ┌────┴────┬────────┬────────┬────────┐
    ▼         ▼        ▼        ▼        ▼
┌────────┐ ┌──────┐ ┌─────────┐ ┌────────┐ ┌──────┐
│ Slack  │ │Email │ │ Discord │ │Webhook │ │ SMS  │
│Channel │ │Chan. │ │ Channel │ │Channel │ │Chan. │
└────────┘ └──────┘ └─────────┘ └────────┘ └──────┘
```

### Component Responsibilities

#### 1. NotificationManager
**Purpose**: Central coordinator for all notification activities

**Responsibilities**:
- Receive events from NecroCode components
- Evaluate event filters and routing rules
- Select appropriate channels based on event type and configuration
- Coordinate message formatting and delivery
- Handle delivery failures and retries
- Maintain delivery metrics

**Key Methods**:
```python
def notify(event: NotificationEvent) -> List[DeliveryResult]
def register_channel(channel: NotificationChannel) -> None
def update_config(config: NotificationConfig) -> None
def get_delivery_status(notification_id: str) -> DeliveryStatus
```

#### 2. NotificationChannel (Abstract Base)
**Purpose**: Interface for all notification delivery mechanisms

**Responsibilities**:
- Implement channel-specific delivery logic
- Handle authentication and connection management
- Format messages according to channel requirements
- Report delivery success/failure
- Support async delivery where applicable

**Key Methods**:
```python
async def send(message: FormattedMessage) -> DeliveryResult
def validate_config() -> bool
def health_check() -> HealthStatus
```

#### 3. TemplateEngine
**Purpose**: Generate formatted messages from event data

**Responsibilities**:
- Load and cache message templates
- Interpolate event data into templates
- Support multiple output formats (Markdown, HTML, JSON)
- Handle localization (Japanese/English)
- Validate template syntax

**Key Methods**:
```python
def render(template_name: str, context: dict) -> FormattedMessage
def register_template(name: str, template: Template) -> None
def list_templates() -> List[str]
```

#### 4. EventFilter
**Purpose**: Determine which events should trigger notifications

**Responsibilities**:
- Evaluate filter expressions against events
- Support complex filtering logic (AND/OR/NOT)
- Filter by event type, severity, source, metadata
- Cache filter evaluation results

**Key Methods**:
```python
def matches(event: NotificationEvent, filter_expr: FilterExpression) -> bool
def compile_filter(filter_config: dict) -> FilterExpression
```

#### 5. ChannelRegistry
**Purpose**: Manage available notification channels

**Responsibilities**:
- Register and configure channels
- Validate channel configurations
- Enable/disable channels dynamically
- Provide channel discovery

## Data Models

### NotificationEvent
```python
@dataclass
class NotificationEvent:
    event_id: str
    event_type: EventType  # job_started, job_completed, job_failed, etc.
    timestamp: datetime
    source: str  # dispatcher, agent_runner, pr_service, etc.
    severity: Severity  # info, warning, error, critical
    title: str
    description: str
    metadata: Dict[str, Any]  # job_id, task_id, pr_url, error_details, etc.
    links: List[Link]  # dashboard, PR, logs
```

### NotificationConfig
```python
@dataclass
class NotificationConfig:
    channels: Dict[str, ChannelConfig]
    event_routing: List[RoutingRule]
    global_filters: List[FilterExpression]
    retry_policy: RetryPolicy
    rate_limits: Dict[str, RateLimit]
```

### ChannelConfig
```python
@dataclass
class ChannelConfig:
    channel_type: str  # slack, email, discord, webhook, sms
    enabled: bool
    credentials: Dict[str, str]  # webhook_url, api_key, etc.
    events: List[EventType]  # Which events to send
    filters: List[FilterExpression]
    template_overrides: Dict[str, str]
    retry_config: RetryConfig
```

### FormattedMessage
```python
@dataclass
class FormattedMessage:
    format: MessageFormat  # slack_blocks, html, markdown, json
    content: Union[str, dict]
    attachments: List[Attachment]
    metadata: Dict[str, Any]
```

### DeliveryResult
```python
@dataclass
class DeliveryResult:
    notification_id: str
    channel: str
    success: bool
    timestamp: datetime
    error: Optional[str]
    retry_count: int
    delivery_time_ms: int
```

## Channel Implementations

### SlackChannel
**Features**:
- Slack Blocks API for rich formatting
- Thread support for related notifications
- Emoji and reaction support
- File attachments
- Interactive buttons (future)

**Configuration**:
```yaml
slack:
  enabled: true
  webhook_url: ${SLACK_WEBHOOK_URL}
  channel: "#necrocode"
  username: "NecroCode Bot"
  icon_emoji: ":robot_face:"
  events:
    - job_completed
    - job_failed
    - pr_created
    - pr_merged
  filters:
    - severity: [warning, error, critical]
```

**Message Format**: Slack Blocks API with sections, fields, and context blocks

### EmailChannel
**Features**:
- HTML + plain text multipart messages
- SMTP with TLS support
- Multiple recipients (to, cc, bcc)
- Attachment support
- Email templates with CSS

**Configuration**:
```yaml
email:
  enabled: true
  smtp_server: smtp.gmail.com
  smtp_port: 587
  use_tls: true
  from: necrocode@example.com
  username: ${EMAIL_USERNAME}
  password: ${EMAIL_PASSWORD}
  to:
    - team@example.com
    - alerts@example.com
  events:
    - job_failed
    - task_failed
```

**Message Format**: HTML with inline CSS, plain text fallback

### DiscordChannel
**Features**:
- Discord Embed format
- Webhook-based delivery
- Color-coded messages by severity
- Thumbnail and image support
- Footer with timestamps

**Configuration**:
```yaml
discord:
  enabled: true
  webhook_url: ${DISCORD_WEBHOOK_URL}
  username: "NecroCode"
  avatar_url: "https://example.com/necrocode-avatar.png"
  events:
    - job_completed
    - job_failed
    - pr_created
```

**Message Format**: Discord Embed with title, description, fields, color

### WebhookChannel
**Features**:
- Generic HTTP POST delivery
- Custom headers and authentication
- JSON payload
- Configurable retry logic
- Signature verification (HMAC)

**Configuration**:
```yaml
webhook:
  enabled: true
  url: https://api.example.com/notifications
  method: POST
  headers:
    Authorization: "Bearer ${WEBHOOK_TOKEN}"
    Content-Type: "application/json"
  signature_secret: ${WEBHOOK_SECRET}
  events:
    - "*"  # All events
```

**Message Format**: JSON with event data and metadata

### SMSChannel (Optional)
**Features**:
- Twilio integration
- SMS delivery for critical alerts
- Character limit handling
- Cost tracking

**Configuration**:
```yaml
sms:
  enabled: false
  provider: twilio
  account_sid: ${TWILIO_ACCOUNT_SID}
  auth_token: ${TWILIO_AUTH_TOKEN}
  from_number: "+1234567890"
  to_numbers:
    - "+819012345678"
  events:
    - job_failed
  filters:
    - severity: [critical]
```

## Event Types and Routing

### Supported Event Types

| Event Type | Description | Default Channels |
|------------|-------------|------------------|
| `job_started` | Job execution begins | Slack, Discord |
| `job_completed` | Job finishes successfully | Slack, Email, Discord |
| `job_failed` | Job fails with error | Slack, Email, Discord, SMS |
| `task_started` | Individual task begins | None (opt-in) |
| `task_completed` | Task finishes successfully | Slack, Discord |
| `task_failed` | Task fails with error | Slack, Email |
| `pr_created` | Pull request created | Slack, Discord |
| `pr_merged` | Pull request merged | Slack, Email |
| `pr_closed` | Pull request closed without merge | Slack |
| `agent_error` | Agent runtime error | Slack, Email |
| `system_alert` | System-level alert | Email, SMS |

### Routing Rules

Routing rules determine which channels receive which events:

```python
@dataclass
class RoutingRule:
    name: str
    event_types: List[EventType]
    channels: List[str]
    filters: List[FilterExpression]
    priority: int  # Higher priority rules evaluated first
```

**Example Routing Configuration**:
```yaml
event_routing:
  - name: "Critical Failures"
    event_types: [job_failed, agent_error]
    channels: [slack, email, sms]
    filters:
      - severity: critical
    priority: 100
  
  - name: "Success Notifications"
    event_types: [job_completed, pr_merged]
    channels: [slack, discord]
    priority: 50
  
  - name: "PR Activity"
    event_types: [pr_created, pr_merged, pr_closed]
    channels: [slack]
    filters:
      - metadata.repo: "necrocode-main"
    priority: 75
```

## Message Templates

### Template Structure

Templates are stored in `templates/notifications/` with the following structure:

```
templates/notifications/
├── slack/
│   ├── job_completed.json
│   ├── job_failed.json
│   └── pr_created.json
├── email/
│   ├── job_completed.html
│   ├── job_failed.html
│   └── base.html
├── discord/
│   ├── job_completed.json
│   └── job_failed.json
└── sms/
    └── job_failed.txt
```

### Template Variables

All templates have access to:
- `event`: The NotificationEvent object
- `timestamp`: Formatted timestamp
- `severity_color`: Color code based on severity
- `dashboard_url`: Link to dashboard
- `metadata`: Event-specific metadata

### Example: Slack Job Completed Template

```json
{
  "blocks": [
    {
      "type": "header",
      "text": {
        "type": "plain_text",
        "text": "✅ Job Completed: {{ event.title }}"
      }
    },
    {
      "type": "section",
      "fields": [
        {
          "type": "mrkdwn",
          "text": "*Job ID:*\n{{ event.metadata.job_id }}"
        },
        {
          "type": "mrkdwn",
          "text": "*Duration:*\n{{ event.metadata.duration }}"
        },
        {
          "type": "mrkdwn",
          "text": "*Tasks:*\n{{ event.metadata.tasks_completed }}/{{ event.metadata.tasks_total }}"
        },
        {
          "type": "mrkdwn",
          "text": "*Status:*\n{{ event.metadata.status }}"
        }
      ]
    },
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "{{ event.description }}"
      }
    },
    {
      "type": "actions",
      "elements": [
        {
          "type": "button",
          "text": {
            "type": "plain_text",
            "text": "View Dashboard"
          },
          "url": "{{ dashboard_url }}"
        }
      ]
    },
    {
      "type": "context",
      "elements": [
        {
          "type": "mrkdwn",
          "text": "{{ timestamp }} | Source: {{ event.source }}"
        }
      ]
    }
  ]
}
```

## Error Handling

### Retry Strategy

**Exponential Backoff**: Failed deliveries are retried with exponential backoff

```python
@dataclass
class RetryPolicy:
    max_retries: int = 3
    initial_delay_ms: int = 1000
    max_delay_ms: int = 30000
    backoff_multiplier: float = 2.0
    retry_on_errors: List[str] = ["timeout", "connection_error", "rate_limit"]
```

### Failure Handling

1. **Immediate Failures**: Log error, attempt retry if configured
2. **Persistent Failures**: Store in failed delivery queue for manual review
3. **Channel Degradation**: Automatically disable channels with high failure rates
4. **Fallback Channels**: Route to alternative channels if primary fails

### Circuit Breaker

Implement circuit breaker pattern for unreliable channels:

```python
@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5  # Failures before opening circuit
    timeout_seconds: int = 60  # Time before attempting reset
    success_threshold: int = 2  # Successes needed to close circuit
```

## Integration Points

### Task Registry Integration

```python
# In task_registry/task_registry.py
def update_task_state(self, task_id: str, state: TaskState):
    # Existing logic...
    
    # Emit notification event
    if state == TaskState.COMPLETED:
        notification_manager.notify(NotificationEvent(
            event_type=EventType.TASK_COMPLETED,
            source="task_registry",
            title=f"Task {task_id} completed",
            metadata={"task_id": task_id, "spec_id": spec_id}
        ))
```

### Dispatcher Integration

```python
# In dispatcher/dispatcher_core.py
def dispatch_task(self, task: Task):
    notification_manager.notify(NotificationEvent(
        event_type=EventType.JOB_STARTED,
        source="dispatcher",
        title=f"Job {task.job_id} started",
        metadata={"job_id": task.job_id, "task_count": len(tasks)}
    ))
```

### Review PR Service Integration

```python
# In review_pr_service/pr_service.py
def create_pull_request(self, pr_data: PRData):
    result = self.git_client.create_pr(pr_data)
    
    notification_manager.notify(NotificationEvent(
        event_type=EventType.PR_CREATED,
        source="pr_service",
        title=f"PR created: {pr_data.title}",
        metadata={"pr_url": result.url, "pr_number": result.number},
        links=[Link(url=result.url, text="View PR")]
    ))
```

## Configuration Management

### Configuration File Location

Primary: `config/notifications.yaml`
Override: `.kiro/notifications.yaml` (workspace-specific)

### Environment Variables

Sensitive credentials loaded from environment:
- `SLACK_WEBHOOK_URL`
- `EMAIL_USERNAME`, `EMAIL_PASSWORD`
- `DISCORD_WEBHOOK_URL`
- `WEBHOOK_TOKEN`, `WEBHOOK_SECRET`
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`

### Dynamic Configuration Updates

Support runtime configuration updates without restart:

```python
notification_manager.reload_config()
notification_manager.enable_channel("slack")
notification_manager.disable_channel("sms")
notification_manager.update_routing_rules(new_rules)
```

## Performance Considerations

### Async Delivery

All channel deliveries are asynchronous to avoid blocking main execution:

```python
async def notify(self, event: NotificationEvent):
    tasks = []
    for channel in self.select_channels(event):
        tasks.append(channel.send_async(event))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

### Rate Limiting

Implement per-channel rate limiting to avoid API throttling:

```python
@dataclass
class RateLimit:
    max_requests: int  # Maximum requests
    window_seconds: int  # Time window
    burst_size: int  # Burst allowance
```

### Message Batching

For high-volume events, support message batching:

```python
@dataclass
class BatchConfig:
    enabled: bool = False
    max_batch_size: int = 10
    max_wait_seconds: int = 30
    batch_by: str = "event_type"  # or "channel"
```

## Testing Strategy

### Unit Tests
- Channel implementations (mock HTTP/SMTP)
- Template rendering
- Event filtering logic
- Retry mechanisms

### Integration Tests
- End-to-end notification flow
- Multi-channel delivery
- Configuration loading
- Error recovery

### Manual Testing
- Real Slack/Discord/Email delivery
- Template rendering verification
- Rate limit behavior
- Circuit breaker functionality

## Security Considerations

### Credential Management
- Never log credentials
- Use environment variables for secrets
- Support credential rotation
- Encrypt stored credentials

### Message Content
- Sanitize user input in templates
- Avoid exposing sensitive data in notifications
- Support PII filtering
- Audit notification content

### Webhook Security
- HMAC signature verification
- IP allowlisting (optional)
- TLS/HTTPS only
- Request validation

## Monitoring and Observability

### Metrics to Track
- Delivery success/failure rates per channel
- Average delivery time
- Retry counts
- Circuit breaker state changes
- Event processing latency

### Logging
- All delivery attempts (success/failure)
- Configuration changes
- Channel health status
- Rate limit hits

### Dashboards
- Real-time delivery status
- Channel health overview
- Event volume trends
- Error rate alerts

## Future Enhancements

1. **Interactive Notifications**: Slack/Discord buttons for actions (approve PR, retry job)
2. **Notification Preferences**: Per-user notification settings
3. **Digest Mode**: Batch notifications into periodic summaries
4. **Mobile Push**: iOS/Android push notifications
5. **Notification History**: Web UI for viewing past notifications
6. **A/B Testing**: Test different message formats
7. **Analytics**: Track notification engagement metrics

## Design Decisions and Rationales

### Decision 1: Publisher-Subscriber Pattern
**Rationale**: Decouples event sources from notification channels, allowing easy addition of new channels without modifying existing code.

### Decision 2: Template-Based Formatting
**Rationale**: Separates message content from delivery logic, enables non-developers to customize messages, supports localization.

### Decision 3: Async Delivery
**Rationale**: Prevents notification failures from blocking main application flow, improves performance under high load.

### Decision 4: Per-Channel Configuration
**Rationale**: Different channels have different requirements and use cases; fine-grained control improves flexibility.

### Decision 5: Event Filtering at Multiple Levels
**Rationale**: Global filters reduce noise, channel-specific filters allow customization, routing rules provide flexibility.

### Decision 6: Circuit Breaker Pattern
**Rationale**: Protects system from cascading failures when notification channels are unavailable, improves resilience.

## Dependencies

- `aiohttp`: Async HTTP client for webhooks
- `aiosmtplib`: Async SMTP client for email
- `jinja2`: Template engine
- `pyyaml`: Configuration parsing
- `twilio` (optional): SMS delivery
- Existing NecroCode components: Task Registry, Dispatcher, PR Service
