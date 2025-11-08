"""Issue Router - automatically routes issues to appropriate agents."""

import logging
from typing import Dict, List, Optional
from framework.communication.message_bus import MessageBus

# Configure logger for issue routing
logger = logging.getLogger(__name__)


class IssueRouter:
    """Routes issues to appropriate agents based on keyword analysis."""
    
    # Routing rules with keywords for each agent type
    ROUTING_RULES = {
        'frontend': [
            'ui', 'ux', 'component', 'style', 'css', 'html',
            'react', 'vue', 'angular', 'フロント', 'コンポーネント',
            'button', 'form', 'page', 'layout', 'responsive',
            'interface', 'view', 'screen', '画面', 'ボタン'
        ],
        'backend': [
            'api', 'endpoint', 'server', 'logic', 'service',
            'rest', 'graphql', 'バックエンド', 'サーバー',
            'authentication', 'authorization', 'middleware',
            'controller', 'route', 'handler', 'ルート', 'エンドポイント'
        ],
        'database': [
            'schema', 'query', 'migration', 'database', 'db',
            'sql', 'nosql', 'データベース', 'スキーマ',
            'table', 'collection', 'index', 'transaction',
            'model', 'entity', 'テーブル', 'クエリ'
        ],
        'qa': [
            'bug', 'test', 'quality', 'coverage', 'テスト',
            'バグ', 'unit test', 'integration', 'e2e',
            'assertion', 'mock', 'fixture', 'testing',
            '品質', 'カバレッジ', 'テストケース'
        ],
        'devops': [
            'deploy', 'docker', 'ci', 'cd', 'infrastructure',
            'デプロイ', 'インフラ', 'kubernetes', 'aws',
            'pipeline', 'container', 'orchestration',
            'deployment', 'build', 'release', 'ビルド'
        ],
        'architect': [
            'architecture', 'design', 'tech stack', '設計',
            'アーキテクチャ', 'pattern', 'structure',
            'scalability', 'performance', 'システム設計',
            'technical design', 'system design'
        ]
    }
    
    def __init__(self, message_bus: MessageBus):
        """Initialize IssueRouter with message bus reference.
        
        Args:
            message_bus: MessageBus instance for accessing registered spirits
        """
        self.message_bus = message_bus
    
    def route_issue(self, issue: Dict) -> Optional[str]:
        """Analyze issue and return appropriate agent identifier.
        
        Args:
            issue: Dictionary containing 'title' and 'description' keys
            
        Returns:
            Agent identifier (e.g., 'frontend_spirit_1') or None if no match
        """
        issue_id = issue.get('id', 'UNKNOWN')
        issue_title = issue.get('title', '')
        
        logger.info(f"🔍 Routing issue {issue_id}: '{issue_title}'")
        
        # Combine title and description for analysis
        content = f"{issue.get('title', '')} {issue.get('description', '')}".lower()
        
        # Analyze keywords to determine agent type
        agent_type = self._analyze_keywords(content)
        
        if not agent_type:
            logger.warning(f"⚠️ No agent type matched for issue {issue_id} - no keywords found")
            return None
        
        logger.info(f"✅ Issue {issue_id} matched agent type: {agent_type}")
        
        # Get available agent of the determined type
        agent_instance = self._get_agent_by_type(agent_type)
        
        if agent_instance:
            logger.info(f"🎯 Issue {issue_id} routed to: {agent_instance}")
        else:
            logger.warning(f"⚠️ No available agents of type {agent_type} for issue {issue_id}")
        
        return agent_instance
    
    def _analyze_keywords(self, content: str) -> Optional[str]:
        """Extract keywords and determine agent type.
        
        Args:
            content: Lowercase text to analyze
            
        Returns:
            Agent type string or None if no clear match
        """
        # Count keyword matches for each agent type
        match_scores = {}
        matched_keywords = {}
        
        for agent_type, keywords in self.ROUTING_RULES.items():
            matches = [keyword for keyword in keywords if keyword in content]
            score = len(matches)
            if score > 0:
                match_scores[agent_type] = score
                matched_keywords[agent_type] = matches
        
        # Log keyword analysis
        if match_scores:
            logger.debug(f"📊 Keyword match scores: {match_scores}")
            for agent_type, keywords in matched_keywords.items():
                logger.debug(f"   {agent_type}: {keywords[:5]}{'...' if len(keywords) > 5 else ''}")
            
            best_match = max(match_scores, key=match_scores.get)
            logger.info(f"🎯 Best match: {best_match} (score: {match_scores[best_match]}, keywords: {matched_keywords[best_match][:3]})")
            return best_match
        
        logger.debug("❌ No keyword matches found in content")
        return None
    
    def _get_agent_by_type(self, agent_type: str) -> Optional[str]:
        """Find available agent of specified type using load balancing.
        
        Args:
            agent_type: Type of agent to find (e.g., 'frontend', 'backend')
            
        Returns:
            Agent identifier or None if no agents are available
        """
        # Find all agents of the requested type
        agents = [s for s in self.message_bus.spirits if s.role == agent_type]
        
        if not agents:
            return None
        
        # Use load balancing to select the least-busy agent
        return self._balance_load(agents)
    
    def _balance_load(self, agents: List) -> str:
        """Select least-busy agent from list using workload tracking.
        
        Args:
            agents: List of BaseSpirit instances
            
        Returns:
            Identifier of the least-busy agent
        """
        # Log workload for all agents of this type
        workloads = {agent.identifier: agent.get_workload() for agent in agents}
        logger.info(f"⚖️ Load balancing across {len(agents)} agents:")
        for agent_id, workload in workloads.items():
            logger.info(f"   {agent_id}: {workload} active tasks")
        
        # Find agent with minimum workload
        least_busy_agent = min(agents, key=lambda agent: agent.get_workload())
        logger.info(f"✨ Selected least-busy agent: {least_busy_agent.identifier} ({least_busy_agent.get_workload()} tasks)")
        
        return least_busy_agent.identifier
