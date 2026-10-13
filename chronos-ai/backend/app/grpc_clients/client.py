"""gRPC client stubs used by the FastAPI gateway (spec sections 4.1 & 5).

All calls carry an explicit deadline. The gateway talks to the single MVP gRPC
server; targets are env-configurable so services can be split later.
"""
from __future__ import annotations

import functools

import grpc

from ..core.config import settings
from ..grpc_gen import (
    ai_extraction_pb2_grpc,
    artifact_pb2_grpc,
    clarification_pb2_grpc,
    date_normalization_pb2_grpc,
    event_validation_pb2_grpc,
    ics_generation_pb2_grpc,
    input_processing_pb2_grpc,
    reminder_pb2_grpc,
)


@functools.lru_cache(maxsize=None)
def _channel(target: str) -> grpc.Channel:
    return grpc.insecure_channel(
        target,
        options=[
            ("grpc.max_receive_message_length", 16 * 1024 * 1024),
            ("grpc.max_send_message_length", 16 * 1024 * 1024),
        ],
    )


def deadline() -> float:
    return settings.GRPC_DEADLINE_SECONDS


class Clients:
    """Lazily-constructed stubs. For the MVP every target points at the same server."""

    @property
    def input(self):
        return input_processing_pb2_grpc.InputProcessingServiceStub(
            _channel(settings.GRPC_INPUT_PROCESSING_TARGET))

    @property
    def extraction(self):
        return ai_extraction_pb2_grpc.AIExtractionServiceStub(
            _channel(settings.GRPC_AI_EXTRACTION_TARGET))

    @property
    def normalize(self):
        return date_normalization_pb2_grpc.DateNormalizationServiceStub(
            _channel(settings.GRPC_DATE_NORMALIZATION_TARGET))

    @property
    def validation(self):
        return event_validation_pb2_grpc.EventValidationServiceStub(
            _channel(settings.GRPC_EVENT_VALIDATION_TARGET))

    @property
    def clarification(self):
        return clarification_pb2_grpc.ClarificationServiceStub(
            _channel(settings.GRPC_CLARIFICATION_TARGET))

    @property
    def reminder(self):
        return reminder_pb2_grpc.ReminderServiceStub(
            _channel(settings.GRPC_REMINDER_TARGET))

    @property
    def ics(self):
        return ics_generation_pb2_grpc.ICSGenerationServiceStub(
            _channel(settings.GRPC_ICS_GENERATION_TARGET))

    @property
    def ics_validation(self):
        return ics_generation_pb2_grpc.ICSValidationServiceStub(
            _channel(settings.GRPC_ICS_GENERATION_TARGET))

    @property
    def artifact(self):
        return artifact_pb2_grpc.ArtifactServiceStub(
            _channel(settings.GRPC_ARTIFACT_TARGET))


clients = Clients()
