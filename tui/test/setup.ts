import { beforeEach } from "vitest";
import { setInstanceAddress } from "../src/api/instance.js";
import { parseInstanceAddress } from "../src/instance/address.js";

beforeEach(() => {
  setInstanceAddress(parseInstanceAddress("http://localhost:8000"));
});
