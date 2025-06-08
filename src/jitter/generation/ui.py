from jitter.source_manipulation.inspection import get_function_lines


# ANSI color codes for terminal output
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


def show_implementation_comparison_and_confirm(func, new_code: str) -> bool:
    """
    Shows the old and new implementation of a function and asks for user confirmation.

    Args:
        func: The function object to be replaced
        new_code: The new implementation code

    Returns:
        bool: True if user confirms, False otherwise
    """
    print(f"\n{'='*60}")
    print(f"IMPLEMENTATION REPLACEMENT FOR: {func.__name__}")
    print(f"{'='*60}")

    # Get current implementation
    try:
        location = get_function_lines(func)
        print(f"File: {Colors.CYAN}{location.filename}{Colors.END}")
        print(f"Lines: {Colors.CYAN}{location.start_line}-{location.end_line}{Colors.END}")

        # Show old implementation
        print(f"\n{Colors.RED}{Colors.BOLD}{'-'*30} OLD IMPLEMENTATION {'-'*30}{Colors.END}")
        with open(location.filename) as f:
            lines = f.readlines()
            for i, line in enumerate(lines[location.start_line-1:location.end_line], location.start_line):
                print(f"{Colors.RED}{i:4d}: {line.rstrip()}{Colors.END}")

        # Show new implementation
        print(f"\n{Colors.GREEN}{Colors.BOLD}{'-'*30} NEW IMPLEMENTATION {'-'*30}{Colors.END}")
        for i, line in enumerate(new_code.split('\n'), location.start_line):
            print(f"{Colors.GREEN}{i:4d}: {line}{Colors.END}")

    except Exception as e:
        print(f"{Colors.YELLOW}Could not show old implementation: {e}{Colors.END}")
        print(f"\n{Colors.GREEN}{Colors.BOLD}{'-'*30} NEW IMPLEMENTATION {'-'*30}{Colors.END}")
        for i, line in enumerate(new_code.split('\n'), 1):
            print(f"{Colors.GREEN}{i:4d}: {line}{Colors.END}")

    print(f"\n{'='*60}")

    # Ask for confirmation
    while True:
        response = input("Replace implementation? (y/n): ").strip().lower()
        if response in ('y', 'yes'):
            return True
        elif response in ('n', 'no'):
            return False
        else:
            print("Please enter 'y' or 'n'")
