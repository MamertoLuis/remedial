# Spec Delta

## Purpose

Defines the runtime contract of the deployed Remedial web application: a stateless service that serves its HTTP traffic and static assets from a single web process, persists durable state only through the configured database, and derives all runtime configuration from the environment.

## ADDED Requirements

### Requirement: Stateless web process serves its own static assets

The deployed application SHALL serve all HTTP traffic, including its static assets, from a single long-running web process and SHALL require no separate static web server. The application SHALL persist no durable state on its own filesystem across restarts; any durable state SHALL be read and written only through the database referenced by `DATABASE_URL`.

#### Scenario: A fresh process serves the full site

- **WHEN** the deployed web process starts with collect static assets available
- **THEN** it serves pages and their static assets without any separate static web server

#### Scenario: Restart loses no durable state

- **WHEN** the deployed web process is restarted on a fresh filesystem
- **THEN** all durable application data is recovered from the configured database and nothing that must persist is lost

### Requirement: Environment-driven configuration with fail-fast startup

The deployed application SHALL derive all runtime configuration from environment variables, including the database connection (`DATABASE_URL`), the signing key (`SECRET_KEY`), and the allowed hostnames (`ALLOWED_HOSTS`), and SHALL refuse to start when required settings are missing or invalid.

#### Scenario: Missing signing key blocks startup

- **WHEN** the deployed application starts without a `SECRET_KEY`
- **THEN** startup fails with a clear error instead of using an insecure fallback

#### Scenario: Host allow-list is taken from the environment

- **WHEN** the deployed application starts with a configured `ALLOWED_HOSTS`
- **THEN** it serves only requests whose Host header matches that allow-list