# Python Resequencer

I basically only made this for a super niche specific "problem" and i just figured it would be a cool thing with python. nothing more, and probably not that useful.

Vanilla Python tool for resequencing list IDs.


It supports these ID styles:

```txt
[s0001] placeholder text,
[d003X] placeholder text,
[o9999] placeholder text,
id: "s0001",
id: 'd0001',
```

The `s`, `d`, and `o` counters are independent. Each prefix starts at `0001` and is resequenced in the order it appears in the file.

## Usage

Requires Python 3. No third-party packages are needed.

Create a new resequenced file:

```powershell
python resequencer.py first_example.txt
```

This writes:

```txt
first_example.resequenced.txt
```

Overwrite the original file:

```powershell
python resequencer.py first_example.txt --in-place
```

Overwrite the original and keep a backup:

```powershell
python resequencer.py first_example.txt --in-place --backup
```

Preview without writing anything:

```powershell
python resequencer.py first_example.txt --dry-run
```

Write to a specific output file:

```powershell
python resequencer.py first_example.txt --output fixed_list.txt
```

## Windows Launcher

You can also run:

```powershell
run_resequencer.bat first_example.txt
```

Or drag a text file onto `run_resequencer.bat`.

## Verification

After resequencing, the tool checks the output in memory before writing.

It verifies:

```txt
s0001 -> s0002 -> s0003 -> ...
d0001 -> d0002 -> d0003 -> ...
o0001 -> o0002 -> o0003 -> ...
```

If verification fails, no file is written.

The report is console-only. It is never added to the output file.
