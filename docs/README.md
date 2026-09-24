# Documentation

Documentation set for the Qualcomm Offline Doc Simplifier — an offline, on-device legal and
financial document simplifier built for the Snapdragon® AI Lab Build & Present Challenge.

Maintainer and sole contributor: **[SaiDhinakar](https://github.com/SaiDhinakar)**.

## Index

| Document | Audience | Contents |
|---|---|---|
| [`PRD.md`](PRD.md) | Reviewers, judges | Problem statement, personas, goals, functional requirements (FR-1 … FR-22), non-functional requirements, mapping to the challenge evaluation criteria, risks, success metrics |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Engineers, reviewers | Design principles, pipeline stages and data flow, data model, technology stack, Qualcomm AI Hub validation strategy, security/privacy design, error handling, testing strategy |
| [`SETUP.md`](SETUP.md) | New contributors | Prerequisites, installation, backend selection (OCR/LLM/embeddings), AI Hub token configuration, troubleshooting, sample documents |
| [`CLI.md`](CLI.md) | Users, demo operators | Full command reference, options, environment variables, worked examples, session semantics |
| [`TESTING.md`](TESTING.md) | Contributors | Test suite layout, how to run (stub and real backends), golden samples, lint and type-check |
| [`PERFORMANCE.md`](PERFORMANCE.md) | Judges, engineers | Profiling method, AI Hub NPU results, local end-to-end timings, known bottlenecks and optimisation targets |
| [`ROADMAP.md`](ROADMAP.md) | Everyone | Build phases, dates, current status, remaining work before submission |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Contributors | Development workflow, code style, testing and documentation expectations, privacy rules |

## Reading order

- **For a first-time reader:** `PRD.md` → `ARCHITECTURE.md` → `PERFORMANCE.md`.
- **To run the project:** `SETUP.md` → `CLI.md`.
- **To change the project:** `CONTRIBUTING.md` → `TESTING.md` → `ARCHITECTURE.md`.

## Conventions used in this documentation

- Requirement identifiers (`FR-n`) refer to §6 of `PRD.md` and are used consistently in code
  comments, tests and architecture sections.
- Design section numbers (`§n`) refer to `ARCHITECTURE.md`.
- Anything marked **TBD** or **open** is a genuine outstanding item, tracked in `ROADMAP.md`;
  design decisions that have been made are recorded in `PRD.md` §11 and `ARCHITECTURE.md` §7.
- Measured numbers are reported with the machine, backend and date they were taken on.
