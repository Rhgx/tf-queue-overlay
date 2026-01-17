# TF2 Queue Timer

A simple overlay utility for Team Fortress 2 that tracks how long you have been queueing for a match.

## How it Works

The program monitors the Team Fortress 2 console log file to detect specific events:

- **Queue Start**: Starts the timer when you join a casual matchmaking queue.
- **Match Found**: Stops the timer when a lobby is assigned.
- **Map Detection**: Displays the current map name once you are connected to a server.

The overlay automatically shows itself when the TF2 window is focused and hides when you tab out.

## Usage

1.  Ensure Team Fortress 2 is installed via Steam.
2.  **Important**: Add `-condebug` to your TF2 launch options (Library -> Right-click TF2 -> Properties -> Launch Options).
3.  Run the executable (`TF2QueueTimer.exe`).
4.  The program will run in the system tray.
5.  Launch Team Fortress 2.
6.  Join a casual queue to see the timer in action.

## Configuration

On the first run, a `settings.json` file is created next to the executable. You can edit this file to adjust:

- **pos**: The [x, y] coordinates of the overlay on your screen.
- **opacity**: The transparency level of the overlay (0.0 to 1.0).
- **font_size**: The size of the text display.
