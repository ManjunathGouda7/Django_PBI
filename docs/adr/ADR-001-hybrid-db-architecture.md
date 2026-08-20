# ADR-001: Hybrid Database Architecture (PostgreSQL Metadata + In-Memory/Redis Telemetry Cache)

## Status
**Accepted**

## Context
APEX BI Studio requires two distinct data management characteristics:
1. **Relational Application Metadata**: Users, Roles, Organizations, Dashboards, Widgets, Row-Level Security Rules, KPI Alert Thresholds, Bookmarks, and Audit Logs require strict relational integrity, transactions (ACID), foreign keys, and structured migrations.
2. **High-Throughput Analytics & Telemetry**: Large raw telemetry feeds, JSON datasets, time series streams, and dynamic calculated measures require zero-latency in-memory slicing, chunked streaming, downsampling, and caching.

## Decision
1. **Application Metadata Layer**:
   - **Production**: PostgreSQL 16+ as the relational database engine.
   - **Local / Desktop Executable**: SQLite3 as the zero-dependency, zero-configuration local database.
2. **Analytics & Cache Layer**:
   - **In-Memory Pandas / Redis**: Fast analytical aggregations and DataFrame caching (`_df_cache`).
   - **Unstructured / Document Storage**: MongoDB for raw JSON payload archiving.

## Consequences
- **Positive**:
  - Full relational integrity for enterprise permissions, multi-tenancy, and audit logging.
  - Sub-millisecond chart filter slicing through in-memory cache and Redis tag invalidation.
  - 100% portable: Can run containerized in Kubernetes with Postgres or as a single `.exe` file with embedded SQLite.
