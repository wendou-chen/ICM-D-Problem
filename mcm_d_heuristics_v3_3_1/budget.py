"""
budget.py
Execution budget management for heuristics.
Controls termination based on time limit or max evaluations.
"""
import time
from typing import Optional, Callable, Any
from .problem import OptimizationProblem

class BudgetExhaustedException(Exception):
    pass

class Budget:
    def __init__(self, time_limit: Optional[float] = None, max_evals: Optional[int] = None):
        self.time_limit = time_limit
        self.max_evals = max_evals
        self.start_time = None
        self.eval_count = 0
        
    def start(self):
        self.start_time = time.time()
        self.eval_count = 0
        
    def check(self):
        """Raise BudgetExhaustedException if limit reached."""
        if self.max_evals is not None and self.eval_count >= self.max_evals:
            raise BudgetExhaustedException("Max evals reached")
        
        if self.time_limit is not None and self.start_time is not None:
            if time.time() - self.start_time >= self.time_limit:
                 raise BudgetExhaustedException("Time limit reached")
                 
    def increment_eval(self, n: int = 1):
        self.eval_count += n
        self.check() # Check immediately after increment

class BudgetedEvaluator:
    """Wraps an OptimizationProblem to enforce budget."""
    def __init__(self, problem: OptimizationProblem, budget: Budget):
        self.problem = problem
        self.budget = budget
        # Monkey patch or wrap? Wrapper is safer.
        
    def evaluate_solution(self, solution: Any, **kwargs) -> float:
        self.budget.increment_eval()
        return self.problem.evaluate_solution(solution, **kwargs)
        
    def __getattr__(self, name):
        """Pass through other lookups to the underlying problem."""
        return getattr(self.problem, name)

def run_with_budget(
    func: Callable[[], Any], 
    budget: Budget
) -> Any:
    """Run a function (e.g. an algorithm loop) with budget monitoring."""
    budget.start()
    try:
        return func()
    except BudgetExhaustedException:
        print("[Budget] Terminated early.")
        return None  # Or handle as needed
