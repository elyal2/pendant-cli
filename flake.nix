{
  description = "Pendant BLE reverse engineering tools";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = [
            pkgs.python311
            pkgs.uv                 # Python package manager
            pkgs.bluez
            pkgs.protobuf           # protobuf compiler
            pkgs.libopus            # opus codec
            # System deps for Python packages
            pkgs.gobject-introspection
            pkgs.glib
            pkgs.cairo
            pkgs.pango
            pkgs.pkg-config
            pkgs.dbus
            # Dev tools
            pkgs.wireshark
            pkgs.ffmpeg
            pkgs.sox
          ];

          # Environment variables for building Python packages
          PKG_CONFIG_PATH = "${pkgs.glib.dev}/lib/pkgconfig:${pkgs.gobject-introspection.dev}/lib/pkgconfig:${pkgs.cairo.dev}/lib/pkgconfig:${pkgs.dbus.dev}/lib/pkgconfig";
          GI_TYPELIB_PATH = "${pkgs.gobject-introspection}/lib/girepository-1.0";
          LD_LIBRARY_PATH = "${pkgs.libopus}/lib";

          shellHook = ''
            echo "Pendant BLE development environment"
            echo ""

            # Generate protobuf if needed
            if [ ! -f proto/pendant_pb2.py ] && [ -f proto/pendant.proto ]; then
              echo "Generating protobuf Python code..."
              protoc --python_out=proto proto/pendant.proto 2>/dev/null || true
            fi

            # Sync dependencies with uv
            if [ -f pyproject.toml ]; then
              echo "Syncing dependencies with uv..."
              uv sync --quiet 2>/dev/null || uv sync
              source .venv/bin/activate 2>/dev/null || true
            fi

            echo ""
            echo "Commands:"
            echo "  pendant status       - Check device status"
            echo "  pendant download -d  - Download and decode audio"
            echo "  pendant bt pair      - Pair with device"
            echo "  pendant bt scan      - Scan for BLE devices"
            echo ""
            echo "Set PENDANT_ADDRESS to your device (pendant bt scan to find it)"
            echo ""
          '';
        };
      }
    );
}
