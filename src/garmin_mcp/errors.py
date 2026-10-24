from dataclasses import dataclass


@dataclass
class Fault(Exception):
    code: str
    message: str
    retryable: bool = False
    http_status: int | None = None

    def __str__(self):
        return self.message

    def as_dict(self):
        return {
            "code": self.code,
            "message": self.message,
            "retryable": self.retryable,
            "http_status": self.http_status,
        }
