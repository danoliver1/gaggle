"""LLM provider integrations for Gaggle agents."""

import asyncio
import aiohttp
import json
from typing import Dict, List, Any, Optional, AsyncGenerator
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import structlog

from ..config.models import ModelConfig, ModelTier
from ..config.settings import settings
from ..utils.logging import get_logger


logger = structlog.get_logger(__name__)


class BaseLLMProvider(ABC):
    """Base class for LLM providers."""
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self.logger = get_logger(f"llm_provider_{config.tier.value}")
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Rate limiting
        self.request_count = 0
        self.last_reset_time = datetime.now()
        self.rate_limit_per_minute = 60  # Default rate limit
        
        # Token usage tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=120)  # 2 minute timeout
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    @abstractmethod
    async def generate_response(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate response from LLM."""
        pass
    
    @abstractmethod
    async def generate_streaming_response(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Generate streaming response from LLM."""
        pass
    
    async def _check_rate_limit(self):
        """Check and enforce rate limiting."""
        now = datetime.now()
        
        # Reset counter every minute
        if (now - self.last_reset_time).total_seconds() >= 60:
            self.request_count = 0
            self.last_reset_time = now
        
        # Check rate limit
        if self.request_count >= self.rate_limit_per_minute:
            wait_time = 60 - (now - self.last_reset_time).total_seconds()
            if wait_time > 0:
                self.logger.warning(
                    "rate_limit_exceeded",
                    provider=self.__class__.__name__,
                    wait_time=wait_time
                )
                await asyncio.sleep(wait_time)
                self.request_count = 0
                self.last_reset_time = datetime.now()
        
        self.request_count += 1
    
    def _update_token_usage(self, input_tokens: int, output_tokens: int):
        """Update token usage tracking."""
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        
        cost = (
            input_tokens * self.config.cost_per_input_token +
            output_tokens * self.config.cost_per_output_token
        )
        self.total_cost += cost
        
        self.logger.info(
            "token_usage_updated",
            provider=self.__class__.__name__,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            total_cost=self.total_cost
        )
    
    def get_usage_metrics(self) -> Dict[str, Any]:
        """Get usage metrics for this provider."""
        return {
            "provider": self.__class__.__name__,
            "model_tier": self.config.tier.value,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "total_cost": self.total_cost,
            "request_count": self.request_count,
            "average_cost_per_request": self.total_cost / max(1, self.request_count)
        }


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude API provider."""
    
    def __init__(self, config: ModelConfig, api_key: Optional[str] = None):
        super().__init__(config)
        self.api_key = api_key or settings.anthropic_api_key
        self.base_url = "https://api.anthropic.com/v1"
        self.rate_limit_per_minute = 50  # Anthropic rate limit
        
        if not self.api_key:
            raise ValueError("Anthropic API key is required")
    
    async def generate_response(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate response from Anthropic Claude."""
        
        await self._check_rate_limit()
        
        # Prepare request
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        request_data = {
            "model": self.config.model_id,
            "messages": messages,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            **kwargs
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/messages",
                json=request_data,
                headers=headers
            ) as response:
                
                response.raise_for_status()
                result = await response.json()
                
                # Extract response content
                content = result.get("content", [])
                response_text = ""
                if content and isinstance(content, list):
                    response_text = content[0].get("text", "")
                
                # Track token usage
                usage = result.get("usage", {})
                input_tokens = usage.get("input_tokens", 0)
                output_tokens = usage.get("output_tokens", 0)
                self._update_token_usage(input_tokens, output_tokens)
                
                self.logger.info(
                    "anthropic_request_success",
                    model=self.config.model_id,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens
                )
                
                return {
                    "response": response_text,
                    "model": self.config.model_id,
                    "usage": {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "total_tokens": input_tokens + output_tokens
                    },
                    "finish_reason": result.get("stop_reason"),
                    "timestamp": datetime.now().isoformat()
                }
                
        except aiohttp.ClientError as e:
            self.logger.error(
                "anthropic_request_failed",
                model=self.config.model_id,
                error=str(e)
            )
            raise
    
    async def generate_streaming_response(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Generate streaming response from Anthropic Claude."""
        
        await self._check_rate_limit()
        
        # Prepare request
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        request_data = {
            "model": self.config.model_id,
            "messages": messages,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "stream": True,
            **kwargs
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/messages",
                json=request_data,
                headers=headers
            ) as response:
                
                response.raise_for_status()
                
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    if line.startswith('data: '):
                        data = line[6:]  # Remove 'data: ' prefix
                        if data == '[DONE]':
                            break
                        
                        try:
                            chunk = json.loads(data)
                            if chunk.get("type") == "content_block_delta":
                                delta = chunk.get("delta", {})
                                text = delta.get("text", "")
                                if text:
                                    yield text
                        except json.JSONDecodeError:
                            continue
                            
        except aiohttp.ClientError as e:
            self.logger.error(
                "anthropic_streaming_failed",
                model=self.config.model_id,
                error=str(e)
            )
            raise


class AWSBedrockProvider(BaseLLMProvider):
    """AWS Bedrock provider for Claude models."""
    
    def __init__(self, config: ModelConfig, region: str = "us-east-1"):
        super().__init__(config)
        self.region = region
        self.rate_limit_per_minute = 100  # Higher limit for Bedrock
        
        # Import boto3 conditionally
        try:
            import boto3
            self.bedrock_client = boto3.client('bedrock-runtime', region_name=region)
        except ImportError:
            self.logger.warning("boto3_not_available", message="Using mock implementation")
            self.bedrock_client = None
    
    async def generate_response(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate response from AWS Bedrock."""
        
        if not self.bedrock_client:
            # Mock response for development
            return await self._generate_mock_response(prompt, system_prompt)
        
        await self._check_rate_limit()
        
        # Prepare request for Bedrock
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "messages": []
        }
        
        if system_prompt:
            body["system"] = system_prompt
        
        body["messages"].append({
            "role": "user",
            "content": prompt
        })
        
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.bedrock_client.invoke_model(
                    modelId=self.config.model_id,
                    body=json.dumps(body)
                )
            )
            
            result = json.loads(response['body'].read())
            
            # Extract response content
            content = result.get("content", [])
            response_text = ""
            if content and isinstance(content, list):
                response_text = content[0].get("text", "")
            
            # Track token usage
            usage = result.get("usage", {})
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            self._update_token_usage(input_tokens, output_tokens)
            
            self.logger.info(
                "bedrock_request_success",
                model=self.config.model_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens
            )
            
            return {
                "response": response_text,
                "model": self.config.model_id,
                "usage": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens
                },
                "finish_reason": result.get("stop_reason"),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(
                "bedrock_request_failed",
                model=self.config.model_id,
                error=str(e)
            )
            raise
    
    async def generate_streaming_response(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Generate streaming response from AWS Bedrock."""
        
        if not self.bedrock_client:
            # Mock streaming response
            response = await self._generate_mock_response(prompt, system_prompt)
            text = response.get("response", "")
            
            # Simulate streaming by yielding chunks
            chunk_size = 20
            for i in range(0, len(text), chunk_size):
                chunk = text[i:i + chunk_size]
                yield chunk
                await asyncio.sleep(0.1)  # Simulate streaming delay
            return
        
        await self._check_rate_limit()
        
        # Bedrock streaming implementation would go here
        # For now, fall back to non-streaming
        response = await self.generate_response(prompt, system_prompt, **kwargs)
        yield response.get("response", "")
    
    async def _generate_mock_response(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Generate mock response for development."""
        
        # Simulate processing time
        await asyncio.sleep(0.5)
        
        # Simple mock response based on prompt
        mock_response = f"This is a mock response to: {prompt[:100]}..."
        
        # Mock token usage
        input_tokens = len(prompt.split()) + (len(system_prompt.split()) if system_prompt else 0)
        output_tokens = len(mock_response.split())
        self._update_token_usage(input_tokens, output_tokens)
        
        return {
            "response": mock_response,
            "model": self.config.model_id,
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens
            },
            "finish_reason": "stop",
            "timestamp": datetime.now().isoformat()
        }


