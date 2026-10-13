"""Bootstrap a single gRPC server hosting all Chronos services (MVP single container).

Includes gRPC health checking and reflection in development. Requires generated stubs.
Run: python -m app.grpc_servers.server
"""
from __future__ import annotations

from concurrent import futures

import grpc
from grpc_health.v1 import health, health_pb2, health_pb2_grpc
from grpc_reflection.v1alpha import reflection

from ..core.config import settings
from ..core.logging import configure_logging, log
from ..grpc_gen import (
    ai_extraction_pb2,
    ai_extraction_pb2_grpc,
    artifact_pb2,
    artifact_pb2_grpc,
    clarification_pb2,
    clarification_pb2_grpc,
    date_normalization_pb2,
    date_normalization_pb2_grpc,
    event_validation_pb2,
    event_validation_pb2_grpc,
    ics_generation_pb2,
    ics_generation_pb2_grpc,
    input_processing_pb2,
    input_processing_pb2_grpc,
    reminder_pb2,
    reminder_pb2_grpc,
)
from . import servicers


def build_server() -> grpc.Server:
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        options=[
            ("grpc.max_receive_message_length", 16 * 1024 * 1024),
            ("grpc.max_send_message_length", 16 * 1024 * 1024),
        ],
    )

    input_processing_pb2_grpc.add_InputProcessingServiceServicer_to_server(
        servicers.InputProcessingServicer(), server)
    ai_extraction_pb2_grpc.add_AIExtractionServiceServicer_to_server(
        servicers.AIExtractionServicer(), server)
    date_normalization_pb2_grpc.add_DateNormalizationServiceServicer_to_server(
        servicers.DateNormalizationServicer(), server)
    event_validation_pb2_grpc.add_EventValidationServiceServicer_to_server(
        servicers.EventValidationServicer(), server)
    clarification_pb2_grpc.add_ClarificationServiceServicer_to_server(
        servicers.ClarificationServicer(), server)
    reminder_pb2_grpc.add_ReminderServiceServicer_to_server(
        servicers.ReminderServicer(), server)
    ics_generation_pb2_grpc.add_ICSGenerationServiceServicer_to_server(
        servicers.ICSGenerationServicer(), server)
    ics_generation_pb2_grpc.add_ICSValidationServiceServicer_to_server(
        servicers.ICSValidationServicer(), server)
    artifact_pb2_grpc.add_ArtifactServiceServicer_to_server(
        servicers.ArtifactServicer(), server)

    # Health checking
    health_servicer = health.HealthServicer()
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)
    health_servicer.set("", health_pb2.HealthCheckResponse.SERVING)

    # Reflection (development only)
    if settings.APP_ENV != "production":
        service_names = (
            input_processing_pb2.DESCRIPTOR.services_by_name["InputProcessingService"].full_name,
            ai_extraction_pb2.DESCRIPTOR.services_by_name["AIExtractionService"].full_name,
            date_normalization_pb2.DESCRIPTOR.services_by_name["DateNormalizationService"].full_name,
            event_validation_pb2.DESCRIPTOR.services_by_name["EventValidationService"].full_name,
            clarification_pb2.DESCRIPTOR.services_by_name["ClarificationService"].full_name,
            reminder_pb2.DESCRIPTOR.services_by_name["ReminderService"].full_name,
            ics_generation_pb2.DESCRIPTOR.services_by_name["ICSGenerationService"].full_name,
            ics_generation_pb2.DESCRIPTOR.services_by_name["ICSValidationService"].full_name,
            artifact_pb2.DESCRIPTOR.services_by_name["ArtifactService"].full_name,
            reflection.SERVICE_NAME,
            health.SERVICE_NAME if hasattr(health, "SERVICE_NAME") else "grpc.health.v1.Health",
        )
        reflection.enable_server_reflection(service_names, server)

    return server


def serve() -> None:
    configure_logging(settings.LOG_LEVEL)
    server = build_server()
    addr = f"0.0.0.0:{settings.GRPC_PORT}"
    server.add_insecure_port(addr)
    server.start()
    log.info("gRPC server listening on %s (mock_mode=%s)", addr, settings.mock_mode)
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
