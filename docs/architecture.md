# RackLab-RTP Architecture

## System Overview

RackLab-RTP is a production-grade automated hardware validation platform designed for Meta's Release-to-Production workflow. The system provides deterministic test execution, failure injection, and automated root cause analysis.

## High-Level Architecture
```mermaid
graph TB
    subgraph "Presentation Layer"
        UI[Web Dashboard<br/>Jinja2 Templates]
        API[REST API<br/>FastAPI]
    end
    
    subgraph "Service Layer"
        TR[Test Runner<br/>Retry/Timeout Logic]
        SIM[System Simulator<br/>Boot Sequence]
        FI[Failure Injector<br/>Deterministic Faults]
        RCA[RCA Engine<br/>Bayesian Classifier]
    end
    
    subgraph "Data Layer"
        DB[(SQLite Database<br/>Test Runs & RCA)]
        LOG[Structured Logs
