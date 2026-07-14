#!/bin/bash

mkdir -p release/macos/ft2-clone-macos.app/Contents/MacOS

SDL2_PATH=$(brew --prefix sdl2-compat)
MHTTPD_PATH=$(brew --prefix libmicrohttpd)

clang -target arm64-apple-macos10.11 -mmacosx-version-min=10.11 -arch arm64 \
  -O3 -g0 -DNDEBUG -DHAS_MIDI -D__MACOSX_CORE__ -stdlib=libc++ \
  -I${SDL2_PATH}/include -I${MHTTPD_PATH}/include \
  -L${SDL2_PATH}/lib -L${MHTTPD_PATH}/lib \
  -ffast-math -Winit-self -Wno-deprecated -Wextra -Wunused -mno-ms-bitfields \
  src/rtmidi/*.cpp src/gfxdata/*.c src/mixer/*.c src/scopes/*.c \
  src/modloaders/*.c src/smploaders/*.c src/*.c \
  -framework CoreMidi -framework CoreAudio -framework Cocoa \
  -lSDL2 -lmicrohttpd -liconv -lpthread -lm -lstdc++ \
  -o release/macos/ft2-clone-macos.app/Contents/MacOS/ft2-clone-macos

echo "Build complete!"
