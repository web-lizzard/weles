# Learning

Private, per-target learning artifacts for Socratic codebase onboarding. One subfolder per learning target at `context/learning/<slug>/`.

## Privacy

All contents under this directory are **gitignored** except `.gitignore` and this README. Learning curricula, cheatsheets, quiz banks, and notes stay on your machine — they are never committed to version control.

## Layout

Per-slug artifacts are created lazily on first `/learn-codebase analyze`:

```
context/learning/<slug>/
├── curriculum.md
├── cheatsheet.md
└── internals/
    ├── .config.json
    └── quiz-bank.md
```

## Entry command

Run `/learn-codebase` to start or resume learning a codebase. Subcommands: `analyze`, `tutor`, `quiz`, `status`.

Learn-codebase skills **refuse** (or warn and suggest `/init`) if `context/learning/` is missing — they do not re-scaffold the parent directory.
