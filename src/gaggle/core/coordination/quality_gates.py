"""Advanced quality gates with multi-stage review and parallel testing."""

import asyncio
import logging
from collections import defaultdict
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from ...config.models import AgentRole
from ...models import Task

logger = logging.getLogger(__name__)


class ReviewStageType(Enum):
    """Types of review stages."""

    REQUIREMENTS_REVIEW = "requirements_review"
    ARCHITECTURE_REVIEW = "architecture_review"
    CODE_REVIEW = "code_review"
    SECURITY_REVIEW = "security_review"
    PERFORMANCE_REVIEW = "performance_review"
    BUSINESS_VALUE_REVIEW = "business_value_review"
    INTEGRATION_TEST = "integration_test"
    USER_ACCEPTANCE_TEST = "user_acceptance_test"


class QualityGateStatus(Enum):
    """Status of quality gate evaluation."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PASSED = "passed"
    FAILED = "failed"
    CONDITIONAL_PASS = "conditional_pass"  # Pass with conditions/follow-up required


class TestType(Enum):
    """Types of tests that can be run in parallel."""

    UNIT_TESTS = "unit_tests"
    INTEGRATION_TESTS = "integration_tests"
    E2E_TESTS = "e2e_tests"
    PERFORMANCE_TESTS = "performance_tests"
    SECURITY_TESTS = "security_tests"
    ACCESSIBILITY_TESTS = "accessibility_tests"
    API_TESTS = "api_tests"


@dataclass
class QualityMetrics:
    """Quality metrics collected during evaluation."""

    # Code quality
    code_coverage: float = 0.0
    test_pass_rate: float = 0.0
    cyclomatic_complexity: float = 0.0
    technical_debt_ratio: float = 0.0

    # Security metrics
    security_vulnerabilities: int = 0
    critical_vulnerabilities: int = 0

    # Performance metrics
    response_time_p95: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0

    # Business metrics
    business_value_score: float = 0.0
    user_satisfaction_score: float = 0.0

    # Process metrics
    review_time_hours: float = 0.0
    defect_density: float = 0.0

    def overall_quality_score(self) -> float:
        """Calculate overall quality score (0-100)."""
        weights = {
            "code_coverage": 0.2,
            "test_pass_rate": 0.25,
            "security_score": 0.2,  # Inverse of vulnerabilities
            "performance_score": 0.15,  # Based on response time
            "business_value_score": 0.2,
        }

        # Normalize metrics to 0-100 scale
        security_score = max(0, 100 - (self.security_vulnerabilities * 10))
        performance_score = max(
            0, 100 - (self.response_time_p95 / 10)
        )  # Assume 1000ms = 0 points

        score = (
            self.code_coverage * weights["code_coverage"]
            + self.test_pass_rate * weights["test_pass_rate"]
            + security_score * weights["security_score"]
            + performance_score * weights["performance_score"]
            + self.business_value_score * weights["business_value_score"]
        )

        return min(100.0, max(0.0, score))


@dataclass
class ReviewCriteria:
    """Criteria for a quality review stage."""

    min_code_coverage: float = 80.0
    max_cyclomatic_complexity: float = 10.0
    max_security_vulnerabilities: int = 0
    max_response_time_ms: float = 1000.0
    min_business_value_score: float = 70.0
    min_test_pass_rate: float = 95.0

    required_approvals: list[AgentRole] = field(default_factory=list)
    blocking_issues: list[str] = field(default_factory=list)

    def evaluate(self, metrics: QualityMetrics) -> tuple[bool, list[str]]:
        """Evaluate metrics against criteria."""
        issues = []

        if metrics.code_coverage < self.min_code_coverage:
            issues.append(
                f"Code coverage {metrics.code_coverage:.1f}% below required {self.min_code_coverage:.1f}%"
            )

        if metrics.cyclomatic_complexity > self.max_cyclomatic_complexity:
            issues.append(
                f"Complexity {metrics.cyclomatic_complexity:.1f} exceeds limit {self.max_cyclomatic_complexity}"
            )

        if metrics.security_vulnerabilities > self.max_security_vulnerabilities:
            issues.append(
                f"Security vulnerabilities: {metrics.security_vulnerabilities}"
            )

        if metrics.response_time_p95 > self.max_response_time_ms:
            issues.append(
                f"Response time {metrics.response_time_p95:.1f}ms exceeds {self.max_response_time_ms}ms"
            )

        if metrics.business_value_score < self.min_business_value_score:
            issues.append(
                f"Business value {metrics.business_value_score:.1f} below required {self.min_business_value_score}"
            )

        if metrics.test_pass_rate < self.min_test_pass_rate:
            issues.append(
                f"Test pass rate {metrics.test_pass_rate:.1f}% below required {self.min_test_pass_rate:.1f}%"
            )

        return len(issues) == 0, issues


@dataclass
class ReviewResult:
    """Result of a quality review stage."""

    stage_type: ReviewStageType
    status: QualityGateStatus
    reviewer: AgentRole

    # Results
    metrics: QualityMetrics
    issues_found: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    # Metadata
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    duration_minutes: float = 0.0

    # Follow-up
    follow_up_tasks: list[str] = field(default_factory=list)
    next_review_required: bool = False


@dataclass
class ReviewStage:
    """Configuration for a quality review stage."""

    stage_type: ReviewStageType
    name: str
    description: str

    # Configuration
    criteria: ReviewCriteria
    reviewer_roles: list[AgentRole]
    prerequisites: list[ReviewStageType] = field(default_factory=list)

    # Execution
    async_enabled: bool = True
    timeout_minutes: int = 30
    retry_count: int = 1

    # Custom evaluation function
    custom_evaluator: Callable | None = None

    def can_start(self, completed_stages: set[ReviewStageType]) -> bool:
        """Check if stage can start based on prerequisites."""
        return all(prereq in completed_stages for prereq in self.prerequisites)


@dataclass
class TestSuite:
    """Configuration for a test suite that can run in parallel."""

    test_type: TestType
    name: str
    command: str
    timeout_minutes: int = 15

    # Parallel execution
    can_run_parallel: bool = True
    resource_requirements: dict[str, Any] = field(default_factory=dict)

    # Results interpretation
    success_criteria: dict[str, Any] = field(default_factory=dict)


class ParallelTester:
    """Manages parallel execution of multiple test suites."""

    def __init__(self, max_concurrent_tests: int = 4):
        self.max_concurrent_tests = max_concurrent_tests
        self.test_suites: dict[TestType, TestSuite] = {}
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent_tests)

    def register_test_suite(self, test_suite: TestSuite) -> None:
        """Register a test suite for parallel execution."""
        self.test_suites[test_suite.test_type] = test_suite
        logger.info(f"Registered test suite: {test_suite.name}")

    async def run_tests(
        self, test_types: list[TestType], context: dict[str, Any] = None
    ) -> dict[TestType, dict[str, Any]]:
        """Run multiple test suites in parallel."""
        context = context or {}
        logger.info(
            f"Starting parallel test execution for: {[t.value for t in test_types]}"
        )

        # Group tests by parallel capability
        parallel_tests = [t for t in test_types if self.test_suites[t].can_run_parallel]
        sequential_tests = [
            t for t in test_types if not self.test_suites[t].can_run_parallel
        ]

        results = {}

        # Run parallel tests concurrently
        if parallel_tests:
            parallel_tasks = [
                self._run_single_test(test_type, context)
                for test_type in parallel_tests
            ]
            parallel_results = await asyncio.gather(
                *parallel_tasks, return_exceptions=True
            )

            for test_type, result in zip(
                parallel_tests, parallel_results, strict=False
            ):
                if isinstance(result, Exception):
                    results[test_type] = {
                        "success": False,
                        "error": str(result),
                        "metrics": {},
                    }
                else:
                    results[test_type] = result

        # Run sequential tests one by one
        for test_type in sequential_tests:
            results[test_type] = await self._run_single_test(test_type, context)

        return results

    async def _run_single_test(
        self, test_type: TestType, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Run a single test suite."""
        test_suite = self.test_suites[test_type]
        start_time = datetime.now()

        try:
            logger.info(f"Starting {test_suite.name}")

            # Simulate test execution (in real implementation, this would run actual tests)
            await asyncio.sleep(0.1)  # Simulate test execution time

            # Mock successful test results
            success = True
            metrics = self._generate_mock_metrics(test_type)

            duration = (datetime.now() - start_time).total_seconds() / 60.0

            return {
                "success": success,
                "duration_minutes": duration,
                "metrics": metrics,
                "test_suite": test_suite.name,
            }

        except Exception as e:
            logger.error(f"Test {test_suite.name} failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "duration_minutes": (datetime.now() - start_time).total_seconds()
                / 60.0,
                "metrics": {},
            }

    def _generate_mock_metrics(self, test_type: TestType) -> dict[str, float]:
        """Generate mock metrics for testing purposes."""
        base_metrics = {
            TestType.UNIT_TESTS: {"coverage": 85.0, "pass_rate": 98.0},
            TestType.INTEGRATION_TESTS: {"coverage": 75.0, "pass_rate": 95.0},
            TestType.E2E_TESTS: {"pass_rate": 90.0, "avg_duration": 45.0},
            TestType.PERFORMANCE_TESTS: {"response_time": 250.0, "throughput": 1000.0},
            TestType.SECURITY_TESTS: {"vulnerabilities": 0, "risk_score": 95.0},
            TestType.ACCESSIBILITY_TESTS: {"compliance_score": 88.0},
            TestType.API_TESTS: {"pass_rate": 97.0, "response_time": 150.0},
        }

        return base_metrics.get(test_type, {"pass_rate": 95.0})


