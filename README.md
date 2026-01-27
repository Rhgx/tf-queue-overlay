# TF2 Queue Timer

A simple overlay utility for Team Fortress 2 that tracks how long you have been queueing for a match.

> [!NOTE]
> Windows may flag this program as suspicious because it is not digitally signed. You can verify that the file is safe by checking it on VirusTotal:
> [VirusTotal Scan Result](https://www.virustotal.com/gui/file-analysis/MDgzNDBmNGE3Nzc0OGU4ZjBjNzc5NmM0Y2E2MWMxYmI6MTc2ODc3MDk5NQ==)

## How it Works

The program monitors the Team Fortress 2 console log file to detect specific events:

- **Queue Start**: Starts the timer when you join a casual matchmaking queue.
- **Match Found**: Stops the timer when a lobby is assigned.
- **Map Detection**: Displays the current map name once you are connected to a server.

The overlay automatically shows itself when the TF2 window is focused and hides when you tab out.

## Showcase

<p align="center">
  <img src="src/showcase.gif" width="50%" alt="TF2 Queue Timer showcase" />
</p>

## Usage

1.  Ensure Team Fortress 2 is installed via Steam.
2.  **Important**: Add `-condebug` to your TF2 launch options (Library -> Right-click TF2 -> Properties -> Launch Options).
3.  Run the executable (`TF2QueueTimer.exe` on Windows, `TF2QueueTimer` on Linux).
4.  The program will run in the system tray.
5.  Launch Team Fortress 2.
6.  Join a casual queue to see the timer in action.

## Linux Notes

This app supports Linux (Ubuntu/Debian and Arch) and expects Steam to be installed in one of the default locations:

- `~/.local/share/Steam`
- `~/.steam/steam`

For automatic focus detection (show overlay only when TF2 is focused), install `xdotool`:

- **Ubuntu/Debian**: `sudo apt install xdotool`
- **Arch**: `sudo pacman -S xdotool`

If `xdotool` is not available, the overlay will stay visible while TF2 is running.

## Build (Linux)

1.  Install dependencies: `pip install -r requirements.txt`
2.  Build with PyInstaller: `python build.py`
3.  Output is in `dist/TF2QueueTimer/`

## Configuration

You can easily adjust the overlay settings directly from the program:

1.  Right-click the **TF2 Queue Timer** icon in your system tray.
2.  Select **Settings...** to open the configuration dialog.
3.  Adjust the following options:
    - **Opacity**: The transparency level of the overlay.
    - **Font Size**: The size of the timer and map text.
    - **Position**: The [X, Y] coordinates of the overlay on your screen.
    - **Wait Period**: Delay in seconds before saving to CSV (allows time for map detection).
    - **Save queue data to CSV**: When enabled, logs each queue session to `queue_log.csv`. (Note: Data is only saved if a map is detected.)

Changes are saved automatically to `settings.json` in the application folder on every save.
