# Workspace Startup Instructions

These instructions apply to the entire `Travel_Laser` workspace.

## Project Context

- Repository: `https://github.com/pengels22/Travel_Laser.git`
- Default branch: `main`
- Workspace file: `Travel_Laser.code-workspace`

## Startup Checklist

When starting work in this workspace:

1. Run `git status --short --branch` to understand the current state.
2. Read `README.md` if it contains project-specific notes.
3. Inspect the file tree with `rg --files -g '!.git'` before making changes.
4. Preserve any user changes already present in the working tree.
5. Keep commits small and focused when the user asks to save work to Git.

## Git Workflow

- Use `main` as the working branch unless the user asks for another branch.
- Remote `origin` should point to `https://github.com/pengels22/Travel_Laser.git`.
- Do not rewrite history or use destructive Git commands unless the user explicitly requests it.
- Before pushing, confirm the working tree contains only intentional changes.

## Coding Preferences

- Prefer simple, readable project structure until the app direction is clearer.
- Add dependencies only when they provide clear value for the requested feature.
- Keep generated artifacts, build output, secrets, caches, and local environment files out of Git.

