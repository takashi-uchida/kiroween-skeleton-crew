"""Architect spirit - designs system architecture from the void."""

from typing import Optional
from .base_agent import BaseSpirit


class ArchitectSpirit(BaseSpirit):
    def __init__(self, *args, message_bus=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.message_bus = message_bus
    
    def receive_message(self, message) -> None:
        """Handle incoming Spirit Protocol messages."""
        if message.message_type == "task_assignment":
            self._handle_task_assignment(message)
        elif message.message_type == "task_completed":
            self._handle_task_completion(message)
    
    def _handle_task_assignment(self, message) -> None:
        """Process task assignment from Scrum Master."""
        task_id = message.payload.get("task_id")
        if task_id:
            self.assign_task(task_id)
            print(self.chant(f"Accepted design task: {task_id}"))
    
    def _handle_task_completion(self, message) -> None:
        """Mark task as complete and notify Scrum Master."""
        task_id = message.payload.get("task_id")
        if task_id:
            self.complete_task(task_id)
            print(self.chant(f"Completed design task: {task_id}"))
    
    def design_system(self, job_description: str) -> dict:
        """Analyze job description and create architecture blueprint."""
        return {
            "chant": self.chant("Sketching ethereal blueprints from the void..."),
            "tech_stack": self._divine_tech_stack(job_description),
            "architecture": self._design_architecture(job_description),
            "api_design": self._design_api(job_description),
        }

    def _divine_tech_stack(self, description: str) -> dict:
        """Divine the optimal technology stack."""
        desc_lower = description.lower()
        
        # Frontend detection
        frontend = "React"
        if "vue" in desc_lower:
            frontend = "Vue.js"
        elif "angular" in desc_lower:
            frontend = "Angular"
        
        # Backend detection
        backend = "Node.js + Express"
        if "python" in desc_lower or "fastapi" in desc_lower:
            backend = "Python + FastAPI"
        elif "django" in desc_lower:
            backend = "Python + Django"
        
        # Database detection
        database = "MongoDB"
        if "postgres" in desc_lower or "sql" in desc_lower:
            database = "PostgreSQL"
        elif "timescale" in desc_lower or "時系列" in description:
            database = "TimescaleDB"
        
        # Real-time detection
        realtime = None
        if "realtime" in desc_lower or "websocket" in desc_lower or "リアルタイム" in description:
            realtime = "Socket.io" if "node" in backend.lower() else "WebSocket"
        
        return {
            "frontend": frontend,
            "backend": backend,
            "database": database,
            "realtime": realtime,
        }

    def _design_architecture(self, description: str) -> dict:
        """Create high-level architecture design."""
        return {
            "pattern": "Microservices" if "iot" in description.lower() else "Monolithic",
            "layers": ["Presentation", "Business Logic", "Data Access"],
            "communication": "REST API + WebSocket" if "realtime" in description.lower() else "REST API",
        }

    def _design_api(self, description: str) -> list:
        """Design API endpoints based on requirements."""
        endpoints = []
        
        if "認証" in description or "auth" in description.lower():
            endpoints.extend([
                {"path": "/api/auth/login", "method": "POST"},
                {"path": "/api/auth/register", "method": "POST"},
            ])
        
        if "メッセージ" in description or "message" in description.lower() or "chat" in description.lower():
            endpoints.extend([
                {"path": "/api/messages", "method": "GET"},
                {"path": "/api/messages", "method": "POST"},
            ])
        
        if "sensor" in description.lower() or "センサー" in description or "iot" in description.lower():
            endpoints.extend([
                {"path": "/api/devices", "method": "GET"},
                {"path": "/api/sensor-data", "method": "POST"},
            ])
        
        return endpoints

    def create_documentation(self) -> str:
        """Generate architecture documentation."""
        return self.chant("Inscribing ancient architecture scrolls...")
