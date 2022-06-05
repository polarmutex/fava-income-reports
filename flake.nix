{
  description = "Application packaged using poetry2nix";

  inputs.flake-utils.url = "github:numtide/flake-utils";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs";
  inputs.poetry2nix.url = "github:nix-community/poetry2nix";
  #inputs.polar-nur.url = "github:polarmutex/nur";

  outputs = { self, nixpkgs, flake-utils, poetry2nix, polar-nur }:
    {
      # Nixpkgs overlay providing the application
      overlay = nixpkgs.lib.composeManyExtensions [
        poetry2nix.overlay
      ];
    } // (flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
          overlays = [
            self.overlay
            #polar-nur.overlays.default
          ];
        };
      in
      {
        devShell =
          let
            fava_income_env = pkgs.poetry2nix.mkPoetryEnv {
              projectDir = ./.;
              editablePackageSources = {
                fava_income_reports = ./fava_income_reports;
              };
              overrides = pkgs.poetry2nix.overrides.withDefaults (
                self: super: {
                  python-magic = pkgs.python39.pkgs.python-magic;
                }
              );
            };
          in
          pkgs.mkShell {
            buildInputs = [
              fava_income_env
              pkgs.poetry
            ];
          };
      }));
}
