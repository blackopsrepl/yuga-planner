from dataclasses import dataclass, field


# =========================
#        DATA MODELS
# =========================
@dataclass(frozen=True, kw_only=True)
class CountDistribution:
    count: int
    weight: float


@dataclass(frozen=True, kw_only=True)
class SkillSet:
    required_skills: tuple[str, ...]
    optional_skills: tuple[str, ...]


@dataclass(kw_only=True)
class TimeTableDataParameters:
    skill_set: SkillSet
    days_in_schedule: int
    employee_count: int
    optional_skill_distribution: tuple[CountDistribution, ...]
    availability_count_distribution: tuple[CountDistribution, ...]
    random_seed: int = field(default=37)
