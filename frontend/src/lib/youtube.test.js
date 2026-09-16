import test from "node:test";
import assert from "node:assert/strict";

import { youtubeWatchUrl } from "./youtube.js";

test("youtubeWatchUrl crea un enlace oficial a partir de cualquier URL compatible", () => {
  assert.equal(
    youtubeWatchUrl("https://youtu.be/dQw4w9WgXcQ"),
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
  );
});

test("youtubeWatchUrl devuelve una cadena vacia si no hay video reconocible", () => {
  assert.equal(youtubeWatchUrl("https://example.com/video"), "");
  assert.equal(youtubeWatchUrl(""), "");
});
