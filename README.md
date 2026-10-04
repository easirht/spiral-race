# Spiral Race

**Race to the Core** - a fast 2D spiral board game built with Python and Pygame, playable in the browser.

**Play now:** https://easirht.github.io/spiral-race/

## Features

- 50-cell inward spiral board, first to reach the glowing Core wins (exact roll needed)
- 1 player vs AI, or 2-4 players on the same device
- **Online multiplayer** with room codes and invite links (WebSocket relay server)
- Random BOOST (green) and TRAP (red) cells every game, with chain reactions
- Smooth token animation, dice roll, particles, confetti and screen effects
- Works on desktop and mobile browsers

## How to play

1. Roll the dice (1-6) and move along the spiral.
2. Green BOOST cells push you forward, red TRAP cells push you back.
3. Land exactly on the Core (cell 50) to win.

## Tech stack

- Python 3, Pygame, compiled to WebAssembly with pygbag
- aiohttp WebSocket server (Render) for online rooms, server-side dice for fair play
- GitHub Pages for hosting

## Run locally

```
pip install pygame
python main.py
```

Online mode works only in the web version.

## Project structure

```
main.py       game loop, states, UI screens
board.py      spiral generation and random special cells
player.py     player and token drawing
particles.py  sparks, rings, confetti
net.py        browser WebSocket bridge
theme.py, ui.py, settings.py
```

Server code: https://github.com/easirht/spiral-server

Made by Md. Easir Rahat