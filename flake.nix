{
  description = "Clean Microsoft Edge and Waydroid search automation with Nix Apps";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      nixpkgs,
      flake-utils,
      ...
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs {
          inherit system;
          config.allowUnfree = true;
        };

        pythonEnv = pkgs.python311.withPackages (ps: [ ]);

        msedge-auto-search = pkgs.stdenv.mkDerivation {
          pname = "msedge-auto-search";
          version = "1.3.1";
          src = ./.;

          nativeBuildInputs = [ pkgs.makeWrapper ];
          buildInputs = [ pythonEnv ];

          installPhase = ''
            mkdir -p $out/share/msedge-auto-search
            cp -r keywords.py script.py waydroid.py keywords.txt $out/share/msedge-auto-search/

            mkdir -p $out/bin

            makeWrapper ${pythonEnv}/bin/python $out/bin/open \
              --add-flags "$out/share/msedge-auto-search/script.py --open" \
              --prefix PATH : ${
                pkgs.lib.makeBinPath [
                  pkgs.microsoft-edge
                  pkgs.coreutils
                ]
              }

            makeWrapper ${pythonEnv}/bin/python $out/bin/pc \
              --add-flags "$out/share/msedge-auto-search/script.py" \
              --prefix PATH : ${
                pkgs.lib.makeBinPath [
                  pkgs.microsoft-edge
                  pkgs.ydotool
                  pkgs.coreutils
                  pkgs.procps
                ]
              }

            makeWrapper ${pythonEnv}/bin/python $out/bin/mobile \
              --add-flags "$out/share/msedge-auto-search/waydroid.py" \
              --prefix PATH : ${
                pkgs.lib.makeBinPath [
                  pkgs.waydroid
                  pkgs.coreutils
                  pkgs.procps
                ]
              }

            makeWrapper ${pythonEnv}/bin/python $out/bin/keywords \
              --add-flags "$out/share/msedge-auto-search/keywords.py"
          '';
        };
      in
      {
        packages.default = msedge-auto-search;

        apps = {
          open = {
            type = "app";
            program = "${msedge-auto-search}/bin/open";
          };
          pc = {
            type = "app";
            program = "${msedge-auto-search}/bin/pc";
          };
          mobile = {
            type = "app";
            program = "${msedge-auto-search}/bin/mobile";
          };
          keywords = {
            type = "app";
            program = "${msedge-auto-search}/bin/keywords";
          };
        };

        devShells.default = pkgs.mkShell {
          buildInputs = [
            pythonEnv
            pkgs.ydotool
            pkgs.microsoft-edge
            pkgs.waydroid
            pkgs.sqlite
          ];
        };
      }
    );
}
