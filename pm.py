import argparse
import os
import subprocess
import urwid
import git

def run_command(command):
    return subprocess.run(command, capture_output=True, text=True, shell=True).stdout.strip()

def get_repos():
    all_repos = run_command("gh repo list --json name --jq '.[].name'").split('\n')
    existing_repos = os.listdir(os.path.expanduser("~/projects"))
    return [repo for repo in all_repos if repo and repo not in existing_repos]

class CustomCheckBox(urwid.WidgetWrap):
    def __init__(self, label):
        self.checkbox = urwid.CheckBox(label)
        self.attr = urwid.AttrMap(self.checkbox, 'normal', 'highlight')
        super().__init__(self.attr)

    @property
    def state(self):
        return self.checkbox.state

    def toggle_state(self):
        self.checkbox.toggle_state()

    def set_state(self, state):
        self.checkbox.set_state(state)

    @property
    def label(self):
        return self.checkbox.label

class RepoSelector(urwid.ListBox):
    def __init__(self, repos):
        self.repos = repos
        body = [CustomCheckBox(repo) for repo in repos]
        super().__init__(urwid.SimpleFocusListWalker(body))

    def keypress(self, size, key):
        if key in ('j', 'k'):
            return super().keypress(size, 'down' if key == 'j' else 'up')
        elif key == 'G':
            self.set_focus(len(self.body) - 1)
            self._invalidate()
        elif key == 'g':
            if self._command_map[key] == 'cursor max':
                self.set_focus(0)
                self._invalidate()
            else:
                return key
        elif key == 'enter':
            self.clone_selected()
            raise urwid.ExitMainLoop()
        elif key == ' ':
            checkbox = self.focus
            if isinstance(checkbox, CustomCheckBox):
                checkbox.toggle_state()
            return None
        return super().keypress(size, key)

    def clone_selected(self):
        for checkbox in self.body:
            if checkbox.state:
                repo = checkbox.label
                print(f"Cloning {repo}...")
                run_command(f"gh repo clone {repo} ~/projects/{repo}")
        print("Cloning completed.")

def clone_repos():
    repos = get_repos()
    selector = RepoSelector(repos)
    palette = [
        ('normal', 'light gray', 'black'),
        ('highlight', 'black', 'light gray'),
        ('selected', 'black', 'dark cyan'),
    ]
    loop = urwid.MainLoop(selector, palette)
    loop.run()

def get_repo_status(repo_path):
    repo = git.Repo(repo_path)
    if repo.is_dirty():
        return "UNCOMMITTED"
    if repo.head.is_detached:
        return "DETACHED HEAD"
    branch = repo.active_branch
    if not branch.tracking_branch():
        return "NO REMOTE TRACKING BRANCH"
    commits_behind = list(repo.iter_commits(f'{branch.name}..{branch.tracking_branch().name}'))
    commits_ahead = list(repo.iter_commits(f'{branch.tracking_branch().name}..{branch.name}'))
    if commits_ahead or commits_behind:
        return "UNSYNCED"
    return "OK"

def status():
    projects_dir = os.path.expanduser("~/projects")
    for repo_name in os.listdir(projects_dir):
        repo_path = os.path.join(projects_dir, repo_name)
        if os.path.isdir(repo_path) and os.path.exists(os.path.join(repo_path, '.git')):
            status = get_repo_status(repo_path)
            print(f"{repo_name}: {status}")

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
