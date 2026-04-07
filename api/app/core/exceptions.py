from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
import structlog

logger = structlog.get_logger()


class PricingError(Exception):
    def __init__(self, message: str, code: str = "PRICING_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class SupplierError(Exception):
    def __init__(self, message: str, supplier: str = None):
        self.message = message
        self.supplier = supplier
        super().__init__(message)


class BlueprintError(Exception):
    def __init__(self, message: str, job_id: str = None):
        self.message = message
        self.job_id = job_id
        super().__init__(message)


async def pricing_error_handler(request: Request, exc: PricingError) -> JSONResponse:
    logger.error("Pricing error", code=exc.code, message=exc.message)
    return JSONResponse(
        status_code=422,
        content={"error": exc.code, "message": exc.message},
    )


async def supplier_error_handler(request: Request, exc: SupplierError) -> JSONResponse:
    logger.error("Supplier error", supplier=exc.supplier, message=exc.message)
    return JSONResponse(
        status_code=503,
        content={"error": "SUPPLIER_ERROR", "message": exc.message},
    )


async def blueprint_error_handler(request: Request, exc: BlueprintError) -> JSONResponse:
    logger.error("Blueprint error", job_id=exc.job_id, message=exc.message)
    return JSONResponse(
        status_code=422,
        content={"error": "BLUEPRINT_ERROR", "message": exc.message, "job_id": exc.job_id},
    )
