"""Async utilities for parallel execution."""

import asyncio
from typing import Any, Awaitable, List, TypeVar, Optional
from concurrent.futures import ThreadPoolExecutor
import structlog

logger = structlog.get_logger("async_utils")

T = TypeVar('T')


async def gather_with_concurrency(
    awaitables: List[Awaitable[T]], 
    max_concurrency: int = 5,
    return_exceptions: bool = False
) -> List[T]:
    """
    Execute awaitables with limited concurrency.
    
    Args:
        awaitables: List of awaitable objects to execute
        max_concurrency: Maximum number of concurrent executions
        return_exceptions: Whether to return exceptions or raise them
    
    Returns:
        List of results in the same order as input awaitables
    """
    semaphore = asyncio.Semaphore(max_concurrency)
    
    async def _run_with_semaphore(awaitable: Awaitable[T]) -> T:
        async with semaphore:
            return await awaitable
    
    wrapped_awaitables = [_run_with_semaphore(aw) for aw in awaitables]
    
    return await asyncio.gather(*wrapped_awaitables, return_exceptions=return_exceptions)


async def run_with_timeout(
    awaitable: Awaitable[T], 
    timeout_seconds: float,
    default_value: Optional[T] = None
) -> T:
    """
    Run an awaitable with a timeout.
    
    Args:
        awaitable: The awaitable to run
        timeout_seconds: Timeout in seconds
        default_value: Value to return if timeout occurs (if None, raises TimeoutError)
    
    Returns:
        Result of the awaitable or default_value on timeout
    """
    try:
        return await asyncio.wait_for(awaitable, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        if default_value is not None:
            logger.warning("operation_timeout", timeout=timeout_seconds)
            return default_value
        raise


async def throttled_gather(
    awaitables: List[Awaitable[T]],
    rate_limit: float = 10.0,  # requests per second
    return_exceptions: bool = False
) -> List[T]:
    """
    Execute awaitables with rate limiting (simplified implementation).
    
    Args:
        awaitables: List of awaitable objects to execute
        rate_limit: Maximum requests per second
        return_exceptions: Whether to return exceptions or raise them
    
    Returns:
        List of results in the same order as input awaitables
    """
    # Simplified implementation without external throttling library
    delay = 1.0 / rate_limit
    
    async def _throttled_execution(i: int, awaitable: Awaitable[T]) -> T:
        if i > 0:
            await asyncio.sleep(delay * i)
        return await awaitable
    
    wrapped_awaitables = [_throttled_execution(i, aw) for i, aw in enumerate(awaitables)]
    
    return await asyncio.gather(*wrapped_awaitables, return_exceptions=return_exceptions)


class ParallelExecutor:
    """Manages parallel execution of tasks with various strategies."""
    
    def __init__(self, max_concurrency: int = 5, rate_limit: Optional[float] = None):
        self.max_concurrency = max_concurrency
        self.rate_limit = rate_limit
        self.executor = ThreadPoolExecutor(max_workers=max_concurrency)
    
    async def execute_parallel(
        self, 
        awaitables: List[Awaitable[T]],
        strategy: str = "concurrency"  # "concurrency", "throttled", or "sequential"
    ) -> List[T]:
        """
        Execute awaitables using the specified strategy.
        
        Args:
            awaitables: List of awaitable objects to execute
            strategy: Execution strategy ("concurrency", "throttled", or "sequential")
        
        Returns:
            List of results in the same order as input awaitables
        """
        if not awaitables:
            return []
        
        logger.info(
            "parallel_execution_start",
            count=len(awaitables),
            strategy=strategy,
            max_concurrency=self.max_concurrency
        )
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            if strategy == "sequential":
                results = []
                for awaitable in awaitables:
                    result = await awaitable
                    results.append(result)
                return results
            
            elif strategy == "throttled" and self.rate_limit:
                results = await throttled_gather(awaitables, self.rate_limit)
            
            else:  # concurrency (default)
                results = await gather_with_concurrency(
                    awaitables, 
                    self.max_concurrency
                )
            
            execution_time = asyncio.get_event_loop().time() - start_time
            
            logger.info(
                "parallel_execution_complete",
                count=len(awaitables),
                strategy=strategy,
                execution_time=execution_time,
                avg_time_per_task=execution_time / len(awaitables)
            )
            
            return results
        
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            logger.error(
                "parallel_execution_error",
                count=len(awaitables),
                strategy=strategy,
                execution_time=execution_time,
                error=str(e)
            )
            raise
    
    def __del__(self):
        """Clean up the thread pool executor."""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)