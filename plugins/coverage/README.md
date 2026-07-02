# Module Test Coverage

Gates Terraform/OpenTofu **module** pull requests on test coverage.

Spacelift module tests instantiate a module through the `project_root` of each test case in
`.spacelift/config.yml` and apply it. This plugin measures how much of the module's surface those
examples collectively exercise, and denies the run when coverage is too low.

## What it measures

Coverage is computed statically (no `terraform apply` needed) by
[`tfcov`](https://github.com/spacelift-solutions/tfcov), over the union of all the module's
example instantiations.

- **Variable coverage** — the percentage of input variables that at least one example passes a
  value for.
- **Branch coverage** — the percentage of *assessable* branch points (`count`, `for_each`,
  `dynamic`, and conditional expressions) that the examples exercise **both ways** (e.g. a
  `count = var.enabled ? 1 : 0` gate seen both enabled and disabled).

Each branch is evaluated against every example's inputs and classified:

| Status | Meaning |
| --- | --- |
| `covered` | Exercised both ways (proven by evaluation). |
| `uncovered` | Only ever exercised one way. |
| `partial` | One way proven; the other undetermined (heuristic). |
| `unknown` | Depends on values not statically knowable (resource attributes, data sources, module outputs). Excluded from the coverage denominator. |

## Usage

1. Install the plugin.
2. Autoattach it to your modules (it self-discovers each module and its examples from
   `.spacelift/config.yml`, so one instance works for any number of modules).

The coverage report is attached to the run's policy input at
`input.third_party_metadata.custom.coverage`, and a summary is posted to the run.

## Parameters

| Parameter | Default | Description |
| --- | --- | --- |
| Mode | `absolute` | `absolute` fails below fixed thresholds; `ratchet` fails when coverage drops below the base ref. |
| Minimum Variable Coverage | `80` | Absolute mode: variable-coverage floor (%). |
| Minimum Branch Coverage | `70` | Absolute mode: branch-coverage floor (%). |
| Fail On | `block` | `block` denies the run; `warn` only reports. |
| Base Ref | *(empty)* | Ratchet mode: git ref to compare against. Empty auto-detects the module's tracked branch, then the previous commit. |

## Limitations

- **`.tf.json` is not supported.** A module authored in JSON is rejected loudly (rather than
  silently undercounted).
- **Override files** (`*_override.tf`) are merged for the cases that affect coverage — variable
  defaults, locals, and `count`/`for_each` — but deep per-argument body merging is not performed.
- **Ratchet requires fetchable git history.** If the base ref can't be resolved (e.g. a shallow
  clone), the ratchet comparison is skipped rather than failing the run.
- **Function support is a curated subset** of Terraform/OpenTofu built-ins. A branch whose
  condition uses an unsupported function is marked `unknown` — never scored incorrectly.

## Development

The coverage analysis is done by [`tfcov`](https://github.com/spacelift-solutions/tfcov), a
standalone tool that also works outside Spacelift via `--examples`/`--module-root`. This plugin
downloads its release binaries at run time, pinned to the version in `plugin.py`. To pick up a new
tfcov release, bump `_TFCOV_VERSION` and regenerate the manifest:

```sh
python -m spaceforge generate plugin.py -o plugin.yaml
```