class LLMProviderManager:
    """Manager for multiple LLM providers with intelligent routing."""
    
    def __init__(self):
        self.providers: Dict[ModelTier, BaseLLMProvider] = {}
        self.logger = get_logger("llm_provider_manager")
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize LLM providers based on configuration."""
        
        from ..config.models import DEFAULT_MODEL_CONFIGS
        
        # Initialize providers for each model tier
        for tier, config in DEFAULT_MODEL_CONFIGS.items():
            try:
                if settings.anthropic_api_key:
                    provider = AnthropicProvider(config)
                else:
                    provider = AWSBedrockProvider(config, region=settings.aws_region)
                
                self.providers[tier] = provider
                
                self.logger.info(
                    "llm_provider_initialized",
                    tier=tier.value,
                    model=config.model_id,
                    provider=provider.__class__.__name__
                )
                
            except Exception as e:
                self.logger.error(
                    "llm_provider_init_failed",
                    tier=tier.value,
                    error=str(e)
                )
    
    async def generate_response(
        self, 
        tier: ModelTier, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate response using appropriate provider for model tier."""
        
        provider = self.providers.get(tier)
        if not provider:
            raise ValueError(f"No provider available for tier: {tier}")
        
        async with provider:
            result = await provider.generate_response(prompt, system_prompt, **kwargs)
            
            # Add tier information to result
            result["model_tier"] = tier.value
            result["provider"] = provider.__class__.__name__
            
            return result
    
    async def generate_streaming_response(
        self, 
        tier: ModelTier, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Generate streaming response using appropriate provider for model tier."""
        
        provider = self.providers.get(tier)
        if not provider:
            raise ValueError(f"No provider available for tier: {tier}")
        
        async with provider:
            async for chunk in provider.generate_streaming_response(prompt, system_prompt, **kwargs):
                yield chunk
    
    async def generate_parallel_responses(
        self, 
        requests: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate multiple responses in parallel across different providers."""
        
        tasks = []
        for request in requests:
            tier = request.get("tier")
            prompt = request.get("prompt")
            system_prompt = request.get("system_prompt")
            kwargs = request.get("kwargs", {})
            
            if tier and prompt:
                task = self.generate_response(tier, prompt, system_prompt, **kwargs)
                tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "error": str(result),
                    "request_index": i,
                    "status": "failed"
                })
            else:
                result["request_index"] = i
                result["status"] = "success"
                processed_results.append(result)
        
        return processed_results
    
    def get_all_usage_metrics(self) -> Dict[str, Any]:
        """Get usage metrics for all providers."""
        
        metrics = {
            "total_cost": 0.0,
            "total_tokens": 0,
            "providers": {}
        }
        
        for tier, provider in self.providers.items():
            provider_metrics = provider.get_usage_metrics()
            metrics["providers"][tier.value] = provider_metrics
            metrics["total_cost"] += provider_metrics["total_cost"]
            metrics["total_tokens"] += provider_metrics["total_tokens"]
        
        metrics["cost_by_tier"] = {
            tier.value: provider.total_cost 
            for tier, provider in self.providers.items()
        }
        
        return metrics
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all providers."""
        
        health_results = {}
        
        for tier, provider in self.providers.items():
            try:
                async with provider:
                    # Simple health check request
                    result = await provider.generate_response(
                        "Health check: respond with 'OK'",
                        system_prompt="You are a health check service. Respond only with 'OK'."
                    )
                    
                    health_results[tier.value] = {
                        "status": "healthy",
                        "response_time": 1.0,  # Would measure actual response time
                        "model": provider.config.model_id
                    }
                    
            except Exception as e:
                health_results[tier.value] = {
                    "status": "unhealthy",
                    "error": str(e),
                    "model": provider.config.model_id
                }
        
        overall_health = all(
            result["status"] == "healthy" 
            for result in health_results.values()
        )
        
        return {
            "overall_health": "healthy" if overall_health else "degraded",
            "providers": health_results,
            "timestamp": datetime.now().isoformat()
        }


# Global provider manager instance
llm_provider_manager = LLMProviderManager()