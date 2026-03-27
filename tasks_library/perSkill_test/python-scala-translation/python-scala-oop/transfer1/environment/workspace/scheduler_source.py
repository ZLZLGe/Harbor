from abc import ABC, abstractmethod
from dataclasses import dataclass


class Job(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def run(self) -> str:
        pass


@dataclass
class CsvJob(Job):
    path: str

    def __init__(self, name: str, path: str):
        super().__init__(name)
        self.path = path

    def run(self) -> str:
        return f"csv:{self.name}:{self.path}"


@dataclass
class ApiJob(Job):
    endpoint: str

    def __init__(self, name: str, endpoint: str):
        super().__init__(name)
        self.endpoint = endpoint

    def run(self) -> str:
        return f"api:{self.name}:{self.endpoint}"


class JobFactory:
    @staticmethod
    def from_kind(kind: str, name: str, arg: str) -> Job:
        if kind == "csv":
            return CsvJob(name, arg)
        return ApiJob(name, arg)


def run_batch(jobs: list[Job]) -> list[str]:
    return [job.run() for job in jobs]
