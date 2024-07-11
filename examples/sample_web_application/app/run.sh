#!/bin/bash
# /opt/python added to the PYTHONPATH allows to access the code of another lambda layers for zip package
PATH="$PATH:$LAMBDA_TASK_ROOT/bin" PYTHONPATH="$LAMBDA_TASK_ROOT:$LAMBDA_TASK_ROOT/app:$LAMBDA_TASK_ROOT/api_models:/opt/python" exec python -m uvicorn  --log-config logging.yaml --port="$PORT" main:app