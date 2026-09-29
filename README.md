# MikroTik Bulk Downgrader

A tool for downgrading many MikroTik routers at once, based on criteria such as
RouterOS version, RouterBOOT firmware version, or configuration version.

The routers are connected to one switch, and the tool works with them
simultaneously. Because factory-reset routers all share the same default IP
(`192.168.88.1`), the tool finds and reaches routers by **MAC address** instead
of IP.

> **Status:** early development. Router discovery (MNDP) is working.
> MAC-Telnet access is next.

---

## Safety first

This tool is meant to change software on routers. Run it **only on an isolated
network** that contains nothing but the routers you intend to downgrade.
Discovery finds every MikroTik device on the same Layer 2 segment, including
production equipment if it is reachable.

---

## Features

- [x] **Discovery** – finds every MikroTik router on the local network using
      MNDP (MikroTik Neighbor Discovery Protocol), even when their IP addresses
      conflict
- [ ] **MAC-Telnet access** – log in to routers by MAC address
- [ ] **Temporary IP assignment** – give each router a unique IP for API access
- [ ] **Downgrade engine** – RouterOS and firmware downgrade by criteria
- [ ] **Parallel processing** – handle many routers at the same time
- [ ] **Web interface** – run everything from a Raspberry Pi

---

## Requirements

| What             | Details                                                                                                                     |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------- |
| Python           | 3.12 or newer                                                                                                               |
| Operating system | Linux for the full tool (MAC-Telnet is Linux only). Discovery also works on Windows.                                        |
| Network          | The machine must be on the **same Layer 2 segment** as the routers. For a VM, use a bridged network, not NAT.               |
| Firewall         | Incoming UDP port **5678** (MNDP) must be allowed.                                                                          |
| Routers          | Connect them through a **LAN port** (e.g. `ether2`). The default configuration blocks discovery and MAC-Telnet on `ether1`. |

---

## Installation (Ubuntu / Debian)

### 1. System packages

```bash
sudo apt update
sudo apt install git python3-venv
```

### 2. Clone the project

```bash
git clone https://github.com/preslaviliev93/mikrotik_bulk_downgrader.git
cd mikrotik_bulk_downgrader
```

### 3. Python virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
```

### 4. MAC-Telnet client (build from source)

> **Do not use `apt install mactelnet-client`.** The packaged version
> (0.4.4 on Ubuntu 24.04) does not support the EC-SRP login method that
> RouterOS **6.43 and newer** require. Logins fail with
> _"Login failed, incorrect username or password"_ even when the password is
> correct.

Remove the old package if it is installed:

```bash
sudo apt remove mactelnet-client
```

Install the build dependencies:

```bash
sudo apt install build-essential autopoint automake autoconf libbsd-dev libssl-dev gettext
```

Download, build, and install the current version. Do this **outside** the
project folder, so the build files don't end up in the repository:

```bash
cd ~
wget https://github.com/haakonnessjoen/MAC-Telnet/tarball/master -O mactelnet.tar.gz
tar zxvf mactelnet.tar.gz
cd haakonness*/
./autogen.sh
./configure
make
sudo make install
```

Refresh the shell's command cache and check that the new binary is used:

```bash
hash -r
which mactelnet        # should print /usr/local/bin/mactelnet
```

### 5. Verify MAC-Telnet by hand

```bash
mactelnet 02:00:00:00:00:01 -u admin
```

Replace the MAC with one of your lab routers (discovery, below, lists them).
You should get a RouterOS prompt. Type `/quit` to exit.

If the login still fails, check on the router that the user's group has the
`telnet` policy (`/user group print`). Winbox logins use a separate `winbox`
policy, so a user can be allowed in Winbox but not in MAC-Telnet.

---

## Installation (Windows, development only)

Discovery and the tests run on Windows. MAC-Telnet does not.

```powershell
git clone https://github.com/preslaviliev93/mikrotik_bulk_downgrader.git
cd mikrotik_bulk_downgrader
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

Allow Python through Windows Firewall on private networks when asked,
otherwise discovery receives nothing.

---

## Usage

### Discover routers

```bash
python socket_ops.py
```

Example output:

```
MAC: 02:00:00:00:00:01, IP: 192.0.2.1, Identity: TestRouter-1, Version: 7.23 (stable) 2026-05-25 09:05:50, Uptime: 52d 20h 5m 11s
```

Routers without an IP address are still found; their IP shows as `N/A`.

---

## Development

### Run the tests

```bash
pytest -v
```

The tests use **fake** MNDP packets built in code, so they need no routers
and contain no real device information.

### Run the linter

```bash
ruff check .
ruff check . --fix     # fix what can be fixed automatically
```

### Continuous integration

Every push to `main` and every pull request runs Ruff and pytest on both
Ubuntu and Windows via GitHub Actions (`.github/workflows/ci.yml`).
Merge only when all checks are green.

### Project structure

```
mikrotik_bulk_downgrader/
├── .github/workflows/ci.yml   # CI pipeline
├── tests/
│   └── test_utils.py          # parser and formatting tests
├── conftest.py                # lets pytest import project modules
├── requirements-dev.txt       # development tools (pytest, ruff)
├── socket_ops.py              # MNDP discovery (sockets)
└── utils.py                   # MNDP packet parsing and formatting
```

### Secrets and local files

Never commit passwords, real router details, or packet captures.
`.gitignore` excludes `.env` files, `config.yaml`, logs, Wireshark captures
(`*.pcap`, `*.pcapng`), and RouterOS packages (`*.npk`).

---

## How discovery works

MikroTik routers announce themselves with **MNDP** on UDP port 5678. The tool
broadcasts a 4-byte discovery request, and every router on the segment
replies immediately. Each reply is a 4-byte header followed by TLV fields
(2-byte type, 2-byte length, value):

| Type | Field            | Notes                                                         |
| ---- | ---------------- | ------------------------------------------------------------- |
| 1    | MAC address      | 6 bytes                                                       |
| 5    | Identity         | text                                                          |
| 7    | RouterOS version | text, includes build date                                     |
| 8    | Platform         | text                                                          |
| 10   | Uptime           | seconds, **little-endian** (all other numbers are big-endian) |
| 11   | Software ID      | text                                                          |
| 12   | Board model      | text                                                          |
| 15   | IPv6 address     | 16 bytes, may appear more than once                           |
| 16   | Interface name   | text                                                          |
| 17   | IPv4 address     | 4 bytes                                                       |

Unknown field types are skipped, since newer RouterOS versions add fields.
