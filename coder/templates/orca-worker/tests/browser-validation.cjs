const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const template = fs.readFileSync(path.join(__dirname, "../main.tf"), "utf8");
const parameter = template.match(/^data "coder_parameter" "repo" \{[\s\S]*?^\}/m);
assert(parameter, "Repository parameter must exist");
const encoded = parameter[0].match(/^\s*regex\s*=\s*("(?:\\.|[^"\\])*")/m);
assert(encoded, "Repository parameter must declare a validation regex");
const regex = new RegExp(JSON.parse(encoded[1]));

for (const value of ["", "https://example.com/project.git", "https://example.com/org/repo"]) {
  assert(regex.test(value), `Browser validation must accept ${JSON.stringify(value)}`);
}
for (const value of [
  "http://example.com/project.git",
  "ssh://example.com/project.git",
  "git@example.com:project.git",
  "https://user:password@example.com/project.git",
  "https://example.com/project name.git",
  "https://example.com/project\nname.git",
  "https://example.com/project\tname.git",
]) {
  assert(!regex.test(value), `Browser validation must reject ${JSON.stringify(value)}`);
}
console.log("Browser repository validation passed (10 cases).");
