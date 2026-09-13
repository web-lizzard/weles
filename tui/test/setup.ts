import { setInstanceAddress } from "../src/api/instance.js";
import { parseInstanceAddress } from "../src/instance/address.js";

setInstanceAddress(parseInstanceAddress("http://localhost:8000"));
