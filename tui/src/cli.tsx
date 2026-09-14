#!/usr/bin/env node
import os from "node:os";
import { render } from "ink";
import meow from "meow";
import { setInstanceAddress } from "./api/instance.js";
import App from "./app.js";
import { runRegisterCommand, runSignInCommand } from "./auth/command.js";
import { readSecret } from "./auth/readSecret.js";
import { runInstanceCommand } from "./instance/command.js";
import { resolveStartup } from "./startup.js";

const cli = meow({
  importMeta: import.meta,
  flags: {},
  commands: ["instance", "register", "sign-in"],
  help: `
    Usage
      $ weles
      $ weles instance
      $ weles instance set <address>
      $ weles register <email>
      $ weles sign-in <email>
  `,
});

const location = { env: process.env, homeDir: os.homedir() };

const authDeps = {
  location,
  readSecret,
  out: (line: string) => console.log(line),
  err: (line: string) => console.error(line),
};

if (cli.command === "instance") {
  const code = await runInstanceCommand(cli.input, {
    location,
    out: authDeps.out,
    err: authDeps.err,
  });
  process.exit(code);
}

if (cli.command === "register") {
  process.exit(await runRegisterCommand(cli.input, authDeps));
}

if (cli.command === "sign-in") {
  process.exit(await runSignInCommand(cli.input, authDeps));
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
