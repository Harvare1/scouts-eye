# Repository instructions for Codex

Read `PROJECT_CONTEXT.md`, `README.txt` and `KURSPLAN.md` before changing code.

- This is a local FastAPI pilot, **not** a production-ready application.
- Keep the product Swedish-language and retain Andrablicken brand palette unless asked otherwise.
- Before changes, identify existing behavior and run relevant tests. Add automated tests for changes involving access control, uploads, submissions or PDF downloads.
- Verify tenant isolation: a club cannot see another club's private assignments or reports; scouts cannot inspect unauthorized private tasks; club reports should only be visible when approved.
- Do not publish or deploy demo credentials. Don't commit secrets or private keys.
- Don't promise legal access to sports video; only use licensed/authorized links.
- Prioritize reliability, UX and testability over visual polish and speculative features.
- Document config, migration, build/test steps and any known security gaps.
- Make changes in small reviewable units; never deploy to a live server without explicit user approval.
