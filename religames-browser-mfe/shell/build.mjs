import { build } from 'esbuild';

// Each entry is bundled independently, mirroring how real, separately-owned
// micro frontends would each ship their own minified bundle + sourcemap.
const entries = [
  {
    entryPoints: ['src/mfe-leaderboard/leaderboard.js'],
    outfile: 'dist/js/mfe-leaderboard.min.js',
    globalName: 'ReliGamesLeaderboard',
  },
  {
    entryPoints: ['src/mfe-profile/profile.js'],
    outfile: 'dist/js/mfe-profile.min.js',
    globalName: 'ReliGamesProfile',
  },
  {
    entryPoints: ['src/shell.js'],
    outfile: 'dist/js/shell.min.js',
  },
];

for (const entry of entries) {
  await build({
    ...entry,
    bundle: true,
    minify: true,
    // 'external': write a .map file but omit the //# sourceMappingURL comment.
    // The .map is served from a non-public path (see nginx.conf) and pulled
    // out manually for upload to New Relic -- a dead sourceMappingURL comment
    // pointing at a 404 would be misleading, so we skip it entirely.
    sourcemap: 'external',
    format: 'iife',
    target: ['es2019'],
    logLevel: 'info',
  });
}
