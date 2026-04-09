#!/bin/bash
export SECRET_KEY="plumbprice-dev-key"
export DATABASE_URL="postgresql+asyncpg://plumbprice:plumbprice_dev@127.0.0.1:5432/plumbprice"
export ENVIRONMENT=development
export HERMES_ENDPOINT_URL="http://localhost:11434/v1"
export HERMES_MODEL="hermes3:3b"
cd /home/djscrew/Projects/Web-Apps/plumbprice/api
exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8200
