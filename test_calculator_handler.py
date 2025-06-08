import test_calculator
from with_replay import not_implemented_handler


if __name__ == "__main__":
    with not_implemented_handler():
        test_calculator.main()
