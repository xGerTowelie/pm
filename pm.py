import argparse
import os
import subprocess
import threading
import urwid
import time


def run_command(command):
    result = subprocess.run(command, capture_output=True, text=True, shell=True)
    return result.stdout.strip(), result.returncode  # Return both output and exit status


def get_repos():
    all_repos = run_command("gh repo list --json name --jq '.[].name'")[0].split('\n')
    existing_repos = os.listdir(os.path.expanduser("~/projects"))
    return [repo for repo in all_repos if repo and repo not in existing_repos]


class CustomCheckBox(urwid.WidgetWrap):
    unchecked_icon = "\uf0c8"  # Nerd Font empty checkbox
    checked_icon = "\uf14a"    # Nerd Font checked checkbox
    spinner_frames = ["\U000f0a9f", "\U000f0aa0", "\U000f0aa1", "\U000f0aa2", "\U000f0aa3", "\U000f0aa4","\U000f0aa5" ]  # Spinner frames
    
    success_color = 'light green'  # Background color for success

    def __init__(self, label):
        self.checkbox = urwid.Text(f"{self.unchecked_icon} {label}")
        self.state = False
        self.cloning = False
        self.cloned = False  # Track if this repo has already been cloned
        self.spinner_index = 0  # Index for spinner frames
        self.attr = urwid.AttrMap(self.checkbox, 'normal', 'highlight')
        super().__init__(self.attr)
        self.update_timer = None  # Timer reference for spinner animation

    def toggle_state(self):
        if not self.cloned:  # Only allow toggling if not cloned
            self.state = not self.state
            icon = self.checked_icon if self.state else self.unchecked_icon
            self.checkbox.set_text(f"{icon} {self.label}")
            if self.state:
                self.attr.set_attr_map({None: 'selected'})
            else:
                self.attr.set_attr_map({None: 'normal'})

    @property
    def label(self):
        return self.checkbox.text.split(" ", 1)[1].split(" (cloning...)")[0]

    def set_cloning(self):
        """Indicate that the repo is being cloned with an animated spinner."""
        self.cloning = True
        self.start_spinner()
        self.checkbox.set_text(f"{self.spinner_frames[self.spinner_index]} {self.label} (cloning...)")
        self.attr.set_attr_map({None: 'highlight'})  # Change background color if needed

    def start_spinner(self):
        """Start the spinner animation."""
        if self.update_timer:
            self.update_timer.cancel()  # Cancel any existing timer
        self.update_timer = threading.Timer(0.1, self.animate_spinner)
        self.update_timer.start()

    def animate_spinner(self):
        """Update spinner frame."""
        if self.cloning:
            self.spinner_index = (self.spinner_index + 1) % len(self.spinner_frames)
            self.checkbox.set_text(f"{self.spinner_frames[self.spinner_index]} {self.label} (cloning...)")
            self._redraw()
            self.start_spinner()

    def set_cloned(self):
        """Mark the repo as cloned with a checkmark."""
        self.cloning = False
        self.cloned = True  # Mark this repo as cloned
        if self.update_timer:
            self.update_timer.cancel()  # Stop the spinner animation
        self.checkbox.set_text(f"{self.checked_icon} {self.label} (cloned)")
        self.attr.set_attr_map({None: 'success'})  # Set background color to success

    def set_error(self):
        """Mark the repo as errored with a message."""
        self.cloning = False
        if self.update_timer:
            self.update_timer.cancel()  # Stop the spinner animation
        self.checkbox.set_text(f"{self.unchecked_icon} {self.label} (error)")
        self.attr.set_attr_map({None: 'error'})  # Set a special style for errors

    def _redraw(self):
        """Force the widget to redraw."""
        self.attr.set_attr_map(self.attr.attr_map)  # Update the widget display


class RepoSelector(urwid.ListBox):
    def __init__(self, repos):
        self.repos = repos
        self.body = [CustomCheckBox(repo) for repo in repos]
        self.filtered_body = urwid.SimpleFocusListWalker(self.body)
        super().__init__(self.filtered_body)
        self.update_loop = None  # Reference to the update loop

    def keypress(self, size, key):
        if key == 'j':
            self.move_focus(1)
            return None
        elif key == 'k':
            self.move_focus(-1)
            return None
        elif key == 'G':
            self.focus_position = len(self.filtered_body) - 1
            return None
        elif key == 'g':
            self.focus_position = 0
            return None
        elif key == 'enter':
            self.clone_selected()
            return None
        elif key == ' ':
            checkbox = self.focus
            if isinstance(checkbox, CustomCheckBox):
                checkbox.toggle_state()
            return None
        elif key == 'q':
            raise urwid.ExitMainLoop()
        return key

    def move_focus(self, direction):
        """Move focus while skipping cloned repositories."""
        current_pos = self.focus_position
        new_pos = current_pos + direction
        while 0 <= new_pos < len(self.filtered_body):
            if not self.filtered_body[new_pos].cloned:
                self.focus_position = new_pos
                break
            new_pos += direction
        return None

    def clone_selected(self):
        """Clone selected repos sequentially and update UI."""
        for checkbox in self.body:
            if checkbox.state and not checkbox.cloned:  # Check if repo is selected and not already cloned
                threading.Thread(target=self.clone_repo, args=(checkbox,)).start()

    def clone_repo(self, checkbox):
        """Handle cloning of an individual repo."""
        checkbox.set_cloning()  # Mark as "cloning..."
        self._redraw()  # Force a redraw to update the UI immediately

        repo = checkbox.label
        _, exit_code = run_command(f"gh repo clone {repo} ~/projects/{repo}")

        if exit_code == 0:
            checkbox.set_cloned()  # Mark as "cloned"
        else:
            checkbox.set_error()  # Mark as "error"
        self._redraw()  # Update UI again after cloning

    def _redraw(self):
        """Force the ListBox to redraw the UI."""
        if self.update_loop:
            self.update_loop.set_alarm_in(0.1, self._force_redraw)

    def _force_redraw(self, loop, data):
        self._invalidate()  # Redraw the listbox
        loop.set_alarm_in(0.1, self._force_redraw)  # Continue updating periodically


class CustomMainLoop(urwid.MainLoop):
    def process_input(self, keys):
        for k in keys:
            if k == 'j':
                self.widget.keypress((0,), 'j')
            elif k == 'k':
                self.widget.keypress((0,), 'k')
            else:
                super().process_input([k])


def clone_repos():
    repos = get_repos()
    selector = RepoSelector(repos)
    palette = [
        ('normal', 'light gray', 'default'),  # Use terminal's background
        ('highlight', 'black', 'light gray'),
        ('selected', 'black', 'dark cyan'),
        ('success', 'light green', 'default'),  # Background color for success
        ('error', 'black', 'dark red'),  # Special color for error state
    ]
    loop = CustomMainLoop(selector, palette)
    selector.update_loop = loop  # Provide reference to the main loop for updates
    loop.set_alarm_in(0.1, selector._force_redraw)  # Start periodic redraws
    loop.screen.set_terminal_properties(colors=256)
    loop.run()


# The main function that handles the command-line arguments and runs the app
def main():
    parser = argparse.ArgumentParser(description="Project Manager")
    parser.add_argument("command", choices=["clone", "status"], help="Command to execute")
    args = parser.parse_args()

    if args.command == "clone":
        clone_repos()
    elif args.command == "status":
        status()  # This is a placeholder, assuming there's a 'status' function defined elsewhere


if __name__ == "__main__":
    main()

