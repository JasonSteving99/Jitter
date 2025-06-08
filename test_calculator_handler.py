import test_calculator
from with_replay import not_implemented_handler

def main():
    # Basic arithmetic formula: (5 + 3) * 2 - 4 / 2 = 14
    result1 = test_calculator.add(5, 3)
    result2 = test_calculator.multiply(result1, 2)
    result3 = test_calculator.divide(4, 2)
    final_result = test_calculator.subtract(result2, result3)
    print(f"Formula result: {final_result}")

    # Another formula: sqrt(16) + 2^3 = 12
    # sqrt_result = square_root(16)
    # power_result = power(2, 3)
    # final_result2 = add(sqrt_result, power_result)
    # print(f"Second formula result: {final_result2}")

if __name__ == "__main__":
    with not_implemented_handler():
        main()
