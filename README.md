# Spiral Race

**Race to the Core** - a fast 2D spiral board game built with Python and Pygame, playable in any browser on desktop and phone.

**Play now:** https://easirht.github.io/spiral-race/

## Features

- 50-cell inward spiral board, first to reach the glowing Core wins (exact roll needed)
- 1 player vs AI, or 2-4 players on the same device
- **Online multiplayer** with room codes and invite links (WebSocket relay server, server-side dice)
- Random BOOST (green) and TRAP (red) cells every game, with chain reactions
- Smooth token animation, dice roll, particles, confetti and screen effects
- Sound effects with a mute button
- Phone friendly: portrait and landscape layouts, tap-to-type name input
- Share button that opens the phone share sheet (or copies the link)

## How to play

1. Roll the dice (1-6) and move along the spiral.
2. Green BOOST cells push you forward, red TRAP cells push you back.
3. Land exactly on the Core (cell 50) to win.

## Tech stack

- Python 3 and Pygame, compiled to WebAssembly with pygbag
- aiohttp WebSocket server (hosted on Render) for online rooms
- GitHub Pages for hosting

## Run locally

```
pip install pygame
python main.py
```

Online mode works only in the web version.

## Build for the web

```
powershell -ExecutionPolicy Bypass -File deploy.ps1
```

This builds with pygbag, patches the page (canvas fit, share preview), and copies everything to `docs/` for GitHub Pages.

## Project structure

```
main.py       game loop, states, layouts (landscape and portrait)
board.py      spiral generation and random special cells
player.py     player and token drawing
particles.py  sparks, rings, confetti
net.py        browser WebSocket and share bridge
sound.py      sound effects
theme.py, ui.py, settings.py
assets/sounds sound effect files
```

## Notes

- The online server runs on a free plan and sleeps when idle, so the first connection can take up to a minute.
- The server rolls the dice and shares the board seed, but it does not validate movement. There is no reconnect after a dropped connection.

Server code: https://github.com/easirht/spiral-server

Made by Md. Easir Rahat
