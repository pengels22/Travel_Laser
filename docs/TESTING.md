# Testing

Run:

```bash
.venv/bin/python -m pytest
```

The suite uses mocks for GPIO, serial, USB, VirtualHere, and network behavior. Safety behavior should always have tests before changes are committed.

