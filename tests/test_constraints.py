import pytest
import sys
from datetime import date, timedelta
from decimal import Decimal
from timefold.solver.test import ConstraintVerifier
from timefold.solver.score import HardSoftDecimalScore

# Import standardized test utilities
from tests.test_utils import get_test_logger, create_test_results

# Initialize standardized test logger
logger = get_test_logger(__name__)

from src.constraint_solvers.timetable.constraints import (
    define_constraints,
    required_skill,
    no_overlapping_tasks,
    task_within_schedule,
    task_fits_in_schedule,
    unavailable_employee,
    maintain_project_task_order,
    undesired_day_for_employee,
    desired_day_for_employee,
    balance_employee_task_assignments,
    no_lunch_break_spanning,
    no_weekend_scheduling,
)

from src.constraint_solvers.timetable.working_hours import task_spans_lunch_break
from src.constraint_solvers.timetable.domain import (
    Employee,
    Task,
    EmployeeSchedule,
    ScheduleInfo,
)


class TestConstraints:
    """
    Comprehensive test suite for all timetable constraints using ConstraintVerifier.
    Each constraint is tested in isolation to verify correct behavior.
    """

    def setup_method(self):
        """Set up common test data and ConstraintVerifier instance."""
        logger.debug("Setting up test constraints and data...")

        self.constraint_verifier = ConstraintVerifier.build(
            define_constraints, EmployeeSchedule, Task
        )

        # Create common test data using generator functions
        self.dates = create_test_dates()
        self.employees = create_standard_employees(self.dates)
        self.schedule_info = create_schedule_info()

        # Create shortcuts for commonly used employees
        self.employee_alice = self.employees["alice"]
        self.employee_bob = self.employees["bob"]
        self.employee_charlie = self.employees["charlie"]

        logger.debug(f"Created {len(self.employees)} test employees and schedule info")

    # ==================== HARD CONSTRAINT TESTS ====================

    def test_required_skill_constraint_violation(self):
        """Test that tasks requiring skills not possessed by assigned employee are penalized."""
        logger.debug("Testing required skill constraint violation...")

        task = create_task(
            task_id="task1",
            description="Python Development",
            required_skill="Python",
            employee=self.employee_bob,  # Bob doesn't have Python skill
        )

        (
            self.constraint_verifier.verify_that(required_skill)
            .given(task, self.employee_bob, self.schedule_info)
            .penalizes_by(1)
        )

        logger.debug("✅ Required skill constraint violation test passed")

    def test_required_skill_constraint_satisfied(self):
        """Test that tasks assigned to employees with required skills are not penalized."""
        logger.debug("Testing required skill constraint satisfaction...")

        task = create_task(
            task_id="task1",
            description="Python Development",
            required_skill="Python",
            employee=self.employee_alice,  # Alice has Python skill
        )

        (
            self.constraint_verifier.verify_that(required_skill)
            .given(task, self.employee_alice, self.schedule_info)
            .penalizes_by(0)
        )

        logger.debug("✅ Required skill constraint satisfaction test passed")

    def test_required_skill_constraint_unassigned_task(self):
        """Test that unassigned tasks don't trigger required skill constraint."""
        logger.debug("Testing required skill constraint with unassigned task...")

        task = create_task(
            task_id="task1",
            description="Python Development",
            required_skill="Python",
            employee=None,  # Unassigned
        )

        (
            self.constraint_verifier.verify_that(required_skill)
            .given(task, self.schedule_info)
            .penalizes_by(0)
        )

        logger.debug("✅ Required skill constraint unassigned task test passed")

    def test_no_overlapping_tasks_constraint_violation(self):
        """Test that overlapping tasks for the same employee are penalized."""
        logger.debug("Testing no overlapping tasks constraint violation...")

        task1 = create_task(
            task_id="task1",
            description="Task 1",
            duration_slots=4,  # slots 0-3
            start_slot=0,
            required_skill="Python",
            employee=self.employee_alice,
        )

        task2 = create_task(
            task_id="task2",
            description="Task 2",
            duration_slots=3,  # slots 2-4 (overlaps with task1 by 2 slots)
            start_slot=2,
            required_skill="Java",
            employee=self.employee_alice,  # Same employee
        )

        # Verify constraint violation (overlap of 2 slots: 2 and 3)
        (
            self.constraint_verifier.verify_that(no_overlapping_tasks)
            .given(task1, task2, self.employee_alice, self.schedule_info)
            .penalizes_by(2)
        )

        logger.debug("✅ No overlapping tasks constraint violation test passed")

    def test_no_overlapping_tasks_constraint_different_employees(self):
        """Test that overlapping tasks for different employees are not penalized."""
        logger.debug("Testing no overlapping tasks with different employees...")

        task1 = create_task(
            task_id="task1",
            description="Task 1",
            duration_slots=4,
            start_slot=0,
            required_skill="Python",
            employee=self.employee_alice,
        )

        task2 = create_task(
            task_id="task2",
            description="Task 2",
            duration_slots=3,
            start_slot=2,  # Overlaps in time but different employee
            required_skill="Java",
            employee=self.employee_bob,  # Different employee
        )

        (
            self.constraint_verifier.verify_that(no_overlapping_tasks)
            .given(
                task1, task2, self.employee_alice, self.employee_bob, self.schedule_info
            )
            .penalizes_by(0)
        )

        logger.debug("✅ No overlapping tasks different employees test passed")

    def test_no_overlapping_tasks_constraint_adjacent_tasks(self):
        """Test that adjacent (non-overlapping) tasks for the same employee are not penalized."""
        logger.debug("Testing no overlapping tasks with adjacent tasks...")

        task1 = create_task(
            task_id="task1",
            description="Task 1",
            duration_slots=4,  # slots 0-3
            start_slot=0,
            required_skill="Python",
            employee=self.employee_alice,
        )

        task2 = create_task(
            task_id="task2",
            description="Task 2",
            duration_slots=3,  # slots 4-6 (no overlap)
            start_slot=4,
            required_skill="Java",
            employee=self.employee_alice,  # Same employee
        )

        (
            self.constraint_verifier.verify_that(no_overlapping_tasks)
            .given(task1, task2, self.employee_alice, self.schedule_info)
            .penalizes_by(0)
        )

        logger.debug("✅ No overlapping tasks adjacent tasks test passed")

    def test_task_within_schedule_constraint_violation(self):
        """Test that tasks starting before slot 0 are penalized."""
        logger.debug("Testing task within schedule constraint violation...")

        task = create_task(
            task_id="task1",
            description="Invalid Task",
            start_slot=-1,  # Invalid start slot
            required_skill="Python",
            employee=self.employee_alice,
        )

        (
            self.constraint_verifier.verify_that(task_within_schedule)
            .given(task, self.employee_alice, self.schedule_info)
            .penalizes_by(1)
        )

        logger.debug("✅ Task within schedule constraint violation test passed")

    def test_task_within_schedule_constraint_satisfied(self):
        """Test that tasks starting at valid slots are not penalized."""
        logger.debug("Testing task within schedule constraint satisfaction...")

        task = create_task(
            task_id="task1",
            description="Valid Task",
            start_slot=0,  # Valid start slot
            required_skill="Python",
            employee=self.employee_alice,
        )

        (
            self.constraint_verifier.verify_that(task_within_schedule)
            .given(task, self.employee_alice, self.schedule_info)
            .penalizes_by(0)
        )

        logger.debug("✅ Task within schedule constraint satisfaction test passed")

    def test_task_fits_in_schedule_constraint_violation(self):
        """Test that tasks extending beyond schedule end are penalized."""
        task = create_task(
            task_id="task1",
            description="Overlong Task",
            duration_slots=10,  # Task extends to slot 65 (beyond 59)
            start_slot=56,  # Start at slot 56, end at slot 65 (beyond schedule)
            required_skill="Python",
            employee=self.employee_alice,
        )

        (
            self.constraint_verifier.verify_that(task_fits_in_schedule)
            .given(task, self.employee_alice, self.schedule_info)
            .penalizes_by(1)
        )

    def test_task_fits_in_schedule_constraint_satisfied(self):
        """Test that tasks fitting within schedule are not penalized."""
        task = create_task(
            task_id="task1",
            description="Valid Task",
            start_slot=0,
            required_skill="Python",
            employee=self.employee_alice,
        )

        (
            self.constraint_verifier.verify_that(task_fits_in_schedule)
            .given(task, self.employee_alice, self.schedule_info)
            .penalizes_by(0)
        )

    def test_unavailable_employee_constraint_violation(self):
        """Test that tasks assigned to unavailable employees are penalized."""
        # With 20 slots per working day, tomorrow starts at slot 20
        task = create_task(
            task_id="task1",
            description="Task on unavailable day",
            start_slot=20,  # Tomorrow (when Alice is unavailable)
            required_skill="Python",
            employee=self.employee_alice,
        )

        (
            self.constraint_verifier.verify_that(unavailable_employee)
            .given(task, self.employee_alice, self.schedule_info)
            .penalizes_by(1)
        )

    def test_unavailable_employee_constraint_satisfied(self):
        """Test that tasks not on unavailable days are not penalized."""
        task = create_task(
            task_id="task1",
            description="Task on available day",
            start_slot=0,  # Today (Alice is available)
            required_skill="Python",
            employee=self.employee_alice,
        )

        (
            self.constraint_verifier.verify_that(unavailable_employee)
            .given(task, self.employee_alice, self.schedule_info)
            .penalizes_by(0)
        )

    def test_maintain_project_task_order_constraint_violation(self):
        """Test that tasks violating project sequence order are penalized."""
        task1 = create_task(
            task_id="task1",
            description="Second Task",
            start_slot=0,  # Starts first but should come second
            required_skill="Python",
            project_id="project1",
            sequence_number=2,
            employee=self.employee_alice,
        )

        task2 = create_task(
            task_id="task2",
            description="First Task",
            start_slot=2,  # Starts during task1 but should come first
            required_skill="Java",
            project_id="project1",
            sequence_number=1,
            employee=self.employee_bob,
        )

        (
            self.constraint_verifier.verify_that(maintain_project_task_order)
            .given(
                task1, task2, self.employee_alice, self.employee_bob, self.schedule_info
            )
            .penalizes_by(6)
        )

    def test_maintain_project_task_order_constraint_satisfied(self):
        """Test that tasks maintaining correct project sequence are not penalized."""
        task1 = create_task(
            task_id="task1",
            description="First Task",
            start_slot=0,  # Comes first and finishes before task2
            required_skill="Python",
            project_id="project1",
            sequence_number=1,
            employee=self.employee_alice,
        )

        task2 = create_task(
            task_id="task2",
            description="Second Task",
            start_slot=5,  # Starts after task1 finishes
            required_skill="Java",
            project_id="project1",
            sequence_number=2,
            employee=self.employee_bob,
        )

        (
            self.constraint_verifier.verify_that(maintain_project_task_order)
            .given(
                task1, task2, self.employee_alice, self.employee_bob, self.schedule_info
            )
            .penalizes_by(0)
        )

    def test_maintain_project_task_order_different_projects(self):
        """Test that tasks in different projects don't affect each other's sequence."""
        task1 = create_task(
            task_id="task1",
            description="Task in Project A",
            start_slot=0,
            required_skill="Python",
            project_id="projectA",
            sequence_number=2,
            employee=self.employee_alice,
        )

        task2 = create_task(
            task_id="task2",
            description="Task in Project B",
            start_slot=2,  # Overlaps but different project
            required_skill="Java",
            project_id="projectB",
            sequence_number=1,
            employee=self.employee_bob,
        )

        (
            self.constraint_verifier.verify_that(maintain_project_task_order)
            .given(
                task1, task2, self.employee_alice, self.employee_bob, self.schedule_info
            )
            .penalizes_by(0)
        )

    def test_no_lunch_break_spanning_constraint_violation(self):
        """Test that tasks spanning lunch break are penalized."""
        task = create_task(
            task_id="task1",
            description="Task spanning lunch",
            start_slot=7,  # Starts at 12:30 (slot 7), spans lunch break
            duration_slots=4,  # 2 hours, ends at 14:30 (slot 11)
            required_skill="Python",
            employee=self.employee_alice,
        )

        (
            self.constraint_verifier.verify_that(no_lunch_break_spanning)
            .given(task, self.employee_alice, self.schedule_info)
            .penalizes_by(1)
        )

    def test_no_lunch_break_spanning_constraint_satisfied(self):
        """Test that tasks not spanning lunch break are not penalized."""
        task = create_task(
            task_id="task1",
            description="Task before lunch",
            start_slot=0,  # Starts at 9:00
            duration_slots=4,  # 2 hours, ends at 11:00
            required_skill="Python",
            employee=self.employee_alice,
        )

        (
            self.constraint_verifier.verify_that(no_lunch_break_spanning)
            .given(task, self.employee_alice, self.schedule_info)
            .penalizes_by(0)
        )

    def test_no_weekend_scheduling_constraint_satisfied(self):
        """Test that weekday tasks are not penalized.

        Note: Since our slot system only includes working days,
        is_weekend_slot should always return False for valid slots.
        """
        task = create_task(
            task_id="task1",
            description="Weekday task",
            start_slot=0,  # First slot of first working day
            required_skill="Python",
            employee=self.employee_alice,
        )

        (
            self.constraint_verifier.verify_that(no_weekend_scheduling)
            .given(task, self.employee_alice, self.schedule_info)
            .penalizes_by(0)
        )

    # ==================== SOFT CONSTRAINT TESTS ====================

    def test_undesired_day_for_employee_constraint_violation(self):
        """Test that tasks on undesired days incur soft penalty."""
        # With 20 slots per working day, day after tomorrow starts at slot 40
        task = create_task(
            task_id="task1",
            description="Task on undesired day",
            start_slot=40,  # Day after tomorrow (Alice's undesired date)
            required_skill="Python",
            employee=self.employee_alice,
        )

        (
            self.constraint_verifier.verify_that(undesired_day_for_employee)
            .given(task, self.employee_alice, self.schedule_info)
            .penalizes_by(1)
        )

    def test_undesired_day_for_employee_constraint_satisfied(self):
        """Test that tasks not on undesired days are not penalized."""
        task = create_task(
            task_id="task1",
            description="Task on neutral day",
            start_slot=0,  # Today (neutral for Alice)
            required_skill="Python",
            employee=self.employee_alice,
        )

        (
            self.constraint_verifier.verify_that(undesired_day_for_employee)
            .given(task, self.employee_alice, self.schedule_info)
            .penalizes_by(0)
        )

    def test_desired_day_for_employee_constraint_reward(self):
        """Test that tasks on desired days provide reward."""
        # Alice's desired day is today (slot 0-19)
        task = create_task(
            task_id="task1",
            description="Task on desired day",
            start_slot=0,  # Today (Alice's desired date)
            required_skill="Python",
            employee=self.employee_alice,
        )

        (
            self.constraint_verifier.verify_that(desired_day_for_employee)
            .given(task, self.employee_alice, self.schedule_info)
            .rewards()
        )

    def test_desired_day_for_employee_constraint_neutral(self):
        """Test that tasks on neutral days don't provide desired day reward."""
        task = create_task(
            task_id="task1",
            description="Task on neutral day",
            start_slot=20,  # Tomorrow (neutral for Alice)
            required_skill="Python",
            employee=self.employee_alice,
        )

        (
            self.constraint_verifier.verify_that(desired_day_for_employee)
            .given(task, self.employee_alice, self.schedule_info)
            .justifies_with()
        )

    def test_balance_employee_task_assignments_constraint_balanced(self):
        """Test that balanced task assignments don't incur penalty."""
        # Create balanced task assignments (2 tasks each)
        tasks = [
            create_task(
                "task1",
                "Alice Task 1",
                start_slot=0,
                required_skill="Python",
                employee=self.employee_alice,
            ),
            create_task(
                "task2",
                "Alice Task 2",
                start_slot=5,
                required_skill="Testing",
                employee=self.employee_alice,
            ),
            create_task(
                "task3",
                "Bob Task 1",
                start_slot=10,
                required_skill="Java",
                employee=self.employee_bob,
            ),
            create_task(
                "task4",
                "Bob Task 2",
                start_slot=15,
                required_skill="Documentation",
                employee=self.employee_bob,
            ),
        ]

        # Verify balanced assignment (both employees have 2 tasks)
        (
            self.constraint_verifier.verify_that(balance_employee_task_assignments)
            .given(
                *tasks,
                self.employee_alice,
                self.employee_bob,
                self.schedule_info,
            )
            .penalizes_by(0)
        )

    def test_balance_employee_task_assignments_constraint_imbalanced(self):
        """Test that imbalanced task assignments incur penalty."""
        # Create imbalanced task assignments (Alice: 3 tasks, Bob: 0 tasks)
        tasks = [
            create_task(
                "task1",
                "Alice Task 1",
                start_slot=0,
                required_skill="Python",
                employee=self.employee_alice,
            ),
            create_task(
                "task2",
                "Alice Task 2",
                start_slot=5,
                required_skill="Testing",
                employee=self.employee_alice,
            ),
            create_task(
                "task3",
                "Alice Task 3",
                start_slot=10,
                required_skill="Java",
                employee=self.employee_alice,
            ),
        ]

        (
            self.constraint_verifier.verify_that(balance_employee_task_assignments)
            .given(
                *tasks,
                self.employee_alice,
                self.employee_bob,
                self.schedule_info,
            )
            .penalizes()
        )

    # ==================== INTEGRATION TESTS ====================

    def test_all_constraints_together_feasible_solution(self):
        """Test all constraints working together on a feasible solution."""
        # Create a feasible mini schedule
        tasks = [
            create_task(
                "task1",
                "Valid Python Task",
                start_slot=0,  # Today (Alice's desired day)
                required_skill="Python",
                project_id="project1",
                sequence_number=1,
                employee=self.employee_alice,
            ),
            create_task(
                "task2",
                "Valid Java Task",
                start_slot=10,  # After lunch break (14:00), non-overlapping
                required_skill="Java",
                project_id="project1",
                sequence_number=2,
                employee=self.employee_alice,
            ),
            create_task(
                "task3",
                "Bob's Valid Task",
                start_slot=14,  # After lunch break (14:00)
                required_skill="Java",
                project_id="project2",
                sequence_number=1,
                employee=self.employee_bob,
            ),
        ]

        (
            self.constraint_verifier.verify_that()
            .given(
                *tasks,
                self.employee_alice,
                self.employee_bob,
                self.schedule_info,
            )
            .scores(HardSoftDecimalScore.of(Decimal("0"), Decimal("1.292893")))
        )

    def test_all_constraints_together_infeasible_solution(self):
        """Test all constraints working together on an infeasible solution."""
        # Create a mini schedule with multiple constraint violations
        tasks = [
            create_task(
                "task1",
                "Valid Python Task",
                start_slot=0,  # Today (Alice's desired day)
                required_skill="Python",
                project_id="project1",
                sequence_number=1,
                employee=self.employee_alice,
            ),
            create_task(
                "task2",
                "Invalid Skill Task",
                start_slot=20,  # Tomorrow (Alice unavailable)
                required_skill="NonExistentSkill",
                project_id="project1",
                sequence_number=2,
                employee=self.employee_alice,
            ),
            create_task(
                "task3",
                "Overlapping Task",
                start_slot=2,  # Overlaps with task1
                required_skill="Testing",
                project_id="project2",
                sequence_number=1,
                employee=self.employee_alice,
            ),
        ]

        (
            self.constraint_verifier.verify_that()
            .given(
                *tasks,
                self.employee_alice,
                self.employee_bob,
                self.schedule_info,
            )
            .scores(HardSoftDecimalScore.of(Decimal("-4"), Decimal("-0.12132")))
        )


