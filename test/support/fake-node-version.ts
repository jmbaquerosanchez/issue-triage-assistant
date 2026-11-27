// Preloaded with `--import` by the tests of the bin's version check: the process
// sees the Node version in FAKE_NODE_VERSION instead of the real one, so the
// check can be tested on the Node that runs the tests.
const version = process.env['FAKE_NODE_VERSION'];
if (version !== undefined) {
  Object.defineProperty(process.versions, 'node', { value: version });
}
