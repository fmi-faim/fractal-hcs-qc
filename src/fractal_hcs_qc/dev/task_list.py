"""Contains the list of tasks available to fractal."""

from fractal_task_tools.task_models import (
    NonParallelTask,
)

AUTHORS = "Facility for Advanced Imaging and Microscopy (FAIM), FMI, Basel"

DOCS_LINK = None


TASK_LIST = [
    NonParallelTask(
        name="Consolidate Tables",
        executable="consolidate_tables_task.py",
        # Modify the meta according to your task requirements
        # If the task requires a GPU, add "needs_gpu": True
        meta={"cpus_per_task": 1, "mem": 4000},
        category="Table Processing",
        tags=["Tables", "HCS"],
        docs_info="file:docs_info/consolidate_tables_task.md",
        # Uncomment the following line to forbid re-running the task on already
        # processed images
        # input_types={"is_blurred": False},
        # output_types={"is_blurred": True},
    ),
]