class MetricsCollector:
    """Collects quality metrics from various sources."""

    def __init__(self):
        self.metric_sources: dict[str, Callable] = {}

    def register_metric_source(self, name: str, collector_func: Callable) -> None:
        """Register a metric collection function."""
        self.metric_sources[name] = collector_func

    async def collect_metrics(
        self, task: Task, test_results: dict[TestType, dict[str, Any]] = None
    ) -> QualityMetrics:
        """Collect comprehensive quality metrics."""
        metrics = QualityMetrics()

        # Collect from test results
        if test_results:
            metrics = self._extract_metrics_from_tests(test_results)

        # Collect from registered sources
        for source_name, collector in self.metric_sources.items():
            try:
                source_metrics = await collector(task)
                metrics = self._merge_metrics(metrics, source_metrics)
            except Exception as e:
                logger.warning(f"Failed to collect metrics from {source_name}: {e}")

        return metrics

    def _extract_metrics_from_tests(
        self, test_results: dict[TestType, dict[str, Any]]
    ) -> QualityMetrics:
        """Extract quality metrics from test results."""
        metrics = QualityMetrics()

        # Code coverage from unit tests
        unit_results = test_results.get(TestType.UNIT_TESTS, {})
        if "coverage" in unit_results.get("metrics", {}):
            metrics.code_coverage = unit_results["metrics"]["coverage"]

        # Test pass rates
        all_pass_rates = []
        for _test_type, results in test_results.items():
            test_metrics = results.get("metrics", {})
            if "pass_rate" in test_metrics:
                all_pass_rates.append(test_metrics["pass_rate"])

        if all_pass_rates:
            metrics.test_pass_rate = sum(all_pass_rates) / len(all_pass_rates)

        # Performance metrics
        perf_results = test_results.get(TestType.PERFORMANCE_TESTS, {})
        if "response_time" in perf_results.get("metrics", {}):
            metrics.response_time_p95 = perf_results["metrics"]["response_time"]

        # Security metrics
        security_results = test_results.get(TestType.SECURITY_TESTS, {})
        if "vulnerabilities" in security_results.get("metrics", {}):
            metrics.security_vulnerabilities = security_results["metrics"][
                "vulnerabilities"
            ]

        return metrics

    def _merge_metrics(
        self, base: QualityMetrics, additional: dict[str, Any]
    ) -> QualityMetrics:
        """Merge additional metrics into base metrics."""
        for key, value in additional.items():
            if hasattr(base, key):
                setattr(base, key, value)
        return base


