# docker-lvmpy

[![Discord](https://img.shields.io/discord/534485763354787851.svg)](https://discord.gg/vvUtWJB)

Docker volume driver for SKALE nodes. Each volume is an LVM logical volume formatted with btrfs.

[node-cli](https://github.com/skalenetwork/node-cli) bundles it as the `lvmpy` submodule. On node init, update and restore it installs the `docker-lvmpy` systemd service, which runs `skale lvmpy run`.

## Development

```bash
uv sync --all-extras
uv run ruff check
```

## Tests

The tests create a loop device, an LVM volume group and the `docker-lvmpy` systemd service. Run them as root on a disposable Ubuntu 24.04 machine:

```bash
sudo env "PATH=$PWD/.venv/bin:$PATH" tests/run-tests.sh
```

To use an existing block device instead of a loop device, pass it in. Its contents are wiped:

```bash
sudo env "PATH=$PWD/.venv/bin:$PATH" BLOCK_DEVICE=/dev/sdX tests/run-tests.sh
```

## License

[![License](https://img.shields.io/github/license/skalenetwork/docker-lvmpy.svg)](LICENSE)

All contributions are made under the [GNU Affero General Public License v3](https://www.gnu.org/licenses/agpl-3.0.en.html). See [LICENSE](LICENSE).

All docker-lvmpy code Copyright (C) SKALE Labs and contributors.
