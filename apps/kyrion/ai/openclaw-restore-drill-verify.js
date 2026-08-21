"use strict";

const crypto = require("node:crypto");
const fs = require("node:fs");
const fsp = require("node:fs/promises");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const restoreRoot = process.env.RESTORE_ROOT || "/restore";
const expectedApplicationUid = 1000;
const expectedApplicationGid = 1000;
const expectedDirectoryMode = 0o755;
const expectedConfigUid = 0;
const expectedConfigGid = 0;
const expectedConfigMode = 0o644;
const startedAt = new Date();
const startedAtMs = Date.now();

let fileCount = 0;
let dataBytes = 0;
let databaseCount = 0;
const aggregate = crypto.createHash("sha256");
const configCandidates = [];
const databaseCandidates = [];

class VerificationError extends Error {
  constructor(code) {
    super(code);
    this.code = code;
  }
}

function fail(code) {
  throw new VerificationError(code);
}

function modeOf(stat) {
  return stat.mode & 0o7777;
}

function updateText(value) {
  aggregate.update(value, "utf8");
  aggregate.update("\0", "utf8");
}

async function sha256File(filePath) {
  return new Promise((resolve, reject) => {
    const hash = crypto.createHash("sha256");
    const stream = fs.createReadStream(filePath);

    stream.on("error", reject);
    stream.on("data", (chunk) => hash.update(chunk));
    stream.on("end", () => resolve(hash.digest("hex")));
  });
}

async function walk(directory, relativeDirectory = "") {
  let entries;
  try {
    entries = await fsp.readdir(directory, { withFileTypes: true });
  } catch {
    fail("restore_tree_unreadable");
  }

  entries.sort((left, right) =>
    Buffer.compare(Buffer.from(left.name), Buffer.from(right.name)),
  );

  for (const entry of entries) {
    const relativePath = relativeDirectory
      ? relativeDirectory + "/" + entry.name
      : entry.name;
    const absolutePath = path.join(directory, entry.name);
    let stat;

    try {
      stat = await fsp.lstat(absolutePath);
    } catch {
      fail("restore_tree_unreadable");
    }

    updateText(relativePath);
    updateText(String(stat.uid));
    updateText(String(stat.gid));
    updateText(String(modeOf(stat)));

    if (stat.isDirectory()) {
      updateText("directory");
      await walk(absolutePath, relativePath);
      continue;
    }

    if (stat.isSymbolicLink() || !stat.isFile()) {
      fail("unexpected_restore_entry");
    }

    const fileDigest = await sha256File(absolutePath).catch(() =>
      fail("restore_file_unreadable"),
    );
    updateText("file");
    updateText(String(stat.size));
    updateText(fileDigest);
    fileCount += 1;
    dataBytes += stat.size;

    if (
      relativePath === ".openclaw/openclaw.json" ||
      relativePath.endsWith("/.openclaw/openclaw.json")
    ) {
      configCandidates.push(absolutePath);
    }

    if (/\.(?:db|sqlite|sqlite3)$/i.test(entry.name)) {
      databaseCandidates.push(absolutePath);
    }
  }
}

async function expectMetadata(filePath, expected, kind) {
  let stat;
  try {
    stat = await fsp.stat(filePath);
  } catch {
    fail("expected_layout_missing");
  }

  const matchesKind = kind === "directory" ? stat.isDirectory() : stat.isFile();
  if (
    !matchesKind ||
    stat.uid !== expected.uid ||
    stat.gid !== expected.gid ||
    modeOf(stat) !== expected.mode
  ) {
    fail("unexpected_ownership_or_mode");
  }
}

async function parseConfig(configPath) {
  let config;
  try {
    config = JSON.parse(await fsp.readFile(configPath, "utf8"));
  } catch {
    fail("config_json_parse");
  }

  if (config === null || Array.isArray(config) || typeof config !== "object") {
    fail("config_json_shape");
  }
}

