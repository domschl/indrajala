# Indrajala

Indrajala (Indra's Net) is a platform for distributed event processing, IoT, and AI integration. It serves as an intelligent event router that connects various data sources, sensors, and processing modules (including LLMs) through a unified protocol.

## Features

- **Distributed Architecture**: Supports Python, C++ (ESP32), Swift (iOS/macOS), and JavaScript/WASM clients.
- **Event-Based**: Uses the `IndraEvent` protocol (MQTT-like addressing with UUIDs) for flexible data routing.
- **Modular**: Easily extensible with new processing modules.
- **AI Integration**: Built-in support for ML models and LLMs.
- **Resilient**: Supports asynchronous processing and fault tolerance.

## Architecture

The system consists of:
- **IndraServer**: The core Python server that routes events between modules.
- **IndraLib**: Libraries for interacting with the server.
- **Client Libraries**: Support for multiple languages (Common Lisp, JS, Swift).

## Installation

### Prerequisites

- Python 3.13 or higher
- `uv` (recommended for dependency management) or `pip`

### Setup

1.  Clone the repository:
    ```bash
    git clone https://codeberg.org/domschl/Indrajala.git
    cd Indrajala
    ```

2.  Install dependencies:
    ```bash
    pip install -r indraserver/requirements.txt
    # OR if using uv
    uv sync
    ```

## Usage

1.  **Configuration**:
    The server requires a configuration file. You can start with the default:
    ```bash
    cp config/indrajala.default.toml config/indrajala.toml
    ```
    Edit `config/indrajala.toml` to enable/disable modules and set paths.

2.  **Run the Server**:
    You can use the provided helper script:
    ```bash
    ./ij.sh
    ```
    Or run directly with Python:
    ```bash
    python indraserver/src/indrajala.py
    ```

## Protocol

Indrajala uses a specific event structure called `IndraEvent`. Messages are routed based on `domain` (like MQTT topics).
See [doc/indra.md](doc/indra.md) for protocol details.

## License

See [LICENSE](LICENSE) file.
