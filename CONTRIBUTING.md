# Contributing to KLYPTRA Studio

Thank you for your interest in contributing to KLYPTRA Studio!

---

## Development Workflow

1. **Fork the Repository** and create a topic branch from `main`:
   ```bash
   git checkout -b feature/my-new-feature
   ```

2. **Code Standards**:
   - **Frontend**: Clean semantic HTML5, utility classes aligned with Tailwind CSS tokens, Liquid Glass theme compliance, and 60 FPS transitions using centralized motion controllers.
   - **Backend**: Python 3.10+ typed functions with Pydantic validation, explicit error handling, and parameterized database queries.
   - **Windows Safety**: Avoid hardcoded path separators (`/` vs `\`). Always use Python's `pathlib.Path` or Node's `path.join()`.

3. **Testing**:
   Before submitting a Pull Request, ensure all automated tests pass:
   ```bash
   python -m pytest backend/tests/ -v
   node test_app_motion.js
   ```

4. **Submitting Changes**:
   - Write clear, concise commit messages following conventional commits (`feat: ...`, `fix: ...`, `docs: ...`).
   - Open a Pull Request targeting `main`. Provide screenshots or recordings demonstrating visual and interactive changes.

