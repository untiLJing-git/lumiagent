"""Collect eval-suite public-suite metadata into local cache and public indexes."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import urllib.request
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
RAW = REPO / ".lumiagent" / "sources"
REPOS = RAW / "repos"
CACHE = RAW / "raw"
PUBLIC = REPO / "benchmarks" / "eval-suite" / "sources"
PYDEPS = REPO / ".lumiagent" / "pydeps"
USER_AGENT = "lumiagent-source-collect/0.1"

SWE_REPO_LICENSES = {
    "astropy/astropy": "BSD-3-Clause",
    "django/django": "BSD-3-Clause",
    "matplotlib/matplotlib": "PSF-based",
    "mwaskom/seaborn": "BSD-3-Clause",
    "pallets/flask": "BSD-3-Clause",
    "psf/requests": "Apache-2.0",
    "pydata/xarray": "Apache-2.0",
    "pylint-dev/pylint": "GPL-2.0-or-later",
    "pytest-dev/pytest": "MIT",
    "scikit-learn/scikit-learn": "BSD-3-Clause",
    "sphinx-doc/sphinx": "BSD-2-Clause",
    "sympy/sympy": "BSD-3-Clause",
}

MULTI_SWE_REPO_LICENSES = {
    "cli/cli": "MIT",
    "grpc/grpc-go": "Apache-2.0",
    "fmtlib/fmt": "MIT",
    "nlohmann/json": "MIT",
    "axios/axios": "MIT",
    "expressjs/express": "MIT",
    "iamkun/dayjs": "MIT",
    "sveltejs/svelte": "MIT",
    "clap-rs/clap": "MIT OR Apache-2.0",
    "serde-rs/serde": "MIT OR Apache-2.0",
    "tokio-rs/tokio": "MIT",
    "vuejs/core": "MIT",
    "mui/material-ui": "MIT",
    "mockito/mockito": "MIT",
    "BurntSushi/ripgrep": "MIT OR Unlicense",
    "facebook/zstd": "BSD-3-Clause OR GPL-2.0",
}

DOWNLOADS = [
    (
        "swe_bench_verified.parquet",
        "https://huggingface.co/datasets/SWE-bench/SWE-bench_Verified/resolve/main/data/test-00000-of-00001.parquet",
    ),
    (
        "swe_bench_pro.parquet",
        "https://huggingface.co/datasets/ScaleAI/SWE-bench_Pro/resolve/main/data/test-00000-of-00001.parquet",
    ),
    (
        "multi_swe_bench_mini.jsonl",
        "https://huggingface.co/datasets/ByteDance-Seed/Multi-SWE-bench_mini/resolve/main/multi_swe_bench_mini.jsonl",
    ),
    (
        "swe_bench_live_lite.parquet",
        "https://huggingface.co/datasets/SWE-bench-Live/SWE-bench-Live/resolve/main/data/lite-00000-of-00001.parquet",
    ),
    (
        "swe_bench_live_verified.parquet",
        "https://huggingface.co/datasets/SWE-bench-Live/SWE-bench-Live/resolve/main/data/verified-00000-of-00001.parquet",
    ),
]

CLONES = [
    {
        "name": "mcpmark",
        "url": "https://github.com/eval-sys/mcpmark.git",
        "sparse": [
            "/LICENSE",
            "/README.md",
            "/docs/mcp/postgres.md",
            "/docs/mcp/filesystem.md",
            "/tasks/postgres/",
            "/tasks/filesystem/",
        ],
    },
    {
        "name": "mcp-universe",
        "url": "https://github.com/SalesforceAIResearch/MCP-Universe.git",
        "sparse": ["/LICENSE", "/README.md", "/mcpuniverse/benchmark/configs/"],
    },
    {
        "name": "mcp-bench",
        "url": "https://github.com/Accenture/mcp-bench.git",
        "sparse": ["/LICENSE", "/README.md", "/tasks/"],
    },
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        print(f"skip existing {dest.name} ({dest.stat().st_size} bytes)")
        return
    print(f"download {dest.name}")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=300) as response:
        tmp = dest.with_suffix(dest.suffix + ".part")
        with tmp.open("wb") as handle:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
        tmp.replace(dest)


def git_sparse_clone(name: str, url: str, sparse: list[str]) -> Path:
    dest = REPOS / name
    if (dest / ".git").exists():
        print(f"skip existing clone {name}")
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"clone {name}")
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse", url, str(dest)],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(dest), "sparse-checkout", "set", "--no-cone", *sparse],
            check=True,
        )
    except subprocess.CalledProcessError:
        if dest.exists():
            shutil.rmtree(dest, ignore_errors=True)
        subprocess.run(["git", "clone", "--depth", "1", url, str(dest)], check=True)
    return dest


def ensure_pyarrow() -> None:
    if str(PYDEPS) not in sys.path and PYDEPS.exists():
        sys.path.insert(0, str(PYDEPS))
    try:
        import pyarrow.parquet  # noqa: F401
        return
    except ImportError:
        pass
    print("install pyarrow into .lumiagent/pydeps")
    PYDEPS.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--target", str(PYDEPS), "pyarrow"],
        check=True,
    )
    if str(PYDEPS) not in sys.path:
        sys.path.insert(0, str(PYDEPS))


def patch_files(patch: str | None) -> list[str]:
    if not patch:
        return []
    return re.findall(r"(?m)^diff --git a/(.+?) b/", patch)


def parse_json_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    text = str(value).strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return [text]
    if isinstance(parsed, list):
        return [str(item) for item in parsed]
    return [str(parsed)]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def index_parquet(src: Path, public_fields: Callable[[dict], dict]) -> list[dict]:
    import pyarrow.parquet as pq

    table = pq.read_table(src)
    rows = []
    for batch in table.to_batches(max_chunksize=64):
        for record in batch.to_pylist():
            rows.append(public_fields(record))
    return rows


def swe_verified_row(record: dict) -> dict:
    repo = record.get("repo") or ""
    files = patch_files(record.get("patch"))
    return {
        "instance_id": record.get("instance_id"),
        "repo": repo,
        "version": record.get("version"),
        "created_at": record.get("created_at"),
        "difficulty": record.get("difficulty"),
        "repo_license": SWE_REPO_LICENSES.get(repo, "see-upstream-repo"),
        "n_fail_to_pass": len(parse_json_list(record.get("FAIL_TO_PASS"))),
        "n_pass_to_pass": len(parse_json_list(record.get("PASS_TO_PASS"))),
        "n_patch_files": len(files),
        "patch_bytes": len((record.get("patch") or "").encode("utf-8")),
        "problem_chars": len(record.get("problem_statement") or ""),
    }


def swe_pro_row(record: dict) -> dict:
    repo = record.get("repo") or ""
    files = patch_files(record.get("patch"))
    return {
        "instance_id": record.get("instance_id"),
        "repo": repo,
        "repo_language": record.get("repo_language"),
        "issue_categories": record.get("issue_categories"),
        "n_patch_files": len(files),
        "patch_bytes": len((record.get("patch") or "").encode("utf-8")),
        "problem_chars": len(record.get("problem_statement") or ""),
        "source_repo_license": "copyleft-GPL-family (do not vendor tree)",
    }


def swe_live_row(record: dict) -> dict:
    repo = record.get("repo") or ""
    files = patch_files(record.get("patch"))
    return {
        "instance_id": record.get("instance_id"),
        "repo": repo,
        "created_at": record.get("created_at"),
        "n_patch_files": len(files),
        "patch_bytes": len((record.get("patch") or "").encode("utf-8")),
        "problem_chars": len(record.get("problem_statement") or ""),
    }


def index_multi_swe(src: Path) -> list[dict]:
    rows = []
    with src.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            org = record.get("org") or ""
            repo = record.get("repo") or ""
            slug = f"{org}/{repo}"
            files = patch_files(record.get("fix_patch"))
            rows.append(
                {
                    "instance_id": record.get("instance_id"),
                    "org": org,
                    "repo": repo,
                    "number": record.get("number"),
                    "title": record.get("title"),
                    "n_resolved_issues": len(record.get("resolved_issues") or []),
                    "n_patch_files": len(files),
                    "patch_bytes": len((record.get("fix_patch") or "").encode("utf-8")),
                    "repo_license": MULTI_SWE_REPO_LICENSES.get(slug, "see-upstream-repo"),
                }
            )
    return rows


def mcpmark_tasks(root: Path, family: str) -> list[dict]:
    tasks_root = root / "tasks" / family
    rows = []
    for meta in tasks_root.rglob("meta.json"):
        data = json.loads(meta.read_text(encoding="utf-8"))
        rel = meta.parent.relative_to(tasks_root).as_posix()
        description = meta.parent / "description.md"
        title = (data.get("task_name") or data.get("task_id") or rel).strip()
        first_line = ""
        if description.exists():
            for line in description.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    first_line = line.strip().lstrip("#").strip()
                    break
        rows.append(
            {
                "task_id": data.get("task_id") or meta.parent.name,
                "path": rel,
                "family": family,
                "difficulty": data.get("difficulty"),
                "tags": data.get("tags") or [],
                "title": title,
                "summary": first_line,
            }
        )
    rows.sort(key=lambda row: row["path"])
    return rows


PAGINATION_RE = re.compile(
    r"(pagination|paginated|page_size|per[_ -]?page|next[_ -]?page|"
    r"\boffset\b|\bcursor\b|fetch all pages|list all (issues|prs|pull requests|results|items))",
    re.I,
)
ISSUE_ENUM_RE = re.compile(
    r"(open issues|closed issues|count (the )?(number of )?(open |closed )?issues|for each (amazing )?repository)",
    re.I,
)


def universe_index(root: Path) -> tuple[list[dict], list[dict]]:
    configs = root / "mcpuniverse" / "benchmark" / "configs" / "mcpuniverse"
    rows = []
    patterns = []
    if not configs.exists():
        return rows, patterns
    for path in sorted(configs.rglob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        rel = path.relative_to(configs).as_posix()
        question = data.get("question") or ""
        servers = [item.get("name") for item in (data.get("mcp_servers") or []) if isinstance(item, dict)]
        row = {
            "path": rel,
            "category": data.get("category"),
            "servers": servers,
            "question_chars": len(question),
        }
        rows.append(row)
        if PAGINATION_RE.search(question) or PAGINATION_RE.search(rel):
            reason = "pagination-keyword"
        elif "repository_management" in rel and ISSUE_ENUM_RE.search(question):
            reason = "github-issue-enumeration"
        else:
            reason = None
        if reason:
            patterns.append(
                {
                    "path": rel,
                    "category": data.get("category"),
                    "servers": servers,
                    "reason": reason,
                    "question_excerpt": question[:240],
                }
            )
    return rows, patterns


def mcp_bench_index(root: Path) -> list[dict]:
    tasks_dir = root / "tasks"
    rows = []
    if not tasks_dir.exists():
        return rows
    for path in sorted(tasks_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for server in data.get("server_tasks") or []:
            server_name = server.get("server_name")
            for task in server.get("tasks") or []:
                desc = task.get("task_description") or ""
                rows.append(
                    {
                        "file": path.name,
                        "server_name": server_name,
                        "task_id": task.get("task_id"),
                        "pagination": bool(PAGINATION_RE.search(desc)),
                        "description_chars": len(desc),
                    }
                )
    return rows


def pick_coding_bug(rows: list[dict]) -> dict:
    preferred_repos = {
        "psf/requests",
        "pallets/flask",
        "pytest-dev/pytest",
        "mwaskom/seaborn",
        "pydata/xarray",
    }
    preferred_licenses = {"MIT", "Apache-2.0", "BSD-3-Clause", "BSD-2-Clause"}

    def easy(row: dict) -> bool:
        difficulty = str(row.get("difficulty") or "").lower()
        return "15" in difficulty or "easy" in difficulty

    ranked = [
        row
        for row in rows
        if row["repo"] in preferred_repos
        and row["repo_license"] in preferred_licenses
        and easy(row)
        and 1 <= row["n_patch_files"] <= 3
        and row["n_fail_to_pass"] <= 5
        and row["patch_bytes"] <= 8000
    ]
    if not ranked:
        ranked = [
            row
            for row in rows
            if row["repo_license"] in preferred_licenses
            and easy(row)
            and row["n_patch_files"] <= 3
            and row["n_fail_to_pass"] <= 5
            and "django/django" not in row["repo"]
            and "pylint" not in row["repo"]
        ]
    ranked.sort(key=lambda row: (row["patch_bytes"], row["n_fail_to_pass"], row["instance_id"]))
    if not ranked:
        raise RuntimeError("no SWE-bench Verified instance matched A1 filters")
    return ranked[0]


def pick_combined_issue(rows: list[dict], exclude: dict) -> dict:
    preferred_licenses = {"MIT", "Apache-2.0", "BSD-3-Clause", "BSD-2-Clause"}

    def easy(row: dict) -> bool:
        difficulty = str(row.get("difficulty") or "").lower()
        return "15" in difficulty or "easy" in difficulty

    ranked = [
        row
        for row in rows
        if row["instance_id"] != exclude["instance_id"]
        and row["repo"] != exclude["repo"]
        and row["repo"] in {"pytest-dev/pytest", "psf/requests", "mwaskom/seaborn", "pydata/xarray"}
        and row["repo_license"] in preferred_licenses
        and easy(row)
        and row["n_patch_files"] <= 4
    ]
    ranked.sort(key=lambda row: (row["patch_bytes"], row["n_fail_to_pass"], row["instance_id"]))
    if not ranked:
        raise RuntimeError("no second SWE-bench Verified instance matched combined_context filters")
    return ranked[0]


def pick_coding_interface(rows: list[dict]) -> dict:
    interface_hint = re.compile(
        r"(interface|overload|iterator|template|intoiterator|breaking|fix!:|feat\([^)]+\):|api)",
        re.I,
    )
    preferred = [
        row
        for row in rows
        if 3 <= row["n_patch_files"] <= 10
        and row["patch_bytes"] <= 40000
        and f"{row['org']}/{row['repo']}" in MULTI_SWE_REPO_LICENSES
        and "GPL" not in row["repo_license"]
    ]
    if not preferred:
        raise RuntimeError("no Multi-SWE mini instance matched A1 filters")
    preferred.sort(
        key=lambda row: (
            0 if interface_hint.search(row["title"] or "") else 1,
            row["patch_bytes"],
            row["instance_id"],
        )
    )
    return preferred[0]


def main() -> int:
    CACHE.mkdir(parents=True, exist_ok=True)
    PUBLIC.mkdir(parents=True, exist_ok=True)
    for filename, url in DOWNLOADS:
        download(url, CACHE / filename)
    for spec in CLONES:
        git_sparse_clone(spec["name"], spec["url"], spec["sparse"])

    ensure_pyarrow()
    verified = index_parquet(CACHE / "swe_bench_verified.parquet", swe_verified_row)
    pro = index_parquet(CACHE / "swe_bench_pro.parquet", swe_pro_row)
    live_lite = index_parquet(CACHE / "swe_bench_live_lite.parquet", swe_live_row)
    live_verified = index_parquet(CACHE / "swe_bench_live_verified.parquet", swe_live_row)
    mini = index_multi_swe(CACHE / "multi_swe_bench_mini.jsonl")
    postgres = mcpmark_tasks(REPOS / "mcpmark", "postgres")
    filesystem = mcpmark_tasks(REPOS / "mcpmark", "filesystem")
    universe_tasks, pagination = universe_index(REPOS / "mcp-universe")
    bench_tasks = mcp_bench_index(REPOS / "mcp-bench")

    write_jsonl(PUBLIC / "swe_bench_verified" / "index.jsonl", verified)
    write_jsonl(PUBLIC / "swe_bench_pro" / "pointers.jsonl", pro)
    write_jsonl(PUBLIC / "swe_bench_live" / "lite_index.jsonl", live_lite)
    write_jsonl(PUBLIC / "swe_bench_live" / "verified_index.jsonl", live_verified)
    write_jsonl(PUBLIC / "multi_swe_bench_mini" / "index.jsonl", mini)
    (PUBLIC / "mcpmark" / "postgres_tasks.json").parent.mkdir(parents=True, exist_ok=True)
    (PUBLIC / "mcpmark" / "postgres_tasks.json").write_text(
        json.dumps(postgres, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (PUBLIC / "mcpmark" / "filesystem_tasks.json").write_text(
        json.dumps(filesystem, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (PUBLIC / "mcp_universe" / "task_index.jsonl").parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(PUBLIC / "mcp_universe" / "task_index.jsonl", universe_tasks)
    (PUBLIC / "mcp_universe" / "pagination_patterns.json").write_text(
        json.dumps(pagination, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (PUBLIC / "mcp_bench" / "task_index.json").parent.mkdir(parents=True, exist_ok=True)
    (PUBLIC / "mcp_bench" / "task_index.json").write_text(
        json.dumps(bench_tasks, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    coding_bug = pick_coding_bug(verified)
    combined_issue = pick_combined_issue(verified, coding_bug)
    coding_interface = pick_coding_interface(mini)
    pagination_refs = [row["path"] for row in pagination if row.get("reason") == "github-issue-enumeration"][:6]
    if not pagination_refs:
        pagination_refs = [row["path"] for row in pagination[:6]]
    bench_pagination = [row["task_id"] for row in bench_tasks if row.get("pagination")][:8]
    selection = {
        "status": "instances_selected_not_task_assets",
        "selected_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "split_note": "A1 six tasks are development-set candidates; holdout grouping waits for the 24-task expansion.",
        "tasks": {
            "coding_bug_001": {
                "suite": "SWE-bench Verified",
                "instance_id": coding_bug["instance_id"],
                "repo": coding_bug["repo"],
                "repo_license": coding_bug["repo_license"],
                "difficulty": coding_bug["difficulty"],
                "n_patch_files": coding_bug["n_patch_files"],
                "n_fail_to_pass": coding_bug["n_fail_to_pass"],
            },
            "coding_interface_001": {
                "suite": "Multi-SWE-bench mini",
                "instance_id": coding_interface["instance_id"],
                "repo": f"{coding_interface['org']}/{coding_interface['repo']}",
                "repo_license": coding_interface["repo_license"],
                "n_patch_files": coding_interface["n_patch_files"],
                "title": coding_interface["title"],
            },
            "mcp_pagination_001": {
                "suite": "MCP-Universe pattern + local frozen seed",
                "pattern_tasks": pagination_refs,
                "a2_pagination_refs": bench_pagination,
                "local_seed": "not_built_yet",
                "note": "Do not call live web/GitHub APIs. Freeze a local pageable catalog in A1. MCP-Bench pagination tasks are A2 references only.",
            },
            "mcp_update_001": {
                "suite": "MCPMark PostgreSQL",
                "task_id": "update_employee_info",
                "path": "easy/chinook/update_employee_info",
                "sample_db": "chinook",
                "upstream_license": "Apache-2.0",
            },
            "combined_context_001": {
                "suite": "Filesystem MCP + SWE-style issue",
                "mcp_server": "@modelcontextprotocol/server-filesystem",
                "issue_instance_id": combined_issue["instance_id"],
                "issue_repo": combined_issue["repo"],
                "repo_license": combined_issue["repo_license"],
                "note": "Issue text is Agent-visible via filesystem MCP; hidden tests stay off the workspace.",
            },
            "combined_readonly_001": {
                "suite": "MCPMark Filesystem (read-only adaptation)",
                "task_id": "structure_analysis",
                "path": "easy/folder_structure/structure_analysis",
                "upstream_license": "Apache-2.0",
                "note": "Mount source tree read-only. Writing existing files is a hard-constraint failure.",
            },
        },
    }
    (PUBLIC / "a1_selection.json").write_text(
        json.dumps(selection, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    inventory = {
        "collected_at": selection["selected_at"],
        "raw_root": str(RAW),
        "downloads": {
            name: {
                "bytes": (CACHE / name).stat().st_size,
                "sha256": sha256_file(CACHE / name),
            }
            for name, _url in DOWNLOADS
        },
        "clones": {
            spec["name"]: {
                "commit": subprocess.check_output(
                    ["git", "-C", str(REPOS / spec["name"]), "rev-parse", "HEAD"],
                    text=True,
                ).strip()
            }
            for spec in CLONES
        },
        "public_counts": {
            "swe_bench_verified": len(verified),
            "swe_bench_pro_pointers": len(pro),
            "swe_bench_live_lite": len(live_lite),
            "swe_bench_live_verified": len(live_verified),
            "multi_swe_bench_mini": len(mini),
            "mcpmark_postgres": len(postgres),
            "mcpmark_filesystem": len(filesystem),
            "mcp_universe_tasks": len(universe_tasks),
            "mcp_universe_pagination_patterns": len(pagination),
            "mcp_bench_tasks": len(bench_tasks),
        },
    }
    (PUBLIC / "inventory.json").write_text(
        json.dumps(inventory, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(inventory["public_counts"], indent=2))
    print("selected", selection["tasks"]["coding_bug_001"]["instance_id"])
    print("selected", selection["tasks"]["coding_interface_001"]["instance_id"])
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"command failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
    except Exception as exc:
        print(f"collect failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
