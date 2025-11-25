"""
LLM Client for Agent Runner

Handles communication with LLM services (OpenAI, etc.) for code generation.
Implements rate limiting, retry logic, and error handling.
"""

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import openai
from openai import OpenAI

from necrocode.agent_runner.exceptions import ImplementationError
from necrocode.agent_runner.models import CodeChange, LLMConfig, LLMResponse

logger = logging.getLogger(__name__)


class LLMClient:
    """LLMサービスとの通信クライアント"""
    
    def __init__(self, config: LLMConfig):
        """
        Args:
            config: LLM設定（APIキー、モデル名、エンドポイント等）
        """
        self.config = config
        self.client = OpenAI(api_key=config.api_key)
        self._last_request_time = 0
        self._min_request_interval = 0.1  # 最小リクエスト間隔（秒）
    
    def generate_code(
        self,
        prompt: str,
        workspace_path: Path,
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        """
        コードを生成
        
        Args:
            prompt: コード生成プロンプト
            workspace_path: ワークスペースパス
            max_tokens: 最大トークン数
            
        Returns:
            LLMResponse: LLMレスポンス
            
        Raises:
            ImplementationError: コード生成に失敗した場合
        """
        max_tokens = max_tokens or self.config.max_tokens
        
        # Log LLM request
        logger.info(
            "LLM code generation request",
            extra={
                "llm_model": self.config.model,
                "max_tokens": max_tokens,
                "prompt_length": len(prompt),
                "workspace_path": str(workspace_path)
            }
        )
        
        # レート制限対策
        self._wait_for_rate_limit()
        
        # リトライロジック
        max_retries = 3
        retry_delay = 1.0
        
        request_start_time = time.time()
        
        for attempt in range(max_retries):
            try:
                logger.debug(
                    f"LLM request attempt {attempt + 1}/{max_retries}",
                    extra={"attempt": attempt + 1, "max_retries": max_retries}
                )
                
                response = self.client.chat.completions.create(
                    model=self.config.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a code generation assistant. Generate code changes in JSON format."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    max_tokens=max_tokens,
                    temperature=0.2,
                    timeout=self.config.timeout_seconds
                )
                
                self._last_request_time = time.time()
                request_duration = time.time() - request_start_time
                
                content = response.choices[0].message.content
                
                # Log LLM response
                logger.info(
                    "LLM code generation response received",
                    extra={
                        "llm_model": response.model,
                        "tokens_used": response.usage.total_tokens,
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "request_duration_seconds": request_duration,
                        "response_length": len(content),
                        "attempt": attempt + 1
                    }
                )
                
                # JSONレスポンスをパース
                try:
                    data = json.loads(content)
                    code_changes = [
                        CodeChange(**change) for change in data.get("code_changes", [])
                    ]
                    explanation = data.get("explanation", "")
                    
                    logger.debug(
                        "LLM response parsed successfully",
                        extra={
                            "code_changes_count": len(code_changes),
                            "explanation_length": len(explanation)
                        }
                    )
                    
                except json.JSONDecodeError as e:
                    logger.error(
                        "Failed to parse LLM response as JSON",
                        extra={
                            "error": str(e),
                            "response_preview": content[:500]
                        }
                    )
                    raise ImplementationError(f"Failed to parse LLM response as JSON: {e}")
                except (KeyError, TypeError) as e:
                    logger.error(
                        "Invalid LLM response format",
                        extra={
                            "error": str(e),
                            "response_preview": content[:500]
                        }
                    )
                    raise ImplementationError(f"Invalid LLM response format: {e}")
                
                return LLMResponse(
                    code_changes=code_changes,
                    explanation=explanation,
                    model=response.model,
                    tokens_used=response.usage.total_tokens
                )
                
            except openai.RateLimitError as e:
                # レート制限エラー - 指数バックオフでリトライ
                logger.warning(
                    "LLM rate limit error",
                    extra={
                        "attempt": attempt + 1,
                        "max_retries": max_retries,
                        "error": str(e)
                    }
                )
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    logger.info(f"Retrying after {wait_time}s due to rate limit")
                    time.sleep(wait_time)
                    continue
                logger.error(f"Rate limit exceeded after {max_retries} retries")
                raise ImplementationError(f"Rate limit exceeded after {max_retries} retries: {e}")
                
            except openai.APITimeoutError as e:
                # タイムアウトエラー - リトライ
                logger.warning(
                    "LLM request timeout",
                    extra={
                        "attempt": attempt + 1,
                        "max_retries": max_retries,
                        "timeout_seconds": self.config.timeout_seconds,
                        "error": str(e)
                    }
                )
                if attempt < max_retries - 1:
                    logger.info(f"Retrying after {retry_delay}s due to timeout")
                    time.sleep(retry_delay)
                    continue
                logger.error(f"LLM request timeout after {max_retries} retries")
                raise ImplementationError(f"LLM request timeout after {max_retries} retries: {e}")
                
            except openai.APIConnectionError as e:
                # 接続エラー - リトライ
                logger.warning(
                    "LLM connection error",
                    extra={
                        "attempt": attempt + 1,
                        "max_retries": max_retries,
                        "error": str(e)
                    }
                )
                if attempt < max_retries - 1:
                    logger.info(f"Retrying after {retry_delay}s due to connection error")
                    time.sleep(retry_delay)
                    continue
                logger.error(f"LLM connection error after {max_retries} retries")
                raise ImplementationError(f"LLM connection error after {max_retries} retries: {e}")
                
            except openai.APIError as e:
                # その他のAPIエラー
                logger.error(
                    "LLM API error",
                    extra={"error": str(e), "error_type": type(e).__name__}
                )
                raise ImplementationError(f"LLM API error: {e}")
                
            except Exception as e:
                # 予期しないエラー
                logger.error(
                    "Unexpected error during code generation",
                    extra={"error": str(e), "error_type": type(e).__name__},
                    exc_info=True
                )
                raise ImplementationError(f"Unexpected error during code generation: {e}")
        
        logger.error("Failed to generate code after all retries")
        raise ImplementationError("Failed to generate code after all retries")
    
    def _wait_for_rate_limit(self) -> None:
        """レート制限のための待機"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
