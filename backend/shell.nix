with import (fetchTarball https://github.com/NixOS/nixpkgs/archive/nixos-21.05.tar.gz) { };
pkgs.mkShell {
  inputsFrom = [ (import ./default.nix) ];
}
