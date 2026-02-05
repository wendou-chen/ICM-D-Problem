import math
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.q1.capacity import rocket_launches_required, completion_time_years, elevator_total_capacity_tpy
from src.q1.feasibility import lower_bound_time_years, alpha_star
from configs.constants import Problem, Elevator

def test_rocket_launches_required():
    # N_B(1e8,150)=666667
    assert rocket_launches_required(1e8, 150.0) == 666667
    # N_B(1e8,100)=1000000
    assert rocket_launches_required(1e8, 100.0) == 1_000_000
    print("test_rocket_launches_required passed")

def test_elevator_capacity():
    # C_E = 3 * 179000 = 537000
    cap = elevator_total_capacity_tpy(3, 179000)
    assert cap == 537000
    print("test_elevator_capacity passed")

def test_completion_time_A():
    # T_A = 1e8 / 537000 approx 186.22
    cap = 537000
    t = completion_time_years(1e8, cap)
    # 186.219739...
    assert abs(t - 186.219739) < 1e-3
    print("test_completion_time_A passed")

def test_alpha_star_bounds():
    # alpha should be between 0 and 1
    alpha = alpha_star(100, 100)
    assert alpha == 0.5
    
    alpha = alpha_star(100, 300)
    assert alpha == 0.25 # 100 / (100+300)
    print("test_alpha_star_bounds passed")

def test_constants_integrity():
    # Ensure constants match problem statement
    assert Problem.TOTAL_MASS_TONS == 100_000_000
    assert Elevator.NUM_HARBOURS == 3
    print("test_constants_integrity passed")

if __name__ == "__main__":
    print("Running manual tests...")
    test_rocket_launches_required()
    test_elevator_capacity()
    test_completion_time_A()
    test_alpha_star_bounds()
    test_constants_integrity()
    print("All tests passed!")
