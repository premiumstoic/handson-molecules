"""Summarize user study logs (T11).

    python scripts/analyze_logs.py                 # reads logs/, writes results/
    python scripts/analyze_logs.py --logs study_logs --out results

Writes results/tasks.csv (one row per participant, condition and task) and
results/summary.md (tables for the report), and prints the summary.
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from handson.analysis import markdown_report, read_logs, write_task_csv  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--logs", type=Path, default=ROOT / "logs")
    parser.add_argument("--out", type=Path, default=ROOT / "results")
    args = parser.parse_args()

    results = read_logs(args.logs)
    if not results:
        sys.exit(f"No study sessions in {args.logs} (only sessions started with --participant are used).")
    write_task_csv(results, args.out / "tasks.csv")
    report = markdown_report(results)
    (args.out / "summary.md").write_text(report)
    print(report)
    print(f"Wrote {args.out / 'tasks.csv'} and {args.out / 'summary.md'}")


if __name__ == "__main__":
    main()
