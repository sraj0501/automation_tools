# Task Manager API

A simple Python task manager API used as the demo project for DevTrack.

## Structure

```
app.py        — API handlers (create, read, list, complete, delete)
models.py     — Task dataclass
utils.py      — Input validation
database.py   — In-memory store with JSON persistence
tests/        — pytest test suite
```

## Running tests

```bash
pytest tests/
```
