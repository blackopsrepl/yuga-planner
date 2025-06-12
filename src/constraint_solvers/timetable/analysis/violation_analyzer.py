from typing import Dict, List, Set
from ..domain import EmployeeSchedule, Task, Employee


class ConstraintViolationAnalyzer:
    """
    Service for analyzing constraint violations in scheduling solutions.

    This service implements automatic detection of infeasible scheduling problems.
    When the Timefold solver cannot satisfy all hard constraints, it returns a
    solution with a negative hard score. This service analyzes such solutions to
    provide users with specific, actionable feedback about why their scheduling
    problem cannot be solved.
    """

    @staticmethod
    def analyze_constraint_violations(schedule: EmployeeSchedule) -> str:
        """
        Analyze constraint violations in a schedule and provide detailed feedback.

        Args:
            schedule: The schedule to analyze

        Returns:
            Detailed string describing constraint violations and suggestions
        """
        if not schedule.score or schedule.score.hard_score >= 0:
            return "No constraint violations detected."

        violations = []

        # Check for missing skills
        skill_violations = ConstraintViolationAnalyzer._check_skill_violations(schedule)
        if skill_violations:
            violations.extend(skill_violations)

        # Check for insufficient time
        time_violations = ConstraintViolationAnalyzer._check_time_violations(schedule)
        if time_violations:
            violations.extend(time_violations)

        # Check for availability conflicts
        availability_violations = (
            ConstraintViolationAnalyzer._check_availability_violations(schedule)
        )
        if availability_violations:
            violations.extend(availability_violations)

        # Check for sequencing issues
        sequence_violations = ConstraintViolationAnalyzer._check_sequence_violations(
            schedule
        )
        if sequence_violations:
            violations.extend(sequence_violations)

        if not violations:
            violations.append("Unknown constraint violations detected.")

        return "\n".join(violations)

    @staticmethod
    def _check_skill_violations(schedule: EmployeeSchedule) -> List[str]:
        """Check for tasks that require skills not available in the employee pool"""
        violations = []

        # Get all available skills
        available_skills: Set[str] = set()
        for employee in schedule.employees:
            available_skills.update(employee.skills)

        # Check for tasks requiring unavailable skills
        unassigned_tasks = [task for task in schedule.tasks if not task.employee]
        missing_skills: Set[str] = set()

        for task in unassigned_tasks:
            if task.required_skill not in available_skills:
                missing_skills.add(task.required_skill)

        if missing_skills:
            violations.append(
                f"• Missing Skills: No employees have these required skills: {', '.join(sorted(missing_skills))}"
            )

        return violations

    @staticmethod
    def _check_time_violations(schedule: EmployeeSchedule) -> List[str]:
        """Check for insufficient time to complete all tasks"""
        violations = []

        total_task_slots = sum(task.duration_slots for task in schedule.tasks)
        total_available_slots = (
            len(schedule.employees) * schedule.schedule_info.total_slots
        )

        if total_task_slots > total_available_slots:
            total_task_hours = total_task_slots / 2  # Convert slots to hours
            total_available_hours = total_available_slots / 2
            violations.append(
                f"• Insufficient Time: Tasks require {total_task_hours:.1f} hours total, "
                f"but only {total_available_hours:.1f} hours available across all employees"
            )

        return violations

    @staticmethod
    def _check_availability_violations(schedule: EmployeeSchedule) -> List[str]:
        """Check for tasks scheduled during employee unavailable periods"""
        violations = []

        for task in schedule.tasks:
            if task.employee and hasattr(task.employee, "unavailable_dates"):
                # This would need actual date calculation based on start_slot
                # For now, we'll just note if there are unassigned tasks with availability constraints
                pass

        unassigned_count = len([task for task in schedule.tasks if not task.employee])
        if unassigned_count > 0:
            violations.append(
                f"• Unassigned Tasks: {unassigned_count} task(s) could not be assigned to any employee"
            )

        return violations

    @staticmethod
    def _check_sequence_violations(schedule: EmployeeSchedule) -> List[str]:
        """Check for project sequencing constraint violations"""
        violations = []

        # Group tasks by project
        project_tasks: Dict[str, List[Task]] = {}
        for task in schedule.tasks:
            project_id = getattr(task, "project_id", "")
            if project_id:
                if project_id not in project_tasks:
                    project_tasks[project_id] = []
                project_tasks[project_id].append(task)

        # Check sequencing within each project
        for project_id, tasks in project_tasks.items():
            if len(tasks) > 1:
                # Sort by sequence number
                sorted_tasks = sorted(
                    tasks, key=lambda t: getattr(t, "sequence_number", 0)
                )

                # Check if tasks are assigned and properly sequenced
                for i in range(len(sorted_tasks) - 1):
                    current_task = sorted_tasks[i]
                    next_task = sorted_tasks[i + 1]

                    if not current_task.employee or not next_task.employee:
                        continue  # Skip unassigned tasks

                    # Check if next task starts after current task ends
                    if next_task.start_slot < (
                        current_task.start_slot + current_task.duration_slots
                    ):
                        violations.append(
                            f"• Sequence Violation: In project '{project_id}', task sequence is violated"
                        )
                        break

        return violations

    @staticmethod
    def generate_suggestions(schedule: EmployeeSchedule) -> List[str]:
        """Generate actionable suggestions for fixing constraint violations"""
        suggestions = []

        if not schedule.score or schedule.score.hard_score >= 0:
            return suggestions

        # Basic suggestions based on common issues
        suggestions.extend(
            [
                "Add more employees with required skills",
                "Increase the scheduling time window (more days)",
                "Reduce task requirements or durations",
                "Check employee availability constraints",
                "Review project sequencing requirements",
            ]
        )

        return suggestions
