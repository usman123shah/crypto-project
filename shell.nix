
{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = [
    pkgs.python3
    pkgs.python3Packages.pip
    pkgs.python3Packages.pandas
    pkgs.python3Packages.scikit-learn
    pkgs.python3Packages.requests
    pkgs.python3Packages.fpdf
    pkgs.python3Packages.python-dotenv
    pkgs.python3Packages.matplotlib
    pkgs.python3Packages.yfinance
    pkgs.python3Packages.feedparser
    pkgs.python3Packages.streamlit
  ];
}
