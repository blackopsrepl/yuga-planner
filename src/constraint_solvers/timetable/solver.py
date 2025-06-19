from timefold.solver import SolverManager, SolverFactory, SolutionManager
from timefold.solver.config import (
    SolverConfig,
    ScoreDirectorFactoryConfig,
    # TerminationConfig,
    # Duration,
)

from .domain import *
from .constraints import define_constraints


solver_config: SolverConfig = SolverConfig(
    solution_class=EmployeeSchedule,
    entity_class_list=[Task],
    score_director_factory_config=ScoreDirectorFactoryConfig(
        constraint_provider_function=define_constraints
    ),
    # termination_config=TerminationConfig(spent_limit=Duration(seconds=30)),  # Commented out to allow unlimited solving time
)

solver_manager: SolverManager = SolverManager.create(
    SolverFactory.create(solver_config)
)
solution_manager: SolutionManager = SolutionManager.create(solver_manager)