# ==================== DATA GENERATOR FUNCTIONS ====================


def create_test_dates():
    """Generate common test dates for consistent usage across tests."""
    today = date.today()
    return {
        "today": today,
        "tomorrow": today + timedelta(days=1),
        "day_after": today + timedelta(days=2),
    }


def create_employee(
    name, skills=None, unavailable_dates=None, undesired_dates=None, desired_dates=None
):
    """Create an employee with specified attributes."""
    return Employee(
        name=name,
        skills=skills or set(),
        unavailable_dates=unavailable_dates or set(),
        undesired_dates=undesired_dates or set(),
        desired_dates=desired_dates or set(),
    )


def create_task(
    task_id,
    description="Test Task",
    duration_slots=4,
    start_slot=0,
    required_skill="Python",
    project_id=None,
    sequence_number=None,
    employee=None,
):
    """Create a task with specified attributes."""
    return Task(
        id=task_id,
        description=description,
        duration_slots=duration_slots,
        start_slot=start_slot,
        required_skill=required_skill,
        project_id=project_id,
        sequence_number=sequence_number,
        employee=employee,
    )


def create_schedule_info(total_slots=60):
    """Create a schedule info object with specified total slots.
    Default is 60 slots = 3 working days * 20 slots per working day.
    """
    return ScheduleInfo(total_slots=total_slots, base_date=date.today())


