from dataclasses import dataclass


@dataclass
class GeneratedImplementation:
    """Result of generating an implementation with necessary imports."""
    implementation: str
    necessary_imports: list[str]