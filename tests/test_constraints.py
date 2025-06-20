import pytest
from datetime import date, timedelta
from decimal import Decimal
from timefold.solver.test import ConstraintVerifier
from timefold.solver.score import HardSoftDecimalScore

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

    # ==================== HARD CONSTRAINT TESTS ====================

    def test_required_skill_constraint_violation(self):
        """Test that tasks requiring skills not possessed by assigned employee are penalized."""
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

    def test_required_skill_constraint_satisfied(self):
        """Test that tasks assigned to employees with required skills are not penalized."""
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

    def test_required_skill_constraint_unassigned_task(self):
        """Test that unassigned tasks don't trigger required skill constraint."""
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

    def test_no_overlapping_tasks_constraint_violation(self):
        """Test that overlapping tasks for the same employee are penalized."""
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

    def test_no_overlapping_tasks_constraint_different_employees(self):
        """Test that overlapping tasks for different employees are not penalized."""
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

    def test_no_overlapping_tasks_constraint_adjacent_tasks(self):
        """Test that adjacent (non-overlapping) tasks for the same employee are not penalized."""
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

    def test_task_within_schedule_constraint_violation(self):
        """Test that tasks starting before slot 0 are penalized."""
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

    def test_task_within_schedule_constraint_satisfied(self):
        """Test that tasks starting at valid slots are not penalized."""
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

    def test_task_fits_in_schedule_constraint_violation(self):
        """Test that tasks extending beyond schedule end are penalized."""
        task = create_task(
            task_id="task1",
            description="Overlong Task",
            duration_slots=10,  # Task extends to slot 64 (beyond 59)
            start_slot=55,
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
        # Assuming 16 slots per working day, tomorrow starts at slot 16
        task = create_task(
            task_id="task1",
            description="Task on unavailable day",
            start_slot=16,  # Tomorrow (when Alice is unavailable)
            required_skill="Python",
            employee=self.employee_alice,
        )

        (
            self.constraint_verifier.verify_that(unavailable_employee)
            .given(task, self.employee_alice, self.schedule_info)
            .penalizes_by(1)
        )

    def test_unavailable_employee_constraint_satisfied(self):
        """Test that tasks assigned on available days are not penalized."""
        task = create_task(
            task_id="task1",
            description="Task on available day",
            start_slot=0,  # Today (when Alice is available)
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
            start_slot=6,  # Starts in morning (slot 6)
            duration_slots=4,  # Ends in afternoon (slot 10), spans lunch
            required_skill="Python",
            employee=self.employee_alice,
        )

        (
            self.constraint_verifier.verify_that(no_lunch_break_spanning)
            .given(task, self.employee_alice, self.schedule_info)
            .penalizes_by(1)
        )

    def test_no_lunch_break_spanning_constraint_satisfied_morning(self):
        """Test that tasks contained in morning session are not penalized."""
        task = create_task(
            task_id="task1",
            description="Morning task",
            start_slot=2,  # Morning session
            duration_slots=4,  # Stays in morning (slots 2-5)
            required_skill="Python",
            employee=self.employee_alice,
        )

        (
            self.constraint_verifier.verify_that(no_lunch_break_spanning)
            .given(task, self.employee_alice, self.schedule_info)
            .penalizes_by(0)
        )

    def test_no_lunch_break_spanning_constraint_satisfied_afternoon(self):
        """Test that tasks contained in afternoon session are not penalized."""
        task = create_task(
            task_id="task1",
            description="Afternoon task",
            start_slot=10,  # Afternoon session (slot 10 = 3rd hour of afternoon)
            duration_slots=4,  # Stays in afternoon (slots 10-13)
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
        # Assuming 16 slots per working day, day after tomorrow starts at slot 32
        task = create_task(
            task_id="task1",
            description="Task on undesired day",
            start_slot=32,  # Day after tomorrow (Alice's undesired date)
            required_skill="Python",
            employee=self.employee_alice,
        )

        (
            self.constraint_verifier.verify_that(undesired_day_for_employee)
            .given(task, self.employee_alice, self.schedule_info)
            .penalizes_by(1)
        )

    def test_undesired_day_for_employee_constraint_satisfied(self):
        """Test that tasks on neutral days don't incur undesired day penalty."""
        task = create_task(
            task_id="task1",
            description="Task on neutral day",
            start_slot=0,  # Today (neutral for Alice, though it's also desired)
            required_skill="Python",
            employee=self.employee_alice,
        )

        (
            self.constraint_verifier.verify_that(undesired_day_for_employee)
            .given(task, self.employee_alice, self.schedule_info)
            .penalizes_by(0)
        )

    def test_desired_day_for_employee_constraint_reward(self):
        """Test that tasks on desired days provide soft reward."""
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
            start_slot=16,  # Tomorrow (neutral for Alice)
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
                start_slot=8,  # Afternoon session, non-overlapping
                required_skill="Java",
                project_id="project1",
                sequence_number=2,
                employee=self.employee_alice,
            ),
            create_task(
                "task3",
                "Bob's Valid Task",
                start_slot=12,
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
            .scores(HardSoftDecimalScore.of(Decimal("-5"), Decimal("-0.12132")))
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


def create_schedule_info(total_slots=48):
    """Create a schedule info object with specified total slots.
    Default is 48 slots = 3 working days * 16 slots per working day.
    """
    return ScheduleInfo(total_slots=total_slots)


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
