#!/usr/bin/env node
import { render } from "ink";
import meow from "meow";
import App from "./app.js";

meow({
  importMeta: import.meta,
  flags: {},
});

if (!process.stdin.isTTY || !process.stdout.isTTY) {
  console.error(
    "Weles TUI needs an interactive terminal (TTY).\n" +
      "Open a new terminal tab in Cursor and run:\n" +
      "  pnpm --dir tui build && pnpm --dir tui start",
  );
  process.exit(1);
}

render(<App />);
