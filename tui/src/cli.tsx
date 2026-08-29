#!/usr/bin/env node
import { render } from "ink";
import meow from "meow";
import App from "./app.js";

meow({
  importMeta: import.meta,
  flags: {},
});

render(<App />);