class QualityGateManager:
    """Manages the complete quality gate process with multi-stage review."""

    def __init__(self):
        self.review_stages: list[ReviewStage] = []
        self.parallel_tester = ParallelTester()
        self.metrics_collector = MetricsCollector()
        self.stage_results: dict[str, list[ReviewResult]] = defaultdict(list)

    def configure_standard_gates(self) -> None:
        """Configure standard quality gate stages."""

        # Requirements Review
        self.add_review_stage(
            ReviewStage(
                stage_type=ReviewStageType.REQUIREMENTS_REVIEW,
                name="Requirements Review",
                description="Review story requirements and acceptance criteria",
                criteria=ReviewCriteria(
                    min_business_value_score=70.0,
                    required_approvals=[AgentRole.PRODUCT_OWNER],
                ),
                reviewer_roles=[AgentRole.PRODUCT_OWNER, AgentRole.TECH_LEAD],
                prerequisites=[],
                async_enabled=False,
            )
        )

        # Architecture Review
        self.add_review_stage(
            ReviewStage(
                stage_type=ReviewStageType.ARCHITECTURE_REVIEW,
                name="Architecture Review",
                description="Review technical design and architecture decisions",
                criteria=ReviewCriteria(
                    max_cyclomatic_complexity=10.0,
                    required_approvals=[AgentRole.TECH_LEAD],
                ),
                reviewer_roles=[AgentRole.TECH_LEAD],
                prerequisites=[ReviewStageType.REQUIREMENTS_REVIEW],
            )
        )

        # Code Review
        self.add_review_stage(
            ReviewStage(
                stage_type=ReviewStageType.CODE_REVIEW,
                name="Code Review",
                description="Review implementation code quality",
                criteria=ReviewCriteria(
                    min_code_coverage=80.0,
                    max_cyclomatic_complexity=8.0,
                    min_test_pass_rate=95.0,
                ),
                reviewer_roles=[AgentRole.TECH_LEAD],
                prerequisites=[ReviewStageType.ARCHITECTURE_REVIEW],
            )
        )

        # Security Review
        self.add_review_stage(
            ReviewStage(
                stage_type=ReviewStageType.SECURITY_REVIEW,
                name="Security Review",
                description="Review security implications and vulnerabilities",
                criteria=ReviewCriteria(
                    max_security_vulnerabilities=0,
                    required_approvals=[AgentRole.TECH_LEAD],
                ),
                reviewer_roles=[AgentRole.TECH_LEAD],
                prerequisites=[ReviewStageType.CODE_REVIEW],
            )
        )

        # Performance Review
        self.add_review_stage(
            ReviewStage(
                stage_type=ReviewStageType.PERFORMANCE_REVIEW,
                name="Performance Review",
                description="Review performance characteristics",
                criteria=ReviewCriteria(max_response_time_ms=1000.0),
                reviewer_roles=[AgentRole.TECH_LEAD],
                prerequisites=[ReviewStageType.CODE_REVIEW],
            )
        )

        # Business Value Review
        self.add_review_stage(
            ReviewStage(
                stage_type=ReviewStageType.BUSINESS_VALUE_REVIEW,
                name="Business Value Review",
                description="Review business value delivery",
                criteria=ReviewCriteria(
                    min_business_value_score=80.0,
                    required_approvals=[AgentRole.PRODUCT_OWNER],
                ),
                reviewer_roles=[AgentRole.PRODUCT_OWNER],
                prerequisites=[
                    ReviewStageType.SECURITY_REVIEW,
                    ReviewStageType.PERFORMANCE_REVIEW,
                ],
            )
        )

        # Configure standard test suites
        self._configure_standard_tests()

    def _configure_standard_tests(self) -> None:
        """Configure standard test suites."""
        test_suites = [
            TestSuite(
                test_type=TestType.UNIT_TESTS,
                name="Unit Test Suite",
                command="pytest tests/unit/",
                timeout_minutes=10,
                can_run_parallel=True,
            ),
            TestSuite(
                test_type=TestType.INTEGRATION_TESTS,
                name="Integration Test Suite",
                command="pytest tests/integration/",
                timeout_minutes=20,
                can_run_parallel=True,
            ),
            TestSuite(
                test_type=TestType.E2E_TESTS,
                name="End-to-End Test Suite",
                command="pytest tests/e2e/",
                timeout_minutes=30,
                can_run_parallel=False,  # Often requires exclusive resources
            ),
            TestSuite(
                test_type=TestType.SECURITY_TESTS,
                name="Security Test Suite",
                command="safety check && bandit -r src/",
                timeout_minutes=15,
                can_run_parallel=True,
            ),
        ]

        for test_suite in test_suites:
            self.parallel_tester.register_test_suite(test_suite)

    def add_review_stage(self, stage: ReviewStage) -> None:
        """Add a review stage to the quality gate process."""
        self.review_stages.append(stage)
        logger.info(f"Added review stage: {stage.name}")

    async def execute_quality_gates(
        self, task: Task, context: dict[str, Any] = None
    ) -> dict[str, Any]:
        """Execute complete quality gate process for a task."""
        context = context or {}
        task_id = task.id

        logger.info(f"Starting quality gate execution for task: {task_id}")

        # Track execution
        start_time = datetime.now()
        completed_stages: set[ReviewStageType] = set()
        all_results: list[ReviewResult] = []
        overall_status = QualityGateStatus.PENDING

        try:
            # Execute review stages in dependency order
            for stage in self._get_execution_order():
                if stage.can_start(completed_stages):
                    logger.info(f"Executing stage: {stage.name}")

                    # Run tests if needed for this stage
                    test_results = None
                    if stage.stage_type == ReviewStageType.CODE_REVIEW:
                        test_types = [TestType.UNIT_TESTS, TestType.INTEGRATION_TESTS]
                        test_results = await self.parallel_tester.run_tests(
                            test_types, context
                        )
                    elif stage.stage_type == ReviewStageType.SECURITY_REVIEW:
                        test_results = await self.parallel_tester.run_tests(
                            [TestType.SECURITY_TESTS], context
                        )

                    # Execute the review stage
                    result = await self._execute_stage(
                        stage, task, test_results, context
                    )
                    all_results.append(result)

                    if result.status == QualityGateStatus.PASSED:
                        completed_stages.add(stage.stage_type)
                    elif result.status == QualityGateStatus.FAILED:
                        logger.warning(
                            f"Stage {stage.name} failed: {result.issues_found}"
                        )
                        overall_status = QualityGateStatus.FAILED
                        break
                    elif result.status == QualityGateStatus.CONDITIONAL_PASS:
                        completed_stages.add(stage.stage_type)
                        overall_status = QualityGateStatus.CONDITIONAL_PASS

            # Determine overall status
            if overall_status != QualityGateStatus.FAILED:
                if all(r.status == QualityGateStatus.PASSED for r in all_results):
                    overall_status = QualityGateStatus.PASSED
                elif any(
                    r.status == QualityGateStatus.CONDITIONAL_PASS for r in all_results
                ):
                    overall_status = QualityGateStatus.CONDITIONAL_PASS

        except Exception as e:
            logger.error(f"Quality gate execution failed: {e}")
            overall_status = QualityGateStatus.FAILED

        # Store results
        self.stage_results[task_id] = all_results

        execution_time = (datetime.now() - start_time).total_seconds() / 60.0

        return {
            "task_id": task_id,
            "overall_status": overall_status,
            "completed_stages": list(completed_stages),
            "stage_results": all_results,
            "execution_time_minutes": execution_time,
            "total_issues": sum(len(r.issues_found) for r in all_results),
            "recommendations": self._consolidate_recommendations(all_results),
        }

    async def _execute_stage(
        self,
        stage: ReviewStage,
        task: Task,
        test_results: dict[TestType, dict[str, Any]] = None,
        context: dict[str, Any] = None,
    ) -> ReviewResult:
        """Execute a single review stage."""
        start_time = datetime.now()

        # Collect metrics
        metrics = await self.metrics_collector.collect_metrics(task, test_results)

        # Evaluate against criteria
        passed, issues = stage.criteria.evaluate(metrics)

        # Determine status
        if passed:
            status = QualityGateStatus.PASSED
        elif len(issues) <= 2 and not any(
            "critical" in issue.lower() for issue in issues
        ):
            status = QualityGateStatus.CONDITIONAL_PASS
        else:
            status = QualityGateStatus.FAILED

        # Generate recommendations
        recommendations = self._generate_stage_recommendations(stage, metrics, issues)

        # Create result
        result = ReviewResult(
            stage_type=stage.stage_type,
            status=status,
            reviewer=(
                stage.reviewer_roles[0] if stage.reviewer_roles else AgentRole.TECH_LEAD
            ),
            metrics=metrics,
            issues_found=issues,
            recommendations=recommendations,
            completed_at=datetime.now(),
            duration_minutes=(datetime.now() - start_time).total_seconds() / 60.0,
        )

        return result

    def _get_execution_order(self) -> list[ReviewStage]:
        """Get stages in execution order based on prerequisites."""
        ordered_stages = []
        remaining_stages = self.review_stages.copy()

        while remaining_stages:
            # Find stages with satisfied prerequisites
            ready_stages = [
                stage
                for stage in remaining_stages
                if all(
                    prereq in [s.stage_type for s in ordered_stages]
                    for prereq in stage.prerequisites
                )
            ]

            if not ready_stages:
                # Add remaining stages without prerequisites to avoid infinite loop
                ready_stages = [
                    stage for stage in remaining_stages if not stage.prerequisites
                ]
                if not ready_stages:
                    ready_stages = remaining_stages[:1]  # Force progress

            # Add ready stages and remove from remaining
            for stage in ready_stages:
                ordered_stages.append(stage)
                remaining_stages.remove(stage)

        return ordered_stages

    def _generate_stage_recommendations(
        self, stage: ReviewStage, metrics: QualityMetrics, issues: list[str]
    ) -> list[str]:
        """Generate recommendations for a review stage."""
        recommendations = []

        if stage.stage_type == ReviewStageType.CODE_REVIEW:
            if metrics.code_coverage < 80:
                recommendations.append("Increase test coverage to at least 80%")
            if metrics.cyclomatic_complexity > 8:
                recommendations.append("Refactor complex methods to reduce complexity")

        elif stage.stage_type == ReviewStageType.SECURITY_REVIEW:
            if metrics.security_vulnerabilities > 0:
                recommendations.append(
                    "Address all security vulnerabilities before deployment"
                )
                recommendations.append("Run additional security scans")

        elif stage.stage_type == ReviewStageType.PERFORMANCE_REVIEW:
            if metrics.response_time_p95 > 1000:
                recommendations.append(
                    "Optimize performance to meet response time requirements"
                )
                recommendations.append("Consider caching or database optimization")

        # Add generic recommendations based on issues
        if issues:
            recommendations.append("Address all identified issues before proceeding")
            if len(issues) > 3:
                recommendations.append(
                    "Consider breaking down this task into smaller pieces"
                )

        return recommendations

    def _consolidate_recommendations(self, results: list[ReviewResult]) -> list[str]:
        """Consolidate recommendations from all stages."""
        all_recommendations = []
        for result in results:
            all_recommendations.extend(result.recommendations)

        # Remove duplicates while preserving order
        consolidated = []
        seen = set()
        for rec in all_recommendations:
            if rec not in seen:
                consolidated.append(rec)
                seen.add(rec)

        return consolidated

    def get_quality_summary(self, task_id: str) -> dict[str, Any]:
        """Get quality summary for a task."""
        results = self.stage_results.get(task_id, [])
        if not results:
            return {"status": "no_data"}

        overall_score = sum(r.metrics.overall_quality_score() for r in results) / len(
            results
        )
        total_issues = sum(len(r.issues_found) for r in results)

        return {
            "overall_quality_score": overall_score,
            "total_issues_found": total_issues,
            "stages_completed": len(results),
            "average_stage_duration": sum(r.duration_minutes for r in results)
            / len(results),
            "status": results[-1].status.value if results else "unknown",
        }
