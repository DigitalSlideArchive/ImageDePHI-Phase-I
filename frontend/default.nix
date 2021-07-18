{ pkgs ? import <nixpkgs> {} }:

let
  packagejson = pkgs.lib.trivial.importJSON "package.json";
in
pkgs.stdenv.mkDerivation rec {
  pname = packagejson.name;
  version = packagejson.version;
  buildInputs = [
    pkgs.nodejs
  ];

  buildPhase = ''
    npm ci
    npm build
  '';

  installPhase = ''
    mkdir -p $out/bin
    mv chord $out/bin
  '';
}
