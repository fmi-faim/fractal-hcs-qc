"""Contains the list of tasks available to fractal."""

from fractal_task_tools.task_models import (
    ParallelTask,
)

AUTHORS = "Jan Eglinger"


DOCS_LINK = None


TASK_LIST = [
    
    
    ParallelTask(
        name="Gaussian Blur",
        executable="gaussian_blur_task.py",
        # Modify the meta according to your task requirements
        # If the task requires a GPU, add "needs_gpu": True
        meta={"cpus_per_task": 1, "mem": 4000},
        category="Image Processing",
        tags=["Denoising", "Gaussian Blur"],
        docs_info="file:docs_info/gaussian_blur_task.md",
        # Uncomment the following line to forbid re-running the task on already
        # processed images
        # input_types={"is_blurred": False},
        output_types={"is_blurred": True},
    ),
    
    
]
