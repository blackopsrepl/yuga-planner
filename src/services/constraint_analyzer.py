from typing import Dict, List, Any
from constraint_solvers.timetable.domain import EmployeeSchedule
from constraint_solvers.timetable.solver import solution_manager


class ConstraintAnalyzerService:
    """
    Service for analyzing scheduling solutions using Timefold's native constraint analysis.

    This service provides methods to analyze constraint violations, generate suggestions,
    and understand solution quality using Timefold's built-in ScoreAnalysis and SolutionManager APIs.
    """

    @staticmethod
    def analyze_constraint_violations(schedule: EmployeeSchedule) -> str:
        """
        Analyze constraint violations in a schedule using Timefold's native score analysis.

        Args:
            schedule: The schedule to analyze

        Returns:
            Detailed string describing constraint violations and their breakdown
        """
        if not schedule.score or schedule.score.hard_score >= 0:
            return "No constraint violations detected."

        # Get Timefold's solution manager and analyze the schedule
        score_analysis = solution_manager.analyze(schedule)

        # Return the built-in summary
        return score_analysis.summary

    @staticmethod
    def get_detailed_analysis(schedule: EmployeeSchedule) -> Dict[str, Any]:
        """
        Get detailed constraint analysis as a structured dictionary.

        Args:
            schedule: The schedule to analyze

        Returns:
            Dictionary containing detailed constraint analysis information
        """
        score_analysis = solution_manager.analyze(schedule)

        analysis_result = {
            "total_score": str(score_analysis.score),
            "hard_score": score_analysis.score.hard_score,
            "soft_score": score_analysis.score.soft_score,
            "constraints": {},
        }

        # Analyze each constraint
        for (
            constraint_ref,
            constraint_analysis,
        ) in score_analysis.constraint_map.items():
            constraint_id = constraint_ref.constraint_id
            constraint_info = {
                "score": str(constraint_analysis.score),
                "match_count": constraint_analysis.match_count,
                "matches": [],
            }

            # Get details for each constraint match
            for match_analysis in constraint_analysis.matches:
                match_info = {
                    "score": str(match_analysis.score),
                    "justification": str(match_analysis.justification)
                    if match_analysis.justification
                    else None,
                }
                constraint_info["matches"].append(match_info)

            analysis_result["constraints"][constraint_id] = constraint_info

        return analysis_result

    @staticmethod
    def get_broken_constraints(schedule: EmployeeSchedule) -> List[Dict[str, Any]]:
        """
        Get a list of broken constraints with their details.

        Args:
            schedule: The schedule to analyze

        Returns:
            List of dictionaries, each containing information about a broken constraint
        """
        score_analysis = solution_manager.analyze(schedule)
        broken_constraints = []

        for (
            constraint_ref,
            constraint_analysis,
        ) in score_analysis.constraint_map.items():
            # Only include constraints that have a negative impact on the score
            if (
                constraint_analysis.score.hard_score < 0
                or constraint_analysis.score.soft_score < 0
            ):

                broken_constraints.append(
                    {
                        "constraint_id": constraint_ref.constraint_id,
                        "score": str(constraint_analysis.score),
                        "hard_score": constraint_analysis.score.hard_score,
                        "soft_score": constraint_analysis.score.soft_score,
                        "match_count": constraint_analysis.match_count,
                        "constraint_name": constraint_ref.constraint_name,
                    }
                )

        return broken_constraints

    @staticmethod
    def compare_solutions(
        old_schedule: EmployeeSchedule, new_schedule: EmployeeSchedule
    ) -> Dict[str, Any]:
        """
        Compare two solutions and identify what changed between them.

        Args:
            old_schedule: The previous schedule solution
            new_schedule: The new schedule solution

        Returns:
            Dictionary containing the differences between the two solutions
        """
        old_analysis = solution_manager.analyze(old_schedule)
        new_analysis = solution_manager.analyze(new_schedule)

        # Calculate the difference
        diff = old_analysis - new_analysis

        comparison_result = {
            "old_score": str(old_analysis.score),
            "new_score": str(new_analysis.score),
            "score_difference": str(diff.score),
            "improved": (
                new_analysis.score.hard_score > old_analysis.score.hard_score
                or (
                    new_analysis.score.hard_score == old_analysis.score.hard_score
                    and new_analysis.score.soft_score > old_analysis.score.soft_score
                )
            ),
            "changed_constraints": {},
        }

        # Analyze changes in constraints
        for constraint_ref, constraint_analysis in diff.constraint_map.items():
            comparison_result["changed_constraints"][constraint_ref.constraint_id] = {
                "score_difference": str(constraint_analysis.score),
                "match_count": constraint_analysis.match_count,
                "changes": [
                    str(match.justification)
                    for match in constraint_analysis.matches
                    if match.justification
                ],
            }

        return comparison_result

    @staticmethod
    def get_heat_map_data(schedule: EmployeeSchedule) -> Dict[Any, Dict[str, Any]]:
        """
        Get heat map data showing which planning entities have the most constraint violations.

        Args:
            schedule: The schedule to analyze

        Returns:
            Dictionary mapping planning entities to their constraint impact
        """
        score_explanation = solution_manager.explain(schedule)
        indictment_map = score_explanation.indictment_map

        heat_map_data = {}

        # Process indictments for tasks
        for task in schedule.tasks:
            indictment = indictment_map.get(task)

            if indictment is not None:
                heat_map_data[task] = {
                    "total_score": str(indictment.score),
                    "hard_score": indictment.score.hard_score,
                    "soft_score": indictment.score.soft_score,
                    "constraint_matches": [
                        {
                            "constraint_name": match.constraint_name,
                            "score": str(match.score),
                        }
                        for match in indictment.constraint_match_set
                    ],
                }

        # Process indictments for employees
        for employee in schedule.employees:
            indictment = indictment_map.get(employee)

            if indictment is not None:
                heat_map_data[employee] = {
                    "total_score": str(indictment.score),
                    "hard_score": indictment.score.hard_score,
                    "soft_score": indictment.score.soft_score,
                    "constraint_matches": [
                        {
                            "constraint_name": match.constraint_name,
                            "score": str(match.score),
                        }
                        for match in indictment.constraint_match_set
                    ],
                }

        return heat_map_data

    @staticmethod
    def generate_improvement_suggestions(schedule: EmployeeSchedule) -> List[str]:
        """
        Generate improvement suggestions based on constraint analysis.

        Args:
            schedule: The schedule to analyze

        Returns:
            List of actionable suggestions for improving the schedule
        """
        if not schedule.score or schedule.score.hard_score >= 0:
            return [
                "Schedule is feasible. Consider optimizing soft constraints for better quality."
            ]

        broken_constraints = ConstraintAnalyzerService.get_broken_constraints(schedule)
        suggestions = []

        # Generate suggestions based on broken constraint types
        for constraint in broken_constraints:
            constraint_id = constraint["constraint_id"].lower()

            match constraint_id:
                case constraint_id if "skill" in constraint_id:
                    suggestions.append(
                        f"Skill constraint violation: Consider adding employees with required skills "
                        f"or reassigning tasks ({constraint['match_count']} violations)"
                    )

                case constraint_id if "availability" in constraint_id or "time" in constraint_id:
                    suggestions.append(
                        f"Time/Availability constraint violation: Check employee schedules and "
                        f"task timing ({constraint['match_count']} violations)"
                    )

                case constraint_id if "sequence" in constraint_id or "order" in constraint_id:
                    suggestions.append(
                        f"Sequencing constraint violation: Review task dependencies and ordering "
                        f"({constraint['match_count']} violations)"
                    )

                case constraint_id if "capacity" in constraint_id or "workload" in constraint_id:
                    suggestions.append(
                        f"Capacity constraint violation: Distribute workload more evenly or "
                        f"add more resources ({constraint['match_count']} violations)"
                    )

                case _:
                    suggestions.append(
                        f"Constraint '{constraint['constraint_id']}' violated "
                        f"({constraint['match_count']} times) - review constraint definition"
                    )

        if not suggestions:
            suggestions.append(
                "Hard constraints violated. Review constraint definitions and problem data."
            )

        return suggestions
