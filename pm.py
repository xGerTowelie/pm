import argparse
import os
import subprocess
import urwid
import git
from termcolor import colored

def run_command(command):
    return subprocess.run(command, capture_output=True, text=True, shell=True).stdout.strip()

def get_repos():
    all_repos = run_command("gh repo list --json name --jq '.[].name'").split('\n')
    existing_repos = os.listdir(os.path.expanduser("~/projects"))
    return [repo for repo in all_repos if repo and repo not in existing_repos]

class CustomCheckBox(urwid.WidgetWrap):
    unchecked_icon = "\uf0c8"  # Nerd Font empty checkbox
    checked_icon = "\uf14a"    # Nerd Font checked checkbox

    def __init__(self, label):
        self.checkbox = urwid.Text(f"{self.unchecked_icon} {label}")
        self.state = False
        self.attr = urwid.AttrMap(self.checkbox, 'normal', 'highlight')
        super().__init__(self.attr)

    def toggle_state(self):
        self.state = not self.state
        icon = self.checked_icon if self.state else self.unchecked_icon
        self.checkbox.set_text(f"{icon} {self.label}")
        if self.state:
            self.attr.set_attr_map({None: 'selected'})
        else:
            self.attr.set_attr_map({None: 'normal'})

    @property
    def label(self):
        return self.checkbox.text.split(" ", 1)[1]

class RepoSelector(urwid.ListBox):
    def __init__(self, repos):
        self.repos = repos
        body = [CustomCheckBox(repo) for repo in repos]
        super().__init__(urwid.SimpleFocusListWalker(body))

    def keypress(self, size, key):
        if key == 'j':
            if self.focus_position < len(self.body) - 1:
                self.focus_position += 1
            return None
        elif key == 'k':
            if self.focus_position > 0:
                self.focus_position -= 1
            return None
        elif key == 'G':
            self.focus_position = len(self.body) - 1
            return None
        elif key == 'g':
            self.focus_position = 0
            return None
        elif key == 'enter':
            self.clone_selected()
            raise urwid.ExitMainLoop()
        elif key == ' ':
            checkbox = self.focus
            if isinstance(checkbox, CustomCheckBox):
                checkbox.toggle_state()
            return None
        elif key == 'q':
            raise urwid.ExitMainLoop()
        return key

    def clone_selected(self):
        for checkbox in self.body:
            if checkbox.state:
                repo = checkbox.label
                print(f"Cloning {repo}...")
                run_command(f"gh repo clone {repo} ~/projects/{repo}")
        print("Cloning completed.")

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
        ('normal', 'light gray', 'black'),
        ('highlight', 'black', 'light gray'),
        ('selected', 'black', 'dark cyan'),
    ]
    loop = CustomMainLoop(selector, palette)
    loop.screen.set_terminal_properties(colors=256)
    loop.run()

# ... (rest of your code remains the same)

def main():
    parser = argparse.ArgumentParser(description="Project Manager")
    parser.add_argument("command", choices=["clone", "status"], help="Command to execute")
    args = parser.parse_args()

    if args.command == "clone":
        clone_repos()
    elif args.command == "status":
        status()

if __name__ == "__main__":
    main()
