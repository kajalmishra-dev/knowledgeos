#!/bin/sh
set -eu

until mc alias set local "http://${MINIO_HOST}:${MINIO_PORT}" "${MINIO_ROOT_USER}" "${MINIO_ROOT_PASSWORD}"; do
  echo "Waiting for MinIO..."
  sleep 2
done

mc mb "local/${MINIO_BUCKET}" --ignore-existing
mc version enable "local/${MINIO_BUCKET}" || true

echo "MinIO bucket '${MINIO_BUCKET}' is ready."