def create_standard_employees(dates):
    """Create the standard set of test employees used across multiple tests."""
    return {
        "alice": create_employee(
            name="Alice",
            skills={"Python", "Java", "Testing"},
            unavailable_dates={dates["tomorrow"]},
            undesired_dates={dates["day_after"]},
            desired_dates={dates["today"]},
        ),
        "bob": create_employee(
            name="Bob",
            skills={"Java", "Documentation", "Management"},
        ),
        "charlie": create_employee(
            name="Charlie",
            skills={"Python", "Testing", "DevOps"},
        ),
    }


if __name__ == "__main__":
    """Direct execution for non-pytest testing"""
    logger.section("Constraint Solver Tests")
    logger.info(
        "Note: This test suite is designed for pytest. For best results, run with:"
    )
    logger.info("  pytest tests/test_constraints.py -v")
    logger.info("  YUGA_DEBUG=true pytest tests/test_constraints.py -v -s")

    # Create test results tracker
    results = create_test_results(logger)

    try:
        # Create test instance
        test_instance = TestConstraints()
        test_instance.setup_method()

        # Run a few sample tests
        logger.info("Running sample constraint tests...")

        sample_tests = [
            (
                "required_skill_violation",
                test_instance.test_required_skill_constraint_violation,
            ),
            (
                "required_skill_satisfied",
                test_instance.test_required_skill_constraint_satisfied,
            ),
            (
                "no_overlapping_violation",
                test_instance.test_no_overlapping_tasks_constraint_violation,
            ),
            (
                "task_within_schedule",
                test_instance.test_task_within_schedule_constraint_satisfied,
            ),
        ]

        for test_name, test_func in sample_tests:
            results.run_test(test_name, test_func)

        logger.info(f"✅ Completed {len(sample_tests)} sample constraint tests")

    except Exception as e:
        logger.error(f"Failed to run constraint tests: {e}")
        results.add_result("constraint_tests_setup", False, str(e))

    # Generate summary and exit with appropriate code
    all_passed = results.summary()

    if not all_passed:
        logger.info(
            "💡 Hint: Use 'pytest tests/test_constraints.py' for full test coverage"
        )

    sys.exit(0 if all_passed else 1)
