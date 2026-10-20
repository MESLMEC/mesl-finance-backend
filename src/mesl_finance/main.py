"""Composition root: the only module that knows every layer and wires adapters to ports."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import timedelta

from fastapi import FastAPI

from mesl_finance.auth.api.router import router as auth_router
from mesl_finance.auth.application.login import Login
from mesl_finance.auth.infrastructure.credentials import Argon2CredentialChecker
from mesl_finance.auth.infrastructure.tokens import JwtTokenService
from mesl_finance.ledger.api.router import router as ledger_router
from mesl_finance.ledger.application.record_deposit import RecordDeposit
from mesl_finance.ledger.infrastructure.unit_of_work import SqlLedgerUnitOfWork
from mesl_finance.shared.api.problems import install_error_handlers
from mesl_finance.shared.infrastructure.database import create_engine
from mesl_finance.shared.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """App factory. Run:  uvicorn --app-dir src mesl_finance.main:create_app --factory"""
    config = settings or Settings()  # pyright: ignore[reportCallIssue]
    engine = create_engine(config)
    tokens = JwtTokenService(
        config.jwt_secret.get_secret_value(), ttl=timedelta(hours=config.jwt_ttl_hours)
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
        yield
        await engine.dispose()

    app = FastAPI(title="MESL Finance", lifespan=lifespan)
    app.state.engine = engine
    app.state.token_service = tokens
    app.state.login = Login(
        Argon2CredentialChecker(config.auth_username, config.auth_password_hash.get_secret_value()),
        tokens,
    )
    app.state.record_deposit = RecordDeposit(lambda actor: SqlLedgerUnitOfWork(engine, actor))

    install_error_handlers(app)
    app.include_router(auth_router)
    app.include_router(ledger_router)
    return app
