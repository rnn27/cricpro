# Git in plain words

- **Repository (repo):** the project folder plus its full history.
- **Commit:** a saved snapshot with a note. You can return to any of them.
- **Push:** upload your commits to GitHub (the online backup).
- **Tag:** a name on a milestone commit, e.g. `v0.1.1`.

The routine, from the inner `cricpro` folder:

    git status                 # what changed since the last snapshot?
    git add -A                 # include all those changes in the next snapshot
    git commit -m "what I did" # take the snapshot
    git push                   # upload it

Useful:

    git log --oneline          # list of snapshots
    git diff                   # exactly what changed (before add)
    git restore <file>         # throw away your changes to a file

The messages about "LF will be replaced by CRLF" on Windows are harmless line-ending notices.
