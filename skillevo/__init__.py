"""SkillEvo: calibrated skill selection and tiered memory for tool-using agents.

The package is deliberately dependency-free (Python standard library only) so
that the reported experiments can be reproduced on a CPU-only machine.
"""

__version__ = "0.1.0"

from .types import BANDS, CLASS_NAMES, FAMILIES, Skill, TaskSpec  # noqa: F401
