#!/usr/bin/env bash
set -o errexit #  exit on errors
set -o nounset # exit on use of uninitialized variable
set -o errtrace # inherits trap on ERR in function and subshell

source utils.sh

mkdir -p tools/

if [ ! -f tools/gn ]; then
  GN_ARCHIVE="${OS}-${ARCH}"
  download "https://chrome-infra-packages.appspot.com/dl/gn/gn/${GN_ARCHIVE}/+/latest" tools/gn.zip
  unzip -o tools/gn.zip -d tools
fi

if [ ! -f tools/ninja ]; then
  NINJA_ARCHIVE="ninja-${OS}.zip"
  if [ "${OS}" = "linux" ] && [ "${ARCH}" == "arm64" ]; then
    NINJA_ARCHIVE="ninja-linux-aarch64.zip"
  fi

  download "https://github.com/ninja-build/ninja/releases/download/v1.12.1/${NINJA_ARCHIVE}" tools/ninja.zip
  unzip -o tools/ninja.zip  -d tools
fi