function validateConfigWithOpenClaw(configPath) {
  const temporaryHome = "/tmp/openclaw-restore-drill";
  try {
    for (const directory of [
      temporaryHome,
      "/tmp/cache",
      "/tmp/config",
      "/tmp/data",
    ]) {
      fs.mkdirSync(directory, { recursive: true, mode: 0o700 });
    }
  } catch {
    fail("temporary_storage_unavailable");
  }

  const validation = spawnSync(
    "node",
    ["/app/dist/index.js", "config", "validate"],
    {
      cwd: temporaryHome,
      env: {
        HOME: temporaryHome,
        NODE_NO_WARNINGS: "1",
        OPENCLAW_CONFIG_PATH: configPath,
        OPENCLAW_NIX_MODE: "1",
        PATH: process.env.PATH || "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        TMPDIR: "/tmp",
        XDG_CACHE_HOME: "/tmp/cache",
        XDG_CONFIG_HOME: "/tmp/config",
        XDG_DATA_HOME: "/tmp/data",
      },
      stdio: "ignore",
      timeout: 120_000,
    },
  );

  if (validation.error || validation.signal || validation.status !== 0) {
    fail("offline_config_validation");
  }
}

async function isSqliteDatabase(filePath) {
  let handle;
  try {
    handle = await fsp.open(filePath, "r");
    const header = Buffer.alloc(16);
    const { bytesRead } = await handle.read(header, 0, header.length, 0);
    return bytesRead === 16 && header.equals(Buffer.from("SQLite format 3\0"));
  } catch {
    fail("database_unreadable");
  } finally {
    await handle?.close();
  }
}

function verifySqliteIntegrity(filePath) {
  let database;
  try {
    const { DatabaseSync } = require("node:sqlite");
    database = new DatabaseSync(filePath, { readOnly: true });
    const result = database.prepare("PRAGMA integrity_check").get();
    if (!result || Object.values(result).length !== 1 || Object.values(result)[0] !== "ok") {
      fail("sqlite_integrity");
    }
  } catch (error) {
    if (error instanceof VerificationError) {
      throw error;
    }
    fail("sqlite_integrity");
  } finally {
    database?.close();
  }
}

function report(result, check, aggregateChecksum) {
  const durationSeconds = ((Date.now() - startedAtMs) / 1000).toFixed(3);
  const fields = [
    "result=" + result,
    "timestamp=" + startedAt.toISOString(),
    "duration_seconds=" + durationSeconds,
    "file_count=" + fileCount,
    "data_bytes=" + dataBytes,
    "database_count=" + databaseCount,
  ];

  if (aggregateChecksum) {
    fields.push("aggregate_sha256=" + aggregateChecksum);
  }
  if (check) {
    fields.push("check=" + check);
  }

  console.log(fields.join(" "));
}

async function main() {
  let rootStat;
  try {
    rootStat = await fsp.lstat(restoreRoot);
  } catch {
    fail("restore_root_missing");
  }
  if (!rootStat.isDirectory() || rootStat.isSymbolicLink()) {
    fail("restore_root_invalid");
  }

  await walk(restoreRoot);
  if (fileCount === 0 || dataBytes === 0 || configCandidates.length !== 1) {
    fail("unexpected_restore_data");
  }

  const configPath = configCandidates[0];
  const applicationHome = path.dirname(configPath);
  const workspacePath = path.join(applicationHome, "workspace");

  await expectMetadata(
    applicationHome,
    {
      uid: expectedApplicationUid,
      gid: expectedApplicationGid,
      mode: expectedDirectoryMode,
    },
    "directory",
  );
  await expectMetadata(
    workspacePath,
    {
      uid: expectedApplicationUid,
      gid: expectedApplicationGid,
      mode: expectedDirectoryMode,
    },
    "directory",
  );
  await expectMetadata(
    configPath,
    {
      uid: expectedConfigUid,
      gid: expectedConfigGid,
      mode: expectedConfigMode,
    },
    "file",
  );

  await parseConfig(configPath);
  validateConfigWithOpenClaw(configPath);

  for (const databasePath of databaseCandidates) {
    if (!(await isSqliteDatabase(databasePath))) {
      fail("unexpected_database_format");
    }
    verifySqliteIntegrity(databasePath);
    databaseCount += 1;
  }

  report("pass", null, aggregate.digest("hex"));
}

main().catch((error) => {
  const check = error instanceof VerificationError ? error.code : "verification_error";
  report("fail", check, null);
  process.exitCode = 1;
});
