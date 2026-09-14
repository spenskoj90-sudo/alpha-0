const smokeMode = process.env.SENTINEL_PACKAGED_HOST_SMOKE === '1';

if (smokeMode) {
  require('./package-smoke');
} else {
  require('./main');
}
