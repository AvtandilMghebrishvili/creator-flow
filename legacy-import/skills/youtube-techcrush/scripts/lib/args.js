/** Minimal --flag / --flag=value / --flag value parser. Zero dependencies by design. */
export function parseArgs(argv = process.argv.slice(2)) {
  const out = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (!a.startsWith('--')) { out._.push(a); continue; }
    const eq = a.indexOf('=');
    if (eq > -1) { out[a.slice(2, eq)] = a.slice(eq + 1); continue; }
    const key = a.slice(2);
    const next = argv[i + 1];
    if (next === undefined || next.startsWith('--')) out[key] = true;
    else { out[key] = next; i++; }
  }
  return out;
}

export function requireArg(args, name, usage) {
  if (args[name] === undefined || args[name] === true) {
    console.error(`Missing --${name}\n\n${usage}`);
    process.exit(1);
  }
  return args[name];
}

import { pathToFileURL } from 'node:url';

/**
 * True when this module is the entrypoint. Uses pathToFileURL because on Windows
 * import.meta.url is file:///D:/... (three slashes) and naive string building
 * produces file://D:/... which never matches.
 */
export const isMain = (url) => url === pathToFileURL(process.argv[1]).href;
