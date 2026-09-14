import { stdin, stdout } from "node:process";

/**
 * Read one line from stdin without echoing characters. Requires a TTY.
 */
export function readSecret(prompt: string): Promise<string> {
  if (!stdin.isTTY) {
    return Promise.reject(new Error("stdin is not a TTY"));
  }

  stdout.write(prompt);

  return new Promise((resolve, reject) => {
    stdin.setRawMode(true);
    stdin.resume();
    stdin.setEncoding("utf8");

    let secret = "";

    const onData = (chunk: string) => {
      for (const char of chunk) {
        if (char === "\n" || char === "\r" || char === "\u0004") {
          cleanup();
          stdout.write("\n");
          resolve(secret);
          return;
        }
        if (char === "\u0003") {
          cleanup();
          reject(new Error("Interrupted"));
          return;
        }
        if (char === "\u007f" || char === "\b") {
          secret = secret.slice(0, -1);
          continue;
        }
        secret += char;
      }
    };

    const cleanup = () => {
      stdin.setRawMode(false);
      stdin.pause();
      stdin.removeListener("data", onData);
    };

    stdin.on("data", onData);
  });
}
