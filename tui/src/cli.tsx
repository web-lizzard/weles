#!/usr/bin/env node
import os from "node:os";
import { render } from "ink";
import meow from "meow";
import { setInstanceAddress } from "./api/instance.js";
import App from "./app.js";
import { runInstanceCommand } from "./instance/command.js";
import { resolveStartup } from "./startup.js";

const cli = meow({
  importMeta: import.meta,
  flags: {},
  commands: ["instance"],
  help: `
    Usage
      $ weles
      $ weles instance
      $ weles instance set <address>
  `,
});

const location = { env: process.env, homeDir: os.homedir() };

if (cli.command === "instance") {
  const code = await runInstanceCommand(cli.input, {
    location,
    out: (line) => console.log(line),
    err: (line) => console.error(line),
  });
  process.exit(code);
}

const decision = await resolveStartup(location);

if (decision.kind === "missing") {
  console.error(decision.message);
  process.exit(1);
}

setInstanceAddress(decision.address);

if (!process.stdin.isTTY || !process.stdout.isTTY) {
  console.error(
    "Weles TUI needs an interactive terminal (TTY).\n" +
      "Open a new terminal tab in Cursor and run:\n" +
      "  pnpm --dir tui build && pnpm --dir tui start",
  );
  process.exit(1);
}

render(<App />);
