#!/usr/bin/env node
import meow from "meow";
import { render } from "ink";
import App from "./app.js";

meow({
  importMeta: import.meta,
  flags: {},
});

render(<App />);
