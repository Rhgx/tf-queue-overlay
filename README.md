# TF2 Queue Timer

A simple overlay utility for Team Fortress 2 that tracks how long you have been queueing for a match.

> [!NOTE]
> Windows may flag this program as suspicious because it is not digitally signed. You can verify that the file is safe by checking it on VirusTotal:
> [VirusTotal Scan Result](https://www.virustotal.com/gui/file-analysis/MTlmOTZlZTRkODI2YWQwOWZmM2E2NTUyYzVjZWU5OWU6MTc2ODc0NjkyNQ==)

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

You can easily adjust the overlay settings directly from the program:

1.  Right-click the **TF2 Queue Timer** icon in your system tray.
2.  Select **Settings...** to open the configuration dialog.
3.  Adjust the following options:
    - **Opacity**: The transparency level of the overlay.
    - **Font Size**: The size of the timer and map text.
    - **Position**: The [X, Y] coordinates of the overlay on your screen.

Changes are saved automatically to `settings.json` in the application folder on every save.
